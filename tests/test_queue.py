import json
import tempfile
import unittest
from pathlib import Path

from src.dreammv.queue import QueueManager


class QueueManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "output"
        self.manager = QueueManager(self.output)
        self.scenes = [
            {"id": 1, "name": "Opening", "start": 0, "end": 10, "prompt": "stars"},
            {"id": 2, "name": "Journey", "start": 10, "end": 20, "prompt": "space"},
            {"id": 3, "name": "Dawn", "start": 20, "end": 25, "prompt": "sunrise"},
        ]

    def test_create_persists_all_scenes_as_queued(self):
        queue = self.manager.create(self.scenes, title="Test Song")
        self.assertEqual(queue["title"], "Test Song")
        self.assertEqual([s["status"] for s in queue["scenes"]], ["queued"] * 3)
        saved = json.loads((self.output / "queue.json").read_text(encoding="utf-8"))
        self.assertEqual(len(saved["scenes"]), 3)

    def test_lifecycle_and_attempt_count(self):
        self.manager.create(self.scenes)
        self.manager.start(1)
        self.manager.complete(1)
        scene = self.manager.load()["scenes"][0]
        self.assertEqual(scene["status"], "completed")
        self.assertEqual(scene["attempts"], 1)

    def test_failed_scene_can_be_retried(self):
        self.manager.create(self.scenes)
        self.manager.start(2)
        self.manager.fail(2, "temporary error")
        self.manager.retry(2)
        scene = self.manager.load()["scenes"][1]
        self.assertEqual(scene["status"], "queued")
        self.assertIsNone(scene["error"])
        self.manager.start(2)
        self.manager.complete(2)
        self.assertEqual(self.manager.load()["scenes"][1]["attempts"], 2)

    def test_only_failed_scenes_can_be_retried(self):
        self.manager.create(self.scenes)
        with self.assertRaises(ValueError):
            self.manager.retry(1)

    def test_invalid_transitions_are_rejected(self):
        self.manager.create(self.scenes)
        with self.assertRaises(ValueError):
            self.manager.complete(1)
        self.manager.start(1)
        with self.assertRaises(ValueError):
            self.manager.start(1)

    def test_next_queued_and_progress(self):
        self.manager.create(self.scenes)
        self.assertEqual(self.manager.next_queued()["id"], 1)
        self.manager.start(1)
        self.manager.complete(1)
        self.manager.start(2)
        self.manager.fail(2, "boom")
        self.assertEqual(self.manager.next_queued()["id"], 3)
        self.assertEqual(self.manager.progress(), {
            "total": 3, "queued": 1, "running": 0,
            "completed": 1, "failed": 1, "progress_percent": 33.3,
        })

    def test_duplicate_scene_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.create([{"id": 1}, {"id": 1}])

    def test_empty_queue_progress(self):
        self.manager.create([])
        self.assertEqual(self.manager.progress()["progress_percent"], 0.0)
        self.assertEqual(self.manager.progress()["total"], 0)
    def test_recover_running_scenes(self):
        self.manager.create([
            {"id": 1, "name": "Scene 1"},
            {"id": 2, "name": "Scene 2"},
        ])

        self.manager.start(1)
        self.manager.start(2)

        recovered = self.manager.recover_running()

        self.assertEqual(recovered, 2)

        scenes = self.manager.load()["scenes"]
        self.assertEqual(
            [scene["status"] for scene in scenes],
            ["queued", "queued"],
        )
        self.assertEqual(
            scenes[0]["error"],
            "Recovered after interrupted session",
        )
        self.assertEqual(scenes[0]["attempts"], 1)

    def test_recover_running_does_not_change_other_states(self):
        self.manager.create([
            {"id": 1, "name": "Queued"},
            {"id": 2, "name": "Completed"},
            {"id": 3, "name": "Failed"},
        ])

        self.manager.start(2)
        self.manager.complete(2)
        self.manager.start(3)
        self.manager.fail(3, "Test error")

        recovered = self.manager.recover_running()

        self.assertEqual(recovered, 0)

        scenes = self.manager.load()["scenes"]
        self.assertEqual(
            [scene["status"] for scene in scenes],
            ["queued", "completed", "failed"],
        )

if __name__ == "__main__":
    unittest.main()
