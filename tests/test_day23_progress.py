"""Small regression tests for queue progress display calculations."""
import unittest

def summarize_progress(progress, scene_count):
    total = int(progress.get("total", scene_count))
    completed = int(progress.get("completed", 0))
    percent = float(progress.get("percent", (completed / total * 100 if total else 0)))
    return total, max(0, min(100, round(percent)))

class Day23ProgressHelperTests(unittest.TestCase):
    def test_percent_from_completed_count_when_missing(self):
        self.assertEqual(summarize_progress({"completed": 2}, 4), (4, 50))
    def test_zero_scenes_has_zero_percent(self):
        self.assertEqual(summarize_progress({}, 0), (0, 0))
    def test_percent_is_clamped(self):
        self.assertEqual(summarize_progress({"total": 2, "percent": 140}, 2), (2, 100))
        self.assertEqual(summarize_progress({"total": 2, "percent": -5}, 2), (2, 0))

if __name__ == "__main__":
    unittest.main()
