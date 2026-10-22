"""Budget decisions must distinguish unavailable accounting from measured zero."""
import contextlib
import io
import json
import sqlite3
from unittest.mock import patch

from tests.test_research_budget import BudgetTestCase, budget, make_state_db
from datetime import datetime, timezone


class AccountingFailureTests(BudgetTestCase):
    def assert_held_unknown(self):
        decision = budget.evaluate(self.config(allowance_usd=30, weekly_token_budget=40_000_000))
        self.assertFalse(decision['allowed'])
        self.assertFalse(decision['accounting_available'])
        for field in ('research_cost_usd', 'research_tokens_last_7_days',
                      'runs_last_7_days', 'runs_weighted_last_7_days', 'usage'):
            self.assertIsNone(decision[field], field)
        self.assertIn(str(self.state_db), decision['reasons'][0])
        return decision

    def test_missing_database_does_not_create_one_or_admit(self):
        self.state_db.unlink()
        self.assert_held_unknown()
        self.assertFalse(self.state_db.exists())

    def test_directory_instead_of_database_holds(self):
        self.state_db.unlink()
        self.state_db.mkdir()
        self.assert_held_unknown()

    def test_corrupt_database_holds_and_does_not_echo_contents(self):
        self.state_db.write_text('private-canary not a SQLite database')
        decision = self.assert_held_unknown()
        self.assertNotIn('private-canary', json.dumps(decision))

    def test_missing_tables_and_columns_hold(self):
        for statement in ('drop table session_model_usage',
                          'alter table sessions drop column source'):
            with self.subTest(statement=statement):
                self.state_db.unlink()
                make_state_db(self.state_db, [])
                with contextlib.closing(sqlite3.connect(self.state_db)) as con:
                    con.execute(statement)
                    con.commit()
                self.assert_held_unknown()

    def test_permission_failure_holds_without_raw_error(self):
        with patch.object(budget.sqlite3, 'connect', side_effect=PermissionError('private-canary')):
            decision = self.assert_held_unknown()
        self.assertNotIn('private-canary', json.dumps(decision))

    def test_exclusive_sqlite_lock_holds(self):
        con = sqlite3.connect(self.state_db)
        self.addCleanup(con.close)
        con.execute('begin exclusive')
        self.assert_held_unknown()
        con.rollback()
        self.assertTrue(budget.evaluate(self.config(allowance_usd=30))['allowed'])

    def test_failure_after_partial_reads_discards_totals(self):
        real = budget._rows
        calls = 0
        def fail_third(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise budget.AccountingUnavailable(f'{self.state_db}: query failed')
            return real(*args, **kwargs)
        with patch.object(budget, '_rows', side_effect=fail_third):
            self.assert_held_unknown()
        self.assertEqual(3, calls)

    def test_valid_empty_database_is_measured_zero(self):
        decision = budget.evaluate(self.config(allowance_usd=30))
        self.assertTrue(decision['allowed'], decision['reasons'])
        self.assertTrue(decision['accounting_available'])
        self.assertEqual(0, decision['research_tokens_last_7_days'])
        self.assertEqual(0, decision['research_cost_usd'])

    def test_encoded_path_is_read_as_literal_filename(self):
        special = self.tmp / 'state?#.db'
        self.state_db.rename(special)
        budget.STATE_DB = special
        self.assertTrue(budget.evaluate(self.config(allowance_usd=30))['allowed'])

    def test_gate_emits_explicit_hold_and_never_writes_marker(self):
        config = self.tmp / 'config.json'
        config.write_text(json.dumps(self.config(allowance_usd=30)))
        self.state_db.unlink()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = budget.main(['--gate', '--write-lock', '--config', str(config)])
        self.assertEqual(0, code)
        lines = output.getvalue().splitlines()
        self.assertFalse(json.loads(lines[-1])['wakeAgent'])
        directive = next(json.loads(line)['researchBudget'] for line in lines
                         if line.startswith('{"researchBudget"'))
        self.assertFalse(directive['allowed'])
        self.assertIsNone(directive['research_cost_usd'])
        self.assertFalse(self.lock.exists())

    def test_status_json_and_digest_render_unknown_not_zero(self):
        config = self.config(allowance_usd=30)
        self.state_db.unlink()
        decision = budget.evaluate(config)
        for text in (budget.resume_block(config, decision), budget.digest(config)):
            self.assertIn('UNKNOWN', text)
            self.assertNotIn('0.0000', text)
        self.assertIsNone(json.loads(json.dumps(decision))['research_cost_usd'])

    def test_invalid_usage_values_cannot_reduce_spend_or_token_totals(self):
        for column, value in (('input_tokens', -1), ('output_tokens', None),
                              ('api_call_count', 1.5), ('estimated_cost_usd', float('inf')),
                              ('estimated_cost_usd', -1), ('input_tokens', 'bad')):
            with self.subTest(column=column, value=value):
                make_state_db(self.state_db, [('research', 'chat', 1, 100, 10, 0.1,
                                                'estimated', 'scout-research')])
                with contextlib.closing(sqlite3.connect(self.state_db)) as con:
                    con.execute(f'update session_model_usage set {column} = ?', (value,))
                    con.commit()
                self.assert_held_unknown()

    def test_unknown_research_pricing_is_not_free_usage(self):
        for status in (None, 'unknown'):
            with self.subTest(status=status):
                make_state_db(self.state_db, [('research', 'chat', 1, 100, 10, 0.0,
                                               status, 'scout-research')])
                decision = budget.evaluate(self.config(allowance_usd=30))
                self.assertFalse(decision['allowed'])
                self.assertTrue(decision['accounting_available'])
                self.assertFalse(decision['pricing_available'])
                self.assertIsNone(decision['research_cost_usd'])
                self.assertEqual(110, decision['research_tokens_last_7_days'])

    def test_unknown_interactive_pricing_does_not_hold_research(self):
        make_state_db(self.state_db, [('interactive', 'chat', 1, 100, 10, 0.0,
                                       'unknown', 'telegram')])
        self.assertTrue(budget.evaluate(self.config(allowance_usd=30))['allowed'])

    def test_positive_session_counter_without_usage_holds_but_zero_does_not(self):
        with contextlib.closing(sqlite3.connect(self.state_db)) as con:
            con.execute('alter table sessions add column api_call_count integer default 0')
            con.execute('insert into sessions values (?, ?, ?, ?)',
                        ('orphan', 'scout-research', datetime.now(timezone.utc).timestamp(), 0))
            con.commit()
        self.assertTrue(budget.evaluate(self.config(allowance_usd=30))['allowed'])
        with contextlib.closing(sqlite3.connect(self.state_db)) as con:
            con.execute('update sessions set api_call_count=1')
            con.commit()
        self.assert_held_unknown()

    def test_recorded_exclusions_still_apply_to_unknown_pricing(self):
        make_state_db(self.state_db, [('verification', 'chat', 1, 100, 10, 0.0,
                                       'unknown', 'scout-research')])
        decision = budget.evaluate(self.config(allowance_usd=30, excluded_sessions=['verification']))
        self.assertTrue(decision['allowed'])

    def test_real_gate_refusal_prevents_wrapper_from_starting_agent(self):
        import os
        from tests.test_session_admission import wrapper
        self.state_db.unlink()
        with patch.dict(os.environ, {'SCOUT_STATE_DB': str(self.state_db)}), \
                patch.object(wrapper, 'FACTORY_DIR', self.tmp / 'factory'), \
                patch.object(wrapper, 'LOCK', self.lock), \
                patch.object(wrapper, 'LOG', self.tmp / 'wrapper.jsonl'), \
                patch.object(wrapper, 'run_agent') as agent, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, wrapper.main([]))
        agent.assert_not_called()
        self.assertFalse(self.lock.exists())

    def test_dashboard_does_not_turn_unknown_accounting_into_zero_gauges(self):
        from tests.test_dashboard import dashboard, snapshot
        self.state_db.unlink()
        decision = budget.evaluate(self.config(allowance_usd=30))
        data = snapshot(budget={'decision': decision})
        cost = dashboard.ui.render_cost(data, [], [])
        self.assertIn('Usage or ceiling unknown', cost)
        self.assertIn('Session count or cap unknown', cost)
        self.assertNotIn('0 of 3 sessions', cost)
        self.assertNotIn('0.0%', cost)
        self.assertIn('hold reasons are resolved', cost)
        overview = dashboard.ui.render_overview(data, [], [])
        self.assertIn('Usage or ceiling unknown', overview)
        self.assertNotIn('0.0% of ceiling', overview)

    def unpriced_config(self, **overrides):
        make_state_db(self.state_db, [('research', 'chat', 1, 100, 10, 0.0,
                                       'unknown', 'scout-research')])
        return self.config(allowance_usd=30, unpriced_research_policy='require_token_budget',
                           **overrides)

    def test_operator_selected_token_policy_preserves_measured_usage(self):
        config = self.unpriced_config(weekly_token_budget=1000)
        decision = budget.evaluate(config)
        self.assertTrue(decision['allowed'], decision['reasons'])
        self.assertEqual(110, decision['research_tokens_last_7_days'])
        self.assertIsNone(decision['research_cost_usd'])
        self.assertTrue(decision['warnings'])
        for output in (budget.resume_block(config, decision), budget.digest(config)):
            self.assertIn('UNKNOWN', output)
            self.assertNotIn('0.0000', output)

    def test_token_policy_requires_a_positive_ceiling(self):
        for ceiling in (None, 0, -1):
            with self.subTest(ceiling=ceiling):
                self.assertFalse(budget.evaluate(self.unpriced_config(weekly_token_budget=ceiling))['allowed'])

    def test_unpriced_calls_still_hit_the_token_ceiling(self):
        decision = budget.evaluate(self.unpriced_config(weekly_token_budget=110))
        self.assertFalse(decision['allowed'])
        self.assertTrue(any('weekly budget' in reason for reason in decision['reasons']))

    def test_token_policy_never_substitutes_for_missing_usage(self):
        config = self.unpriced_config(weekly_token_budget=1000)
        self.state_db.unlink()
        self.assertFalse(budget.evaluate(config)['allowed'])

    def test_unknown_policy_is_not_permission_to_ignore_pricing(self):
        config = self.unpriced_config(weekly_token_budget=1000)
        config['unpriced_research_policy'] = 'ignore'
        self.assertFalse(budget.evaluate(config)['allowed'])
