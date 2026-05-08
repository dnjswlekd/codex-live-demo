"""
Project-local agent skill packaging checks.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestProjectSkills(unittest.TestCase):
    def test_codex_skills_directory_not_used(self):
        self.assertFalse((ROOT / ".codex" / "skills").exists())

    def test_project_commands_restored(self):
        commands = {
            "harness.md": "Harness",
            "review.md": "리뷰",
        }

        for command_name, content_hint in commands.items():
            with self.subTest(command=command_name):
                command_file = ROOT / ".codex" / "commands" / command_name
                self.assertTrue(command_file.exists())
                self.assertIn(content_hint, command_file.read_text(encoding="utf-8"))

    def test_project_skills_exist_with_frontmatter(self):
        skills = {
            "harness": "Harness",
            "project-review": "review",
        }

        for skill_name, description_hint in skills.items():
            with self.subTest(skill=skill_name):
                skill_file = ROOT / ".agents" / "skills" / skill_name / "SKILL.md"
                self.assertTrue(skill_file.exists())

                content = skill_file.read_text(encoding="utf-8")
                self.assertTrue(content.startswith("---\n"))
                self.assertIn(f"name: {skill_name}\n", content)
                self.assertIn("description: ", content)
                self.assertIn(description_hint, content)


if __name__ == "__main__":
    unittest.main()
