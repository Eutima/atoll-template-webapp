from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = REPO_ROOT / ".claude" / "rules"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


class ClaudeMdLinksRulesTests(SimpleTestCase):
    def test_every_rules_file_is_referenced_in_claude_md(self) -> None:
        claude_md = CLAUDE_MD.read_text()
        rules_files = sorted(RULES_DIR.glob("*.md"))

        self.assertTrue(rules_files, f"no rules files found under {RULES_DIR}")

        for path in rules_files:
            rel = path.relative_to(REPO_ROOT).as_posix()
            with self.subTest(rules_file=rel):
                self.assertTrue(
                    rel in claude_md,
                    f"{rel} is not linked in CLAUDE.md — add a reference so the "
                    f"harness auto-loads it",
                )
