"""Project creation and persistence for DreamMV."""

from __future__ import annotations

import json
import shutil

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from typing import Any

from .planner import StoryPlanner


class ProjectManager:
    """Create, load, and update a DreamMV project folder."""

    def __init__(
        self,
        planner: StoryPlanner | None = None,
    ):
        self.planner = (
            planner
            or StoryPlanner()
        )

    @staticmethod
    def _write_json(
        path: Path,
        data: dict[str, Any],
    ) -> None:

        path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def create_from_audio(
        self,
        audio_path: str | Path,
        project_dir: str | Path | None = None,
    ) -> dict[str, Any]:

        source = (
            Path(audio_path)
            .expanduser()
            .resolve()
        )

        if (
            not source.exists()
            or not source.is_file()
        ):
            raise FileNotFoundError(
                f"音声ファイルが見つかりません: {source}"
            )

        target = (
            Path(project_dir)
            .expanduser()
            .resolve()
            if project_dir
            else (
                source.parent
                / f"{source.stem}.dreammv"
            )
        )

        target.mkdir(
            parents=True,
            exist_ok=True,
        )

        scenes_dir = (
            target / "scenes"
        )

        output_dir = (
            target / "output"
        )

        scenes_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        stored_audio = (
            target
            / f"song{source.suffix.lower()}"
        )

        if source != stored_audio.resolve():

            shutil.copy2(
                source,
                stored_audio,
            )

        #
        # Audio Analysis
        #
        from .audio import AudioAnalyzer

        audio_info = (
            AudioAnalyzer()
            .analyze(
                stored_audio
            )
        )

        #
        # Whisper
        #
        lyrics = []

        try:

            from .whisper_engine import (
                WhisperEngine
            )

            whisper = (
                WhisperEngine()
            )

            lyrics = (
                whisper.transcribe(
                    stored_audio
                )
            )

            print(
                f"[DreamMV] lyrics: "
                f"{len(lyrics)}"
            )

        except Exception as exc:

            print(
                "[DreamMV] Whisper disabled:"
            )

            print(exc)

            lyrics = []

        #
        # Planner
        #
        plan = (
            self.planner.create_plan(
                audio_info[
                    "duration"
                ],
                lyrics,
            )
        )

        project = {

            "schema_version": 2,

            "title":
                source.stem,

            "audio": {

                "filename":
                    stored_audio.name,

                "original_path":
                    str(source),

                "format":
                    audio_info[
                        "format"
                    ],

                "sample_rate":
                    audio_info[
                        "sample_rate"
                    ],
            },

            "duration":
                audio_info[
                    "duration"
                ],

            "scene_duration":
                plan[
                    "scene_duration"
                ],

            "scene_count":
                plan[
                    "scene_count"
                ],

            "theme":
                plan.get(
                    "theme",
                    "default",
                ),

            "lyrics":
                lyrics,

            "status":
                "planned",

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "scenes":
                plan["scenes"],
        }

        self._write_json(
            target
            / "project.json",
            project,
        )

        self._write_json(
            output_dir
            / "job.json",
            {
                "title":
                    project["title"],

                "status":
                    "queued",

                "type":
                    "planning",

                "error":
                    None,

                "created_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            },
        )

        return {
            "project_dir":
                target,

            "project":
                project,
        }

    def load(
        self,
        project_dir: str | Path,
    ) -> dict[str, Any]:

        target = (
            Path(project_dir)
            .expanduser()
            .resolve()
        )

        project_file = (
            target
            / "project.json"
        )

        if not project_file.is_file():

            raise FileNotFoundError(
                f"project.json が見つかりません: "
                f"{project_file}"
            )

        try:

            project = json.loads(
                project_file.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                f"project.json の JSON 形式が正しくありません: {exc}"
            ) from exc

        return {
            "project_dir":
                target,

            "project":
                project,
        }

    def save(
        self,
        project_dir: str | Path,
        project: dict[str, Any],
    ) -> Path:

        target = (
            Path(project_dir)
            .expanduser()
            .resolve()
        )

        target.mkdir(
            parents=True,
            exist_ok=True,
        )

        project_file = (
            target
            / "project.json"
        )

        self._write_json(
            project_file,
            project,
        )

        return project_file