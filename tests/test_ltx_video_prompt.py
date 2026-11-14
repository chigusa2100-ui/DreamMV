import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from dreammv.render_worker import build_ltx_video_prompt


class LTXVideoPromptTests(unittest.TestCase):

    def test_director_character_and_action_reach_video_prompt(self):
        scene = {
            "prompt": "anime cinematic illustration, sunrise over the ocean",
            "director": {
                "subject": "a silver-haired female anime protagonist in a blue coat",
                "continuity": "the same silver-haired female protagonist",
                "action": "running toward the horizon",
                "setting": "by the ocean",
                "time_of_day": "at dawn",
                "lighting": "soft golden sunrise light",
                "composition": "dynamic wide shot",
            },
            "camera_motion": "zoom_in",
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertIn("silver-haired female anime protagonist", prompt)
        self.assertIn("running toward the horizon", prompt)
        self.assertIn("by the ocean", prompt)
        self.assertIn("at dawn", prompt)
        self.assertIn("soft golden sunrise light", prompt)
        self.assertIn("moves closer", prompt)
        self.assertIn("visible, coherent movement", prompt)

    def test_visual_language_and_motifs_are_included(self):
        scene = {
            "prompt": "cinematic anime scene",
            "director": {
                "action_style": "expressive natural movement",
                "environment_style": "detailed futuristic city",
                "lighting_style": "soft blue highlights",
                "composition_style": "cinematic framing",
                "visual_motifs": ["blue butterflies", "glowing flowers"],
            },
            "camera_style": "tracking shot from behind",
            "camera_motion": "pan_left",
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertIn("expressive natural movement", prompt)
        self.assertIn("detailed futuristic city", prompt)
        self.assertIn("soft blue highlights", prompt)
        self.assertIn("blue butterflies", prompt)
        self.assertIn("glowing flowers", prompt)
        self.assertIn("tracking shot from behind", prompt)
        self.assertIn("pans to the left", prompt)

    def test_legacy_scene_without_director_remains_supported(self):
        scene = {
            "prompt": "anime scene from an older project",
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertIn("anime scene from an older project", prompt)
        self.assertIn("visual continuity", prompt)

    def test_invalid_director_data_does_not_crash(self):
        scene = {
            "prompt": "cinematic anime scene",
            "director": None,
            "camera_motion": "unsupported",
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertIn("cinematic anime scene", prompt)
        self.assertNotIn("unsupported", prompt)


    def test_lyric_text_is_excluded_but_director_guidance_remains(self):
        lyric = "NEVER_DISPLAY_THIS_LYRIC_12345"
        scene = {
            "prompt": "cinematic anime scene",
            "lyric": lyric,
            "director": {
                "subject": "a silver-haired female protagonist",
                "action": "turning toward a distant light",
                "setting": "on a quiet seaside cliff",
            },
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertNotIn(lyric, prompt)
        self.assertNotIn("Core lyrical meaning to visualize", prompt)
        self.assertIn("silver-haired female protagonist", prompt)
        self.assertIn("turning toward a distant light", prompt)
        self.assertIn("on a quiet seaside cliff", prompt)
        self.assertIn("visible, coherent movement", prompt)

    def test_character_continuity_is_included_separately(self):
        scene = {
            "prompt": "cinematic anime scene",
            "director": {
                "subject": "a silver-haired female protagonist",
                "continuity": "the same female protagonist with silver hair and blue eyes",
            },
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertIn("Main character:", prompt)
        self.assertIn("Character identity and continuity:", prompt)
        self.assertIn("blue eyes", prompt)

    def test_empty_lyric_does_not_affect_video_prompt(self):
        scene = {
            "prompt": "cinematic anime scene",
            "lyric": "   ",
        }

        prompt = build_ltx_video_prompt(scene)

        self.assertNotIn("Core lyrical meaning to visualize", prompt)


if __name__ == "__main__":
    unittest.main()
