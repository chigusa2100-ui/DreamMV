"""Create illustration scenes from timestamped narration transcripts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


NARRATION_SCENE_DURATION = 10.0
NARRATION_MIN_SCENE_DURATION = 4.0
NARRATION_MAX_SCENE_DURATION = 16.0


@dataclass(frozen=True)
class NarrationPlanner:
    """Build a narration illustration plan using DreamMV's shared themes."""

    scene_duration: float = NARRATION_SCENE_DURATION
    min_scene_duration: float = NARRATION_MIN_SCENE_DURATION
    max_scene_duration: float = NARRATION_MAX_SCENE_DURATION
    config_path: str | Path | None = None
    themes: dict[str, dict[str, Any]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.scene_duration <= 0:
            raise ValueError(
                "scene_duration は0より大きい値にしてください。"
            )

        if self.min_scene_duration <= 0:
            raise ValueError(
                "min_scene_duration は0より大きい値にしてください。"
            )

        if self.max_scene_duration < self.min_scene_duration:
            raise ValueError(
                "max_scene_duration は min_scene_duration 以上にしてください。"
            )

        if not (
            self.min_scene_duration
            <= self.scene_duration
            <= self.max_scene_duration
        ):
            raise ValueError(
                "scene_duration は min_scene_duration と "
                "max_scene_duration の範囲内にしてください。"
            )

        themes = self.load_themes()
        object.__setattr__(self, "themes", themes)

        print(
            f"[DreamMV][Narration] テーマフォルダ: "
            f"{self._get_theme_dir()}",
            flush=True,
        )
        print(
            f"[DreamMV][Narration] 読み込みテーマ数: {len(themes)}",
            flush=True,
        )

    def _get_theme_dir(self) -> Path:
        """Return the shared theme directory."""
        if self.config_path is not None:
            supplied_path = Path(self.config_path).expanduser().resolve()

            if supplied_path.is_dir():
                return supplied_path / "themes"

            return supplied_path.parent / "themes"

        project_root = Path(__file__).resolve().parents[2]
        return project_root / "config" / "themes"

    def load_themes(self) -> dict[str, dict[str, Any]]:
        """Load shared JSON theme definitions used by the music planner."""
        theme_dir = self._get_theme_dir()
        themes: dict[str, dict[str, Any]] = {}

        if not theme_dir.is_dir():
            print(
                f"[DreamMV][Narration] 警告: テーマフォルダがありません: "
                f"{theme_dir}",
                flush=True,
            )
            return themes

        for file_path in sorted(theme_dir.glob("*.json")):
            try:
                data = json.loads(
                    file_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"[DreamMV][Narration] テーマ読み込み失敗: "
                    f"{file_path.name}: {exc}",
                    flush=True,
                )
                continue

            if not isinstance(data, dict):
                print(
                    f"[DreamMV][Narration] 警告: JSONの形式が不正です: "
                    f"{file_path.name}",
                    flush=True,
                )
                continue

            theme_name = str(
                data.get("name") or file_path.stem
            ).strip()

            if theme_name:
                themes[theme_name] = data

        return themes

    def create_plan(
        self,
        segments: Iterable[dict[str, Any]],
        audio_duration: float | None = None,
        title: str = "朗読",
    ) -> dict[str, Any]:
        """Create a JSON-serializable illustration plan."""
        if audio_duration is not None and audio_duration <= 0:
            raise ValueError(
                "audio_duration は0より大きい値にしてください。"
            )

        cleaned_segments = self._clean_segments(
            segments,
            audio_duration=audio_duration,
        )

        if not cleaned_segments:
            raise ValueError(
                "有効な文字起こし結果がありません。"
                "音声と文字起こしを確認してください。"
            )

        grouped_segments = self._group_segments(cleaned_segments)

        if audio_duration is None:
            audio_duration = max(
                item["end"] for item in cleaned_segments
            )

        transcript = " ".join(
            item["text"] for item in cleaned_segments
        ).strip()

        theme_name = self.detect_theme(transcript)

        print(
            f"[DreamMV][Narration] 選択テーマ: {theme_name}",
            flush=True,
        )

        theme = self.themes.get(theme_name, {})

        if theme_name == "default" and self.themes:
            print(
                "[DreamMV][Narration] 注意: 文字起こし内容に一致する"
                "テーマキーワードが見つかりませんでした。",
                flush=True,
            )

        scenes: list[dict[str, Any]] = []

        for index, group in enumerate(grouped_segments):
            start = group[0]["start"]
            end = max(item["end"] for item in group)
            text = " ".join(
                item["text"] for item in group
            ).strip()

            stage = self.get_stage(
                theme,
                index,
                len(grouped_segments),
            )

            emotion = self.detect_emotion(text, theme)

            scene_name = self.generate_scene_name(
                text,
                theme,
                stage,
                index,
            )

            description = self._build_description(
                text,
                stage,
            )

            prompt = self._build_prompt(
                text=text,
                theme_name=theme_name,
                theme=theme,
                stage=stage,
                emotion=emotion,
                scene_index=index,
            )

            scenes.append(
                {
                    "id": f"narration_scene_{index + 1:04d}",
                    "name": scene_name,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "duration": round(end - start, 3),
                    "text": text,
                    "theme": theme_name,
                    "stage": str(stage.get("name") or ""),
                    "emotion": emotion,
                    "description": description,
                    "prompt": prompt,
                    "visual_prompt": prompt,
                    "status": "queued",
                }
            )

        return {
            "schema_version": 1,
            "project_type": "narration_illustrations",
            "title": title.strip() or "朗読",
            "audio_duration": round(audio_duration, 3),
            "scene_duration": self.scene_duration,
            "render_clip_duration": NARRATION_SCENE_DURATION,
            "theme": theme_name,
            "scene_count": len(scenes),
            "status": "queued",
            "transcript": transcript,
            "scenes": scenes,
        }

    def _clean_segments(
        self,
        segments: Iterable[dict[str, Any]],
        audio_duration: float | None,
    ) -> list[dict[str, Any]]:
        """Validate, normalize, sort, and clamp transcript segments."""
        cleaned: list[dict[str, Any]] = []

        for segment in segments:
            if not isinstance(segment, dict):
                continue

            try:
                start = float(segment["start"])
                end = float(segment["end"])
            except (KeyError, TypeError, ValueError):
                continue

            text = str(segment.get("text", "")).strip()

            if not text or start < 0 or end <= start:
                continue

            if audio_duration is not None:
                if start >= audio_duration:
                    continue

                end = min(end, audio_duration)

            if end <= start:
                continue

            cleaned.append(
                {
                    "start": start,
                    "end": end,
                    "text": text,
                }
            )

        cleaned.sort(
            key=lambda item: (item["start"], item["end"])
        )

        return cleaned

    def _group_segments(
        self,
        segments: list[dict[str, Any]],
    ) -> list[list[dict[str, Any]]]:
        """Group transcript segments near the target duration."""
        groups: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []

        for segment in segments:
            if not current:
                current = [segment]
                continue

            current_start = current[0]["start"]
            current_end = max(
                item["end"] for item in current
            )
            current_span = current_end - current_start

            proposed_end = max(
                current_end,
                segment["end"],
            )
            proposed_span = proposed_end - current_start

            should_split = (
                current_span >= self.min_scene_duration
                and proposed_span > self.scene_duration
            )

            must_split = (
                proposed_span > self.max_scene_duration
            )

            if should_split or must_split:
                groups.append(current)
                current = [segment]
            else:
                current.append(segment)

        if current:
            groups.append(current)

        return groups

    def detect_theme(self, text: str) -> str:
        """Choose the theme with the most matching keywords."""
        if not self.themes:
            return "default"

        normalized_text = str(text or "").casefold()
        scores: dict[str, int] = {}

        for name, theme in self.themes.items():
            keywords = self._string_list(
                theme.get("keywords")
            )

            scores[name] = sum(
                normalized_text.count(keyword.casefold())
                for keyword in keywords
                if keyword
            )

        if not scores:
            return "default"

        best_theme = max(
            scores,
            key=scores.get,
        )

        return (
            best_theme
            if scores[best_theme] > 0
            else "default"
        )

    @staticmethod
    def detect_emotion(
        text: str,
        theme: dict[str, Any],
    ) -> str | None:
        """Detect an emotion using the theme's emotion keywords."""
        emotion_keywords = theme.get(
            "emotion_keywords",
            {},
        )

        if not isinstance(emotion_keywords, dict) or not text:
            return None

        normalized_text = text.casefold()
        scores: dict[str, int] = {}

        for emotion, values in emotion_keywords.items():
            keywords = NarrationPlanner._string_list(values)

            score = sum(
                normalized_text.count(keyword.casefold())
                for keyword in keywords
                if keyword
            )

            if score:
                scores[str(emotion)] = score

        return (
            max(scores, key=scores.get)
            if scores
            else None
        )

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        """Convert a JSON list into a list of non-empty strings."""
        if not isinstance(value, list):
            return []

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    @staticmethod
    def _pick_by_scene(
        values: list[str],
        scene_index: int,
    ) -> str | None:
        """Rotate through available visual settings by scene."""
        if not values:
            return None

        return values[scene_index % len(values)]

    @staticmethod
    def get_stage(
        theme: dict[str, Any],
        scene_index: int,
        scene_count: int,
    ) -> dict[str, Any]:
        """Select a stage across the theme's story arc."""
        stages = theme.get("stages", [])

        if not isinstance(stages, list):
            stages = []

        stages = [
            stage
            for stage in stages
            if isinstance(stage, dict)
        ]

        if not stages:
            return {
                "name": f"朗読シーン {scene_index + 1:03d}",
                "description": "",
                "prompt": (
                    "high-quality anime storybook illustration"
                ),
            }

        stage_index = min(
            (scene_index * len(stages))
            // max(scene_count, 1),
            len(stages) - 1,
        )

        return stages[stage_index]

    @staticmethod
    def generate_scene_name(
        text: str,
        theme: dict[str, Any],
        stage: dict[str, Any],
        scene_index: int,
    ) -> str:
        """Create a concise name grounded in narration and theme."""
        normalized_text = " ".join(
            str(text or "").split()
        )

        keywords = NarrationPlanner._string_list(
            theme.get("keywords")
        )

        for keyword in keywords:
            if keyword.casefold() in normalized_text.casefold():
                return (
                    keyword
                    if len(keyword) <= 24
                    else keyword[:24]
                )

        if normalized_text:
            max_length = 24

            if len(normalized_text) > max_length:
                return (
                    normalized_text[:max_length]
                    .rstrip(" 、。！？")
                    + "…"
                )

            return normalized_text

        stage_name = str(
            stage.get("name") or ""
        ).strip()

        return (
            stage_name
            or f"朗読シーン {scene_index + 1:03d}"
        )

    @staticmethod
    def _build_description(
        text: str,
        stage: dict[str, Any],
    ) -> str:
        """Combine the stage description with narration content."""
        stage_description = str(
            stage.get("description") or ""
        ).strip()

        narration_description = (
            f"朗読内容をもとにした挿絵。"
            f"この場面で描く内容：{text}"
        )

        if stage_description:
            return (
                f"{stage_description}。"
                f"{narration_description}"
            )

        return narration_description

    @staticmethod
    def _build_prompt(
        text: str,
        theme_name: str,
        theme: dict[str, Any],
        stage: dict[str, Any],
        emotion: str | None,
        scene_index: int,
    ) -> str:
        """Combine stage and shared theme settings into an image prompt."""
        base_prompt = str(
            stage.get("prompt")
            or "High-quality anime storybook illustration"
        ).strip()

        parts = [
            base_prompt,
            "High-quality anime storybook illustration",
            "cinematic composition, beautiful painterly lighting",
            (
                "clear focal point, detailed environment, "
                "coherent visual storytelling"
            ),
            "wide 16:9 composition",
        ]

        emotion_styles = theme.get(
            "emotion_styles",
            {},
        )

        if emotion and isinstance(emotion_styles, dict):
            style = emotion_styles.get(emotion)

            if isinstance(style, str) and style.strip():
                parts.append(
                    f"emotional visual style: {style.strip()}"
                )

        camera = NarrationPlanner._pick_by_scene(
            NarrationPlanner._string_list(
                theme.get("camera_styles")
            ),
            scene_index,
        )

        palette = NarrationPlanner._pick_by_scene(
            NarrationPlanner._string_list(
                theme.get("color_palette")
            ),
            scene_index,
        )

        location = NarrationPlanner._pick_by_scene(
            NarrationPlanner._string_list(
                theme.get("locations")
            ),
            scene_index,
        )

        if camera:
            parts.append(f"camera: {camera}")

        if palette:
            parts.append(f"color palette: {palette}")

        if location:
            parts.append(f"setting: {location}")

        parts.extend(
            [
                (
                    "Keep character designs and visual style "
                    "consistent across the story."
                ),
                (
                    "No text, no subtitles, no lettering, "
                    "no logo, no watermark."
                ),
                f"Theme: {theme_name}.",
                f"Narration content: {text}",
            ]
        )

        return ", ".join(parts)