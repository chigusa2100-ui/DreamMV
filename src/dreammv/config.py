"""DreamMV configuration.

The defaults are intentionally conservative for local development. Settings can be
changed in config.json in the project root without editing Python source.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "scene_duration": 5,
    "audio_sample_rate": 22050,
    "audio_mono": True,
    "output_subdir": "output",
    "scenes_subdir": "scenes",
    "project_filename": "project.json",
    "job_filename": "job.json",
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load JSON settings, falling back to defaults when no file exists.

    Invalid existing configuration raises ValueError with a readable explanation;
    it is safer to report the problem than silently ignore a user's settings.
    """
    config = DEFAULT_CONFIG.copy()
    if path is None:
        path = Path.cwd() / "config.json"
    else:
        path = Path(path)

    if path.exists():
        try:
            user_config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"設定ファイルを読み込めません: {path}\n{exc}") from exc
        if not isinstance(user_config, dict):
            raise ValueError("config.json の内容は JSON オブジェクトである必要があります。")
        config.update(user_config)

    try:
        duration = float(config["scene_duration"])
        sample_rate = int(config["audio_sample_rate"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("scene_duration と audio_sample_rate の設定値を確認してください。") from exc

    if duration <= 0:
        raise ValueError("scene_duration は 0 より大きい値にしてください。")
    if sample_rate <= 0:
        raise ValueError("audio_sample_rate は 0 より大きい値にしてください。")

    config["scene_duration"] = duration
    config["audio_sample_rate"] = sample_rate
    return config


def write_default_config(path: str | Path) -> Path:
    """Create a default config file, but never overwrite an existing one."""
    target = Path(path)
    if not target.exists():
        target.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return target
