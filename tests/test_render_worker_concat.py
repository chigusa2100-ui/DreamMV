"""Regression checks for Windows-safe FFmpeg concat-list generation."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RenderWorkerConcatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "src" / "dreammv" / "render_worker.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_concat_writer_uses_real_newlines_and_relative_names(self):
        function = next(
            node for node in self.tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_write_concat_file"
        )
        body = ast.get_source_segment(self.source, function)
        self.assertIn('"\\n".join(lines) + "\\n"', body)
        self.assertIn("clip.name", body)
        self.assertNotIn("resolve()", body)

    def test_concat_ffmpeg_runs_from_normalized_directory(self):
        self.assertIn('"-i", concat_txt.name', self.source)
        self.assertIn("cwd=norm_dir", self.source)

    def test_ffmpeg_error_details_are_preserved(self):
        self.assertIn("result.stderr", self.source)
        self.assertIn("FFmpeg の処理に失敗しました", self.source)


if __name__ == "__main__":
    unittest.main()
