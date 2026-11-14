import copy
import unittest
from factory.worker_budget import completed_charge, completed_hours, monthly_usage


class WorkerBudgetTests(unittest.TestCase):
    def record(self):
        return dict(status='deleted', server_id=123, created_at='2026-11-01T00:00:00Z',
                    deleted_at='2026-11-01T00:05:00Z', rate_ceiling_eur='0.08',
                    provider_hourly_eur='0.05868', reservation_eur='0.16',
                    budget_months=['2026-11'])

    def test_short_job_pays_one_hour_and_releases_unused_reservation(self):
        r=self.record()
        self.assertEqual(str(completed_charge(r)), '0.08')
        self.assertEqual(str(completed_charge(r,'provider_hourly_eur')), '0.05868')
        self.assertEqual(monthly_usage([r], '2026-11')['charged_eur'], '0.08')
        self.assertEqual(r['reservation_eur'],'0.16')

    def test_active_and_uncertain_workers_keep_full_reservation(self):
        for changes in [dict(status='running'),dict(server_id=None),dict(deleted_at=None),
                        dict(deleted_at='2026-10-01T00:00:00Z'),dict(rate_ceiling_eur='NaN'),
                        dict(created_at='2026-11-01T00:00:00')]:
            r={**self.record(),**changes}
            with self.subTest(changes=changes):
                self.assertIsNone(completed_charge(r))
                self.assertEqual(monthly_usage([r],'2026-11')['charged_eur'],'0.16')

    def test_rounding_and_overrun_are_not_capped_at_original_reservation(self):
        r=self.record();r['deleted_at']='2026-11-01T01:00:00Z'
        self.assertEqual(completed_hours(r),1)
        r['deleted_at']='2026-11-01T02:00:00.000001Z'
        self.assertEqual(str(completed_charge(r)),'0.24')

    def test_cross_month_charges_remain_conservative_and_mixed_ledger_sums(self):
        r=self.record();r['budget_months']=['2026-10','2026-11']
        active={**r,'status':'running'}
        for month in r['budget_months']:
            self.assertEqual(monthly_usage([r,active],month)['charged_eur'],'0.24')
        self.assertEqual(monthly_usage([r,active],'2026-12')['charged_eur'],'0')
