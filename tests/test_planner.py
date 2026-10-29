import json
import tempfile
import unittest
from pathlib import Path

from src.dreammv.narration_planner import NarrationPlanner


class NarrationPlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.theme_dir = Path(self.temp_dir.name) / "themes"
        self.theme_dir.mkdir()

        self.theme_data = {
            "name": "hope",
            "keywords": ["希望", "未来", "明日", "光", "夢"],
            "emotion_keywords": {
                "struggle": ["暗闇", "壁"],
                "hope": ["希望", "光", "未来", "明日"],
                "freedom": ["羽ばたく", "空", "飛ぶ"],
            },
            "emotion_styles": {
                "struggle": "dramatic shadows breaking into light",
                "hope": "radiant golden sunrise, uplifting atmosphere",
                "freedom": "open sky, wind-swept sense of liberation",
            },
            "camera_styles": [
                "low angle hero shot",
                "wide sunrise shot",
            ],
            "color_palette": [
                "sunrise gold",
                "sky blue",
            ],
            "locations": [
                "mountain ridge",
                "city rooftop at dawn",
            ],
            "stages": [
                {
                    "name": "暗闇の中で",
                    "description": "小さな光を見つける",
                    "prompt": "lone figure in a dark landscape seeing a small distant light",
                },
                {
                    "name": "一歩",
                    "description": "迷いながらも前へ進む",
                    "prompt": "determined character walking along a long road at dawn",
                },
                {
                    "name": "新しい朝",
                    "description": "未来へ続く景色を見渡す",
                    "prompt": "vast golden sunrise over a peaceful world",
                },
            ],
        }

        (self.theme_dir / "hope.json").write_text(
            json.dumps(self.theme_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.planner = NarrationPlanner(
            config_path=Path(self.temp_dir.name),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_narration_illustration_plan(self):
        segments = [
            {"start": 0.0, "end": 3.0, "text": "森の中に小さな家がありました。"},
            {"start": 3.0, "end": 7.0, "text": "そこには一人の少女が住んでいました。"},
            {"start": 7.0, "end": 11.0, "text": "少女は毎朝、森を歩きました。"},
            {"start": 11.0, "end": 15.0, "text": "ある日、不思議な光を見つけました。"},
        ]

        plan = self.planner.create_plan(
            segments,
            audio_duration=15.0,
            title="森の少女",
        )

        self.assertEqual(plan["project_type"], "narration_illustrations")
        self.assertEqual(plan["title"], "森の少女")
        self.assertEqual(plan["render_clip_duration"], 10.0)
        self.assertEqual(plan["audio_duration"], 15.0)
        self.assertGreater(plan["scene_count"], 0)

        for scene in plan["scenes"]:
            self.assertTrue(scene["text"])
            self.assertTrue(scene["prompt"])
            self.assertTrue(scene["visual_prompt"])
            self.assertTrue(scene["name"])
            self.assertEqual(scene["status"], "queued")
            self.assertGreater(scene["end"], scene["start"])

    def test_sorts_segments_and_skips_invalid_entries(self):
        segments = [
            {"start": 5.0, "end": 8.0, "text": "後の文章です。"},
            {"start": 0.0, "end": 2.0, "text": "最初の文章です。"},
            {"start": 2.0, "end": 2.0, "text": "時間がゼロです。"},
            {"start": 1.0, "end": 2.0, "text": "   "},
            {"start": "invalid", "end": 4.0, "text": "不正な時刻です。"},
            None,
        ]

        plan = self.planner.create_plan(segments)

        self.assertEqual(
            plan["transcript"],
            "最初の文章です。 後の文章です。",
        )
        self.assertEqual(plan["scenes"][0]["start"], 0.0)

    def test_clamps_segment_end_to_audio_duration(self):
        segments = [
            {"start": 8.0, "end": 14.0, "text": "音声の最後の文章です。"},
        ]

        plan = self.planner.create_plan(
            segments,
            audio_duration=10.0,
        )

        self.assertEqual(plan["scenes"][0]["end"], 10.0)
        self.assertEqual(plan["scenes"][0]["duration"], 2.0)

    def test_rejects_empty_transcript(self):
        with self.assertRaisesRegex(ValueError, "有効な文字起こし結果"):
            self.planner.create_plan([])

    def test_rejects_invalid_audio_duration(self):
        with self.assertRaises(ValueError):
            self.planner.create_plan(
                [{"start": 0, "end": 1, "text": "文章"}],
                audio_duration=0,
            )

    def test_rejects_invalid_scene_duration(self):
        with self.assertRaises(ValueError):
            NarrationPlanner(scene_duration=0)

    def test_rejects_scene_duration_outside_bounds(self):
        with self.assertRaises(ValueError):
            NarrationPlanner(
                scene_duration=20,
                min_scene_duration=4,
                max_scene_duration=16,
            )

    def test_scene_groups_respect_target_duration_when_possible(self):
        segments = [
            {"start": 0, "end": 5, "text": "第一の場面。"},
            {"start": 5, "end": 10, "text": "第二の場面。"},
            {"start": 10, "end": 15, "text": "第三の場面。"},
            {"start": 15, "end": 20, "text": "第四の場面。"},
        ]

        plan = self.planner.create_plan(segments)

        self.assertEqual(plan["scene_count"], 2)
        self.assertEqual(
            [(scene["start"], scene["end"]) for scene in plan["scenes"]],
            [(0.0, 10.0), (10.0, 20.0)],
        )

    def test_loads_shared_theme_json(self):
        self.assertIn("hope", self.planner.themes)
        self.assertEqual(
            self.planner.themes["hope"]["name"],
            "hope",
        )

    def test_detects_theme_from_narration_keywords(self):
        theme_name = self.planner.detect_theme(
            "希望を胸に、明日の光を探して進みます。"
        )

        self.assertEqual(theme_name, "hope")

    def test_detects_emotion_from_theme_keywords(self):
        emotion = self.planner.detect_emotion(
            "未来への希望を見つけた。",
            self.theme_data,
        )

        self.assertEqual(emotion, "hope")

    def test_scene_prompt_includes_theme_visual_settings(self):
        plan = self.planner.create_plan(
            [
                {
                    "start": 0,
                    "end": 10,
                    "text": "希望の光を見つけ、未来へ進みます。",
                }
            ],
            audio_duration=10,
        )

        scene = plan["scenes"][0]
        prompt = scene["prompt"]

        self.assertEqual(scene["theme"], "hope")
        self.assertEqual(scene["emotion"], "hope")
        self.assertIn("radiant golden sunrise", prompt)
        self.assertIn("camera:", prompt)
        self.assertIn("color palette:", prompt)
        self.assertIn("setting:", prompt)
        self.assertIn("希望の光", prompt)

    def test_scene_name_uses_matching_theme_keyword(self):
        name = self.planner.generate_scene_name(
            "希望の光を見つけた。",
            self.theme_data,
            {"name": "暗闇の中で"},
            0,
        )

        self.assertEqual(name, "希望")

    def test_scene_uses_theme_stage_description(self):
        plan = self.planner.create_plan(
            [
                {
                    "start": 0,
                    "end": 10,
                    "text": "希望を胸に歩き始めた。",
                }
            ],
            audio_duration=10,
        )

        scene = plan["scenes"][0]

        self.assertEqual(scene["stage"], "暗闇の中で")
        self.assertIn("小さな光を見つける", scene["description"])

    def test_unknown_theme_falls_back_to_default(self):
        name = self.planner.detect_theme("今日は穏やかな一日でした。")

        self.assertEqual(name, "default")

    def test_plan_keeps_narration_clip_duration_at_ten_seconds(self):
        plan = self.planner.create_plan(
            [{"start": 0, "end": 8, "text": "静かな森を歩きます。"}],
            audio_duration=8,
        )

        self.assertEqual(plan["scene_duration"], 10.0)
        self.assertEqual(plan["render_clip_duration"], 10.0)


if __name__ == "__main__":
    unittest.main()