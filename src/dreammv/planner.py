
"""Lyric-aware scene planner for DreamMV."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG, load_config


class StoryPlanner:
    """Create a scene plan from song duration and lyrics."""

    def __init__(
        self,
        scene_duration: float | None = None,
        config_path=None,
    ) -> None:
        if scene_duration is None:
            config = (
                load_config(config_path)
                if config_path is not None
                else DEFAULT_CONFIG
            )
            scene_duration = config["scene_duration"]

        self.scene_duration = float(scene_duration)

        if (
            not math.isfinite(self.scene_duration)
            or self.scene_duration <= 0
        ):
            raise ValueError(
                "scene_duration は 0 より大きい有限の秒数にしてください。"
            )

        self.themes = self.load_themes()

    # =====================================================
    # Theme Loader
    # =====================================================

    def load_themes(self) -> dict[str, dict[str, Any]]:
        themes: dict[str, dict[str, Any]] = {}

        base_dir = Path(__file__).resolve().parents[2]
        theme_dir = base_dir / "config" / "themes"

        if not theme_dir.exists():
            print(
                "[DreamMV] theme directory not found: "
                f"{theme_dir}"
            )
            return themes

        for file in sorted(theme_dir.glob("*.json")):
            try:
                data = json.loads(
                    file.read_text(encoding="utf-8")
                )

                if not isinstance(data, dict):
                    print(
                        f"[DreamMV] invalid theme format: "
                        f"{file.name}"
                    )
                    continue

                theme_name = str(
                    data.get("name", file.stem)
                )
                themes[theme_name] = data

                print(
                    f"[DreamMV] loaded theme: {theme_name}"
                )

            except (OSError, json.JSONDecodeError) as exc:
                print(
                    f"[DreamMV] failed loading "
                    f"{file.name}: {exc}"
                )

        return themes

    # =====================================================
    # Lyrics
    # =====================================================

    def normalize_lyrics(
        self,
        lyrics,
    ) -> list[dict[str, Any]]:
        if not lyrics:
            return []

        result: list[dict[str, Any]] = []

        for item in lyrics:
            if isinstance(item, dict):
                try:
                    start = float(item.get("start", 0.0))
                    end = float(item.get("end", 0.0))
                except (TypeError, ValueError):
                    continue

                if (
                    not math.isfinite(start)
                    or not math.isfinite(end)
                ):
                    continue

                result.append(
                    {
                        "start": start,
                        "end": end,
                        "text": str(
                            item.get("text", "")
                        ).strip(),
                    }
                )

            elif isinstance(item, str):
                text = item.strip()
                if text:
                    result.append(
                        {
                            "start": 0.0,
                            "end": 0.0,
                            "text": text,
                        }
                    )

        return result

    def get_lyrics_for_scene(
        self,
        lyrics,
        start_time: float,
        end_time: float,
    ) -> str:
        if not lyrics:
            return ""

        matched = []

        for item in lyrics:
            if (
                item["start"] <= end_time
                and item["end"] >= start_time
                and item["text"]
            ):
                matched.append(item["text"])

        return "\n".join(matched)

    # =====================================================
    # Theme Detection
    # =====================================================

    def detect_theme(
        self,
        lyrics: list[dict[str, Any]],
    ) -> str:
        if not self.themes:
            return "default"

        text = "\n".join(
            item["text"] for item in lyrics
        ).casefold()

        scores: dict[str, int] = {}

        for theme_name, theme in self.themes.items():
            words = theme.get("keywords", [])

            if not isinstance(words, list):
                words = []

            scores[theme_name] = sum(
                text.count(str(word).casefold())
                for word in words
                if str(word)
            )

        if not scores:
            return "default"

        best_theme = max(scores, key=scores.get)

        # キーワードが一つも一致しない場合は既定テーマを使う。
        if scores[best_theme] <= 0:
            return "default"

        return best_theme

    # =====================================================
    # Scene Name
    # =====================================================

    def generate_scene_name(
        self,
        lyric: str,
        keywords: list[str] | None = None,
        stage_name: str = "",
    ) -> str:
        """Generate a readable scene name without external dependencies."""
        stage_name = str(stage_name or "").strip()
        lyric_text = " ".join(str(lyric or "").split())

        # 歌詞にテーマキーワードが含まれる場合は名前に反映する。
        lyric_lower = lyric_text.casefold()

        for keyword in keywords or []:
            keyword_text = str(keyword).strip()

            if (
                keyword_text
                and keyword_text.casefold() in lyric_lower
            ):
                return f"{stage_name or 'Scene'} - {keyword_text}"

        # 歌詞がある場合は、短い見出しとして使用する。
        if lyric_text:
            max_length = 24
            if len(lyric_text) > max_length:
                return lyric_text[:max_length].rstrip() + "…"
            return lyric_text

        return stage_name or "Scene"

    # =====================================================
    # Stage
    # =====================================================

    def get_stage(
        self,
        theme_name: str,
        scene_index: int,
        scene_count: int,
    ) -> dict[str, Any]:
        theme = self.themes.get(theme_name, {})
        stages = theme.get("stages", [])

        if not isinstance(stages, list) or not stages:
            return {
                "name": f"Scene {scene_index + 1}",
                "description": "",
                "prompt": "cinematic anime scene",
            }

        stage_index = min(
            (
                scene_index * len(stages)
            ) // max(scene_count, 1),
            len(stages) - 1,
        )

        stage = stages[stage_index]

        if not isinstance(stage, dict):
            return {
                "name": f"Scene {scene_index + 1}",
                "description": "",
                "prompt": "cinematic anime scene",
            }

        return stage

    # =====================================================
    # Per-scene emotion and visual styling
    # =====================================================

    @staticmethod
    def _string_list(value) -> list[str]:
        """JSON ?????????????????"""
        if not isinstance(value, list):
            return []
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    def detect_emotion(
        self,
        lyric: str,
        theme: dict[str, Any],
    ) -> str | None:
        """????????????????????????"""
        emotion_keywords = theme.get("emotion_keywords", {})
        if not isinstance(emotion_keywords, dict) or not lyric:
            return None

        text = lyric.casefold()
        scores: dict[str, int] = {}

        for emotion, words in emotion_keywords.items():
            keywords = self._string_list(words)
            score = sum(
                text.count(word.casefold())
                for word in keywords
            )
            if score > 0:
                scores[str(emotion)] = score

        if not scores:
            return None

        # ?????? JSON ??????????
        return max(scores, key=scores.get)

    @staticmethod
    def _pick_by_scene(
        values: list[str],
        scene_index: int,
    ) -> str | None:
        """????????????????????"""
        if not values:
            return None
        return values[scene_index % len(values)]

    def build_scene_prompt(
        self,
        stage: dict[str, Any],
        theme: dict[str, Any],
        lyric: str,
        scene_index: int,
    ) -> tuple[str, str | None]:
        """????????????????????????"""
        base_prompt = str(
            stage.get("prompt") or "cinematic anime scene"
        ).strip()
        parts = [base_prompt]

        emotion = self.detect_emotion(lyric, theme)
        emotion_styles = theme.get("emotion_styles", {})

        if emotion and isinstance(emotion_styles, dict):
            style = emotion_styles.get(emotion)
            if isinstance(style, str) and style.strip():
                parts.append(
                    f"emotional visual style: {style.strip()}"
                )

        camera = self._pick_by_scene(
            self._string_list(theme.get("camera_styles")),
            scene_index,
        )
        palette = self._pick_by_scene(
            self._string_list(theme.get("color_palette")),
            scene_index,
        )
        location = self._pick_by_scene(
            self._string_list(theme.get("locations")),
            scene_index,
        )

        if camera:
            parts.append(f"camera: {camera}")
        if palette:
            parts.append(f"color palette: {palette}")
        if location:
            parts.append(f"setting: {location}")

        return ", ".join(parts), emotion

    # =====================================================
    # Main
    # =====================================================

    def create_plan(
        self,
        song_length: float,
        lyrics=None,
    ) -> dict[str, Any]:
        length = float(song_length)

        if (
            not math.isfinite(length)
            or length <= 0
        ):
            raise ValueError(
                "song_length は 0 より大きい有限の秒数にしてください。"
            )

        normalized_lyrics = self.normalize_lyrics(lyrics)

        scene_count = max(
            1,
            math.ceil(length / self.scene_duration),
        )

        theme_name = self.detect_theme(normalized_lyrics)
        theme = self.themes.get(theme_name, {})
        keywords = theme.get("keywords", [])

        if not isinstance(keywords, list):
            keywords = []

        scenes: list[dict[str, Any]] = []

        for index in range(scene_count):
            start = round(
                index * self.scene_duration,
                3,
            )

            end = round(
                min(
                    (index + 1) * self.scene_duration,
                    length,
                ),
                3,
            )

            stage = self.get_stage(
                theme_name,
                index,
                scene_count,
            )

            lyric = self.get_lyrics_for_scene(
                normalized_lyrics,
                start,
                end,
            )

            stage_name = str(
                stage.get("name", f"Scene {index + 1}")
            )

            scene_name = self.generate_scene_name(
                lyric,
                keywords,
                stage_name,
            )

            prompt_text, emotion = self.build_scene_prompt(
                stage,
                theme,
                lyric,
                index,
            )

            scenes.append(
                {
                    "id": index + 1,
                    "name": scene_name,
                    "start": start,
                    "end": end,
                    "duration": round(end - start, 3),
                    "theme": theme_name,
                    "lyric": lyric,
                    "description": stage.get(
                        "description", ""
                    ),
                    "emotion": emotion,
                    "prompt": prompt_text,
                }
            )

        return {
            "length": round(length, 3),
            "scene_duration": self.scene_duration,
            "scene_count": scene_count,
            "theme": theme_name,
            "status": "planning",
            "scenes": scenes,
        }
