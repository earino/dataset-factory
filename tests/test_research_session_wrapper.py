"""Tests for the research-session wrapper.

Two regression cases found by reproducing against the real job rather than a probe:

* A job's **own** fire looked like an overlapping execution. The scheduler writes a 'running'
  row for the job before its script starts, so a gate that consulted that ledger held every fire
  against itself - the configured job never ran.
* A held **checkpoint** was silent. The two-week checkpoint is a research job, so once three
  research sessions had run it was held by the weekly cap and sent nothing. A held checkpoint
  now delivers a deterministic report instead.

The wrapper is loaded with `exec(compile(...))` and its side effects are monkeypatched, so these
tests never start an agent, never call a model and never touch the network.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "scout_research_session.py"
BUDGET = ROOT / "scripts" / "research-budget.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


wrapper = load("scout_research_session", WRAPPER)
budget = load("research_budget_for_wrapper", BUDGET)


class ActionableWorkTests(unittest.TestCase):
    """The --if-work gate: high cadence must not mean paying for empty ticks."""

    def test_a_qualified_candidate_needs_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "candidates" / "x").mkdir(parents=True)
            (root / "candidates" / "x" / "record.json").write_text(
                json.dumps({"id": "x", "status": "qualified"}))
            self.assertEqual([("x", "package")], wrapper.actionable_work(root))

    def test_a_packaged_candidate_is_release_work_but_one_awaiting_the_flip_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, awaiting in (("ready", False), ("held", True)):
                folder = root / "candidates" / name
                folder.mkdir(parents=True)
                (folder / "record.json").write_text(
                    json.dumps({"id": name, "status": "packaged", "awaiting_operator": awaiting}))
            self.assertEqual([("ready", "release")], wrapper.actionable_work(root))

    def test_parked_published_and_investigating_without_go_are_idle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, status, action in (("p", "parked", ""), ("d", "published", ""),
                                         ("i", "investigating", "waiting on a licence answer")):
                folder = root / "candidates" / name
                folder.mkdir(parents=True)
                (folder / "record.json").write_text(
                    json.dumps({"id": name, "status": status, "next_action": action}))
            self.assertEqual([], wrapper.actionable_work(root))


class PromptTests(unittest.TestCase):
    def test_the_scheduler_brief_selects_the_task_without_lifting_the_limits(self):
        prompt = wrapper.build_prompt("CONTEXT", "Do the thing.")
        self.assertIn("## Task for this session", prompt)
        self.assertIn("operator set the following through the scheduler", prompt)
        self.assertIn("selects the task for this session", prompt)
        self.assertIn("does not lift the standing limits", prompt)
        self.assertIn("Do the thing.", prompt)

    def test_no_task_section_is_added_when_there_is_no_brief(self):
        prompt = wrapper.build_prompt("CONTEXT")
        self.assertNotIn("## Task for this session", prompt)

    def test_the_session_context_is_interpolated(self):
        prompt = wrapper.build_prompt("allowance: 5.0 USD", "")
        self.assertIn("allowance: 5.0 USD", prompt)
        self.assertNotIn("{{SESSION_CONTEXT}}", prompt)


class PromptFileTests(unittest.TestCase):
    """A relative brief resolves against the repository, not the caller's cwd.

    The first live discovery tick died with `FileNotFoundError: docs/discovery-session-prompt.md`
    because the scheduler runs the script from elsewhere. Reproduced here by chdir-ing to a
    directory that has no `docs/`, which fails on the pre-fix code and passes after it.
    """

    def test_a_relative_brief_resolves_against_the_repository(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            cwd = Path.cwd()
            try:
                import os
                os.chdir(elsewhere)
                prompt = wrapper.build_prompt("CONTEXT", "",
                                              "docs/discovery-session-prompt.md")
            finally:
                os.chdir(cwd)
        self.assertIn("discovery only", prompt)
        self.assertIn("The number of verdicts is an activity count, not a quality target.", prompt)
        self.assertIn("Do not build, qualify, package, publish", prompt)

    def test_a_missing_brief_still_raises(self):
        with self.assertRaises(FileNotFoundError):
            wrapper.build_prompt("CONTEXT", "", "docs/no-such-brief.md")


class FooterTests(unittest.TestCase):
    def test_the_cli_footer_is_not_part_of_the_report(self):
        output = ("Session report text.\n"
                  "\n"
                  "Resume this session with:\n"
                  "  hermes --resume 20260919_062008_7b6775\n"
                  "Session:        20260919_062008_7b6775\n"
                  "Duration:       51s\n")
        self.assertEqual("Session report text.", wrapper.strip_footer(output))


class HeldTickTests(unittest.TestCase):
    def setUp(self):
        # The wrapper appends to the routine's runtime log. A test must never write there: the
        # log is evidence about real sessions, and test entries in it are indistinguishable from
        # held ticks that actually happened.
        self._tmp = tempfile.TemporaryDirectory()
        self._saved = (wrapper.LOG, wrapper.FACTORY_DIR)
        wrapper.FACTORY_DIR = Path(self._tmp.name)
        wrapper.LOG = Path(self._tmp.name) / "research-sessions.jsonl"

    def tearDown(self):
        wrapper.LOG, wrapper.FACTORY_DIR = self._saved
        self._tmp.cleanup()

    def _run(self, argv, held_reason):
        buffer = io.StringIO()
        with patch.object(wrapper, "run_gate", return_value=(False, "block", held_reason)), \
                patch.object(wrapper.subprocess, "run") as fake_run, \
                contextlib.redirect_stdout(buffer):
            code = wrapper.main(argv)
        return code, buffer.getvalue(), fake_run

    def test_a_held_routine_tick_is_silent_by_default(self):
        code, output, fake = self._run([], "3 research session(s) already ran (cap 3)")
        self.assertEqual(0, code)
        self.assertEqual("", output.strip())
        fake.assert_not_called()

    def test_a_held_checkpoint_still_reports_and_says_why(self):
        code, output, fake = self._run(
            ["--fallback-report"], "3 research session(s) already ran in the last 7 days (cap 3)")
        self.assertEqual(0, code)
        self.assertIn("Held, so no model work ran", output)
        self.assertIn("cap 3", output)
        # the deterministic digest is produced by research-budget.py, not by a model
        fake.assert_called()
        self.assertIn("--digest", fake.call_args[0][0])

    def test_a_held_tick_that_needs_a_decision_is_reported(self):
        code, output, _ = self._run([], "no allowance configured (allowance_usd is null)")
        self.assertEqual(0, code)
        self.assertIn("held", output.lower())

    def test_a_held_tick_is_recorded_in_the_session_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "sessions.jsonl"
            with patch.object(wrapper, "LOG", log), \
                    patch.object(wrapper, "FACTORY_DIR", Path(tmp)), \
                    patch.object(wrapper, "run_gate", return_value=(False, "block", "cap reached")), \
                    contextlib.redirect_stdout(io.StringIO()):
                wrapper.main([])
            entry = json.loads(log.read_text().strip())
            self.assertEqual("skipped", entry["event"])
            self.assertIn("cap reached", entry["reason"])


class LedgerTests(unittest.TestCase):
    """The ledger bug, as a regression test on the gate itself."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._saved = (budget.EXECUTIONS_DB, budget.STATE_DB, budget.LOCK_PATH)
        budget.EXECUTIONS_DB = self.tmp / "executions.db"
        budget.STATE_DB = self.tmp / "state.db"
        budget.LOCK_PATH = self.tmp / "lock"
        # Lock tests need valid zero-use accounting, not an unavailable database.
        from tests.test_research_budget import make_state_db
        make_state_db(budget.STATE_DB, [])

    def tearDown(self):
        (budget.EXECUTIONS_DB, budget.STATE_DB, budget.LOCK_PATH) = self._saved
        self._tmp.cleanup()

    def test_a_jobs_own_running_execution_row_does_not_hold_it(self):
        import sqlite3
        con = sqlite3.connect(budget.EXECUTIONS_DB)
        con.execute("create table executions (id text, job_id text, source text, process_id text, "
                    "pid int, process_started_at int, status text, handoff_pending int, "
                    "handoff_started_at text, claimed_at text, started_at text, finished_at text, "
                    "error text, delivery_outcome text, scheduled_instant text)")
        con.execute("insert into executions values ('r1','aabbccddeeff','chronos','p',1,0,"
                    "'running',0,null,null,'2026-09-19T06:39:37+00:00',null,null,null,null)")
        con.commit()
        con.close()
        config = dict(budget.DEFAULTS)
        config.update({"allowance_usd": 5.0, "research_job_ids": ["aabbccddeeff"],
                       "research_sources": []})
        decision = budget.evaluate(config)
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_a_lock_from_a_dead_process_is_not_honoured(self):
        budget.LOCK_PATH.write_text(json.dumps({"session_id": "scout-research",
                                                "pid": 999999999}))
        config = dict(budget.DEFAULTS)
        config.update({"allowance_usd": 5.0, "research_sources": []})
        decision = budget.evaluate(config)
        self.assertTrue(decision["allowed"], decision["reasons"])


if __name__ == "__main__":
    unittest.main()
