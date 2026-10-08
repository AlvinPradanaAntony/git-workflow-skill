"""Fail-closed checks for release selection and distribution integrity."""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib


SPEC = importlib.util.spec_from_file_location("release_helpers", Path(__file__).resolve().parents[1] / "scripts/release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def binary(target: str) -> bytes:
    data = bytearray(128)
    if target == "windows":
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 64)
        data[64:68] = b"PE\0\0"
        struct.pack_into("<H", data, 68, 0x8664)
    elif target == "linux":
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 62)
    else:
        data[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", data, 4, 0x01000007)
    return bytes(data)


class ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "scripts").mkdir()
        payload = {
            ".agents/skills/git-workflow/SKILL.md": "Skill content",
            ".agents/skills/git-workflow/references/help.md": "Help",
            ".agents/skills/git-workflow/references/gitrelease.md": "Release",
        }
        encoded = base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode()
        (self.root / "git_workflow.py").write_bytes(
            f'VERSION = "2.13.0"\r\nPAYLOAD_B64 = {encoded!r}\r\n'.encode()
        )
        for name in ("README.md", "Panduan-Git-Workflow.md", "requirements-build.txt",
                     "scripts/install-cli.ps1", "scripts/install-cli.sh"):
            (self.root / name).write_text(name + "\n", encoding="utf-8")
        (self.root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [2.13.0] - 2026-10-08\n\n### Added\n\n- Portable CLI.\n\n"
            "## [2.12.4] - 2026-09-22\n\n- Old installer.\n", encoding="utf-8"
        )
        self.metadata = release.project_metadata(self.root)
        self.sha = "a" * 40

    def prepare_assets(self) -> tuple[Path, Path]:
        incoming = Path(self.temp.name) / "incoming"
        output = Path(self.temp.name) / "assets"
        for target in release.PLATFORMS:
            executable = Path(self.temp.name) / release.archive_members(target)[0]
            executable.write_bytes(binary(target))
            release.package_native(self.root, executable, "2.13.0", target, incoming)
        return incoming, output

    def collect(self) -> Path:
        incoming, output = self.prepare_assets()
        release.collect_artifacts(incoming, output, self.root, self.metadata)
        return output

    def test_release_uses_single_version(self) -> None:
        self.assertEqual(self.metadata["version"], "2.13.0")
        self.assertNotIn("bundled_version", self.metadata)

    def test_banner_asset_must_match_standalone_source(self) -> None:
        asset = self.root / "assets/banner/ASCIILogo.txt"
        asset.parent.mkdir(parents=True)
        asset.write_text("Logo\n", encoding="utf-8")
        source = self.root / "git_workflow.py"
        source.write_text(source.read_text() + '\nBANNER = "Logo\\n"\n', encoding="utf-8")
        release.project_metadata(self.root)
        asset.write_text("Changed logo\n", encoding="utf-8")
        with self.assertRaisesRegex(release.ReleaseError, "Banner asset differs"):
            release.project_metadata(self.root)

    def test_unsafe_versions_fail(self) -> None:
        for version in ("v2.13.0", "02.13.0", "2.13", "2.13.0\n", "2.13.0-01", "../../2.13.0"):
            with self.subTest(version=version), self.assertRaises(release.ReleaseError):
                release.version_value(version)
        self.assertEqual(release.version_value("2.13.0-rc.1+build.123"), "2.13.0-rc.1+build.123")

    def test_build_metadata_hyphen_is_not_a_prerelease(self) -> None:
        for version, expected in (("2.13.0+build-1", "false"), ("2.13.0-rc.1+build-1", "true")):
            path = self.root / "git_workflow.py"
            current = release.constant(path, "VERSION")
            path.write_bytes(path.read_bytes().replace(
                f'VERSION = "{current}"'.encode(), f'VERSION = "{version}"'.encode()
            ))
            self.assertEqual(release.project_metadata(self.root)["prerelease"], expected)

    def test_main_and_manual_builds_do_not_publish(self) -> None:
        for event, ref in (("push", "refs/heads/main"), ("workflow_dispatch", "refs/heads/main")):
            result = release.preflight(self.root, event, ref)
            self.assertEqual(result["publish"], "false")

    def test_tag_and_manual_versions_must_match_metadata(self) -> None:
        with self.assertRaises(release.ReleaseError):
            release.preflight(self.root, "push", "refs/tags/v2.13.1", sha=self.sha)
        with self.assertRaises(release.ReleaseError):
            release.preflight(self.root, "workflow_dispatch", "refs/heads/main", "2.13.1")
        with self.assertRaises(release.ReleaseError):
            release.preflight(self.root, "push", "refs/tags/2.13.0", sha=self.sha)

    def test_release_requires_existing_tag_at_exact_checkout(self) -> None:
        for event, ref in (("push", "refs/tags/v2.13.0"), ("workflow_dispatch", "refs/heads/main")):
            with patch.object(release, "git_output", side_effect=[self.sha, self.sha, "b" * 40]):
                with self.assertRaises(release.ReleaseError):
                    release.preflight(self.root, event, ref, publish=True, sha=self.sha)
            with patch.object(release, "git_output", side_effect=[self.sha, self.sha, self.sha]):
                result = release.preflight(self.root, event, ref, publish=True, sha=self.sha)
                self.assertEqual(result["publish"], "true")
            with patch.object(release, "git_output", side_effect=release.ReleaseError("Tag missing")):
                with self.assertRaises(release.ReleaseError):
                    release.preflight(self.root, event, ref, publish=True, sha=self.sha)

    def test_annotated_workflow_sha_is_peeled_to_commit(self) -> None:
        for raw_sha in ("b" * 40, self.sha):
            with patch.object(release, "git_output", side_effect=[self.sha, self.sha, self.sha]) as git:
                result = release.preflight(self.root, "push", "refs/tags/v2.13.0", sha=raw_sha)
                self.assertEqual(result["sha"], self.sha)
                self.assertEqual(result["publish"], "true")
                self.assertEqual(git.call_args_list[0].args[-1], raw_sha + "^{commit}")

    def test_invalid_event_sha_is_rejected_before_git(self) -> None:
        with patch.object(release, "git_output") as git:
            with self.assertRaises(release.ReleaseError):
                release.preflight(self.root, "workflow_dispatch", "refs/heads/main", sha="HEAD;publish")
            git.assert_not_called()

    def test_remote_annotated_tag_must_match(self) -> None:
        listing = f"{'b' * 40}\trefs/tags/v2.13.0\n{self.sha}\trefs/tags/v2.13.0^{{}}"
        with patch.object(release, "git_output", side_effect=[self.sha, self.sha, listing]):
            release.validate_tag(self.root, "2.13.0", self.sha, remote=True)
        with patch.object(release, "git_output", side_effect=[self.sha, self.sha,
                                                             f"{'b' * 40}\trefs/tags/v2.13.0"]):
            with self.assertRaises(release.ReleaseError):
                release.validate_tag(self.root, "2.13.0", self.sha, remote=True)

    def test_missing_empty_or_duplicate_changelog_fails(self) -> None:
        for changelog in ("## [2.13.1]\n- Wrong version", "## [2.13.0]\n### Added\n<!-- TODO -->\n",
                          "## [2.13.0]\n- First\n## [2.13.0]\n- Duplicate"):
            with self.subTest(changelog=changelog), self.assertRaises(release.ReleaseError):
                release.release_notes(changelog, "2.13.0")

    def test_notes_include_exact_version_only(self) -> None:
        notes = release.release_notes((self.root / "CHANGELOG.md").read_text(), "2.13.0")
        self.assertIn("Portable CLI.", notes)
        self.assertNotIn("Old installer", notes)

    def test_embedded_version_is_rejected_to_keep_one_source_of_truth(self) -> None:
        path = self.root / "git_workflow.py"
        encoded = release.constant(path, "PAYLOAD_B64")
        payload = json.loads(zlib.decompress(base64.b64decode(encoded)))
        payload[".agents/skills/git-workflow/VERSION"] = "2.12.4\n"
        replacement = base64.b64encode(zlib.compress(json.dumps(payload).encode())).decode()
        path.write_text(path.read_text().replace(repr(encoded), repr(replacement)), encoding="utf-8")
        with self.assertRaisesRegex(release.ReleaseError, "generated from VERSION"):
            release.project_metadata(self.root)

    def test_collect_preserves_python_cli_bytes_and_four_distributions(self) -> None:
        output = self.collect()
        self.assertEqual(len(list(output.iterdir())), 5)
        self.assertEqual((output / "git_workflow.py").read_bytes(),
                         (self.root / "git_workflow.py").read_bytes())
        release.verify_release(output, self.root, self.metadata)

    def test_missing_or_extra_matrix_archive_fails(self) -> None:
        incoming, output = self.prepare_assets()
        expected = incoming / release.archive_name("2.13.0", "linux")
        saved = expected.read_bytes()
        expected.unlink()
        with self.assertRaises(release.ReleaseError):
            release.collect_artifacts(incoming, output, self.root, self.metadata)
        expected.write_bytes(saved)
        (incoming / "unexpected.bin").write_bytes(b"extra")
        with self.assertRaises(release.ReleaseError):
            release.collect_artifacts(incoming, output, self.root, self.metadata)

    def test_wrong_architecture_and_extra_archive_member_fail(self) -> None:
        incoming, _ = self.prepare_assets()
        archive = incoming / release.archive_name("2.13.0", "windows")
        with zipfile.ZipFile(archive, "a") as data:
            data.writestr("unapproved.txt", "unexpected")
        with self.assertRaises(release.ReleaseError):
            release.verify_archive(archive, "windows", self.root)
        with self.assertRaises(release.ReleaseError):
            release.validate_binary(binary("linux"), "windows")

    def test_corrupted_asset_checksum_or_manifest_fails(self) -> None:
        output = self.collect()
        source = output / "git_workflow.py"
        saved = source.read_bytes()
        source.write_bytes(saved + b"corruption")
        with self.assertRaises(release.ReleaseError):
            release.verify_release(output, self.root, self.metadata)
        source.write_bytes(saved)
        checksum = output / "SHA256SUMS.txt"
        original = checksum.read_text()
        for text in (original + original.splitlines()[0] + "\n", original.replace("  git_workflow.py", "  bad.py")):
            checksum.write_text(text)
            with self.assertRaises(release.ReleaseError):
                release.verify_release(output, self.root, self.metadata)

    def test_python_source_change_rejected_even_with_regenerated_checksum(self) -> None:
        output = self.collect()
        source = output / "git_workflow.py"
        old_digest = release.sha256(source)
        source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
        checksums = output / "SHA256SUMS.txt"
        checksums.write_text(checksums.read_text().replace(old_digest, release.sha256(source)))
        with self.assertRaises(release.ReleaseError):
            release.verify_release(output, self.root, self.metadata)


if __name__ == "__main__":
    unittest.main()
