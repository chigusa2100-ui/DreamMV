import unittest

from src.dreammv.planner import StoryPlanner


class ThemeDirectorConfigTests(unittest.TestCase):
    def setUp(self):
        self.planner = StoryPlanner(scene_duration=5)
        self.planner.themes = {
            "test_theme": {
                "name": "test_theme",
                "keywords": ["星"],
                "stages": [{"name": "星の世界", "description": "星空", "prompt": "anime starry sky"}],
                "color_palette": ["deep blue", "silver"],
                "locations": ["crystal observatory"],
                "emotion_keywords": {},
                "emotion_styles": {},
                "director": {
                    "character": {
                        "description": "same silver-haired anime protagonist"
                    },
                    "visual_language": {
                        "action_style": "clear expressive gestures",
                        "environment_style": "crystal observatory with star maps",
                        "lighting_style": "silver starlight",
                        "composition_style": "wide cinematic framing",
                        "visual_motifs": ["star maps", "crystal glass"],
                    },
                    "scene_progression": ["星の世界"],
                    "camera_guidance": {"principle": "vary framing"},
                },
            }
        }

    def test_director_character_and_visual_language_reach_prompt(self):
        plan = self.planner.create_plan(5, ["星を見上げる"])
        scene = plan["scenes"][0]
        self.assertIn("same silver-haired anime protagonist", scene["prompt"])
        self.assertIn("crystal observatory with star maps", scene["prompt"])
        self.assertIn("silver starlight", scene["prompt"])
        self.assertIn("star maps", scene["prompt"])
        self.assertEqual(scene["director"]["subject"], "same silver-haired anime protagonist")


if __name__ == "__main__":
    unittest.main()
