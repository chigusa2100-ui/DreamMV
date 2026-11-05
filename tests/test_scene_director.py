import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dreammv.planner import StoryPlanner

class SceneDirectorTests(unittest.TestCase):
    def setUp(self):
        self.planner = StoryPlanner(scene_duration=5)
        self.theme = {
            "main_character": "a silver-haired anime girl in a blue coat",
            "emotion_keywords": {"hope": ["希望", "未来"]},
            "emotion_styles": {"hope": "golden sunrise glow"},
            "locations": ["sunlit rooftop"],
            "stages": [{"name": "Opening", "prompt": "cinematic anime scene", "description": "opening"}],
        }
        self.planner.themes = {"default": self.theme}
        self.planner.detect_theme = lambda lyrics: "default"

    def test_interprets_action_location_time_and_emotion(self):
        plan = self.planner.create_plan(5, [{"start": 0, "end": 5, "text": "希望を胸に海辺を走り、夜明けの空を見上げる"}])
        scene = plan["scenes"][0]
        self.assertEqual(scene["director"]["subject"], self.theme["main_character"])
        self.assertEqual(scene["director"]["action"], "running")
        self.assertIn("ocean", scene["director"]["setting"])
        self.assertEqual(scene["director"]["time_of_day"], "at dawn")
        self.assertEqual(scene["emotion"], "hope")
        self.assertIn("scene action: running", scene["prompt"])
        self.assertIn("golden sunrise glow", scene["prompt"])

    def test_empty_lyric_has_no_invented_director_content(self):
        direction = self.planner.direct_scene("", self.theme)
        self.assertTrue(all(value is None for value in direction.values()))

    def test_fallback_camera_motion_uses_engine_supported_values(self):
        plan = self.planner.create_plan(5, [{"start": 0, "end": 5, "text": "希望の未来"}])
        self.assertEqual(plan["scenes"][0]["camera_motion"], "zoom_in")

    def test_theme_character_is_kept_consistent_across_scenes(self):
        plan = self.planner.create_plan(10, [
            {"start": 0, "end": 5, "text": "海辺を歩く"},
            {"start": 5, "end": 10, "text": "星空を見上げる"},
        ])
        self.assertEqual(plan["scenes"][0]["director"]["continuity"], plan["scenes"][1]["director"]["continuity"])

if __name__ == "__main__":
    unittest.main()
