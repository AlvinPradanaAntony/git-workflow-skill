"""Exercise project discovery and the actual bundled installer lifecycle."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import git_workflow as cli


class TtyBuffer(io.StringIO):
    def isatty(self):
        return True

    @property
    def encoding(self):
        return "utf-8"


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="git-workflow-cli-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repository"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.child = self.repo / "src" / "nested"
        self.child.mkdir(parents=True)
        self.other = self.root / "outside"
        self.other.mkdir()
        create_temporary_directory = tempfile.mkdtemp
        managed_backups = patch.object(
            cli.tempfile, "mkdtemp",
            side_effect=lambda *args, **kwargs: create_temporary_directory(
                *args, dir=str(self.root), **kwargs
            ),
        )
        managed_backups.start()
        self.addCleanup(managed_backups.stop)

    def invoke(self, args, directory=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with working_directory(directory or self.child), redirect_stdout(stdout), redirect_stderr(stderr):
            result = cli.main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    def assert_parser_error(self, args, directory=None):
        with self.assertRaises(SystemExit) as caught:
            self.invoke(args, directory)
        self.assertEqual(caught.exception.code, 2)

    def test_no_arguments_print_help_without_writes(self):
        before = snapshot(self.root)
        result, stdout, _ = self.invoke([])
        self.assertEqual(result, 0)
        self.assertIn("usage: git-workflow", stdout)
        self.assertEqual(snapshot(self.root), before)

    def test_help_and_version_do_not_invoke_installer(self):
        for argument in ("--help", "--version"):
            with self.subTest(argument=argument), patch.object(cli, "manage_installation") as engine:
                with self.assertRaises(SystemExit) as caught:
                    self.invoke([argument], self.other)
                self.assertEqual(caught.exception.code, 0)
                engine.assert_not_called()
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit):
            cli.main(["--version"])
        self.assertEqual(output.getvalue().strip(), f"Git Workflow {cli.VERSION}")
        self.assertEqual(snapshot(self.root), {})

    def test_nearest_git_root_accepts_directory_and_worktree_file(self):
        self.assertEqual(cli.find_project_root(self.child), self.repo.resolve())
        nested_repo = self.child / "worktree"
        nested_repo.mkdir()
        (nested_repo / ".git").write_text("gitdir: /unused/worktree-metadata\n", encoding="utf-8")
        leaf = nested_repo / "packages"
        leaf.mkdir()
        self.assertEqual(cli.find_project_root(leaf), nested_repo.resolve())
        self.assertIsNone(cli.find_project_root(self.other))

    def test_discovered_root_ignores_script_and_frozen_paths(self):
        with patch.object(cli, "__file__", str(self.other / "git_workflow.py")), \
                patch.object(cli.sys, "frozen", True, create=True), \
                patch.object(cli, "manage_installation", return_value=0) as engine:
            result, _, _ = self.invoke(["install"])
        self.assertEqual(result, 0)
        engine.assert_called_once_with(self.repo.resolve(), global_install=False, remove=False, apply=False, replace=False)

    def test_project_install_dry_run_apply_idempotency_and_uninstall(self):
        existing_agents = b"# Existing instructions\nKeep the user's project conventions.\n"
        (self.repo / "AGENTS.md").write_bytes(existing_agents)
        before = snapshot(self.repo)
        result, stdout, _ = self.invoke(["install"])
        self.assertEqual(result, 0)
        self.assertIn("Dry run only", stdout)
        self.assertEqual(snapshot(self.repo), before)

        result, _, _ = self.invoke(["--apply"])
        self.assertEqual(result, 0)
        skill = self.repo / ".agents" / "skills" / "git-workflow"
        self.assertTrue((skill / "SKILL.md").is_file())
        self.assertEqual((skill / "VERSION").read_text(encoding="utf-8").strip(), cli.VERSION)
        self.assertTrue((self.repo / "AGENTS.md").read_bytes().startswith(existing_agents))
        manifest_path = self.repo / ".agents" / "git-workflow-install.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], cli.VERSION)
        installed = snapshot(self.repo)

        result, stdout, _ = self.invoke(["install", "--apply"])
        self.assertEqual(result, 0)
        self.assertIn("Already installed", stdout)
        self.assertEqual(snapshot(self.repo), installed)
        result, stdout, _ = self.invoke(["uninstall"])
        self.assertEqual(result, 0)
        self.assertIn("Dry run only", stdout)
        self.assertEqual(snapshot(self.repo), installed)
        result, _, _ = self.invoke(["uninstall", "--apply"])
        self.assertEqual(result, 0)
        self.assertFalse(manifest_path.exists())
        self.assertFalse(skill.exists())
        remaining_agents = (self.repo / "AGENTS.md").read_bytes()
        self.assertTrue(remaining_agents.startswith(existing_agents))
        self.assertNotIn(cli.BEGIN.encode(), remaining_agents)

    def test_modified_file_blocks_install_and_uninstall_without_partial_writes(self):
        self.assertEqual(self.invoke(["install", "--apply"])[0], 0)
        skill_path = self.repo / ".agents" / "skills" / "git-workflow" / "SKILL.md"
        changed = skill_path.read_bytes() + b"\nUser customization\n"
        skill_path.write_bytes(changed)
        before = snapshot(self.repo)
        for command in ("install", "uninstall"):
            with self.subTest(command=command):
                result, _, stderr = self.invoke([command, "--apply"])
                self.assertEqual(result, 2)
                self.assertIn("--replace", stderr)
                self.assertEqual(snapshot(self.repo), before)

        backup_root = self.root / "backups"
        backup_root.mkdir()
        with patch.object(cli.tempfile, "mkdtemp", return_value=str(backup_root)):
            result, stdout, _ = self.invoke(["uninstall", "--replace", "--apply"])
        self.assertEqual(result, 0)
        self.assertIn("Exact previous-file backup", stdout)
        self.assertEqual((backup_root / ".agents" / "skills" / "git-workflow" / "SKILL.md").read_bytes(), changed)
        self.assertFalse(skill_path.exists())

    def test_one_version_controls_output_payload_and_upgrade_manifest(self):
        with patch.object(cli, "VERSION", "2.12.4"):
            self.assertEqual(self.invoke(["install", "--apply"])[0], 0)
        before = snapshot(self.repo)
        with patch.object(cli, "VERSION", "9.2.0"):
            output = io.StringIO()
            with redirect_stdout(output), self.assertRaises(SystemExit):
                cli.main(["--version"])
            self.assertEqual(output.getvalue().strip(), "Git Workflow 9.2.0")
            self.assertEqual(cli.load_payload()[".agents/skills/git-workflow/VERSION"], "9.2.0\n")
            self.assertEqual(self.invoke(["install", "--apply"])[0], 0)
        after = snapshot(self.repo)
        version_path = ".agents/skills/git-workflow/VERSION"
        manifest_path = ".agents/git-workflow-install.json"
        self.assertEqual(after[version_path], b"9.2.0\n")
        manifest = json.loads(after[manifest_path])
        self.assertEqual(manifest["version"], "9.2.0")
        self.assertEqual(manifest["files"][version_path], cli.digest(after[version_path]))
        self.assertEqual({name for name in before if before[name] != after[name]},
                         {version_path, manifest_path})

    def test_explicit_project_can_target_existing_directory_outside_git(self):
        with patch.object(cli, "manage_installation", return_value=0) as engine:
            result, _, _ = self.invoke(["--project", str(self.other), "--apply"], self.other)
        self.assertEqual(result, 0)
        engine.assert_called_once_with(self.other.resolve(), global_install=False, remove=False, apply=True, replace=False)

    def test_global_routes_to_engine_without_home_writes_or_discovery(self):
        with patch.object(cli, "find_project_root") as discovery, \
                patch.object(cli, "manage_installation", return_value=0) as engine:
            result, _, _ = self.invoke(["uninstall", "--global", "--replace", "--apply"], self.other)
        self.assertEqual(result, 0)
        discovery.assert_not_called()
        engine.assert_called_once_with(Path.home().resolve(), global_install=True, remove=True, apply=True, replace=True)
        self.assertEqual(snapshot(self.root), {})

    def test_legacy_uninstall_flag_is_supported(self):
        with patch.object(cli, "manage_installation", return_value=0) as engine:
            self.invoke(["--uninstall"])
        engine.assert_called_once_with(self.repo.resolve(), global_install=False, remove=True, apply=False, replace=False)

    def test_ambiguous_or_unknown_arguments_fail_before_writes(self):
        for arguments in (
            ["install", "--uninstall"],
            ["--global", "--project", str(self.repo)],
            ["install", "uninstall"],
            ["--unknown"],
        ):
            with self.subTest(arguments=arguments), patch.object(cli, "manage_installation") as engine:
                self.assert_parser_error(arguments)
                engine.assert_not_called()
        self.assertEqual(snapshot(self.root), {})

    def test_outside_repository_reports_explicit_scope_hints(self):
        stderr = io.StringIO()
        with working_directory(self.other), redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
            cli.main(["install"])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("--project PATH", stderr.getvalue())
        self.assertIn("--global", stderr.getvalue())
        self.assertEqual(snapshot(self.root), {})

    def test_python_distribution_runs_alone_from_another_directory(self):
        script = self.other / "git_workflow.py"
        shutil.copyfile(Path(cli.__file__), script)
        temporary = self.root / "process-temp"
        temporary.mkdir()
        environment = dict(os.environ, TMP=str(temporary), TEMP=str(temporary), TMPDIR=str(temporary))

        def run(*arguments):
            result = subprocess.run(
                [sys.executable, "-I", str(script), *arguments], cwd=self.child,
                env=environment, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout

        before = snapshot(self.repo)
        self.assertIn("usage: git-workflow", run())
        self.assertEqual(run("--version").strip(), f"Git Workflow {cli.VERSION}")
        self.assertIn("Dry run only", run("install"))
        self.assertEqual(snapshot(self.repo), before)
        run("install", "--apply")
        self.assertTrue((self.repo / ".agents/skills/git-workflow/SKILL.md").is_file())
        self.assertFalse((self.child / ".agents").exists())
        self.assertIn("Already installed", run("install", "--apply"))
        run("uninstall", "--apply")
        self.assertFalse((self.repo / ".agents/skills/git-workflow").exists())
        self.assertEqual([file.name for file in self.other.iterdir()], ["git_workflow.py"])

    def test_engine_errors_are_reported_cleanly(self):
        with patch.object(cli, "manage_installation", side_effect=ValueError("Unsafe package path")):
            result, _, stderr = self.invoke(["install"])
        self.assertEqual(result, 2)
        self.assertIn("Installation stopped: Unsafe package path", stderr)

    def interactive(self, answers, args=None):
        stdout = TtyBuffer()
        with working_directory(self.child), patch.dict(os.environ, {"CI": "", "TERM": "xterm"}), \
                patch.object(cli.sys, "stdin", TtyBuffer()), redirect_stdout(stdout), \
                patch("builtins.input", side_effect=answers):
            result = cli.main([] if args is None else args)
        return result, stdout.getvalue()

    def test_menu_navigation_and_declined_plan_do_not_write(self):
        before = snapshot(self.root)
        result, output = self.interactive(["bad", "4", "5", "1", "codex", "1", "n", "0"])
        self.assertEqual(result, 0)
        for text in ("A g e n t i c", "Interactive menu", "Unknown selection", "Agent commands", "Quick start", "Preview"):
            self.assertIn(text, output)
        self.assertEqual(snapshot(self.root), before)

    def test_menu_install_status_and_uninstall_use_selected_repo(self):
        result, output = self.interactive(["1", "codex", "1", "y", "3", "codex", "1", "2", "codex", "1", "y", "0"])
        self.assertEqual(result, 0)
        self.assertIn("All manifest files intact", output)
        self.assertIn("[4/4] Installation complete", output)
        self.assertIn("[4/4] Uninstall complete", output)
        self.assertIn("Apply file changes", output)
        self.assertIn("Remove managed files", output)
        self.assertFalse((self.repo / ".agents/skills/git-workflow").exists())
        self.assertFalse((self.child / ".agents").exists())

    def test_menu_requires_terminal_and_read_only_commands_reject_apply(self):
        for args in (["menu"], ["commands", "--apply"], ["status", "--replace"]):
            with self.subTest(args=args):
                self.assert_parser_error(args)
        self.assertEqual(snapshot(self.repo), {})

    def test_redirected_commands_do_not_prompt_or_emit_control_sequences(self):
        with patch("builtins.input", side_effect=AssertionError("Unexpected prompt")):
            result, output, _ = self.invoke(["commands"], self.other)
        self.assertEqual(result, 0)
        self.assertIn("gitrelease", output)
        self.assertNotIn("\033", output)
        self.assertNotIn("\r", output)

    def test_plain_and_no_color_and_ascii_fallback(self):
        with patch.dict(os.environ, {"CI": "", "TERM": "xterm", "NO_COLOR": ""}):
            output = TtyBuffer()
            with redirect_stdout(output), patch("builtins.input", side_effect=AssertionError("Unexpected prompt")):
                self.assertEqual(cli.main(["--plain"]), 0)
            self.assertIn("usage: git-workflow", output.getvalue())
            self.assertNotIn("\033", output.getvalue())
            ui = cli.TerminalUI(stream=TtyBuffer())
            self.assertFalse(ui.color)
            ui = cli.TerminalUI(no_color=True, stream=TtyBuffer())
            self.assertFalse(ui.color)
            ui.unicode = False
            ui.banner()
            cli.show_commands(ui)
            ui.stream.getvalue().encode("ascii")

    def test_narrow_terminal_wraps_panels_and_tables(self):
        output = TtyBuffer()
        with patch.dict(os.environ, {"CI": "", "TERM": "xterm", "NO_COLOR": ""}), \
                patch.object(cli.shutil, "get_terminal_size", return_value=os.terminal_size((32, 24))):
            ui = cli.TerminalUI(stream=output)
            ui.banner()
            ui.table("Target", [("Directory", "a very long project directory with spaces/and/a/long/file.md")])
            ui.panel("Help", ["Run inside a Git repository or select --project PATH."])
            ui.step(1, "Inspect installed skill and read metadata")
        self.assertTrue(all(len(line) <= 32 for line in output.getvalue().splitlines()))

    def test_banner_asset_and_standalone_and_frozen_fallback_match(self):
        asset = Path(cli.__file__).resolve().parent / "assets/banner/ASCIILogo.txt"
        self.assertEqual(cli.BANNER, asset.read_text(encoding="utf-8-sig"))
        for frozen in (False, True):
            with self.subTest(frozen=frozen), patch.object(cli, "__file__", str(self.other / "git_workflow.py")), \
                    patch.object(cli.sys, "frozen", frozen, create=True), \
                    patch.dict(os.environ, {"CI": "", "TERM": "xterm", "NO_COLOR": ""}):
                output = TtyBuffer()
                ui = cli.TerminalUI(stream=output)
                ui.width = 90
                ui.banner()
                self.assertIn(cli.BANNER.strip(), output.getvalue().strip())

    def test_status_is_read_only_and_reports_changed_missing_and_unsafe_files(self):
        self.assertEqual(self.invoke(["install", "--apply"])[0], 0)
        skill = self.repo / ".agents/skills/git-workflow/SKILL.md"
        skill.write_bytes(skill.read_bytes() + b"\nPersonal edits\n")
        (self.repo / ".agents/skills/git-workflow/VERSION").unlink()
        before = snapshot(self.repo)
        result, output, _ = self.invoke(["status"])
        self.assertEqual(result, 1)
        self.assertIn("MODIFIED", output)
        self.assertIn("MISSING", output)
        self.assertEqual(snapshot(self.repo), before)
        path = self.repo / ".agents/git-workflow-install.json"
        manifest = json.loads(path.read_bytes())
        manifest["files"]["../private.txt"] = "a" * 64
        path.write_text(json.dumps(manifest), encoding="utf-8")
        before = snapshot(self.repo)
        result, _, error = self.invoke(["status"])
        self.assertEqual(result, 2)
        self.assertIn("Unsafe installer manifest", error)
        self.assertEqual(snapshot(self.repo), before)

    def test_keyboard_interrupt_rolls_back_install_and_uninstall(self):
        before = snapshot(self.repo)
        original_write = cli.atomic_write
        calls = 0

        def interrupted_write(path, data):
            nonlocal calls
            original_write(path, data)
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()

        with patch.object(cli, "atomic_write", side_effect=interrupted_write):
            self.assertEqual(self.invoke(["install", "--apply"])[0], 130)
        self.assertEqual(snapshot(self.repo), before)
        self.assertEqual(self.invoke(["install", "--apply"])[0], 0)
        before = snapshot(self.repo)
        original_unlink = Path.unlink
        interrupted = False

        def interrupted_unlink(path, *args, **kwargs):
            nonlocal interrupted
            original_unlink(path, *args, **kwargs)
            if not interrupted and self.repo in path.parents:
                interrupted = True
                raise KeyboardInterrupt()

        with patch.object(Path, "unlink", interrupted_unlink):
            self.assertEqual(self.invoke(["uninstall", "--apply"])[0], 130)
        self.assertEqual(snapshot(self.repo), before)


if __name__ == "__main__":
    unittest.main()
