"""
Git hook checks for project validation before commit.
"""

import stat
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestGitHooks(unittest.TestCase):
    def test_pre_commit_hook_exists(self):
        self.assertTrue((ROOT / ".githooks" / "pre-commit").exists())

    def test_pre_commit_hook_runs_project_validation(self):
        content = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")

        self.assertIn("npm run lint", content)
        self.assertIn("npm run build", content)
        self.assertIn("npm run test", content)

    def test_pre_commit_hook_is_executable(self):
        mode = (ROOT / ".githooks" / "pre-commit").stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
