
"""Narration-to-illustration project creation.

This service is intentionally separate from the existing music MV pipeline.
It creates a narration project and its scene plan, but does not render video.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.dreammv.narration_planner import NarrationPlanner
from src.dreammv.whisper_engine import WhisperEngine


class NarrationProjectService:
    """Create a project from a narrated audio file."""

    SUPPORTED_AUDIO_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".flac",
        ".ogg",
        ".m4a",
        ".aac",
    }

    def __init__(
        self,
        whisper_engine: WhisperEngine | None = None,
        planner: NarrationPlanner | None = None,
    ) -> None:
        self.whisper_engine = whisper_engine or WhisperEngine()
        self.planner = planner or NarrationPlanner()

    def create_project(
        self,
        audio_file: str | Path,
        project_dir: str | Path,
        title: str | None = None,
        audio_duration: float | None = None,
    ) -> dict[str, Any]:
        """Transcribe audio and save a standalone narration project."""

        source = Path(audio_file).expanduser().resolve()
        destination = Path(project_dir).expanduser().resolve()

        if not source.is_file():
            raise FileNotFoundError(
                f"朗読音声ファイルが見つかりません: {source}"
            )

        if source.suffix.lower() not in self.SUPPORTED_AUDIO_EXTENSIONS:
            raise ValueError(
                "対応していない音声形式です: "
                f"{source.suffix or '(拡張子なし)'}"
            )

        # Avoid accidentally placing the project inside the source directory
        # or overwriting an existing project.
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError(
                f"保存先フォルダが空ではありません: {destination}"
            )

        destination.mkdir(parents=True, exist_ok=True)

        audio_dir = destination / "audio"
        output_dir = destination / "output"
        audio_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)

        copied_audio = audio_dir / source.name

        try:
            if source != copied_audio.resolve():
                shutil.copy2(source, copied_audio)

            # Whisper returns timestamped segments:
            # [{"start": float, "end": float, "text": str}, ...]
            segments = self.whisper_engine.transcribe(copied_audio)

            plan = self.planner.create_plan(
                segments=segments,
                audio_duration=audio_duration,
                title=title or source.stem,
            )

            plan["audio_file"] = str(
                copied_audio.relative_to(destination)
            )

            plan["status"] = "planned"

            plan_path = destination / "narration_plan.json"
            transcript_path = destination / "transcript.json"

            self._write_json(plan_path, plan)
            self._write_json(
                transcript_path,
                {
                    "audio_file": plan["audio_file"],
                    "audio_duration": plan["audio_duration"],
                    "transcript": plan["transcript"],
                    "segments": segments,
                },
            )

            # Keep narration metadata separate from the existing music queue.
            project_metadata = {
                "schema_version": 1,
                "project_type": "narration_illustrations",
                "title": plan["title"],
                "audio_file": plan["audio_file"],
                "audio_duration": plan["audio_duration"],
                "scene_duration": plan["scene_duration"],
                "render_clip_duration": plan["render_clip_duration"],
                "scene_count": plan["scene_count"],
                "status": "planned",
                "plan_file": "narration_plan.json",
                "transcript_file": "transcript.json",
            }

            self._write_json(
                destination / "project.json",
                project_metadata,
            )

            return {
                "project_dir": str(destination),
                "project": project_metadata,
                "plan": plan,
                "plan_path": str(plan_path),
                "transcript_path": str(transcript_path),
            }

        except Exception:
            # Do not silently delete files or folders: leave any partial output
            # available for inspection and recovery.
            raise

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
