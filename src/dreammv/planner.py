
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
        song_length: float | None = None,
    ) -> list[dict[str, Any]]:
        """Normalize lyric segments and distribute entries without timestamps.

        Timestamped segments keep their original timing. Plain strings and
        dictionaries without a usable time range are spread evenly across
        the song when song_length is supplied.
        """
        if not lyrics:
            return []

        result: list[dict[str, Any] | None] = []
        untimed_indices: list[int] = []

        for item in lyrics:
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                try:
                    start = float(item.get("start"))
                    end = float(item.get("end"))
                except (TypeError, ValueError):
                    start = end = 0.0

                if (
                    math.isfinite(start)
                    and math.isfinite(end)
                    and start >= 0
                    and end > start
                ):
                    result.append({
                        "start": start,
                        "end": end,
                        "text": text,
                    })
                else:
                    untimed_indices.append(len(result))
                    result.append({
                        "start": 0.0,
                        "end": 0.0,
                        "text": text,
                    })

            elif isinstance(item, str):
                text = item.strip()
                if text:
                    untimed_indices.append(len(result))
                    result.append({
                        "start": 0.0,
                        "end": 0.0,
                        "text": text,
                    })

        if untimed_indices and song_length is not None:
            try:
                length = float(song_length)
            except (TypeError, ValueError):
                length = 0.0

            if math.isfinite(length) and length > 0:
                slot = length / len(untimed_indices)
                for order, result_index in enumerate(untimed_indices):
                    start = order * slot
                    end = length if order == len(untimed_indices) - 1 else (order + 1) * slot
                    result[result_index]["start"] = round(start, 3)
                    result[result_index]["end"] = round(end, 3)

        return [item for item in result if item is not None]

    def get_lyrics_for_scene(
        self,
        lyrics,
        start_time: float,
        end_time: float,
    ) -> str:
        """Return lyric segments that overlap a scene's half-open time range."""
        if not lyrics:
            return ""

        matched = []
        for item in lyrics:
            if (
                item["start"] < end_time
                and item["end"] > start_time
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

    # =====================================================
    # Lyric Interpreter / Scene Director
    # =====================================================

    _ACTION_RULES = (
        ("embracing", ("抱きしめ", "抱きしめる", "抱く", "寄り添")),
        ("singing", ("歌う", "歌って", "歌声", "歌い")),
        ("dancing", ("踊", "舞う", "舞い")),
        ("running", ("走", "駆け", "駆け抜け")),
        ("walking forward", ("歩", "進む", "歩み")),
        ("reaching toward something", ("手を伸ば", "掴", "つかむ", "届か")),
        ("looking into the distance", ("見上げ", "見つめ", "見渡", "眺め", "見て", "見る")),
        ("flying freely", ("飛ぶ", "飛ん", "羽ばた", "空へ")),
        ("crying softly", ("泣", "涙", "哀し")),
        ("smiling gently", ("微笑", "笑顔", "笑っ", "笑う")),
        ("waiting quietly", ("待つ", "待って", "待ち続け")),
        ("standing still", ("佇む", "立ち尽く", "立って")),
        ("falling", ("落ちる", "堕ちる", "崩れ")),
        ("opening something", ("開く", "開ける", "扉を")),
    )

    _LOCATION_RULES = (
        ("by the ocean, with the horizon stretching into the distance", ("海", "波", "潮", "浜辺", "水平線")),
        ("beneath a vast open sky", ("空", "雲", "青空", "星空")),
        ("among a quiet forest and drifting leaves", ("森", "木々", "木漏れ日", "葉")),
        ("on a quiet city street", ("街", "都会", "ビル", "交差点", "街角")),
        ("at a train station or beside railway tracks", ("駅", "列車", "電車", "ホーム", "線路")),
        ("inside a quiet room by the window", ("部屋", "窓辺", "窓", "カーテン")),
        ("on a rooftop overlooking the city", ("屋上", "高層", "街を見下ろ")),
        ("among flowers in a field", ("花", "草原", "野原", "花畑")),
        ("among ancient ruins", ("遺跡", "廃墟", "崩れた壁")),
    )

    _TIME_RULES = (
        ("at dawn", ("夜明け", "朝焼け", " dawn", " sunrise")),
        ("in the morning", ("朝", " sunrise")),
        ("at sunset", ("夕暮れ", "夕焼け", "黄昏", " sunset")),
        ("at night", ("夜", "月", "星", "真夜中", " midnight")),
    )

    _EMOTION_LIGHTING = {
        "hope": "soft golden backlight and luminous atmosphere",
        "joy": "bright natural light with sparkling highlights",
        "happiness": "bright natural light with sparkling highlights",
        "sadness": "soft cool-blue light and gentle shadows",
        "loneliness": "muted blue light with spacious negative space",
        "struggle": "dramatic directional light and deep shadows",
        "anger": "strong contrast with intense warm rim light",
        "fear": "low-key lighting with restrained cold highlights",
        "love": "warm diffused light and delicate highlights",
        "nostalgia": "soft hazy sunset light and subtle film glow",
    }

    def interpret_lyric(
        self, lyric: str, theme: dict[str, Any], emotion: str | None = None,
    ) -> dict[str, str | None]:
        """Convert lyric cues into conservative, structured visual direction.

        This is a deterministic keyword interpreter, not an LLM. Theme JSON may
        provide ``main_character`` or ``character_description`` to keep the
        same protagonist wording across scenes.
        """
        text = str(lyric or "").strip()
        if not text:
            return {
                "subject": None, "action": None, "setting": None,
                "time_of_day": None, "lighting": None, "composition": None,
                "continuity": None,
            }

        folded = text.casefold()
        action = next((label for label, words in self._ACTION_RULES
                       if any(word.casefold() in folded for word in words)), None)
        setting = next((label for label, words in self._LOCATION_RULES
                        if any(word.casefold() in folded for word in words)), None)
        time_of_day = next((label for label, words in self._TIME_RULES
                            if any(word.casefold() in folded for word in words)), None)

        director_config = theme.get("director", {})
        if not isinstance(director_config, dict):
            director_config = {}
        character_config = director_config.get("character", {})
        if not isinstance(character_config, dict):
            character_config = {}

        subject = str(
            character_config.get("description")
            or theme.get("character_description")
            or theme.get("main_character")
            or theme.get("protagonist")
            or "the same anime protagonist"
        ).strip()
        if not action:
            action = "expressing the lyric's feeling through a subtle, natural gesture"

        lighting = None
        if emotion:
            lighting = self._EMOTION_LIGHTING.get(str(emotion).casefold())
        if not lighting and time_of_day == "at dawn":
            lighting = "soft pastel dawn light with a delicate golden rim"
        elif not lighting and time_of_day == "at sunset":
            lighting = "warm sunset light with long atmospheric shadows"
        elif not lighting and time_of_day == "at night":
            lighting = "cool moonlight with subtle luminous highlights"
        elif not lighting and time_of_day == "in the morning":
            lighting = "clear morning light with soft natural shadows"

        if action in ("crying softly", "smiling gently"):
            composition = "intimate facial close-up, expressive eyes, cinematic depth of field"
        elif action in ("running", "walking forward", "flying freely", "dancing"):
            composition = "dynamic wide shot, clear body silhouette, cinematic sense of movement"
        elif action in ("reaching toward something", "looking into the distance"):
            composition = "medium-wide over-the-shoulder composition, strong visual direction"
        else:
            composition = "cinematic medium shot with clear subject silhouette and balanced negative space"

        visual_language = director_config.get("visual_language", {})
        if not isinstance(visual_language, dict):
            visual_language = {}

        return {
            "subject": subject, "action": action, "setting": setting,
            "time_of_day": time_of_day, "lighting": lighting,
            "composition": composition, "continuity": subject,
            "action_style": visual_language.get("action_style"),
            "environment_style": visual_language.get("environment_style"),
            "lighting_style": visual_language.get("lighting_style"),
            "composition_style": visual_language.get("composition_style"),
            "visual_motifs": visual_language.get("visual_motifs", []),
        }

    def direct_scene(
        self, lyric: str, theme: dict[str, Any], emotion: str | None = None,
    ) -> dict[str, str | None]:
        """Public scene-director entry point; returns additive metadata only."""
        return self.interpret_lyric(lyric, theme, emotion)

    def build_scene_prompt(
        self,
        stage: dict[str, Any],
        theme: dict[str, Any],
        lyric: str,
        scene_index: int,
    ) -> tuple[str, str | None]:
        """Build an Animagine-friendly prompt from theme and lyric direction."""
        base_prompt = str(
            stage.get("prompt") or "cinematic anime scene"
        ).strip()
        parts = [base_prompt]

        emotion = self.detect_emotion(lyric, theme)
        emotion_styles = theme.get("emotion_styles", {})

        if emotion and isinstance(emotion_styles, dict):
            style = emotion_styles.get(emotion)
            if isinstance(style, str) and style.strip():
                parts.append(f"emotional visual style: {style.strip()}")

        palette = self._pick_by_scene(
            self._string_list(theme.get("color_palette")), scene_index,
        )
        location = self._pick_by_scene(
            self._string_list(theme.get("locations")), scene_index,
        )
        direction = self.direct_scene(lyric, theme, emotion)

        if palette:
            parts.append(f"color palette: {palette}")
        lyric_setting = direction.get("setting")
        if lyric_setting:
            parts.append(f"lyric-based environment: {lyric_setting}")
        elif location:
            parts.append(f"setting: {location}")
        if direction.get("subject"):
            parts.append(f"consistent main character: {direction['subject']}")
        if direction.get("action"):
            parts.append(f"scene action: {direction['action']}")
        if direction.get("time_of_day"):
            parts.append(f"time of day: {direction['time_of_day']}")
        if direction.get("lighting"):
            parts.append(f"lighting: {direction['lighting']}")
        if direction.get("composition"):
            parts.append(f"composition: {direction['composition']}")

        # Theme-specific Director language is optional, preserving legacy themes.
        for key, label in (
            ("action_style", "directed action language"),
            ("environment_style", "theme environment direction"),
            ("lighting_style", "theme lighting direction"),
            ("composition_style", "theme composition direction"),
        ):
            value = direction.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(f"{label}: {value.strip()}")

        motifs = direction.get("visual_motifs")
        if isinstance(motifs, list) and motifs:
            parts.append("recurring visual motifs: " + ", ".join(
                str(item).strip() for item in motifs if str(item).strip()
            ))

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

        normalized_lyrics = self.normalize_lyrics(lyrics, length)

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
            # Camera composition and camera movement are metadata for the
            # video stage, never natural-language instructions for Animagine.
            camera_style = self._pick_by_scene(
                self._string_list(theme.get("camera_styles")),
                index,
            )
            camera_motion = self._pick_by_scene(
                self._string_list(theme.get("camera_motions")),
                index,
            )
            if camera_motion is None:
                camera_motion = {
                    "hope": "zoom_in", "joy": "pan_right",
                    "happiness": "pan_right", "love": "zoom_in",
                    "sadness": "zoom_out", "loneliness": "zoom_out",
                    "nostalgia": "pan_left", "struggle": "zoom_in",
                    "anger": "pan_right", "fear": "zoom_out",
                }.get(str(emotion).casefold() if emotion else "")

            director = self.direct_scene(lyric, theme, emotion)

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
                    "camera_style": camera_style,
                    "camera_motion": camera_motion,
                    "director": director,
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
