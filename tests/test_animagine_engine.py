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

    def test_gui_uses_animagine_label_and_settings(self):
        source = (ROOT / "DreamMV.py").read_text(encoding="utf-8")
        self.assertIn("anime_settings.json", source)
        self.assertIn("AnimagineでMV生成", source)
        self.assertNotIn("preset=settings.get", source)


if __name__ == "__main__":
    unittest.main()
