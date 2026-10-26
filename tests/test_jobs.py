import json
import tempfile
import unittest
from pathlib import Path

from src.dreammv.jobs import JobManager


class JobManagerTests(unittest.TestCase):
    def test_job_state_is_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = JobManager(Path(tmp)).update("completed", "sample", "planning")
            saved = json.loads((Path(tmp) / "job.json").read_text(encoding="utf-8"))
            self.assertEqual(job["status"], "completed")
            self.assertEqual(saved["title"], "sample")

    def test_invalid_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                JobManager(tempfile.gettempdir()).update("unknown", "sample")


if __name__ == "__main__":
    unittest.main()
