"""Exercise ownership across agents using real temporary installations."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import git_workflow as cli
import test_cli
from test_cli import snapshot, working_directory


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="git-workflow-agents-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.repo.mkdir()
        self.home.mkdir()
        (self.repo / ".git").mkdir()
        for name in ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "HERMES_HOME", "PI_CODING_AGENT_DIR", "OMP_PROFILE", "PI_PROFILE"):
            env = patch.dict(os.environ, {name: ""})
            env.start()
            self.addCleanup(env.stop)
        home = patch.object(Path, "home", return_value=self.home)
        home.start()
        self.addCleanup(home.stop)
        original = tempfile.mkdtemp
        backup = patch.object(cli.tempfile, "mkdtemp", side_effect=lambda *a, **kw: original(*a, dir=self.root, **kw))
        backup.start()
        self.addCleanup(backup.stop)

    def invoke(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with working_directory(self.repo), redirect_stdout(output), redirect_stderr(error):
            result = cli.main(list(args) + ["--plain"])
        self.assertEqual(result, 0, output.getvalue() + error.getvalue())
        return output.getvalue()

    def manifest(self, global_install=False):
        return json.loads((self.home / ".config/git-workflow/install.json" if global_install else self.repo / ".agents/git-workflow-install.json").read_bytes())

    def test_every_agent_real_local_and_global_install_and_roundtrip(self):
        for scope in ([], ["--global"]):
            with self.subTest(scope=scope):
                before = snapshot(self.root)
                self.invoke("install", "--agent", "all", *scope)
                self.assertEqual(before, snapshot(self.root))
                self.invoke("install", "--agent", "all", *scope, "--apply")
                root = self.home if scope else self.repo
                manifest = self.manifest(bool(scope))
                self.assertEqual(set(manifest["agents"]), set(cli.AGENTS))
                for agent, info in cli.AGENTS.items():
                    skill = root / info[2 if scope else 1] / "git-workflow"
                    self.assertEqual((skill / "VERSION").read_text().strip(), cli.VERSION)
                    self.assertTrue((skill / "references/commitmsg.md").is_file())
                    self.assertNotIn(".agents/rules", (skill / "SKILL.md").read_text())
                    for name in manifest["agents"][agent]["files"]:
                        self.assertEqual(cli.digest(cli.check_path(root, name).read_bytes()), manifest["files"][name])
                self.assertIn("All manifest files intact", self.invoke("status", *scope))
                installed = snapshot(self.root)
                self.assertIn("Already installed", self.invoke("install", "--agent", "all", *scope, "--apply"))
                self.assertEqual(installed, snapshot(self.root))
                self.invoke("uninstall", "--agent", "all", *scope, "--apply")
                self.assertFalse((root / (".config/git-workflow/install.json" if scope else ".agents/git-workflow-install.json")).exists())

    def test_partial_install_update_and_uninstall_preserve_other_agents(self):
        self.invoke("install", "--agent", "claude-code,codex", "--apply")
        claude = snapshot(self.repo / ".claude")
        self.invoke("install", "--agent", "cursor", "--apply")
        self.assertEqual(claude, snapshot(self.repo / ".claude"))
        self.assertEqual(set(self.manifest()["agents"]), {"claude-code", "codex", "cursor"})
        self.invoke("uninstall", "--agent", "cursor", "--apply")
        self.assertEqual(claude, snapshot(self.repo / ".claude"))
        self.assertEqual(set(self.manifest()["agents"]), {"claude-code", "codex"})

    def test_shared_file_last_owner_and_managed_block(self):
        self.invoke("install", "--agent", "codex,antigravity,amp", "--apply")
        before = snapshot(self.repo / ".agents/skills")
        self.invoke("uninstall", "--agent", "codex", "--apply")
        self.assertEqual(before, snapshot(self.repo / ".agents/skills"))
        self.assertIn(cli.BEGIN, (self.repo / "AGENTS.md").read_text())
        self.invoke("uninstall", "--agent", "antigravity", "--apply")
        self.assertEqual(before, snapshot(self.repo / ".agents/skills"))
        self.invoke("uninstall", "--agent", "amp", "--apply")
        self.assertFalse((self.repo / ".agents/skills/git-workflow").exists())
        self.assertFalse((self.repo / "AGENTS.md").exists())

    def test_shared_global_paths_and_versions(self):
        self.invoke("install", "--agent", "codex,pi,zcode", "--global", "--apply")
        with patch.object(cli, "VERSION", "9.1.0"):
            self.invoke("install", "--agent", "pi", "--global", "--apply")
        self.assertEqual({record["version"] for record in self.manifest(True)["agents"].values()}, {"9.1.0"})
        self.invoke("uninstall", "--agent", "pi", "--global", "--apply")
        self.assertTrue((self.home / ".agents/skills/git-workflow/SKILL.md").exists())

    def test_legacy_manifest_is_migrated_without_losing_unselected_ownership(self):
        self.invoke("install", "--agent", "codex,antigravity-ide,antigravity-cli", "--global", "--apply")
        path = self.home / ".config/git-workflow/install.json"
        manifest = self.manifest(True)
        manifest.pop("agents")
        manifest.pop("schema")
        path.write_text(json.dumps(manifest))
        self.invoke("install", "--agent", "cursor", "--global", "--apply")
        self.assertEqual(set(self.manifest(True)["agents"]), {*cli.LEGACY_AGENTS, "cursor"})
        self.invoke("uninstall", "--agent", "codex", "--global", "--apply")
        self.assertTrue((self.home / ".gemini/config/skills/git-workflow/SKILL.md").exists())

    def test_selected_status_ignores_other_agent_changes(self):
        self.invoke("install", "--agent", "codex,cursor", "--apply")
        (self.repo / ".cursor/skills/git-workflow/VERSION").unlink()
        self.assertIn("All manifest files intact", self.invoke("status", "--agent", "codex"))

    def test_unknown_agent_rejected_before_any_writes(self):
        before = snapshot(self.root)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.main(["install", "--agent", "unknown", "--apply"])
        self.assertEqual(before, snapshot(self.root))

    def test_tampered_ownership_cannot_remove_another_agents_files(self):
        self.invoke("install", "--agent", "codex,cursor", "--apply")
        path = self.repo / ".agents/git-workflow-install.json"
        manifest = self.manifest()
        manifest["agents"]["codex"]["files"].append(".cursor/skills/git-workflow/VERSION")
        path.write_text(json.dumps(manifest))
        before = snapshot(self.root)
        with working_directory(self.repo), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["uninstall", "--agent", "codex", "--apply"]), 2)
        self.assertEqual(before, snapshot(self.root))

    def test_external_config_roots_and_changed_environment_are_protected(self):
        config = self.root / "external config"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
            self.invoke("install", "--agent", "amp,opencode", "--global", "--apply")
            self.assertTrue((config / "opencode/skills/git-workflow/SKILL.md").is_file())
            self.assertTrue((config / "agents/skills/git-workflow/SKILL.md").is_file())
        before = snapshot(self.root)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["uninstall", "--global", "--apply"]), 2)
        self.assertEqual(before, snapshot(self.root))
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
            self.invoke("uninstall", "--agent", "opencode", "--global", "--apply")
            self.assertTrue((config / "agents/skills/git-workflow/SKILL.md").is_file())

    def test_global_ownership_cannot_claim_another_legacy_agents_directory(self):
        self.invoke("install", "--agent", "codex,antigravity-ide", "--global", "--apply")
        path = self.home / ".config/git-workflow/install.json"
        manifest = self.manifest(True)
        manifest["agents"]["codex"]["files"].extend(manifest["agents"].pop("antigravity-ide")["files"])
        path.write_text(json.dumps(manifest))
        before = snapshot(self.root)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["uninstall", "--agent", "codex", "--global", "--apply"]), 2)
        self.assertEqual(before, snapshot(self.root))

    def test_unrelated_invalid_environment_does_not_block_selected_agent(self):
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "relative/path"}):
            self.invoke("install", "--agent", "codex", "--global", "--apply")
            self.invoke("uninstall", "--agent", "codex", "--global", "--apply")

    def test_named_omp_profile_and_external_agent_homes(self):
        env = {"OMP_PROFILE": "work", "CLAUDE_CONFIG_DIR": str(self.root / "claude"),
               "HERMES_HOME": str(self.root / "hermes")}
        with patch.dict(os.environ, env):
            self.invoke("install", "--agent", "oh-my-pi,claude,hermes", "--global", "--apply")
            for path in (self.home / ".omp/profiles/work/agent/skills", self.root / "claude/skills", self.root / "hermes/skills"):
                self.assertTrue((path / "git-workflow/SKILL.md").is_file())
            self.invoke("uninstall", "--agent", "all", "--global", "--apply")

    def test_custom_roots_that_alias_share_ownership(self):
        base = self.root / "shared config"
        with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(base), "HERMES_HOME": str(base)}):
            self.invoke("install", "--agent", "claude,hermes", "--global", "--apply")
            records = self.manifest(True)["agents"]
            self.assertEqual(records["claude-code"]["files"], records["hermes"]["files"])
            self.invoke("uninstall", "--agent", "claude", "--global", "--apply")
            self.assertTrue((base / "skills/git-workflow/SKILL.md").is_file())
            self.invoke("uninstall", "--agent", "hermes", "--global", "--apply")
            self.assertFalse((base / "skills/git-workflow").exists())

    def test_bundled_inventory_uses_each_agents_version_and_external_paths(self):
        config = self.root / "custom config"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
            self.invoke("install", "--agent", "claude,opencode", "--global", "--apply")
            with patch.object(cli, "VERSION", "9.4.0"):
                self.invoke("install", "--agent", "opencode", "--global", "--apply")
            for skill, version in ((self.home / ".claude/skills/git-workflow", cli.VERSION),
                                   (config / "opencode/skills/git-workflow", "9.4.0")):
                result = subprocess.run([sys.executable, "-I", str(skill / "scripts/check_installation.py"),
                                         "--skill-dir", str(skill), "--user-home", str(self.home)],
                                        cwd=self.repo, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stderr)
                inventory = json.loads(result.stdout)
                active = next(row for row in inventory["installations"] if row["active"])
                self.assertEqual(active["recorded_version"], version)
                self.assertEqual(active["status"], "installed_verified", active)
                self.assertEqual(inventory["active_version"], version)


class SetupTests(unittest.TestCase):
    setUp = test_cli.CliTests.setUp
    interactive = test_cli.CliTests.interactive
    def test_setup_selects_multiple_agents_and_decline_stays_read_only(self):
        result, output = self.interactive(["codex,cursor", "1", "n"], ["setup"])
        self.assertEqual(result, 0)
        self.assertIn("Selected agents", output)
        self.assertFalse((self.repo / ".agents").exists())

    def test_setup_apply_installs_selected_agents(self):
        result, output = self.interactive(["claude,roo", "1", "y"], ["setup"])
        self.assertEqual(result, 0, output)
        self.assertTrue((self.repo / ".claude/skills/git-workflow/SKILL.md").is_file())
        self.assertTrue((self.repo / ".roo/skills/git-workflow/SKILL.md").is_file())
        self.assertFalse((self.repo / "AGENTS.md").exists())

    def test_setup_replace_previews_and_backs_up_modified_files(self):
        result, output = self.interactive(["claude", "1", "y"], ["setup"])
        self.assertEqual(result, 0, output)
        skill = self.repo / ".claude/skills/git-workflow/SKILL.md"
        skill.write_bytes(b"custom local edits")
        result, output = self.interactive(["claude", "1", "n"], ["setup", "--replace"])
        self.assertEqual(result, 0, output)
        self.assertEqual(skill.read_bytes(), b"custom local edits")
        result, output = self.interactive(["claude", "1", "y"], ["setup", "--replace"])
        self.assertEqual(result, 0, output)
        self.assertNotEqual(skill.read_bytes(), b"custom local edits")
