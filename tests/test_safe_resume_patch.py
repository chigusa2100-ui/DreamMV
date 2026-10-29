"""Safety tests for assembling completed clips without rerunning image generation."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SafeResumePatchTests(unittest.TestCase):
    def test_gui_has_explicit_assemble_only_button(self):
        source = (ROOT / "DreamMV.py").read_text(encoding="utf-8")
        self.assertIn("完了済みシーンから再結合（再生成なし）", source)
        self.assertIn("def start_assemble_only(self):", source)
        self.assertIn("self.generate_button.setEnabled(False)", source)
        self.assertIn("self.assemble_button.clicked.connect(self.start_assemble_only)", source)

    def test_assemble_worker_does_not_load_animagine(self):
        source = (ROOT / "src" / "dreammv" / "render_worker.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AssembleWorker")
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
        run_source = ast.get_source_segment(source, methods[0])
        self.assertIn("self.queue.load()", run_source)
        self.assertIn("assemble(", run_source)
        self.assertNotIn("AnimeEngine(", run_source)
        self.assertNotIn("engine.load()", run_source)

    def test_existing_completed_outputs_are_checked_before_mux(self):
        source = (ROOT / "src" / "dreammv" / "render_worker.py").read_text(encoding="utf-8")
        self.assertIn("完了扱いですが動画ファイルが見つからないシーン", source)
        self.assertIn("self.project_dir / \"output\" / \"music_video.mp4\"", source)


if __name__ == "__main__":
    unittest.main()
