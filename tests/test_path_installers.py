"""Test extracted-archive PATH helpers in isolated temporary directories."""
from __future__ import annotations

import base64
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
        (self.source / "git-workflow").write_bytes(b"#!/bin/sh\nexit 0\n")
        self.user_home = self.root / "isolated home"
        self.user_home.mkdir()
        self.bin_directory = self.root / "bin [literal] $`'"
        self.environment = os.environ.copy()
        self.environment["HOME"] = shell_path(self.user_home)
        self.environment["SHELL"] = "/bin/bash"

    def run_shell(self, command):
        return subprocess.run(
            [BASH, *command], env=self.environment,
            cwd=str(self.root), capture_output=True, text=True, check=True,
        )

    def install(self, *extra):
        return self.run_shell([
            shell_path(self.source / "install-cli.sh"),
            "--bin-dir", shell_path(self.bin_directory), *extra,
        ])

    def sourced_path(self, *profiles):
        sourcing = "; ".join(". " + shlex.quote(shell_path(profile)) for profile in profiles)
        return self.run_shell(["-c", sourcing + '; printf "%s" "$PATH"']).stdout

    def test_explicit_profile_quotes_literal_path_and_is_idempotent(self):
        selected = self.root / "custom profile"
        self.install("--profile", shell_path(selected))
        first = selected.read_bytes()
        self.install("--profile", shell_path(selected))
        self.assertEqual(selected.read_bytes(), first)
        self.assertEqual(first.count(b"# Git Workflow CLI"), 1)
        self.assertEqual((self.bin_directory / "git-workflow").read_bytes(), (self.source / "git-workflow").read_bytes())
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


@unittest.skipUnless(POWERSHELL, "PowerShell is unavailable")
class PowerShellInstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="git-workflow-powershell-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "release archive"
        self.source.mkdir()
        shutil.copy2(PROJECT_ROOT / "scripts/install-cli.ps1", self.source / "install-cli.ps1")
        (self.source / "git-workflow.exe").write_bytes(bytes(range(20)))
        self.destination = self.root / "installed [literal]"

    def run_powershell(self, script):
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            cwd=str(self.root), capture_output=True, text=True, check=True,
        )

    def test_copy_repeated_install_and_whatif_do_not_change_user_path(self):
        preview = self.root / "preview only"
        invocation = (
            "& " + powershell_literal(self.source / "install-cli.ps1")
            + " -InstallDir " + powershell_literal(self.destination) + " -NoPathUpdate"
        )
        result = self.run_powershell(
            "$ErrorActionPreference = 'Stop'\n"
            "$initialUserPath = [Environment]::GetEnvironmentVariable('Path', 'User')\n"
            "$initialProcessPath = $env:Path\n"
            + invocation + "\n" + invocation + "\n"
            + "& " + powershell_literal(self.source / "install-cli.ps1")
            + " -InstallDir " + powershell_literal(preview) + " -NoPathUpdate -WhatIf\n"
            + "if ($initialUserPath -cne [Environment]::GetEnvironmentVariable('Path', 'User')) { throw 'User PATH changed' }\n"
            + "if ($initialProcessPath -cne $env:Path) { throw 'Process PATH changed' }\n"
        )
        self.assertEqual((self.destination / "git-workflow.exe").read_bytes(), (self.source / "git-workflow.exe").read_bytes())
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
            "& " + powershell_literal(self.source / "install-cli.ps1")
            + " -InstallDir 'relative bin' -NoPathUpdate\n"
        )
        self.assertTrue((shell_directory / "relative bin/git-workflow.exe").is_file())
        self.assertFalse((process_directory / "relative bin/git-workflow.exe").exists())


if __name__ == "__main__":
    unittest.main()
