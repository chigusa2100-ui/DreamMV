import unittest

from src.dreammv.narration_planner import NarrationPlanner


class NarrationPlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = NarrationPlanner()

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


if __name__ == "__main__":
    unittest.main()