"""Regression tests for the Animagine-only render path."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AnimagineEngineTests(unittest.TestCase):
    def test_animagine_config_targets_sdxl_stills_and_720p_output(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from src.dreammv.anime_engine import ANIME_CONFIG

        self.assertEqual(ANIME_CONFIG["repo"], "cagliostrolab/animagine-xl-4.0")
        self.assertEqual((ANIME_CONFIG["width"], ANIME_CONFIG["height"]), (1280, 720))
        self.assertGreater(ANIME_CONFIG["steps"], 0)

    def test_active_renderer_does_not_import_wan_engine(self):
        source = (ROOT / "src" / "dreammv" / "render_worker.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module or "")
            elif isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
        self.assertNotIn("wan_engine", imported_modules)

    def test_render_worker_forwards_separate_camera_motion(self):
        source = (ROOT / "src" / "dreammv" / "render_worker.py").read_text(encoding="utf-8")
        self.assertIn('camera_motion=scene.get("camera_motion")', source)

    def test_gui_supports_animagine_and_ltx25_engine_selection(self):
        source = (ROOT / "DreamMV.py").read_text(encoding="utf-8")
        self.assertIn("anime_settings.json", source)
        self.assertIn('"animagine"', source)
        self.assertIn('"ltx25"', source)
        self.assertIn('"LTX-2.5', source)
        self.assertIn("self.render_button = QPushButton(", source)
        self.assertNotIn("preset=settings.get", source)


    def test_animagine_load_uses_local_files_only(self):
        source = (ROOT / "src" / "dreammv" / "anime_engine.py").read_text(encoding="utf-8")
        self.assertIn("local_files_only=True", source)
        self.assertIn("Animagine XL 4.0 is not installed locally", source)
        self.assertIn("installer\\\\download_model.py", source)

    def test_installer_makes_both_model_downloads_optional(self):
        source = (ROOT / "installer" / "install.ps1").read_text(encoding="utf-8")
        self.assertIn('Read-YesNo "Download Animagine XL 4.0 now?"', source)
        self.assertIn('Read-YesNo "Download approximately 66 GB of LTX-2.5 model files now?"', source)
        self.assertIn('Skipping Animagine XL 4.0.', source)
        self.assertIn('Skipping LTX-2.5 model download.', source)


if __name__ == "__main__":
    unittest.main()
