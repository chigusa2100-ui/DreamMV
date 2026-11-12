"""Regression checks for Windows-safe FFmpeg concat-list generation."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RenderWorkerConcatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            ROOT / "src" / "dreammv" / "render_worker.py"
        ).read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_concat_writer_uses_real_newlines_and_relative_names(self):
        function = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_write_concat_file"
        )
        body = ast.get_source_segment(self.source, function)

        self.assertIn('"\\n".join(lines) + "\\n"', body)
        self.assertIn("clip.name", body)
        self.assertNotIn("resolve()", body)

    def test_concat_ffmpeg_runs_from_normalized_directory(self):
        calls = [
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_run_ffmpeg"
        ]

        concat_call = next(
            call for call in calls
            if any(
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "concat_txt"
                and node.attr == "name"
                for node in ast.walk(call)
            )
        )

        cwd = next(
            keyword.value
            for keyword in concat_call.keywords
            if keyword.arg == "cwd"
        )

        self.assertIsInstance(cwd, ast.Name)
        self.assertEqual(cwd.id, "norm_dir")

    def test_ffmpeg_error_details_are_preserved(self):
        self.assertIn("result.stderr", self.source)
        self.assertIn("FFmpeg の処理に失敗しました", self.source)
        self.assertIn("details[-6000:]", self.source)


if __name__ == "__main__":
    unittest.main()
