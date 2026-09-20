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


    def test_a_running_job_is_watched_without_being_listed_anywhere(self):
        """The job records are the source, so a launch cannot be forgotten - and a job whose record
        has been marked terminal must not be watched."""
        import json
        import tempfile
        from pathlib import Path as _Path

        with tempfile.TemporaryDirectory() as folder:
            root = _Path(folder)
            (root / "jobs").mkdir()
            (root / "jobs" / "noaa-009.json").write_text(json.dumps(
                {"status": "running", "job": {"id": "noaa-009"}}))
            (root / "jobs" / "noaa-008.json").write_text(json.dumps(
                {"status": "deleted", "job": {"id": "noaa-008"}}))
            original = watch.ROOT
            watch.ROOT = root
            try:
                watched = watch.watchlist()
            finally:
                watch.ROOT = original
        self.assertEqual(["noaa-009"], watched)

    def test_an_explicit_watchlist_entry_is_still_honoured(self):
        import json
        import tempfile
        from pathlib import Path as _Path

        with tempfile.TemporaryDirectory() as folder:
            root = _Path(folder)
            (root / "jobs").mkdir()
            (root / ".factory").mkdir()
            (root / ".factory" / "watchlist.json").write_text(json.dumps(["noaa-010"]))
            original = watch.ROOT
            watch.ROOT = root
            try:
                watched = watch.watchlist()
            finally:
                watch.ROOT = original
        self.assertEqual(["noaa-010"], watched)



    def test_the_scheduled_entrypoint_is_executable_by_the_scheduler(self):
        """The scheduler runs `.py` as Python and `.sh` via bash.

        The first entrypoint was a shell script named `.py`, so every tick raised SyntaxError and the
        watchdog never ran at all - while looking, from the outside, exactly like a watchdog with
        nothing to report. Check the extension against the contents.
        """
        entrypoint = Path("/opt/data/scripts/scout_job_watch.sh")
        if not entrypoint.is_file():
            self.skipTest("scheduled entrypoint is not on this machine")
        text = entrypoint.read_text()
        self.assertTrue(text.startswith("#!"), "a scheduled script needs a shebang")
        self.assertIn("/bin/sh", text.splitlines()[0],
                      ".sh entrypoints are run by a shell; anything else must be valid Python")



    def test_pretty_printed_collector_output_is_parsed(self):
        """The collector prints JSON across several lines.

        A line-based reader that required a line to start with `{` never matched, so a job that was
        running got reported as gone - the third silent parsing bug in this watchdog, which is why
        the real output shape is pinned here.
        """
        parsed = watch._parse_json('{\n  "job": "noaa-baseline-001",\n  "status": "running",\n'
                                   '  "expires": 1789891102\n}\n')
        self.assertEqual({"job": "noaa-baseline-001", "status": "running", "expires": 1789891102},
                         parsed)

    def test_a_worker_gone_message_parses_as_no_json(self):
        self.assertIsNone(watch._parse_json(
            "factory: Worker is gone; recover artifacts from the recorded staging release\n"))

    def test_a_finished_job_line_is_rendered_from_the_collected_record(self):
        line = watch.render({"job": "noaa-baseline-001", "state": "succeeded", "exit_code": 0,
                             "elapsed_minutes": 44, "assets": 3, "release_id": 1, "uploaded": True})
        self.assertIn("succeeded", line)
        self.assertIn("elapsed_min=44", line)



if __name__ == "__main__":
    unittest.main()
