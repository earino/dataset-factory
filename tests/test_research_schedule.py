"""Regression tests for missed-slot recovery. No Hermes/model calls or network."""
import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.test_research_session_wrapper import load, ROOT

schedule = load("research_schedule_test", ROOT / "scripts/scout_research_schedule.py")
session = schedule.session
STAMP = 1792756800  # 2026-10-23 12:00 UTC


class ResumptionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        for name, value in (("FACTORY_DIR", self.folder), ("LOCK", self.folder / "session.lock"),
                            ("LOG", self.folder / "sessions.jsonl")):
            stack.enter_context(patch.object(session, name, value))
        self.gate = stack.enter_context(patch.object(session, "run_gate", return_value=(True, "context", "clear")))
        self.work = stack.enter_context(patch.object(session, "actionable_work", return_value=[("nz", "build")]))
        self.agent = stack.enter_context(patch.object(session, "run_agent", side_effect=self.fake_agent))
        self.output = io.StringIO()
        stack.enter_context(contextlib.redirect_stdout(self.output))

    def fake_agent(self, command, timeout, fd):
        # Launch is downstream of durable admission and still owns the real OS mutex.
        states = [json.loads(p.read_text()) for p in self.folder.glob("research-schedule-*.json")]
        self.assertTrue(any(s["event"] == "admitted" for s in states))
        with self.assertRaises(session.SessionBusy):
            with session.admission_lock():
                self.fail("model launch lost the admission lock")
        return subprocess.CompletedProcess(command, 0, "completed", "")

    def tick(self, role="discovery", stamp=STAMP):
        args = session.parse_args(["--if-work"] if role == "advancement" else [])
        return schedule.tick(role, args, stamp)

    def test_busy_slot_recovers_on_next_check_without_manual_trigger(self):
        """Used as the hosted timer-fired no-model recovery probe as well."""
        lock = self.folder / "research-session.mutex"
        holder = subprocess.Popen(
            [sys.executable, "-c", "import fcntl,sys; f=open(sys.argv[1],'a'); "
             "fcntl.flock(f,fcntl.LOCK_EX); print('locked',flush=True); sys.stdin.readline()", str(lock)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual("locked", holder.stdout.readline().strip())
            self.assertEqual(0, self.tick())
            self.assertEqual(0, self.tick(stamp=STAMP + 300))
            self.gate.assert_not_called()
            self.agent.assert_not_called()
            self.assertIsNone(schedule.read_state("discovery")["slot"])
            self.assertEqual(1, self.output.getvalue().count("deferred"))
        finally:
            holder.communicate("release\n", timeout=5)
        # Fresh invocation reads the durable receipt, not an in-memory pending flag.
        self.assertEqual(0, self.tick(stamp=STAMP + 600))
        self.agent.assert_called_once()
        self.assertEqual("completed", schedule.read_state("discovery")["event"])
        self.tick(stamp=STAMP + 900)
        self.agent.assert_called_once()

    def test_budget_hold_retains_slot_and_reports_once_then_rechecks_gate(self):
        self.gate.return_value = (False, "context", "token allowance exhausted")
        self.tick()
        self.tick(stamp=STAMP + 300)
        self.agent.assert_not_called()
        self.assertEqual(1, self.output.getvalue().count("deferred"))
        self.assertIsNone(schedule.read_state("discovery")["slot"])
        self.gate.return_value = (True, "context", "clear")
        self.tick(stamp=STAMP + 600)
        self.agent.assert_called_once()
        self.assertEqual(3, self.gate.call_count)

    def test_missing_or_corrupt_accounting_cannot_consume_slot_or_launch(self):
        self.gate.side_effect = session.AdmissionError("accounting unavailable")
        with self.assertRaises(session.AdmissionError):
            self.tick()
        self.agent.assert_not_called()
        self.assertIsNone(schedule.read_state("discovery")["slot"])

    def test_long_outage_coalesces_and_clock_rollback_does_not_replay(self):
        self.tick()
        self.tick(stamp=STAMP + 3 * 86400)
        self.tick(stamp=STAMP + 3 * 86400 + 300)
        self.tick(stamp=STAMP)
        self.assertEqual(2, self.agent.call_count)

    def test_failed_launch_is_not_retried_every_five_minutes(self):
        self.agent.side_effect = FileNotFoundError()
        self.assertEqual(2, self.tick())
        self.tick(stamp=STAMP + 300)
        self.agent.assert_called_once()
        self.tick(stamp=STAMP + schedule.PERIOD)
        self.assertEqual(2, self.agent.call_count)

    def test_crash_after_admission_is_not_replayed(self):
        self.agent.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.tick("advancement")
        self.work.return_value = [("new", "package")]
        self.tick("advancement", STAMP + 300)
        self.agent.assert_called_once()
        self.assertFalse(schedule.read_state("advancement")["followup_allowed"])

    def test_one_early_advancement_for_new_eligible_stage_not_unchanged_work(self):
        self.tick("advancement")
        self.tick("advancement", STAMP + 300)
        self.agent.assert_called_once()
        self.work.return_value = [("nz", "package")]
        self.tick("advancement", STAMP + 600)
        self.assertEqual(2, self.agent.call_count)
        self.work.return_value = [("nz", "release")]
        self.tick("advancement", STAMP + 900)
        self.assertEqual(2, self.agent.call_count)
        self.tick("advancement", STAMP + schedule.PERIOD)
        self.assertEqual(3, self.agent.call_count)

    def test_removing_work_does_not_trigger_followup(self):
        self.work.return_value = [("a", "build"), ("b", "build")]
        self.tick("advancement")
        self.work.return_value = [("b", "build")]
        self.tick("advancement", STAMP + 300)
        self.agent.assert_called_once()

    def test_idle_is_free_and_new_eligible_work_resumes_before_next_slot(self):
        self.work.return_value = []
        self.tick("advancement")
        self.gate.assert_not_called()
        self.agent.assert_not_called()
        self.work.return_value = [("nz", "build")]
        self.tick("advancement", STAMP + 300)
        self.agent.assert_called_once()

    def test_duplicate_same_role_does_not_corrupt_receipt(self):
        with schedule.role_lock("discovery"):
            with self.assertRaises(session.SessionBusy):
                self.tick()
        self.agent.assert_not_called()

    def test_bad_receipt_and_symlink_fail_closed(self):
        path = schedule.state_path("discovery")
        for body in ("{", "{}", '{"version":1,"version":1}'):
            path.write_text(body)
            with self.assertRaises(session.AdmissionError):
                self.tick()
        path.unlink()
        path.symlink_to(self.folder / "unrelated")
        with self.assertRaises(session.AdmissionError):
            self.tick()
        self.agent.assert_not_called()

    def test_status_and_dry_run_are_read_only_from_other_working_directory(self):
        previous = Path.cwd()
        try:
            os.chdir(self.folder)
            self.assertEqual(0, schedule.main(["--role", "discovery", "--status"]))
            self.assertEqual(0, schedule.main(["--role", "discovery", "--dry-run"]))
        finally:
            os.chdir(previous)
        self.agent.assert_not_called()
        self.assertFalse(schedule.state_path("discovery").exists())
        self.assertIn("GATE: ALLOWED", self.output.getvalue())

    def test_original_utc_offsets_cross_midnight(self):
        self.assertEqual(STAMP, schedule.slot_for("discovery", STAMP + 3600))
        self.assertEqual(STAMP - 7200, schedule.slot_for("advancement", STAMP))
        midnight = STAMP - 43200
        self.assertEqual(midnight - 7200, schedule.slot_for("advancement", midnight + 60))


if __name__ == "__main__":
    unittest.main()
