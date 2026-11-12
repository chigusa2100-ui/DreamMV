"""Tests for the native LTX-2.5 CLI engine."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from dreammv.ltx25_engine import (
    DEFAULT_FPS,
    JAPANESE_ANIME_STYLE,
    LTX25Engine,
    LTX25Error,
)


class LTX25EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.ltx_root = self.root / "LTX-2"
        self.model_root = self.root / "models"

        self.python = (
            self.ltx_root / ".venv" / "Scripts" / "python.exe"
        )
        self.python.parent.mkdir(parents=True, exist_ok=True)
        self.python.write_bytes(b"test")

        self.model_files = [
            self.model_root
            / "diffusion_models"
            / "ltx-2.5-22b-distilled-transformer-bf16.safetensors",
            self.model_root
            / "text_encoders"
            / "gemma4-12b-with-proj-ltx-2.5-bf16.safetensors",
            self.model_root
            / "vae"
            / "ltx-2.5-video-vae-bf16.safetensors",
            self.model_root
            / "vae"
            / "ltx-2.5-audio-vae-bf16.safetensors",
            self.model_root
            / "model_patches"
            / "ltx-2.5-duration-head-bf16.safetensors",
            self.model_root
            / "latent_upscale_models"
            / "ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors",
        ]

        for path in self.model_files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test")

        self.engine = LTX25Engine(
            ltx_root=self.ltx_root,
            model_root=self.model_root,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_validates_runtime_and_model_files(self):
        self.engine.load()

        self.assertTrue(self.engine._loaded)
        self.assertTrue(self.engine.python.is_file())

    def test_missing_model_file_is_reported(self):
        self.model_files[0].unlink()

        with self.assertRaises(LTX25Error) as context:
            self.engine.load()

        self.assertIn(
            str(self.model_files[0]),
            str(context.exception),
        )

    def test_frame_count_uses_ltx_temporal_stride(self):
        self.assertEqual(self.engine.frame_count(5), 121)
        self.assertEqual(self.engine.frame_count(5.2), 129)
        self.assertEqual(self.engine.frame_count(0.1), 9)

    def test_frame_count_is_always_eight_n_plus_one(self):
        for duration in (0.1, 1, 2.5, 5, 5.2, 10, 30):
            frames = self.engine.frame_count(duration)

            self.assertGreaterEqual(frames, 9)
            self.assertEqual((frames - 1) % 8, 0)

    def test_build_prompt_adds_japanese_anime_style(self):
        prompt = self.engine.build_prompt(
            "A girl walking through a futuristic city at night"
        )

        self.assertTrue(prompt.startswith(JAPANESE_ANIME_STYLE))
        self.assertIn(
            "A girl walking through a futuristic city at night",
            prompt,
        )

    def test_build_prompt_does_not_duplicate_existing_style(self):
        original = (
            "Japanese 2D anime illustration style, "
            "a girl standing beneath neon lights"
        )

        self.assertEqual(
            self.engine.build_prompt(original),
            original,
        )

    def test_empty_prompt_is_rejected(self):
        with self.assertRaises(LTX25Error):
            self.engine.build_prompt("   ")

    def test_build_command_uses_native_ltx_cli(self):
        output = self.root / "output" / "scene_001.mp4"

        command = self.engine.build_command(
            prompt="A cinematic anime scene",
            duration=5,
            output_path=output,
            seed=12345,
        )

        self.assertEqual(command[0], str(self.python))
        self.assertEqual(command[1:3], ["-m", "ltx_pipelines.distilled"])

        self.assertIn("--transformer-path", command)
        self.assertIn("--text-encoder-path", command)
        self.assertIn("--video-vae-path", command)
        self.assertIn("--audio-vae-path", command)
        self.assertIn("--duration-head-path", command)
        self.assertIn("--spatial-upsampler-path", command)

        self.assertIn("--offload", command)
        self.assertEqual(command[command.index("--offload") + 1], "disk")

        self.assertIn("--quantization", command)
        self.assertEqual(
            command[command.index("--quantization") + 1],
            "fp8-cast",
        )

        self.assertEqual(
            command[command.index("--num-frames") + 1],
            "121",
        )
        self.assertEqual(
            command[command.index("--frame-rate") + 1],
            str(DEFAULT_FPS),
        )
        self.assertEqual(
            command[command.index("--seed") + 1],
            "12345",
        )
        self.assertEqual(
            command[command.index("--output-path") + 1],
            str(output.resolve()),
        )

        prompt = command[command.index("--prompt") + 1]
        self.assertTrue(prompt.startswith(JAPANESE_ANIME_STYLE))
        self.assertIn("A cinematic anime scene", prompt)

        self.assertTrue(output.parent.is_dir())
        self.assertTrue(self.engine._loaded)

    def test_build_command_generates_seed_when_omitted(self):
        output = self.root / "output" / "random_seed.mp4"

        command = self.engine.build_command(
            prompt="A scene",
            duration=5,
            output_path=output,
        )

        seed = command[command.index("--seed") + 1]

        self.assertTrue(seed.isdigit())
        self.assertGreaterEqual(int(seed), 0)
        self.assertLess(int(seed), 2**31 - 1)

    def test_build_command_rejects_empty_prompt(self):
        output = self.root / "output" / "empty.mp4"

        with self.assertRaises(LTX25Error):
            self.engine.build_command(
                prompt="",
                duration=5,
                output_path=output,
            )

    def test_timeout_has_minimum_value(self):
        engine = LTX25Engine(
            ltx_root=self.ltx_root,
            model_root=self.model_root,
            timeout=1,
        )

        self.assertEqual(engine.timeout, 10.0)


if __name__ == "__main__":
    unittest.main()
