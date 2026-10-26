"""Validate DreamMV theme JSON files and planner compatibility."""
import json
from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
THEME_DIR = ROOT / "config" / "themes"
REQUIRED_STAGE_KEYS = {"name", "description", "prompt"}

class ThemeDataTests(unittest.TestCase):
    def test_all_theme_files_are_valid_json(self):
        files = sorted(THEME_DIR.glob("*.json"))
        self.assertGreaterEqual(len(files), 10)
        names = set()
        for path in files:
            with self.subTest(file=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict)
                self.assertTrue(data.get("name"))
                self.assertIsInstance(data.get("keywords"), list)
                self.assertTrue(data["keywords"])
                self.assertIsInstance(data.get("stages"), list)
                self.assertGreaterEqual(len(data["stages"]), 3)
                names.add(data["name"])
                for stage in data["stages"]:
                    self.assertIsInstance(stage, dict)
                    self.assertTrue(REQUIRED_STAGE_KEYS.issubset(stage))
                    self.assertTrue(stage["prompt"].strip())
        self.assertEqual(len(names), len(files))

    def test_planner_loads_themes_and_generates_prompts(self):
        from dreammv.planner import StoryPlanner
        planner = StoryPlanner(scene_duration=10)
        self.assertGreaterEqual(len(planner.themes), 10)
        plan = planner.create_plan(
            25,
            [{"start": 0, "end": 10, "text": "狐 神社 祈り"}],
        )
        self.assertEqual(plan["scene_count"], 3)
        self.assertTrue(all(scene["prompt"] for scene in plan["scenes"]))

if __name__ == "__main__":
    unittest.main()
