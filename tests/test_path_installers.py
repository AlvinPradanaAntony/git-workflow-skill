"""Test extracted-archive PATH helpers in isolated temporary directories."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def native_bash():
    if os.name == "nt":
        candidates = (
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin/bash.exe",
        )
        return next((str(candidate) for candidate in candidates if candidate.is_file()), None)
    return shutil.which("bash") or shutil.which("sh")


BASH = native_bash()
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def shell_path(path):
    path = Path(path).resolve()
    if os.name == "nt":
        return "/" + path.drive[0].lower() + "/" + "/".join(path.parts[1:])
    return str(path)


def powershell_literal(path):
    return "'" + str(path).replace("'", "''") + "'"


@unittest.skipUnless(BASH, "A native Bash or POSIX shell is unavailable")
class ShellInstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="git-workflow-shell-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "release archive"
        self.source.mkdir()
        shutil.copy2(PROJECT_ROOT / "scripts/install-cli.sh", self.source / "install-cli.sh")
        shutil.copy2(PROJECT_ROOT / "scripts/uninstall-cli.sh", self.source / "uninstall-cli.sh")
        (self.source / "git-workflow").write_bytes(b"#!/bin/sh\nexit 0\n")
        for name in ("README.md", "Panduan-Git-Workflow.md"):
            (self.source / name).write_text(name + "\n", encoding="utf-8")
        self.package_bytes = {path.name: path.read_bytes() for path in self.source.iterdir()}
        self.uninstall_driver = self.root / "uninstall-cli.sh"
        shutil.copyfile(self.source / "uninstall-cli.sh", self.uninstall_driver)
        self.user_home = self.root / "isolated home"
        self.user_home.mkdir()
        self.bin_directory = self.root / "bin [literal] $`'"
        self.environment = os.environ.copy()
        self.environment["HOME"] = shell_path(self.user_home)
        self.environment["SHELL"] = "/bin/bash"

    def run_shell(self, command, input_text="", check=True):
        return subprocess.run(
            [BASH, *command], env=self.environment,
            cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", check=check, input=input_text,
        )

    def install(self, *extra):
        helper = self.source / "install-cli.sh"
        if not helper.exists():
            helper = self.bin_directory / "install-cli.sh"
        return self.run_shell([
            shell_path(helper),
            "--bin-dir", shell_path(self.bin_directory), "--yes", *extra,
        ])

    def sourced_path(self, *profiles):
        sourcing = "; ".join(". " + shlex.quote(shell_path(profile)) for profile in profiles)
        return self.run_shell(["-c", sourcing + '; printf "%s" "$PATH"']).stdout

    def uninstall(self, *extra):
        helper = self.bin_directory / "uninstall-cli.sh"
        if not helper.exists():
            helper = self.uninstall_driver
        return self.run_shell([
            shell_path(helper),
            "--bin-dir", shell_path(self.bin_directory), "--yes", *extra,
        ])

    def test_uninstall_cleans_installer_blocks_after_shell_change_and_keeps_other_files(self):
        bashrc = self.user_home / ".bashrc"
        bashrc.write_text("# Keep settings\nexport EDITOR=vim\n", encoding="utf-8")
        self.install()
        unrelated = self.bin_directory / "other-tool"
        unrelated.write_text("keep", encoding="utf-8")
        skills = self.user_home / ".agents/skills/git-workflow/SKILL.md"
        skills.parent.mkdir(parents=True)
        skills.write_text("keep skill", encoding="utf-8")
        self.environment["SHELL"] = "/bin/zsh"
        self.uninstall()
        self.assertFalse((self.bin_directory / "git-workflow").exists())
        self.assertTrue(unrelated.is_file())
        self.assertEqual(skills.read_text(), "keep skill")
        self.assertEqual(bashrc.read_text(), "# Keep settings\nexport EDITOR=vim\n\n")
        self.assertNotIn("Git Workflow CLI", (self.user_home / ".profile").read_text())
        first = bashrc.read_bytes()
        self.uninstall()
        self.assertEqual(bashrc.read_bytes(), first)
        self.assertFalse((self.user_home / ".zshrc").exists())

    def test_custom_profile_dry_run_and_no_path_update(self):
        selected = self.root / "custom profile"
        self.install("--profile", shell_path(selected))
        original = selected.read_bytes()
        preview = self.uninstall("--profile", shell_path(selected), "--dry-run")
        self.assertIn("Would remove Git Workflow PATH block", preview.stdout)
        self.assertTrue((self.bin_directory / "git-workflow").exists())
        self.assertEqual(selected.read_bytes(), original)
        self.uninstall("--profile", shell_path(selected), "--no-path-update")
        self.assertFalse((self.bin_directory / "git-workflow").exists())
        self.assertEqual(selected.read_bytes(), original)
        self.uninstall("--profile", shell_path(selected))
        self.assertNotIn("Git Workflow CLI", selected.read_text())

    def test_uninstall_preserves_edited_and_other_installation_blocks(self):
        selected = self.root / "custom profile"
        self.install("--profile", shell_path(selected))
        block = selected.read_text()
        edited = block.replace("esac", "esac # user edit")
        other = block.replace("export PATH=", "export OTHER_PATH=")
        selected.write_text(edited + other + block + "# keep final", encoding="utf-8")
        self.uninstall("--profile", shell_path(selected))
        self.assertEqual(selected.read_text(), edited + other + "\n# keep final\n")
        # Without any complete matching block the file remains byte-identical.
        selected.write_bytes(b"# user profile without final newline")
        self.uninstall("--profile", shell_path(selected))
        self.assertEqual(selected.read_bytes(), b"# user profile without final newline")

    def test_uninstall_missing_installation_and_relative_directory(self):
        self.uninstall()
        self.assertFalse(self.bin_directory.exists())
        self.assertEqual(list(self.user_home.iterdir()), [])
        self.install("--no-path-update")
        self.run_shell([
            shell_path(self.bin_directory / "uninstall-cli.sh"),
            "--bin-dir", self.bin_directory.name, "--no-path-update", "--yes",
        ])
        self.assertFalse((self.bin_directory / "git-workflow").exists())

    def test_explicit_profile_quotes_literal_path_and_is_idempotent(self):
        selected = self.root / "custom profile"
        self.install("--profile", shell_path(selected))
        first = selected.read_bytes()
        self.install("--profile", shell_path(selected))
        self.assertEqual(selected.read_bytes(), first)
        self.assertEqual(first.count(b"# Git Workflow CLI"), 1)
        self.assertEqual((self.bin_directory / "git-workflow").read_bytes(), self.package_bytes["git-workflow"])
        current_path = self.sourced_path(selected, selected)
        self.assertEqual(current_path.split(":").count(shell_path(self.bin_directory)), 1)
        self.assertTrue(current_path.startswith(shell_path(self.bin_directory) + ":"))
        self.assertEqual(list(self.user_home.iterdir()), [])

    def test_bash_registers_nonlogin_and_selected_login_profile(self):
        for existing_login, expected_login in (
            (".bash_profile", ".bash_profile"),
            (".bash_login", ".bash_login"),
            (None, ".profile"),
        ):
            with self.subTest(existing_login=existing_login):
                for profile in self.user_home.iterdir():
                    profile.unlink()
                if existing_login:
                    (self.user_home / existing_login).write_text("# Existing settings\n", encoding="utf-8")
                self.install()
                interactive_profile = self.user_home / ".bashrc"
                login_profile = self.user_home / expected_login
                self.assertTrue(interactive_profile.is_file())
                self.assertTrue(login_profile.is_file())
                first_profiles = {path.name: path.read_bytes() for path in self.user_home.iterdir()}
                self.install()
                self.assertEqual({path.name: path.read_bytes() for path in self.user_home.iterdir()}, first_profiles)
                current_path = self.sourced_path(interactive_profile, login_profile)
                self.assertEqual(current_path.split(":").count(shell_path(self.bin_directory)), 1)
                self.assertEqual(set(first_profiles), {".bashrc", expected_login})

    def test_bash_prefers_existing_bash_profile_over_bash_login(self):
        bash_profile = self.user_home / ".bash_profile"
        bash_login = self.user_home / ".bash_login"
        bash_profile.write_text("# selected\n", encoding="utf-8")
        bash_login.write_text("# unselected\n", encoding="utf-8")
        self.install()
        self.assertIn("# Git Workflow CLI", bash_profile.read_text(encoding="utf-8"))
        self.assertEqual(bash_login.read_text(encoding="utf-8"), "# unselected\n")

    def test_zsh_and_posix_shells_use_their_expected_profile(self):
        for shell, expected_profile in (
            ("/bin/zsh", ".zshrc"),
            ("/bin/sh", ".profile"),
            ("/bin/dash", ".profile"),
            ("/bin/ksh", ".profile"),
        ):
            with self.subTest(shell=shell):
                for profile in self.user_home.iterdir():
                    profile.unlink()
                self.environment["SHELL"] = shell
                self.install()
                self.assertEqual([path.name for path in self.user_home.iterdir()], [expected_profile])

    def test_unsupported_shell_requires_manual_path_without_fake_profile(self):
        self.environment["SHELL"] = "/usr/bin/fish"
        result = self.install()
        self.assertIn("requires manual PATH configuration", result.stdout)
        self.assertTrue((self.bin_directory / "git-workflow").is_file())
        self.assertEqual(list(self.user_home.iterdir()), [])
        self.assertNotIn("Open a new terminal", result.stdout)

    def test_no_path_update_does_not_create_selected_or_default_profiles(self):
        selected = self.root / "unused profile"
        self.install("--profile", shell_path(selected), "--no-path-update")
        self.assertFalse(selected.exists())
        self.assertEqual(list(self.user_home.iterdir()), [])

    def test_install_confirmation_default_no_and_success_checklist(self):
        command = [shell_path(self.source / "install-cli.sh"), "--bin-dir", shell_path(self.bin_directory)]
        for answer in ("n\n", "\n"):
            result = self.run_shell(command, input_text=answer)
            self.assertIn("Git Workflow CLI", result.stdout)
            self.assertIn("[y/N]", result.stdout)
            self.assertIn("Operasi dibatalkan", result.stdout)
            self.assertNotIn("Install CLI sukses", result.stdout)
            self.assertFalse(self.bin_directory.exists())
            self.assertEqual(list(self.user_home.iterdir()), [])
        self.environment["LC_ALL"] = "C"
        result = self.run_shell(command, input_text="y\n")
        self.assertTrue((self.bin_directory / "git-workflow").is_file())
        self.assertIn("[OK] Installed CLI:", result.stdout)
        self.assertIn("[OK] PATH registered in", result.stdout)
        self.assertIn("[OK] Install CLI sukses", result.stdout)
        self.assertNotIn("\x1b", result.stdout)
        self.assertNotIn("\r", result.stdout)

    def test_uninstall_confirmation_preserves_files_until_approved(self):
        self.install()
        profile = self.user_home / ".bashrc"
        original = profile.read_bytes()
        command = [shell_path(self.bin_directory / "uninstall-cli.sh"), "--bin-dir", shell_path(self.bin_directory)]
        result = self.run_shell(command, input_text="n\n")
        self.assertIn("Operasi dibatalkan", result.stdout)
        self.assertTrue((self.bin_directory / "git-workflow").exists())
        self.assertEqual(profile.read_bytes(), original)
        result = self.run_shell(command, input_text="yes\n")
        self.assertFalse((self.bin_directory / "git-workflow").exists())
        self.assertNotIn("Git Workflow CLI", profile.read_text())
        self.assertIn("Uninstall CLI sukses", result.stdout)
        self.assertNotIn("\x1b", result.stdout)

    def test_missing_confirmation_input_fails_closed_and_install_preview_is_read_only(self):
        command = [shell_path(self.source / "install-cli.sh"), "--bin-dir", shell_path(self.bin_directory)]
        result = self.run_shell(command, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--yes", result.stderr)
        self.assertFalse(self.bin_directory.exists())
        result = self.run_shell(command + ["--dry-run"])
        self.assertIn("Preview selesai", result.stdout)
        self.assertFalse(self.bin_directory.exists())
        self.install("--no-path-update")
        result = self.run_shell([
            shell_path(self.bin_directory / "uninstall-cli.sh"), "--bin-dir", shell_path(self.bin_directory),
        ], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.bin_directory / "git-workflow").exists())

    def test_install_failure_never_reports_success(self):
        profile_directory = self.root / "not a profile file"
        profile_directory.mkdir()
        result = self.run_shell([
            shell_path(self.source / "install-cli.sh"), "--bin-dir", shell_path(self.bin_directory),
            "--profile", shell_path(profile_directory), "--yes",
        ], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Install CLI sukses", result.stdout)
        self.assertIn("[ERROR] Install CLI gagal", result.stderr)
        self.assertNotIn("Tekan tombol", result.stdout)

    def test_no_pause_keeps_confirmation_and_early_errors_keep_exit_code(self):
        for helper in (self.source / "install-cli.sh", self.uninstall_driver):
            with self.subTest(helper=helper.name):
                result = self.run_shell([
                    shell_path(helper), "--no-pause", "--bin-dir", shell_path(self.bin_directory),
                    "--no-path-update",
                ], input_text="n\n")
                self.assertIn("[y/N]", result.stdout)
                self.assertIn("Operasi dibatalkan", result.stdout)
                self.assertNotIn("Tekan tombol", result.stdout)
                result = self.run_shell([shell_path(helper), "--unknown"], check=False)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Unknown argument", result.stderr)
                self.assertIn("exit code 2", result.stderr)
                self.assertNotIn("Tekan tombol", result.stdout)
        self.assertFalse(self.bin_directory.exists())

    @unittest.skipIf(os.name == "nt", "A native POSIX PTY is required")
    def test_terminal_waits_for_one_key_on_cancel_success_and_error(self):
        import pty
        import select
        import termios
        import time

        def run_terminal(helper, answer=None, extra=(), expected_status=0, expected_text=""):
            master, slave = pty.openpty()
            original = termios.tcgetattr(slave)
            process = subprocess.Popen(
                [BASH, shell_path(helper), "--bin-dir", shell_path(self.bin_directory),
                 "--no-path-update", *extra], env=self.environment, cwd=str(self.root),
                stdin=slave, stdout=slave, stderr=slave,
            )
            output = b""
            sent_answer = False
            try:
                deadline = time.monotonic() + 10
                while b"Tekan tombol apa saja" not in output:
                    self.assertLess(time.monotonic(), deadline, output.decode(errors="replace"))
                    if select.select([master], [], [], 0.1)[0]:
                        output += os.read(master, 65536)
                    if answer is not None and not sent_answer and b"[y/N]" in output:
                        os.write(master, answer.encode() + b"\n")
                        sent_answer = True
                self.assertIn(expected_text, output.decode())
                self.assertIsNone(process.poll(), "Script exited before the closing key")
                os.write(master, b"x")  # No Enter: a single key must release the pause.
                self.assertEqual(process.wait(timeout=5), expected_status)
                self.assertEqual(termios.tcgetattr(slave), original, "TTY state was not restored")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)
                os.close(slave)

        run_terminal(self.source / "install-cli.sh", "n", expected_text="Operasi dibatalkan")
        run_terminal(self.source / "install-cli.sh", "y", expected_text="Install CLI sukses")
        helper = self.bin_directory / "uninstall-cli.sh"
        run_terminal(helper, "n", expected_text="Operasi dibatalkan")
        run_terminal(helper, extra=("--unknown",), expected_status=2, expected_text="[ERROR]")
        run_terminal(helper, "y", expected_text="Uninstall CLI sukses")
        shutil.copyfile(PROJECT_ROOT / "scripts/install-cli.sh", self.source / "install-cli.sh")
        run_terminal(self.source / "install-cli.sh", expected_status=2, expected_text="[ERROR]")

    def test_complete_package_is_cut_and_installed_helper_removes_every_owned_file(self):
        self.install("--no-path-update")
        self.assertEqual(list(self.source.iterdir()), [])
        for name, content in self.package_bytes.items():
            self.assertEqual((self.bin_directory / name).read_bytes(), content)
        # No --bin-dir: the installed uninstaller discovers its own receipt.
        self.run_shell([shell_path(self.bin_directory / "uninstall-cli.sh"), "--no-path-update", "--yes"])
        self.assertFalse(self.bin_directory.exists())

    def test_conflicting_destination_or_incomplete_archive_does_not_move_files(self):
        self.bin_directory.mkdir()
        conflicting = self.bin_directory / "README.md"
        conflicting.write_text("other tool", encoding="utf-8")
        with self.assertRaises(subprocess.CalledProcessError):
            self.install("--no-path-update")
        self.assertEqual(conflicting.read_text(), "other tool")
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, self.package_bytes)
        conflicting.unlink()
        (self.source / "Panduan-Git-Workflow.md").unlink()
        with self.assertRaises(subprocess.CalledProcessError):
            self.install("--no-path-update")
        self.assertTrue((self.source / "git-workflow").exists())
        self.assertEqual(list(self.bin_directory.iterdir()), [])

    def test_default_location_is_dedicated_and_fully_removed(self):
        self.run_shell([shell_path(self.source / "install-cli.sh"), "--yes"])
        dedicated = self.user_home / ".local/share/git-workflow/bin"
        self.assertTrue((dedicated / "uninstall-cli.sh").is_file())
        self.assertEqual(list(self.source.iterdir()), [])
        self.run_shell([shell_path(dedicated / "uninstall-cli.sh"), "--yes"])
        self.assertFalse(dedicated.parent.exists())
        self.assertNotIn("Git Workflow CLI", (self.user_home / ".bashrc").read_text())

    def test_invalid_package_inventory_blocks_uninstall_and_legacy_docs_are_preserved(self):
        self.install("--no-path-update")
        receipt = self.bin_directory / ".git-workflow-cli.files"
        receipt.write_text("../other-file\n", encoding="utf-8")
        with self.assertRaises(subprocess.CalledProcessError):
            self.uninstall("--no-path-update")
        self.assertTrue((self.bin_directory / "git-workflow").exists())
        receipt.unlink()
        self.uninstall("--no-path-update")
        self.assertFalse((self.bin_directory / "git-workflow").exists())
        self.assertTrue((self.bin_directory / "README.md").is_file())

    def test_preview_and_cancel_preserve_entire_source_archive(self):
        self.install("--dry-run")
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, self.package_bytes)
        self.run_shell([
            shell_path(self.source / "install-cli.sh"), "--bin-dir", shell_path(self.bin_directory),
        ], input_text="n\n")
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, self.package_bytes)
        self.assertFalse(self.bin_directory.exists())

    def test_update_from_fresh_archive_moves_files_and_preserves_other_tools(self):
        self.install("--no-path-update")
        (self.bin_directory / "other-tool").write_text("keep", encoding="utf-8")
        for name, content in self.package_bytes.items():
            (self.source / name).write_bytes(content)
        (self.source / "README.md").write_text("new release docs", encoding="utf-8")
        self.install("--no-path-update")
        self.assertEqual(list(self.source.iterdir()), [])
        self.assertEqual((self.bin_directory / "README.md").read_text(), "new release docs")
        self.uninstall("--no-path-update")
        self.assertEqual([p.name for p in self.bin_directory.iterdir()], ["other-tool"])


# These helpers manage Windows executables, LOCALAPPDATA and user PATH.
# PowerShell also ships on Ubuntu/macOS; its presence does not make them Windows.
@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows with PowerShell is required")
class PowerShellInstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="git-workflow-powershell-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "release archive"
        self.source.mkdir()
        shutil.copy2(PROJECT_ROOT / "scripts/install-cli.ps1", self.source / "install-cli.ps1")
        shutil.copy2(PROJECT_ROOT / "scripts/uninstall-cli.ps1", self.source / "uninstall-cli.ps1")
        (self.source / "git-workflow.exe").write_bytes(bytes(range(20)))
        for name in ("README.md", "Panduan-Git-Workflow.md"):
            (self.source / name).write_text(name + "\n", encoding="utf-8")
        self.package_bytes = {path.name: path.read_bytes() for path in self.source.iterdir()}
        self.uninstall_driver = self.root / "uninstall-cli.ps1"
        shutil.copyfile(self.source / "uninstall-cli.ps1", self.uninstall_driver)
        self.destination = self.root / "installed [literal]"

    def install_command(self):
        source = powershell_literal(self.source / "install-cli.ps1")
        installed = powershell_literal(self.destination / "install-cli.ps1")
        return "& $(if (Test-Path -LiteralPath " + source + ") { " + source + " } else { " + installed + " })"

    def uninstall_command(self):
        installed = powershell_literal(self.destination / "uninstall-cli.ps1")
        fallback = powershell_literal(self.uninstall_driver)
        return "& $(if (Test-Path -LiteralPath " + installed + ") { " + installed + " } else { " + fallback + " })"

    def run_powershell(self, script, check=True):
        script = "[Console]::OutputEncoding = [Text.UTF8Encoding]::new()\n" + script
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        try:
            return subprocess.run(
                [POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                cwd=str(self.root), capture_output=True, text=True, encoding="utf-8", check=check, input="",
            )
        except subprocess.CalledProcessError as error:
            error.cmd = [POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", "<omitted>"]
            if hasattr(error, "add_note"):
                error.add_note("PowerShell stdout:\n" + error.stdout[-4000:] + "\nPowerShell stderr:\n" + error.stderr[-4000:])
            raise

    def test_move_repeated_install_and_whatif_do_not_change_user_path(self):
        preview = self.root / "preview only"
        invocation = (
            self.install_command()
            + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes"
        )
        result = self.run_powershell(
            "$ErrorActionPreference = 'Stop'\n"
            "$initialUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')\n"
            "$initialProcessPath = $env:Path\n"
            + invocation + "\n" + invocation + "\n"
            + self.install_command()
            + " -InstallDir " + powershell_literal(preview) + " -NoPathUpdate -WhatIf\n"
            + "if ($initialUserPath -cne [Environment]::GetEnvironmentVariable('Path', 'User')) { throw 'User PATH changed' }\n"
            + "if ($initialProcessPath -cne $env:Path) { throw 'Process PATH changed' }\n"
        )
        self.assertEqual((self.destination / "git-workflow.exe").read_bytes(), self.package_bytes["git-workflow.exe"])
        self.assertFalse(preview.exists())
        self.assertIn("What if:", result.stdout)

    def test_relative_install_directory_uses_powershell_current_location(self):
        process_directory = self.root / "process directory"
        shell_directory = self.root / "shell directory"
        process_directory.mkdir()
        shell_directory.mkdir()
        self.run_powershell(
            "$ErrorActionPreference = 'Stop'\n"
            "[Environment]::CurrentDirectory = " + powershell_literal(process_directory) + "\n"
            "Set-Location -LiteralPath " + powershell_literal(shell_directory) + "\n"
            + self.install_command()
            + " -InstallDir 'relative bin' -NoPathUpdate -Yes\n"
        )
        self.assertTrue((shell_directory / "relative bin/git-workflow.exe").is_file())
        self.assertFalse((process_directory / "relative bin/git-workflow.exe").exists())

    def test_uninstall_preview_no_path_update_and_repeated_removal(self):
        self.run_powershell(
            "$ErrorActionPreference = 'Stop'\n"
            "$initialUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')\n"
            "$initialProcessPath = $env:Path\n"
            + self.install_command()
            + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes\n"
            + self.uninstall_command()
            + " -InstallDir " + powershell_literal(self.destination) + " -WhatIf\n"
            + "if (-not (Test-Path -LiteralPath " + powershell_literal(self.destination / "git-workflow.exe")
            + ")) { throw 'Preview removed CLI' }\n"
            + "Set-Content -LiteralPath " + powershell_literal(self.destination / "other-tool.txt") + " -Value 'keep'\n"
            + (self.uninstall_command()
               + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes\n") * 2
            + "if ($initialUserPath -cne [Environment]::GetEnvironmentVariable('Path', 'User')) { throw 'User PATH changed' }\n"
            + "if ($initialProcessPath -cne $env:Path) { throw 'Process PATH changed' }\n"
        )
        self.assertFalse((self.destination / "git-workflow.exe").exists())
        self.assertFalse((self.destination / ".git-workflow-cli.json").exists())
        self.assertTrue((self.destination / "other-tool.txt").is_file())

    def mock_user_path_helpers(self):
        # Replace only the two user-PATH APIs in temporary copies. Production
        # scripts run fully, but the real registry/user environment is never written.
        for script in (self.source / "install-cli.ps1", self.source / "uninstall-cli.ps1", self.uninstall_driver):
            content = script.read_text(encoding="utf-8").replace(
                "[Environment]::GetEnvironmentVariable('Path', 'User')", "(Get-TestUserPath)"
            ).replace(
                "[Environment]::SetEnvironmentVariable('Path', $newUserPath, 'User')",
                "Set-TestUserPath $newUserPath",
            )
            script.write_text(content, encoding="utf-8")
        self.package_bytes = {path.name: path.read_bytes() for path in self.source.iterdir()}
        return (
            "$ErrorActionPreference = 'Stop'\n"
            "function Get-TestUserPath { return $global:TestUserPath }\n"
            "function Set-TestUserPath([string]$value) { $global:TestUserPath = $value }\n"
        )

    def test_uninstall_only_removes_owned_user_path_and_preserves_raw_other_entries(self):
        prefix = self.mock_user_path_helpers()
        install = self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -Yes\n"
        uninstall = self.uninstall_command() + " -InstallDir " + powershell_literal(self.destination) + " -Yes\n"
        self.run_powershell(
            prefix + "$global:TestUserPath = '%SYSTEMROOT%\\other;;C:\\Tools;'\n"
            "$expectedPath = $global:TestUserPath\n"
            + install * 2 + uninstall
            + "if ($global:TestUserPath -cne $expectedPath) { throw 'Uninstall changed unrelated PATH entries' }\n"
        )
        for name, content in self.package_bytes.items():
            (self.source / name).write_bytes(content)
        self.run_powershell(
            prefix + "$global:TestUserPath = " + powershell_literal(self.destination) + " + ';%SYSTEMROOT%\\other'\n"
            "$expectedPath = $global:TestUserPath\n" + install + uninstall
            + "if ($global:TestUserPath -cne $expectedPath) { throw 'Uninstall removed preexisting PATH entry' }\n"
        )
        self.assertFalse((self.destination / "git-workflow.exe").exists())

    def test_legacy_installation_retains_untracked_path(self):
        prefix = self.mock_user_path_helpers()
        self.destination.mkdir()
        shutil.copyfile(self.source / "git-workflow.exe", self.destination / "git-workflow.exe")
        result = self.run_powershell(
            prefix + "$global:TestUserPath = " + powershell_literal(self.destination) + "\n"
            "$expectedPath = $global:TestUserPath\n"
            + self.uninstall_command()
            + " -InstallDir " + powershell_literal(self.destination) + " -Yes\n"
            + "if ($global:TestUserPath -cne $expectedPath) { throw 'Untracked PATH changed' }\n"
        )
        self.assertFalse((self.destination / "git-workflow.exe").exists())
        self.assertIn("No CLI installation receipt found", result.stdout + result.stderr)

    def test_invalid_receipt_stops_before_removing_executable(self):
        self.destination.mkdir()
        executable = self.destination / "git-workflow.exe"
        executable.write_bytes(b"keep")
        (self.destination / ".git-workflow-cli.json").write_text(
            '{"schema": 1, "install_dir": "different location", "path_added": true}', encoding="utf-8"
        )
        with self.assertRaises(subprocess.CalledProcessError) as failure:
            self.run_powershell(
                self.uninstall_command()
                + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes"
            )
        self.assertIn("Invalid CLI installation receipt", failure.exception.stderr)
        self.assertEqual(executable.read_bytes(), b"keep")

    def test_confirmation_cancel_then_approve_install_and_uninstall(self):
        install = self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate\n"
        uninstall = self.uninstall_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate\n"
        executable = powershell_literal(self.destination / "git-workflow.exe")
        result = self.run_powershell(
            "$ErrorActionPreference = 'Stop'\n"
            "[Console]::OutputEncoding = [Text.UTF8Encoding]::new()\n"
            "function Read-Host([string]$Prompt) { Write-Host $Prompt; return $global:TestAnswer }\n"
            "$global:TestAnswer = 'n'\n" + install
            + "if (Test-Path -LiteralPath " + powershell_literal(self.destination) + ") { throw 'Cancelled install wrote files' }\n"
            + "$global:TestAnswer = 'y'\n" + install
            + "if (-not (Test-Path -LiteralPath " + executable + ")) { throw 'Approved install did not copy CLI' }\n"
            + "$global:TestAnswer = ''\n" + uninstall
            + "if (-not (Test-Path -LiteralPath " + executable + ")) { throw 'Cancelled uninstall removed CLI' }\n"
            + "$global:TestAnswer = 'yes'\n" + uninstall
            + "if (Test-Path -LiteralPath " + executable + ") { throw 'Approved uninstall left CLI' }\n"
        )
        self.assertEqual(result.stdout.count("Operasi dibatalkan"), 2)
        self.assertIn(chr(0x2713) + " Installed CLI:", result.stdout)
        self.assertIn(chr(0x2713) + " Install CLI sukses", result.stdout)
        self.assertIn(chr(0x2713) + " Uninstall CLI sukses", result.stdout)
        self.assertNotIn("\x1b", result.stdout)

    def test_noninteractive_execution_requires_yes_before_writing(self):
        install = self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate"
        result = self.run_powershell(install, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("-Yes", result.stderr)
        self.assertFalse(self.destination.exists())
        self.run_powershell(install + " -Yes")
        uninstall = self.uninstall_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate"
        result = self.run_powershell(uninstall, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.destination / "git-workflow.exe").exists())

    def test_ascii_output_encoding_uses_readable_success_marker(self):
        result = self.run_powershell(
            "[Console]::OutputEncoding = [Text.Encoding]::ASCII\n"
            + self.install_command()
            + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes"
        )
        self.assertIn("[OK] Install CLI sukses", result.stdout)
        self.assertTrue((self.destination / "git-workflow.exe").is_file())

    def test_pause_runs_after_cancel_success_and_validation_error(self):
        # Replace only the terminal input APIs in isolated copies; execute the
        # actual finally blocks even though the test process has redirected input.
        for helper in (self.source / "install-cli.ps1", self.source / "uninstall-cli.ps1", self.uninstall_driver):
            content = helper.read_text(encoding="utf-8").replace(
                "[Console]::IsInputRedirected", "$false"
            ).replace("$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')", "(Read-TestKey)")
            helper.write_text(content, encoding="utf-8")
        prefix = (
            "$ErrorActionPreference = 'Stop'\n"
            "function Read-Host([string]$Prompt) { Write-Host $Prompt; return $global:TestAnswer }\n"
            "function Read-TestKey { Write-Host '[TEST] closing key read' }\n"
        )
        install = self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate\n"
        uninstall = self.uninstall_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate\n"
        result = self.run_powershell(
            prefix + "$global:TestAnswer = 'n'\n" + install
            + "$global:TestAnswer = 'y'\n" + install
            + "$global:TestAnswer = 'n'\n" + uninstall
            + "$global:TestAnswer = 'y'\n" + uninstall
        )
        self.assertEqual(result.stdout.count("[TEST] closing key read"), 4)
        self.assertEqual(result.stdout.count("Operasi dibatalkan"), 2)
        self.assertIn("Install CLI sukses", result.stdout)
        self.assertIn("Uninstall CLI sukses", result.stdout)

        # Both helpers fail before asking for operation confirmation.
        self.destination.mkdir()
        (self.destination / ".git-workflow-cli.json").write_text("invalid json", encoding="utf-8")
        for helper in (self.source / "install-cli.ps1", self.uninstall_driver):
            # The installer moved itself; restore it to exercise missing EXE.
            if not helper.exists():
                content = (PROJECT_ROOT / "scripts/install-cli.ps1").read_text(encoding="utf-8")
                helper.write_text(content.replace("[Console]::IsInputRedirected", "$false").replace(
                    "$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')", "(Read-TestKey)"
                ), encoding="utf-8")
            command = "& " + powershell_literal(helper) + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate"
            result = self.run_powershell(prefix + command, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertLess(result.stdout.index("[ERROR]"), result.stdout.index("[TEST] closing key read"))
            result = self.run_powershell(prefix + command + " -NoPause", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("[TEST] closing key read", result.stdout)

    def test_no_pause_retains_operation_confirmation(self):
        result = self.run_powershell(
            "function Read-Host([string]$Prompt) { Write-Host $Prompt; return 'n' }\n"
            + self.install_command() + " -InstallDir " + powershell_literal(self.destination)
            + " -NoPathUpdate -NoPause"
        )
        self.assertIn("[y/N]", result.stdout)
        self.assertIn("Operasi dibatalkan", result.stdout)
        self.assertNotIn("Tekan tombol", result.stdout)
        self.assertFalse(self.destination.exists())

    def test_complete_package_is_cut_and_installed_helper_cleans_custom_directory(self):
        self.run_powershell(self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes")
        self.assertEqual(list(self.source.iterdir()), [])
        for name, content in self.package_bytes.items():
            self.assertEqual((self.destination / name).read_bytes(), content)
        self.run_powershell(
            "Set-Location -LiteralPath " + powershell_literal(self.destination) + "\n"
            "& " + powershell_literal(self.destination / "uninstall-cli.ps1") + " -NoPathUpdate -Yes"
        )
        self.assertFalse(self.destination.exists())

    def test_conflicting_destination_and_incomplete_archive_do_not_move_files(self):
        self.destination.mkdir()
        conflicting = self.destination / "README.md"
        conflicting.write_text("other tool", encoding="utf-8")
        command = self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes"
        result = self.run_powershell(command, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(conflicting.read_text(), "other tool")
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, self.package_bytes)
        conflicting.unlink()
        (self.source / "Panduan-Git-Workflow.md").unlink()
        result = self.run_powershell(command, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.source / "git-workflow.exe").exists())
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_tampered_package_inventory_cannot_remove_files_outside_installation(self):
        self.run_powershell(self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes")
        receipt = self.destination / ".git-workflow-cli.json"
        metadata = json.loads(receipt.read_text(encoding="utf-8-sig"))
        metadata["files"][0] = "../other-file"
        receipt.write_text(json.dumps(metadata), encoding="utf-8")
        result = self.run_powershell(self.uninstall_command() + " -NoPathUpdate -Yes", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.destination / "git-workflow.exe").is_file())
        self.assertTrue((self.destination / "README.md").is_file())

    def test_preview_preserves_every_source_file(self):
        self.run_powershell(self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -WhatIf")
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, self.package_bytes)
        self.assertFalse(self.destination.exists())

    def test_default_windows_folder_and_empty_product_parent_are_removed(self):
        isolated_appdata = self.root / "isolated appdata"
        default_dir = isolated_appdata / "Programs/git-workflow/bin"
        self.run_powershell(
            "$env:LOCALAPPDATA = " + powershell_literal(isolated_appdata) + "\n"
            + self.install_command() + " -NoPathUpdate -Yes\n"
            + "Set-Location -LiteralPath " + powershell_literal(default_dir) + "\n"
            + "& " + powershell_literal(default_dir / "uninstall-cli.ps1") + " -NoPathUpdate -Yes"
        )
        self.assertFalse(default_dir.parent.exists())
        self.assertTrue(default_dir.parent.parent.is_dir())
        self.assertEqual(list(self.source.iterdir()), [])

    def test_file_launch_resolves_default_directory_in_windows_powershell(self):
        isolated_appdata = self.root / "file launch appdata"
        destination = isolated_appdata / "Programs/git-workflow/bin"
        environment = os.environ.copy()
        environment["LOCALAPPDATA"] = str(isolated_appdata)
        # Windows PowerShell 5.1 may not populate PSScriptRoot while evaluating
        # parameter defaults with -File. Cover that launcher as well as pwsh.
        runners = list(dict.fromkeys(filter(None, (POWERSHELL, shutil.which("powershell")))))
        for runner in runners:
            with self.subTest(runner=runner):
                for name, content in self.package_bytes.items():
                    (self.source / name).write_bytes(content)
                for helper in (self.source / "install-cli.ps1", destination / "uninstall-cli.ps1"):
                    result = subprocess.run(
                        [runner, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
                         str(helper), "-NoPathUpdate", "-Yes"],
                        cwd=self.root, env=environment, capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(destination.parent.exists())

    def test_update_from_fresh_archive_moves_new_docs_and_retains_unrelated_files(self):
        command = self.install_command() + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate -Yes"
        self.run_powershell(command)
        (self.destination / "other-tool.txt").write_text("keep", encoding="utf-8")
        for name, content in self.package_bytes.items():
            (self.source / name).write_bytes(content)
        (self.source / "README.md").write_text("new release docs", encoding="utf-8")
        self.run_powershell(command)
        self.assertEqual(list(self.source.iterdir()), [])
        self.assertEqual((self.destination / "README.md").read_text(), "new release docs")
        self.run_powershell(self.uninstall_command() + " -NoPathUpdate -Yes")
        self.assertEqual([p.name for p in self.destination.iterdir()], ["other-tool.txt"])


if __name__ == "__main__":
    unittest.main()
