"""Tests for per-scene emotion and visual styling in StoryPlanner."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dreammv.planner import StoryPlanner


class ThemePromptEnhancementTests(unittest.TestCase):
    def setUp(self):
        self.planner = StoryPlanner(scene_duration=5)
        self.theme = {
            "name": "hope",
            "keywords": ["希望", "光", "未来"],
            "emotion_keywords": {
                "hope": ["希望", "光", "未来"],
                "struggle": ["暗闇", "負けない"],
            },
            "emotion_styles": {
                "hope": "radiant golden sunrise, uplifting atmosphere",
                "struggle": "dramatic shadows, determined atmosphere",
            },
            "camera_styles": ["wide cinematic shot", "close-up shot"],
            "color_palette": ["gold and blue", "violet and silver"],
            "locations": ["sunlit rooftop", "futuristic city street"],
            "stages": [
                {
                    "name": "Opening",
                    "description": "Opening scene",
                    "prompt": "cinematic anime scene",
                }
            ],
        }
        self.planner.themes = {"hope": self.theme}
        self.planner.detect_theme = lambda lyrics: "hope"

    def test_emotion_and_visual_styles_are_added_to_prompt(self):
        plan = self.planner.create_plan(
            5,
            [{"start": 0, "end": 5, "text": "希望の光を見つけて未来へ"}],
        )
        scene = plan["scenes"][0]

        self.assertEqual(scene["emotion"], "hope")
        self.assertIn("cinematic anime scene", scene["prompt"])
        self.assertIn("radiant golden sunrise", scene["prompt"])
        self.assertIn("camera: wide cinematic shot", scene["prompt"])
        self.assertIn("color palette: gold and blue", scene["prompt"])
        self.assertIn("setting: sunlit rooftop", scene["prompt"])

    def test_emotion_keyword_selects_matching_style(self):
        plan = self.planner.create_plan(
            5,
            [{"start": 0, "end": 5, "text": "暗闇でも負けない"}],
        )
        scene = plan["scenes"][0]

        self.assertEqual(scene["emotion"], "struggle")
        self.assertIn("dramatic shadows", scene["prompt"])

    def test_visual_options_cycle_by_scene_index(self):
        plan = self.planner.create_plan(
            10,
            [
                {"start": 0, "end": 5, "text": "希望"},
                {"start": 5, "end": 10, "text": "未来"},
            ],
        )
        first, second = plan["scenes"]

        self.assertIn("camera: wide cinematic shot", first["prompt"])
        self.assertIn("camera: close-up shot", second["prompt"])
        self.assertIn("color palette: gold and blue", first["prompt"])
        self.assertIn("color palette: violet and silver", second["prompt"])
        self.assertEqual(first["start"], 0)
        self.assertEqual(second["start"], 5)

    def test_missing_optional_fields_keep_base_prompt_working(self):
        prompt, emotion = self.planner.build_scene_prompt(
            {"prompt": "simple anime scene"},
            {},
            "",
            0,
        )
        self.assertEqual(prompt, "simple anime scene")
        self.assertIsNone(emotion)

    def test_no_matching_emotion_keeps_visual_styles(self):
        plan = self.planner.create_plan(
            5,
            [{"start": 0, "end": 5, "text": "知らない言葉"}],
        )
        scene = plan["scenes"][0]

        self.assertIsNone(scene["emotion"])
        self.assertNotIn("emotional visual style:", scene["prompt"])
        self.assertIn("camera: wide cinematic shot", scene["prompt"])


if __name__ == "__main__":
    unittest.main()
