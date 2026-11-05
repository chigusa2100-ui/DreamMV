import unittest

from src.dreammv.planner import StoryPlanner


class StoryPlannerTests(unittest.TestCase):
    def test_splits_song_into_scenes(self):
        plan = StoryPlanner(scene_duration=10).create_plan(25)
        self.assertEqual(plan["scene_count"], 3)
        self.assertEqual([(s["start"], s["end"]) for s in plan["scenes"]], [(0, 10), (10, 20), (20, 25)])

    def test_scene_duration_is_configurable(self):
        plan = StoryPlanner(scene_duration=8).create_plan(17)
        self.assertEqual(plan["scene_count"], 3)
        self.assertEqual([(s["start"], s["end"]) for s in plan["scenes"]], [(0, 8), (8, 16), (16, 17)])

    def test_untimed_string_lyrics_are_distributed_across_song(self):
        plan = StoryPlanner(scene_duration=5).create_plan(
            15,
            ["first lyric", "second lyric", "third lyric"],
        )
        self.assertEqual(
            [scene["lyric"] for scene in plan["scenes"]],
            ["first lyric", "second lyric", "third lyric"],
        )

    def test_timestamped_lyrics_do_not_duplicate_at_scene_boundaries(self):
        plan = StoryPlanner(scene_duration=5).create_plan(
            10,
            [{"start": 0, "end": 5, "text": "first"},
             {"start": 5, "end": 10, "text": "second"}],
        )
        self.assertEqual(plan["scenes"][0]["lyric"], "first")
        self.assertEqual(plan["scenes"][1]["lyric"], "second")

    def test_rejects_invalid_length(self):
        with self.assertRaises(ValueError):
            StoryPlanner().create_plan(0)

    def test_rejects_invalid_scene_duration(self):
        with self.assertRaises(ValueError):
            StoryPlanner(scene_duration=0)


if __name__ == "__main__":
    unittest.main()
