"""Offline tests for the research-budget gate.

The gate decides whether a scheduled tick may wake the model, so its failure modes are
expensive: allowing a session when the allowance is spent, or believing a configured number
that was never established. Both directions are tested here against synthetic ledgers - no
network, no real Hermes state.
"""
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "research-budget.py"

spec = importlib.util.spec_from_file_location("research_budget_script", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
budget = importlib.util.module_from_spec(spec)
sys.modules["research_budget_script"] = budget
exec(compile(SCRIPT.read_bytes(), str(SCRIPT), "exec"), budget.__dict__)

JOB = "aabbccddeeff"


def make_state_db(path, rows, session_age_minutes=60):
    """rows: (session_id, task, calls, in_tok, out_tok, cost, cost_status, source)"""
    con = sqlite3.connect(path)
    con.execute("create table if not exists sessions (id text primary key, source text, "
                "started_at real)")
    con.execute(
        "create table if not exists session_model_usage (session_id text, model text, "
        "billing_provider text, billing_base_url text, billing_mode text, task text, "
        "api_call_count integer, input_tokens integer, output_tokens integer, "
        "cache_read_tokens integer, cache_write_tokens integer, reasoning_tokens integer, "
        "estimated_cost_usd real, actual_cost_usd real, cost_status text, cost_source text, "
        "first_seen real, last_seen real)"
    )
    con.execute("delete from session_model_usage")
    con.execute("delete from sessions")
    seen = set()
    now = datetime.now(timezone.utc).timestamp()
    started_at = now - session_age_minutes * 60
    for session_id, task, calls, in_tok, out_tok, cost, cost_status, source in rows:
        con.execute("insert into session_model_usage values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (session_id, "m", "nous", "u", "", task, calls, in_tok, out_tok, 0, 0, 0,
                     cost, 0.0, cost_status, "provider_models_api", started_at, now))
        if session_id not in seen:
            con.execute("insert into sessions (id, source, started_at) values (?,?,?)",
                        (session_id, source, started_at))
            seen.add(session_id)
    con.commit()
    con.close()


def make_exec_db(path, runs):
    """runs: (job_id, status, minutes_ago, error)"""
    con = sqlite3.connect(path)
    con.execute(
        "create table if not exists executions (id text, job_id text, source text, "
        "process_id text, pid int, process_started_at int, status text, handoff_pending int, "
        "handoff_started_at text, claimed_at text, started_at text, finished_at text, "
        "error text, delivery_outcome text, scheduled_instant text)"
    )
    con.execute("delete from executions")
    now = datetime.now(timezone.utc)
    for i, (job_id, status, minutes_ago, error) in enumerate(runs):
        started = (now - timedelta(minutes=minutes_ago)).isoformat()
        con.execute(
            "insert into executions values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"run{i}", job_id, "chronos", "p", 1, 0, status, 0, None, started, started,
             started, error, "suppressed", started))
    con.commit()
    con.close()


class BudgetTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.state_db = self.tmp / "state.db"
        self.exec_db = self.tmp / "executions.db"
        self.lock = self.tmp / "session.lock"
        self._saved = (budget.STATE_DB, budget.EXECUTIONS_DB, budget.LOCK_PATH, budget.USAGE_AUDIT)
        budget.STATE_DB = self.state_db
        budget.EXECUTIONS_DB = self.exec_db
        budget.LOCK_PATH = self.lock
        budget.USAGE_AUDIT = self.tmp / "usage_audit.jsonl"
        make_state_db(self.state_db, [])
        make_exec_db(self.exec_db, [])

    def tearDown(self):
        (budget.STATE_DB, budget.EXECUTIONS_DB, budget.LOCK_PATH,
         budget.USAGE_AUDIT) = self._saved  # type: ignore[assignment]
        self._tmp.cleanup()

    def config(self, **overrides):
        config = dict(budget.DEFAULTS)
        config["research_job_ids"] = [JOB]
        config.update(overrides)
        return config


class PeriodTests(BudgetTestCase):
    def test_a_monthly_period_starts_on_the_reset_day(self):
        moment = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
        start = budget.period_start(self.config(), moment)
        self.assertEqual(datetime(2026, 9, 1, tzinfo=timezone.utc), start)

    def test_before_the_reset_day_the_period_started_last_month(self):
        moment = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
        start = budget.period_start(self.config(period={"kind": "monthly", "reset_day": 15}),
                                    moment)
        self.assertEqual(datetime(2026, 8, 15, tzinfo=timezone.utc), start)

    def test_a_weekly_period_starts_on_monday(self):
        moment = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)  # a Friday
        start = budget.period_start(self.config(period={"kind": "weekly"}), moment)
        self.assertEqual(datetime(2026, 9, 14, tzinfo=timezone.utc), start)


class GateTests(BudgetTestCase):
    def test_an_unconfigured_allowance_refuses_to_wake_the_model(self):
        decision = budget.evaluate(self.config())
        self.assertFalse(decision["allowed"])
        self.assertTrue(any("no allowance configured" in reason
                            for reason in decision["reasons"]))

    def test_an_unspent_allowance_allows_a_session(self):
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_spending_past_the_stop_fraction_holds_the_session(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 10, 1000, 500, 0.96, "estimated", "cron")])
        decision = budget.evaluate(self.config(allowance_usd=1.0))
        self.assertFalse(decision["allowed"])
        self.assertTrue(any("of the 1.0 USD period allowance" in reason
                            for reason in decision["reasons"]))
        self.assertAlmostEqual(0.96, decision["research_cost_usd"], places=6)

    def test_interactive_and_auxiliary_spend_do_not_count_against_the_allowance(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 2, 900, 100, 0.10, "estimated", "cron"),
            ("20260918_114324_d05acadf", "", 900, 9000, 900, 3.00, "estimated", "telegram"),
            ("20260918_114324_d05acadf", "approval", 40, 400, 40, 0.30, "estimated", "telegram"),
        ])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertAlmostEqual(0.10, decision["research_cost_usd"], places=6)
        self.assertEqual({"research", "interactive", "auxiliary"}, set(decision["usage"]))
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_the_gate_no_longer_consults_the_execution_ledger_for_overlap(self):
        """Regression: a job's own 'running' row held every fire against itself.

        The scheduler writes that row before the job's script starts, so overlap is now decided
        by the session lock alone. Covered in detail in tests/test_research_session_wrapper.py.
        """
        make_exec_db(self.exec_db, [(JOB, "running", 1, None)])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_a_fresh_lock_blocks_a_second_session_and_a_stale_one_does_not(self):
        self.lock.write_text(json.dumps({"session_id": "cron"}))
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertFalse(decision["allowed"])
        self.assertTrue(any("lock held" in reason for reason in decision["reasons"]))
        old = datetime.now(timezone.utc).timestamp() - 60 * 60 * 3
        import os
        os.utime(self.lock, (old, old))
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_sessions_excluded_by_id_do_not_count(self):
        make_state_db(self.state_db, [
            ("20260919_060228_2003f8", "", 20, 20000, 1000, 0.05, "estimated", "scout-research"),
            ("20260919_070000_cccc", "", 20, 20000, 1000, 0.05, "estimated", "scout-research"),
        ])
        config = self.config(allowance_usd=5.0,
                             excluded_sessions=["20260919_060228_2003f8"])
        decision = budget.evaluate(config)
        self.assertEqual(1, decision["runs_last_7_days"])
        # the excluded session's spend is not charged to the allowance either
        self.assertAlmostEqual(0.05, decision["research_cost_usd"], places=6)

    def test_the_weekly_session_cap_holds_further_sessions(self):
        make_state_db(self.state_db, [
            (f"202609{session}_080000_aaaa", "", 20, 20000, 1000, 0.05, "estimated",
             "scout-research")
            for session in ("15", "16", "17")])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertFalse(decision["allowed"])
        self.assertTrue(any("cap 3" in reason for reason in decision["reasons"]))
        self.assertEqual(3, decision["runs_last_7_days"])

    def test_sessions_older_than_a_week_do_not_count_against_the_cap(self):
        make_state_db(self.state_db, [
            ("20260910_080000_aaaa", "", 20, 20000, 1000, 0.05, "estimated", "scout-research")],
            session_age_minutes=60 * 24 * 8)
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertEqual(0, decision["runs_last_7_days"])
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_sessions_from_other_sources_do_not_count_against_the_cap(self):
        make_state_db(self.state_db, [
            (f"202609{session}_080000_aaaa", "", 20, 20000, 1000, 0.05, "estimated", "cli")
            for session in ("15", "16", "17")])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertEqual(0, decision["runs_last_7_days"])
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_a_session_that_overshoots_the_token_cap_counts_double(self):
        make_state_db(self.state_db, [
            ("20260918_080000_aaaa", "", 20, 700000, 1000, 0.30, "estimated", "scout-research"),
            ("20260919_080000_bbbb", "", 20, 1000, 500, 0.02, "estimated", "scout-research"),
        ])
        decision = budget.evaluate(self.config(allowance_usd=5.0, sessions_per_week=3))
        self.assertEqual(2, decision["runs_last_7_days"])
        self.assertEqual(1, decision["sessions_over_token_cap"])
        self.assertEqual(3, decision["runs_weighted_last_7_days"])
        self.assertFalse(decision["allowed"])
        self.assertTrue(any("count double" in reason for reason in decision["reasons"]))

    def test_a_session_within_the_token_cap_counts_once(self):
        make_state_db(self.state_db, [
            ("20260919_080000_bbbb", "", 20, 400000, 500, 0.20, "estimated", "scout-research")])
        decision = budget.evaluate(self.config(allowance_usd=5.0, sessions_per_week=3))
        self.assertEqual(1, decision["runs_weighted_last_7_days"])
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_a_tick_beyond_the_catch_up_window_is_skipped_not_caught_up(self):
        config = self.config(allowance_usd=5.0, catch_up_window_minutes=120)
        self.assertTrue(budget.evaluate(config, late_minutes=30)["allowed"])
        late = budget.evaluate(config, late_minutes=600)
        self.assertFalse(late["allowed"])
        self.assertTrue(any("beyond the 120 min window" in reason for reason in late["reasons"]))

    def test_other_scheduled_jobs_neither_block_nor_charge_the_research_allowance(self):
        make_exec_db(self.exec_db, [("e80975eddd4a", "running", 2, None)])
        make_state_db(self.state_db, [
            ("cron_e80975eddd4a_20260918", "", 30, 5000, 100, 0.40, "estimated", "cron")])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertTrue(decision["allowed"], decision["reasons"])
        self.assertAlmostEqual(0.0, decision["research_cost_usd"], places=6)
        self.assertIn("scheduled-other", decision["usage"])


class RenderTests(BudgetTestCase):
    def test_the_gate_emits_a_skip_directive_when_held(self):
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = budget.main(["--gate", "--config", str(self.tmp / "absent.json")])
        output = buffer.getvalue()
        self.assertEqual(0, code, "the skip path must still exit 0 so cron reads the directive")
        last = [line for line in output.splitlines() if line.strip()][-1]
        self.assertEqual(False, json.loads(last)["wakeAgent"])

    def test_the_resume_block_states_limits_and_remaining_allowance(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 2, 900, 100, 0.25, "estimated", "cron")])
        config = self.config(allowance_usd=2.0)
        block = budget.resume_block(config, budget.evaluate(config))
        self.assertIn("remaining: 1.7500 USD", block)
        self.assertIn("ENFORCED by the runtime", block)
        self.assertIn("60 tool-calling iterations", block)
        self.assertIn("ADVISORY", block)
        self.assertIn("600,000 estimated tokens", block)

    def test_auxiliary_calls_inside_a_research_session_are_charged_to_research(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 2, 900, 100, 0.10, "estimated", "cron"),
            (f"cron_{JOB}_20260918", "approval", 40, 400, 40, 0.30, "estimated", "cron"),
        ])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertAlmostEqual(0.40, decision["research_cost_usd"], places=6)
        self.assertNotIn("auxiliary", decision["usage"])

    def test_a_wrapper_session_tagged_by_source_counts_as_research(self):
        make_state_db(self.state_db, [
            ("20260921_080000_abcdef", "", 30, 90000, 5000, 0.60, "estimated", "scout-research"),
        ])
        decision = budget.evaluate(self.config(allowance_usd=5.0))
        self.assertAlmostEqual(0.60, decision["research_cost_usd"], places=6)
        self.assertIn("research", decision["usage"])

    def test_the_reserve_holds_a_session_with_too_little_left_for_the_next(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 30, 90000, 5000, 4.70, "estimated", "cron")])
        decision = budget.evaluate(self.config(allowance_usd=5.0, reserve_usd=0.40))
        self.assertFalse(decision["allowed"])
        self.assertTrue(any("reserve" in reason for reason in decision["reasons"]))

    def test_the_reserve_still_allows_a_session_when_enough_remains(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 30, 90000, 5000, 4.50, "estimated", "cron")])
        decision = budget.evaluate(self.config(allowance_usd=5.0, reserve_usd=0.40))
        self.assertTrue(decision["allowed"], decision["reasons"])

    def test_the_digest_says_the_figures_are_estimates_and_names_the_decision(self):
        text = budget.digest(self.config())
        self.assertIn("NOT ESTABLISHED", text)
        self.assertIn("Decision needed from the operator", text)
        self.assertIn("Estimates only", text)

    def test_the_digest_counts_sessions_the_way_the_cap_does_and_ticks_separately(self):
        make_state_db(self.state_db, [
            ("20260919_080000_bbbb", "", 20, 20000, 1000, 0.05, "estimated", "scout-research")])
        make_exec_db(self.exec_db, [(JOB, "completed", 5, None), (JOB, "completed", 10, None)])
        text = budget.digest(self.config(allowance_usd=5.0, research_job_ids=[JOB]))
        self.assertIn("Sessions this week: 1/3", text)
        # two execution rows, one of which ran the session above: ticks are not sessions
        self.assertIn("Scheduler ticks this period: 2", text)

    def test_the_digest_reports_usage_against_a_configured_allowance(self):
        make_state_db(self.state_db, [
            (f"cron_{JOB}_20260918", "", 2, 900, 100, 0.50, "estimated", "cron")])
        text = budget.digest(self.config(allowance_usd=4.0))
        self.assertIn("0.5000 / 4.0 USD used", text)
        self.assertIn("3.5000 USD remaining", text)


if __name__ == "__main__":
    unittest.main()
