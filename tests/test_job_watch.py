"""The worker watchdog's output, which decides what the operator sees and when.

Two failure modes are worth pinning: reporting a finished job as "running" (so the watchdog waits
forever), and emitting anything time-varying while a job runs (which would defeat the change
detector and wake the agent every tick).
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("job_watch", ROOT / "scripts/scout-job-watch.py")
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class JobWatchTests(unittest.TestCase):
    def test_running_output_carries_nothing_that_changes_between_ticks(self):
        line = watch.render({"job": "noaa-003", "state": "running"})
        self.assertEqual("noaa-003: running", line)

    def test_a_finished_job_reports_its_outcome(self):
        line = watch.render({"job": "noaa-002", "state": "failed", "exit_code": 1,
                             "elapsed_minutes": 30, "assets": 15, "release_id": 392201946,
                             "uploaded": True})
        for fragment in ("noaa-002", "failed", "exit=1", "elapsed_min=30", "assets=15"):
            self.assertIn(fragment, line)

    def test_a_dead_worker_is_not_reported_as_running(self):
        """A collected job whose worker is destroyed must not look like a job in flight."""
        line = watch.render({"job": "noaa-002", "state": "unknown", "detail": "no parseable result"})
        self.assertNotIn("running", line)


if __name__ == "__main__":
    unittest.main()
