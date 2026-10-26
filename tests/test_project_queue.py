import json
import tempfile
import unittest
import sys
from pathlib import Path

# Add the project's src directory to Python's module search path.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dreammv.project_queue import ProjectQueueService

class ProjectQueueServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp.name) / "demo.dreammv"
        self.project_dir.mkdir()
        self.service = ProjectQueueService(self.project_dir)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_queue_persists_inside_project_output(self):
        plan = {
            "scenes": [
                {"id": "scene-01", "name": "Opening", "start": 0, "end": 10, "prompt": "dawn"},
                {"id": "scene-02", "name": "Verse", "start": 10, "end": 20, "prompt": "city"},
            ]
        }
        result = self.service.create_from_plan(plan, title="Demo Song")
        queue_path = self.project_dir / "output" / "queue.json"
        self.assertTrue(queue_path.exists())
        self.assertEqual(result["title"], "Demo Song")
        self.assertEqual(len(self.service.load()["scenes"]), 2)

    def test_progress_reflects_scene_states(self):
        self.service.create_from_scenes([
            {"id": "a", "name": "A", "start": 0, "end": 10},
            {"id": "b", "name": "B", "start": 10, "end": 20},
        ])
        self.service.queue.start("a")
        self.service.queue.complete("a")
        progress = self.service.progress()
        self.assertEqual(progress["total"], 2)
        self.assertEqual(progress["completed"], 1)
        self.assertEqual(progress["progress_percent"], 50.0)

    def test_retry_failed_requeues_all_failed_scenes(self):
        self.service.create_from_scenes([
            {"id": "a", "name": "A", "start": 0, "end": 10},
            {"id": "b", "name": "B", "start": 10, "end": 20},
        ])
        self.service.queue.start("a")
        self.service.queue.fail("a", "test error")
        self.service.queue.start("b")
        self.service.queue.fail("b", "test error")
        self.assertEqual(self.service.retry_failed(), 2)
        self.assertEqual(self.service.progress()["queued"], 2)
        self.assertEqual(self.service.progress()["failed"], 0)

    def test_invalid_plan_scenes_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.create_from_plan({"scenes": "not a list"})

    def test_queue_json_is_valid_utf8_json(self):
        self.service.create_from_scenes([{"id": "scene-01", "name": "祈り", "start": 0, "end": 5}])
        queue_path = self.project_dir / "output" / "queue.json"
        loaded = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["scenes"][0]["name"], "祈り")


if __name__ == "__main__":
    unittest.main()
