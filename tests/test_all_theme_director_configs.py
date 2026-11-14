import json
import re
from pathlib import Path
import unittest

THEME_DIR = Path(__file__).resolve().parents[1] / "config" / "themes"


class AllThemeDirectorConfigTests(unittest.TestCase):
    pass


def make_theme_test(theme_path):
    def test_theme(self):
        with self.subTest(theme=theme_path.stem):
            data = json.loads(theme_path.read_text(encoding="utf-8-sig"))

            self.assertIsInstance(data, dict)
            self.assertEqual(data.get("name"), theme_path.stem)

            self.assertTrue(
                isinstance(data.get("character_description"), str)
                and data["character_description"].strip(),
                "character_description is missing",
            )

            director = data.get("director")
            self.assertIsInstance(director, dict, "director is missing")

            character = director.get("character")
            self.assertIsInstance(character, dict, "director.character is missing")

            self.assertTrue(
                isinstance(character.get("description"), str)
                and character["description"].strip(),
                "director.character.description is missing",
            )

            rules = character.get("consistency_rules")
            self.assertIsInstance(rules, list, "consistency_rules must be a list")
            self.assertTrue(rules, "consistency_rules is empty")

            visual = director.get("visual_language")
            self.assertIsInstance(visual, dict, "visual_language is missing")

            for key in (
                "action_style",
                "environment_style",
                "lighting_style",
                "composition_style",
            ):
                self.assertTrue(
                    isinstance(visual.get(key), str) and visual[key].strip(),
                    f"visual_language.{key} is missing",
                )

            self.assertIsInstance(
                visual.get("visual_motifs"),
                list,
                "visual_motifs must be a list",
            )

            progression = director.get("scene_progression")
            self.assertIsInstance(progression, list, "scene_progression must be a list")
            self.assertTrue(progression, "scene_progression is empty")

            camera = director.get("camera_guidance")
            self.assertIsInstance(camera, dict, "camera_guidance is missing")
            self.assertIsInstance(
                camera.get("available_styles"),
                list,
                "camera_guidance.available_styles must be a list",
            )
            self.assertTrue(
                isinstance(camera.get("principle"), str)
                and camera["principle"].strip(),
                "camera_guidance.principle is missing",
            )

            stages = data.get("stages")
            self.assertIsInstance(stages, list, "stages must be a list")
            self.assertTrue(stages, "stages is empty")

            for index, stage in enumerate(stages):
                self.assertIsInstance(stage, dict, f"stage {index} must be an object")
                self.assertTrue(
                    isinstance(stage.get("name"), str) and stage["name"].strip(),
                    f"stage {index}: name is missing",
                )
                self.assertTrue(
                    isinstance(stage.get("prompt"), str) and stage["prompt"].strip(),
                    f"stage {index}: prompt is missing",
                )

    return test_theme


theme_files = sorted(THEME_DIR.glob("*.json"))

for theme_path in theme_files:
    safe_name = re.sub(r"\W+", "_", theme_path.stem)
    test_name = f"test_theme_{safe_name}"
    setattr(
        AllThemeDirectorConfigTests,
        test_name,
        make_theme_test(theme_path),
    )


if __name__ == "__main__":
    unittest.main()
