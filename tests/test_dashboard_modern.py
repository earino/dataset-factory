import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factory.dashboard_modern import collect
from factory.state import Store
from tests.test_dashboard import dashboard, snapshot, ui

ROOT = Path(__file__).resolve().parents[1]


class ModernDashboardTests(unittest.TestCase):
    def legacy(self):
        return {'records': [{'id': 'old', 'status': 'packaged', 'awaiting_operator': False}],
                'counts': {'packaged': 1}, 'live': [], 'release': {'pending': [{'id': 'old'}]}}, {
                'releases': [], 'errors': []}

    def test_modern_work_queue_does_not_inherit_legacy_shipping_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            manifest = json.loads((ROOT / 'tests/fixtures/modern-site/MANIFEST.json').read_text())
            receipt = json.loads((ROOT / 'audits/rewrite/ucmr-publication-success/publication.json').read_text())
            store.add('source-published', {'source': {'dataset_id': manifest['dataset'], 'task': manifest['task']},
                                          'evidence': {'MANIFEST.json': manifest}, 'publication': receipt,
                                          'private_payload': 'DO_NOT_EXPORT'})
            with store.connect() as db:
                db.execute("UPDATE candidates SET stage='published' WHERE id='source-published'")
            store.add('source-building', {'source': {'dataset_id': 'other'}, 'private_payload': 'DO_NOT_EXPORT'})
            with store.connect() as db:
                db.execute("UPDATE candidates SET stage='build' WHERE id='source-building'")
            c, r, m = collect(folder, *self.legacy())
            self.assertEqual(c['counts'], {'published': 1, 'build': 1})
            self.assertEqual(c['release']['pending'], [])
            self.assertEqual(c['legacy_counts'], {'packaged': 1})
            self.assertEqual(len(c['live']), 1)
            self.assertEqual(r['releases'][0]['detail_id'], 'source-published')
            self.assertNotIn('DO_NOT_EXPORT', json.dumps([c, r, m]))
            s = snapshot(candidates=c, releases=r, modern=m)
            html = ui.render_overview(s, [], [])
            self.assertIn('1 build', html)
            self.assertIn('candidate-source-published.html', html)
            self.assertIn('website not observed', html)

    def test_missing_modern_state_is_explicit_legacy_history(self):
        with tempfile.TemporaryDirectory() as folder:
            c, r, m = collect(folder, *self.legacy())
            self.assertEqual(m['status'], 'unavailable')
            self.assertEqual(c['counts'], {'packaged': 1})
            self.assertIn('modern state unavailable', c['scope'])

    def test_shipped_total_and_chart_keep_historical_public_releases(self):
        c = {'workflow': 'modern', 'scope': 'Modern factory', 'counts': {'published': 1},
             'live': [], 'records': []}
        releases = [{'dataset': name, 'release_tag': 'v1', 'published': True,
                     'verified_all': True, 'verified': {}, 'rows': 2, 'workflow': workflow}
                    for name, workflow in [('earlier', 'legacy'), ('current', 'modern')]]
        history = [{'published': 14}, {'workflow': 'modern', 'published': 5},
                   {'workflow': 'modern', 'published_scope': 'all_workflows', 'published': 19}]
        s = snapshot(candidates=c, releases={'releases': releases}, history=history)
        with patch.object(ui, 'sparkline', return_value='chart') as chart:
            html = ui.render_overview(s, [])
        self.assertIn('<h1>2 datasets shipped</h1>', html)
        self.assertIn('1 shipped by the modern factory; 1 earlier datasets', html)
        self.assertIn([14, 19], [call.args[0] for call in chart.call_args_list])

    def test_cost_and_alarms_use_normal_operation_and_weighted_sessions(self):
        decision = {'research_tokens_last_7_days': 45_800_000,
                    'normal_operation_tokens_last_7_days': 35_000_000,
                    'development_tokens_last_7_days': 10_800_000, 'weekly_token_budget': 40_000_000,
                    'runs_last_7_days': 250, 'normal_operation_runs_weighted_last_7_days': 200,
                    'session_cap_per_week': 200, 'allowed': False, 'reasons': ['weighted session cap']}
        s = snapshot(budget={'decision': decision})
        cost = ui.render_cost(s, [])
        self.assertIn('35.00M', cost)
        self.assertIn('10.80M', cost)
        self.assertIn('200 OF 200 SESSIONS', cost)
        _, alarms, _ = dashboard.derive_alarms(s)
        self.assertTrue(any('weighted session cap' in a for a in alarms))
        self.assertFalse(any('114%' in a for a in alarms))


if __name__ == '__main__':
    unittest.main()
