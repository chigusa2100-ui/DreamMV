import json
import tempfile
import unittest
from pathlib import Path

from src.dreammv.config import load_config, write_default_config


class ConfigTests(unittest.TestCase):
    def test_default_config_is_created_and_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            write_default_config(path)
            config = load_config(path)
            self.assertEqual(config["scene_duration"], 5)
            self.assertEqual(config["audio_sample_rate"], 22050)

    def test_does_not_overwrite_existing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"scene_duration": 7}), encoding="utf-8")
            write_default_config(path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["scene_duration"], 7)

    def test_invalid_config_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()

