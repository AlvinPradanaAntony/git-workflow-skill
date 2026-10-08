#!/usr/bin/env python3
"""Validate, build and verify Git Workflow release assets using native runners."""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("windows", "linux", "macos")
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?\Z"
)
COMMIT_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class ReleaseError(ValueError):
    """A release validation failed; publication must stop."""


def version_value(value: str) -> str:
    match = SEMVER.fullmatch(value)
    if not match or any(
        part.isdigit() and len(part) > 1 and part.startswith("0")
        for part in (match.group(4) or "").split(".")
    ):
        raise ReleaseError(f"Invalid SemVer: {value!r}; use a version without a v prefix")
    return value


def constant(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    values = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    ]
    if len(values) != 1 or not isinstance(values[0], str):
        raise ReleaseError(f"{path.name} must contain one literal string {name}")
    return values[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_metadata(root: Path) -> dict[str, str]:
    required = (
        "git_workflow.py", "CHANGELOG.md",
        "README.md", "Panduan-Git-Workflow.md", "requirements-build.txt",
        "scripts/install-cli.ps1", "scripts/install-cli.sh",
    )
    for name in required:
        if not (root / name).is_file():
            raise ReleaseError(f"Python CLI project is missing {name}")
    source = root / "git_workflow.py"
    version = version_value(constant(source, "VERSION"))
    banner = root / "assets/banner/ASCIILogo.txt"
    if banner.exists() and constant(source, "BANNER") != banner.read_text(encoding="utf-8-sig"):
        raise ReleaseError("Banner asset differs from the bundled BANNER in git_workflow.py")
    payload = json.loads(zlib.decompress(base64.b64decode(constant(source, "PAYLOAD_B64"))))
    if not isinstance(payload, dict) or not payload:
        raise ReleaseError("Bundled skill payload is empty or invalid")
    for name, content in payload.items():
        path = PurePosixPath(name)
        if (not isinstance(content, str) or path.is_absolute() or ".." in path.parts
                or "\\" in name or ":" in name
                or not name.startswith(".agents/skills/git-workflow/")):
            raise ReleaseError("Bundled skill payload contains an unsafe file")
    prefix = ".agents/skills/git-workflow/"
    for name in ("SKILL.md", "references/help.md", "references/gitrelease.md"):
        if not payload.get(prefix + name, "").strip():
            raise ReleaseError(f"Bundled skill payload is missing {name}")
    if prefix + "VERSION" in payload:
        raise ReleaseError("Package version file must be generated from VERSION")
    return {
        "project": "python-cli", "version": version,
        "tag": f"v{version}", "python_sha256": sha256(source),
        "prerelease": str(bool(SEMVER.fullmatch(version).group(4))).lower(),
    }


def release_notes(changelog: str, version: str) -> str:
    """Read one exact version section, without borrowing a neighboring release."""
    version_value(version)
    lines = changelog.splitlines()
    heading = re.compile(r"^## \[" + re.escape(version) + r"\](?:\s+-\s+.+)?\s*$")
    matches = [index for index, line in enumerate(lines) if heading.fullmatch(line)]
    if len(matches) != 1:
        raise ReleaseError(f"CHANGELOG.md must contain one exact ## [{version}] section")
    start = matches[0] + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("## ")),
               len(lines))
    body = "\n".join(lines[start:end]).strip()
    meaningful = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    meaningful = "\n".join(line for line in meaningful.splitlines()
                           if not line.lstrip().startswith(("#", "<", "[")))
    if not re.sub(r"[\s#>*_`\-]+", "", meaningful):
        raise ReleaseError(f"Release notes for {version} are empty")
    return f"## Git Workflow v{version}\n\n{body}\n"


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], check=False,
                            capture_output=True, text=True)
    if result.returncode:
        raise ReleaseError(f"Git validation failed: {result.stderr.strip() or ' '.join(args)}")
    return result.stdout.strip()


def validate_tag(root: Path, version: str, sha: str, remote: bool = False) -> None:
    version_value(version)
    if not COMMIT_SHA.fullmatch(sha):
        raise ReleaseError("Publication requires an exact commit SHA")
    if git_output(root, "rev-parse", "HEAD") != sha:
        raise ReleaseError("Checkout HEAD does not match the approved commit SHA")
    tag = "refs/tags/v" + version
    if git_output(root, "rev-parse", "--verify", tag + "^{commit}") != sha:
        raise ReleaseError(f"Existing tag v{version} must point at checkout HEAD")
    if remote:
        refs = {}
        for line in git_output(root, "ls-remote", "--exit-code", "origin", tag, tag + "^{}").splitlines():
            commit, ref = line.split("\t", 1)
            refs[ref] = commit
        if refs.get(tag + "^{}", refs.get(tag)) != sha:
            raise ReleaseError(f"Remote tag v{version} does not match the approved commit")


def preflight(root: Path, event: str, ref: str, requested_version: str = "",
              publish: bool = False, sha: str = "") -> dict[str, str]:
    metadata = project_metadata(root)
    selected = version_value(requested_version) if requested_version else metadata["version"]
    if event == "push":
        if ref.startswith("refs/tags/"):
            tag = ref.removeprefix("refs/tags/")
            if not tag.startswith("v"):
                raise ReleaseError("Release tags must use the vVERSION format")
            selected = version_value(tag[1:])
            publish = True
        elif ref == "refs/heads/main":
            publish = False
        else:
            raise ReleaseError("Push builds are allowed only for main or vVERSION tags")
    elif event not in ("workflow_dispatch", "local"):
        raise ReleaseError(f"Unsupported workflow event: {event}")
    if event == "local" and publish:
        raise ReleaseError("Local validation cannot publish a release")
    if selected != metadata["version"]:
        raise ReleaseError(f"Requested version {selected} differs from VERSION {metadata['version']}")
    release_notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), selected)
    if sha:
        if not COMMIT_SHA.fullmatch(sha):
            raise ReleaseError("Workflow SHA must be an exact hexadecimal object ID")
        # Annotated tag events can identify the tag object; downstream builds need its commit.
        sha = git_output(root, "rev-parse", "--verify", sha + "^{commit}")
        if not COMMIT_SHA.fullmatch(sha):
            raise ReleaseError("Workflow object did not resolve to an exact commit SHA")
    if publish:
        validate_tag(root, selected, sha)
    elif sha and git_output(root, "rev-parse", "HEAD") != sha:
        raise ReleaseError("Checkout HEAD differs from the workflow commit")
    metadata.update({"publish": str(publish).lower(), "sha": sha})
    return metadata


def load_metadata(path: Path, root: Path) -> dict[str, str]:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ReleaseError("Preflight metadata must be a JSON object")
    actual = project_metadata(root)
    for name in actual:
        if metadata.get(name) != actual[name]:
            raise ReleaseError(f"Preflight metadata no longer matches the checkout: {name}")
    return metadata


def archive_name(version: str, target: str) -> str:
    version_value(version)
    if target not in PLATFORMS:
        raise ReleaseError(f"Unknown native platform: {target}")
    return f"git-workflow-{version}-{target}-x64" + (".zip" if target == "windows" else ".tar.gz")


def archive_members(target: str) -> tuple[str, ...]:
    return ("git-workflow.exe" if target == "windows" else "git-workflow",
            "install-cli.ps1" if target == "windows" else "install-cli.sh",
            "README.md", "Panduan-Git-Workflow.md")


def validate_binary(data: bytes, target: str) -> None:
    """Reject a binary for a different operating system or CPU architecture."""
    valid = False
    if target == "windows" and len(data) >= 64 and data[:2] == b"MZ":
        offset = struct.unpack_from("<I", data, 60)[0]
        valid = (len(data) >= offset + 6 and data[offset:offset + 4] == b"PE\0\0"
                 and struct.unpack_from("<H", data, offset + 4)[0] == 0x8664)
    elif target == "linux" and len(data) >= 64:
        valid = (data[:6] == b"\x7fELF\x02\x01"
                 and struct.unpack_from("<H", data, 18)[0] == 62)
    elif target == "macos" and len(data) >= 32:
        valid = (data[:4] == b"\xcf\xfa\xed\xfe"
                 and struct.unpack_from("<I", data, 4)[0] == 0x01000007)
    if not valid:
        raise ReleaseError(f"Archive executable is not a {target} x64 binary")


def verify_archive(path: Path, target: str, root: Path) -> None:
    expected = archive_members(target)
    if target == "windows":
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) != len(expected) or {item.filename for item in members} != set(expected):
                raise ReleaseError(f"Unexpected or missing members in {path.name}")
            if any(item.is_dir() or ((item.external_attr >> 16) & 0o170000) == 0o120000
                   for item in members):
                raise ReleaseError(f"Non-regular members in {path.name}")
            contents = {name: archive.read(name) for name in expected}
    else:
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            if len(members) != len(expected) or {item.name for item in members} != set(expected):
                raise ReleaseError(f"Unexpected or missing members in {path.name}")
            if any(not item.isfile() for item in members):
                raise ReleaseError(f"Non-regular members in {path.name}")
            if any(not archive.getmember(name).mode & 0o111 for name in expected[:2]):
                raise ReleaseError(f"Executable permissions missing in {path.name}")
            contents = {name: archive.extractfile(name).read() for name in expected}
    validate_binary(contents[expected[0]], target)
    for name in expected[1:]:
        source = root / ("scripts/" + name if name.startswith("install-cli.") else name)
        if contents[name] != source.read_bytes():
            raise ReleaseError(f"Bundled {name} differs from the approved checkout")


def run_checked(arguments: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, check=False,
                            timeout=180)
    if result.returncode:
        raise ReleaseError(f"Command failed ({result.returncode}): {arguments[0]}\n"
                           + result.stdout + result.stderr)
    return result


def smoke_test(executable: Path, version: str) -> None:
    with tempfile.TemporaryDirectory(prefix="git-workflow-smoke-") as directory:
        cwd = Path(directory)
        output = run_checked([str(executable), "--version"], cwd).stdout
        if output.strip() != f"Git Workflow {version}":
            raise ReleaseError("Frozen executable reports incorrect package version")
        catalog = run_checked([str(executable), "commands"], cwd).stdout
        if "Agent commands" not in catalog or "gitrelease" not in catalog or "\033" in catalog:
            raise ReleaseError("Frozen command tree is invalid or decorates redirected output")
        project = cwd / "project with spaces"
        project.mkdir()
        (project / ".git").mkdir()
        nested = project / "nested" / "directory"
        nested.mkdir(parents=True)
        command = [str(executable), "install"]
        run_checked(command, nested)
        if (project / ".agents").exists() or (project / "AGENTS.md").exists():
            raise ReleaseError("Frozen dry-run unexpectedly wrote project files")
        run_checked(command + ["--apply"], nested)
        installed = project / ".agents/skills/git-workflow/VERSION"
        if installed.read_text(encoding="utf-8").strip() != version:
            raise ReleaseError("Frozen executable installed the wrong skill version")
        manifest = json.loads((project / ".agents/git-workflow-install.json").read_text(encoding="utf-8"))
        if manifest.get("version") != version:
            raise ReleaseError("Frozen executable wrote an incorrect manifest version")
        status = run_checked([str(executable), "status", "--plain"], nested).stdout
        if "All manifest files intact" not in status:
            raise ReleaseError("Frozen status did not verify the installed manifest files")
        if (nested / ".agents").exists() or (nested / "AGENTS.md").exists():
            raise ReleaseError("Frozen executable installed into the nested directory instead of the Git root")
        run_checked([str(executable), "uninstall", "--apply"], nested)
        if installed.exists() or (project / ".agents/git-workflow-install.json").exists():
            raise ReleaseError("Frozen uninstall left managed skill files behind")
        if (nested / ".agents").exists() or (nested / "AGENTS.md").exists():
            raise ReleaseError("Frozen uninstall unexpectedly wrote nested directory files")


def package_native(root: Path, executable: Path, version: str, target: str, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / archive_name(version, target)
    members = archive_members(target)
    sources = [executable, root / "scripts" / members[1], root / members[2], root / members[3]]
    if target == "windows":
        with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, source in zip(members, sources):
                archive.write(source, arcname=name)
    else:
        with tarfile.open(artifact, "w:gz") as archive:
            for index, (name, source) in enumerate(zip(members, sources)):
                item = archive.gettarinfo(str(source), arcname=name)
                item.mode = 0o755 if index < 2 else 0o644
                with source.open("rb") as data:
                    archive.addfile(item, data)
    verify_archive(artifact, target, root)
    return artifact


def smoke_installer(root: Path, executable: Path, target: str) -> None:
    """Verify the archive's PATH installer without changing the runner's PATH."""
    with tempfile.TemporaryDirectory(prefix="git-workflow-path-") as directory:
        workspace = Path(directory)
        bundle = workspace / "bundle"
        bundle.mkdir()
        shutil.copyfile(executable, bundle / executable.name)
        helper = "install-cli.ps1" if target == "windows" else "install-cli.sh"
        shutil.copyfile(root / "scripts" / helper, bundle / helper)
        destination = workspace / "user bin"
        if target == "windows":
            command = ["pwsh", "-NoProfile", "-File", str(bundle / helper),
                       "-InstallDir", str(destination), "-NoPathUpdate"]
        else:
            (bundle / executable.name).chmod(0o755)
            command = ["sh", str(bundle / helper), "--bin-dir", str(destination), "--no-path-update"]
        run_checked(command, workspace)
        installed = destination / executable.name
        if not installed.is_file() or sha256(installed) != sha256(executable):
            raise ReleaseError("PATH installer did not preserve the executable bytes")
        run_checked([str(installed), "--version"], workspace)


def build_native(root: Path, metadata: dict[str, str], target: str, output: Path) -> Path:
    host = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    if host != target or platform.machine().lower() not in ("amd64", "x86_64") or struct.calcsize("P") != 8:
        raise ReleaseError(f"{target} x64 builds require a native x64 runner and Python")
    with tempfile.TemporaryDirectory(prefix="git-workflow-build-") as directory:
        build = Path(directory)
        command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
                   "--console", "--noupx", "--name", "git-workflow", "--distpath", str(build / "dist"),
                   "--workpath", str(build / "work"), "--specpath", str(build / "spec")]
        if target == "macos":
            command.extend(("--target-arch", "x86_64"))
        subprocess.run(command + [str(root / "git_workflow.py")], cwd=root, check=True)
        executable = build / "dist" / archive_members(target)[0]
        smoke_test(executable, metadata["version"])
        smoke_installer(root, executable, target)
        return package_native(root, executable, metadata["version"], target, output)


def distribution_names(version: str) -> set[str]:
    return {archive_name(version, target) for target in PLATFORMS} | {"git_workflow.py"}


def verify_release(directory: Path, root: Path, metadata: dict[str, str]) -> None:
    expected = distribution_names(metadata["version"])
    actual = {path.name for path in directory.iterdir()}
    if actual != expected | {"SHA256SUMS.txt"} or any(not path.is_file() for path in directory.iterdir()):
        raise ReleaseError("Release must contain exactly four distributions and SHA256SUMS.txt")
    hashes = {}
    for line in (directory / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match or match.group(2) in hashes:
            raise ReleaseError("Checksum manifest contains invalid or duplicate entries")
        hashes[match.group(2)] = match.group(1)
    if set(hashes) != expected:
        raise ReleaseError("Checksum manifest must cover all four distributions exactly")
    for name, digest in hashes.items():
        if sha256(directory / name) != digest:
            raise ReleaseError(f"SHA-256 mismatch: {name}")
    source = directory / "git_workflow.py"
    if sha256(source) != metadata["python_sha256"] or source.read_bytes() != (root / source.name).read_bytes():
        raise ReleaseError("Standalone Python CLI differs from the approved source")
    for target in PLATFORMS:
        verify_archive(directory / archive_name(metadata["version"], target), target, root)


def collect_artifacts(incoming: Path, output: Path, root: Path, metadata: dict[str, str]) -> None:
    expected = {archive_name(metadata["version"], target) for target in PLATFORMS}
    if {path.name for path in incoming.iterdir()} != expected or any(not path.is_file() for path in incoming.iterdir()):
        raise ReleaseError("Matrix artifacts must contain exactly the three expected native archives")
    if output.exists() and any(output.iterdir()):
        raise ReleaseError("Collect output directory must be empty to prevent stale release assets")
    output.mkdir(parents=True, exist_ok=True)
    for target in PLATFORMS:
        name = archive_name(metadata["version"], target)
        verify_archive(incoming / name, target, root)
        shutil.copyfile(incoming / name, output / name)
    shutil.copyfile(root / "git_workflow.py", output / "git_workflow.py")
    manifest = "".join(f"{sha256(output / name)}  {name}\n" for name in sorted(distribution_names(metadata["version"])))
    (output / "SHA256SUMS.txt").write_text(manifest, encoding="ascii", newline="\n")
    verify_release(output, root, metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("preflight")
    check.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "local"))
    check.add_argument("--ref", default=os.environ.get("GITHUB_REF", ""))
    check.add_argument("--version", default=os.environ.get("INPUT_VERSION", ""))
    check.add_argument("--publish", choices=("true", "false"), default=os.environ.get("INPUT_PUBLISH", "false"))
    check.add_argument("--sha", default=os.environ.get("GITHUB_SHA", ""))
    check.add_argument("--output", type=Path, default=Path(".release/metadata.json"))
    check.add_argument("--github-output", type=Path, default=os.environ.get("GITHUB_OUTPUT"))
    build = commands.add_parser("build")
    build.add_argument("--platform", choices=PLATFORMS, required=True)
    build.add_argument("--metadata", type=Path, required=True)
    build.add_argument("--out-dir", type=Path, required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--incoming", type=Path, required=True)
    collect.add_argument("--out-dir", type=Path, required=True)
    collect.add_argument("--metadata", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--directory", type=Path, required=True)
    verify.add_argument("--metadata", type=Path, required=True)
    notes = commands.add_parser("notes")
    notes.add_argument("--version", required=True)
    notes.add_argument("--output", type=Path, required=True)
    tag = commands.add_parser("validate-tag")
    tag.add_argument("--version", required=True)
    tag.add_argument("--sha", required=True)
    tag.add_argument("--remote", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "preflight":
            metadata = preflight(root, args.event, args.ref, args.version, args.publish == "true", args.sha)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            if args.github_output:
                with args.github_output.open("a", encoding="utf-8") as output:
                    for name, value in metadata.items():
                        output.write(f"{name}={value}\n")
            print(json.dumps(metadata, indent=2))
        elif args.command == "build":
            metadata = load_metadata(args.metadata, root)
            print(build_native(root, metadata, args.platform, args.out_dir.resolve()))
        elif args.command == "collect":
            collect_artifacts(args.incoming, args.out_dir, root, load_metadata(args.metadata, root))
            print("Verified four distributions and SHA-256 checksums")
        elif args.command == "verify":
            verify_release(args.directory, root, load_metadata(args.metadata, root))
            print("All release assets verified")
        elif args.command == "notes":
            metadata = project_metadata(root)
            if args.version != metadata["version"]:
                raise ReleaseError("Release notes version differs from VERSION")
            content = release_notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), args.version)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding="utf-8", newline="\n")
            print(f"Extracted release notes for {args.version}")
        else:
            validate_tag(root, args.version, args.sha, args.remote)
            print(f"Existing tag v{args.version} matches {args.sha}")
        return 0
    except (ReleaseError, OSError, SyntaxError, json.JSONDecodeError, zipfile.BadZipFile,
            tarfile.TarError, subprocess.CalledProcessError, subprocess.TimeoutExpired, zlib.error) as error:
        print(f"Release validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
