"""Exercise the installed release helper and actual changelog output contract."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import git_workflow as cli
from scripts.release import release_notes


class SkillReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="git-workflow-release-skill-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        original = tempfile.mkdtemp
        backup = patch.object(cli.tempfile, "mkdtemp", side_effect=lambda *a, **kw: original(*a, dir=self.root, **kw))
        backup.start()
        self.addCleanup(backup.stop)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.manage_installation(self.root, agents=("cursor",), apply=True), 0)
        path = self.root / ".cursor/skills/git-workflow/scripts/release_notes.py"
        spec = importlib.util.spec_from_file_location("bundled_release_notes", path)
        self.notes = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.notes
        self.addCleanup(sys.modules.pop, spec.name)
        spec.loader.exec_module(self.notes)

    def test_installed_helper_matches_current_repository_release_body(self):
        changelog = (Path(cli.__file__).parent / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(self.notes.render(changelog, cli.VERSION, project_name="Git Workflow"),
                         release_notes(changelog, cli.VERSION))

    def test_exact_middle_version_excludes_neighbors_comments_and_examples(self):
        content = """# Changelog
<!-- ## [1.2.0] - 2026-10-08 -->
```markdown
## [1.2.0] - 2026-10-08
- Example only.
```
## [1.3.0] - 2026-10-08
### Added
- Future change.
## [1.2.0] - 2026-10-08
### Fixed
- Perbaikan yang diverifikasi.
## [1.1.0] - 2026-10-07
### Added
- Previous change.
"""
        self.assertEqual(self.notes.render(content, "1.2.0", project_name="Produk"),
                         "## 📋 Apa yang Baru di v1.2.0?\n\n### Fixed\n- Perbaikan yang diverifikasi.\n")

    def test_missing_duplicate_empty_and_invalid_version_fail(self):
        header = "## [1.2.0] - 2026-10-08\n"
        valid = header + "### Fixed\n- Perbaikan.\n"
        for content, version in ((valid, "1.2.1"), (valid + valid, "1.2.0"),
                                 (header + "### Fixed\n", "1.2.0"), (valid, "01.2.0")):
            with self.subTest(content=content, version=version), self.assertRaises(ValueError):
                self.notes.render(content, version, project_name="Produk")

    def test_notes_file_is_exact_and_changelog_is_preserved(self):
        changelog = self.root / "CHANGELOG.md"
        original = b"## [1.2.0] - 2026-10-08\n### Fixed\n- Perbaikan.\n"
        changelog.write_bytes(original)
        output = self.root / ".release/release-notes.md"
        args = ["--changelog", str(changelog), "--version", "1.2.0", "--project-name", "Produk"]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.notes.main(args + ["--output", str(output)]), 0)
        self.assertEqual(output.read_text(encoding="utf-8"), "## 📋 Apa yang Baru di v1.2.0?\n\n### Fixed\n- Perbaikan.\n")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.notes.main(args + ["--output", str(changelog)])
        self.assertEqual(changelog.read_bytes(), original)

    def test_category_only_legacy_output_and_explicit_previous_are_supported(self):
        content = "## [1.2.0] - 2026-10-08\n### Fixed\n- Baru.\n## [1.1.0] - 2026-10-07\n### Added\n- Lama.\n"
        self.assertEqual(self.notes.render(content, "1.2.0"), "### Fixed\n- Baru.\n")
        extended = self.notes.render(content, "1.2.0", previous="1.1.0", project_name="Produk")
        self.assertIn("#### Added\n- Lama.", extended)
        self.assertTrue(extended.startswith("## 📋 Apa yang Baru di v1.2.0?\n"))

    def test_redirected_stdout_preserves_heading_emoji_as_utf8(self):
        changelog = self.root / "CHANGELOG.md"
        changelog.write_text("## [1.2.0] - 2026-10-09\n### Fixed\n- Perbaikan.\n", encoding="utf-8")
        data = io.BytesIO()
        stream = io.TextIOWrapper(data, encoding="ascii")
        with redirect_stdout(stream):
            self.assertEqual(self.notes.main([
                "--changelog", str(changelog), "--version", "1.2.0", "--project-name", "Produk",
            ]), 0)
        stream.flush()
        self.assertEqual(data.getvalue().decode("utf-8").splitlines()[0], "## 📋 Apa yang Baru di v1.2.0?")


if __name__ == "__main__":
    unittest.main()
