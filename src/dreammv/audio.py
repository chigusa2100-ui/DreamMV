"""Audio analysis helpers for DreamMV."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import librosa


class AudioAnalyzer:
    """Extract basic metadata from an audio file."""

    def analyze(self, path: str | Path, sample_rate: int = 22050, mono: bool = True) -> dict[str, Any]:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"音声ファイルが見つかりません: {source}")
        if not source.is_file():
            raise ValueError(f"音声ファイルではありません: {source}")
        if source.suffix.lower() not in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}:
            raise ValueError(f"対応していない音声形式です: {source.suffix}")

        try:
            audio, sr = librosa.load(str(source), sr=sample_rate, mono=mono)
            duration = float(librosa.get_duration(y=audio, sr=sr))
        except Exception as exc:
            raise RuntimeError(f"音声を解析できませんでした。\n{exc}") from exc

        return {
            "title": source.stem,
            "source_path": str(source.resolve()),
            "duration": duration,
            "duration_seconds": round(duration, 3),
            "sample_rate": int(sr),
            "channels": 1 if mono else None,
            "format": source.suffix.lower().lstrip("."),
        }
