import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from prediction_fixtures import research_contract

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'skills/dataset-qualification/scripts/qualify_dataset.py'
gate = ModuleType('contract_gate')
exec(compile(PATH.read_bytes(), str(PATH), 'exec'), gate.__dict__)


def columns(rows):
    names = list(rows[0])
    return names, {k: [str(row[k]) for row in rows] for k in names}


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = {split: columns([{'id': split, 'date': day, 'x': 2, 'y': 0}])
                     for split, day in [('train', '2020-01-01'), ('eval', '2021-01-01'), ('holdout', '2022-01-01')]}
        self.q = {'target': 'y', 'positive_label': 1, 'id_columns': ['id'],
                  'evaluation_contract': research_contract(['id', 'date', 'x', 'y'], 'y')}

    def checks(self):
        report = gate.Report(self.root)
        gate.check_evaluation_contract(self.root, self.q, report, self.rows)
        return {r['check']: r for r in report.results}, report

    def ledger(self, late=False):
        self.q['evaluation_contract']['availability_ledger'] = 'availability.csv'
        with (self.root/'availability.csv').open('w') as handle:
            writer = csv.DictWriter(handle, fieldnames=['split','id','prediction_time','features_available_at','label_available_at'])
            writer.writeheader()
            for split, year in [('train',2020), ('eval',2021), ('holdout',2022)]:
                writer.writerow({'split':split,'id':split,'prediction_time':f'{year}-01-01T00:00:00Z',
                                 'features_available_at':f'{year}-01-01T00:00:00Z',
                                 'label_available_at':f'{year + (1 if late and split == "train" else 0)}-02-01T00:00:00Z'})

    def test_missing_contract_fails(self):
        self.q.pop('evaluation_contract')
        _, r = self.checks()
        self.assertFalse(r.ok)

    def test_research_scope_is_allowed_without_claiming_real_time_validity(self):
        _, r = self.checks()
        self.assertTrue(r.ok, r.render())
        self.q['evaluation_contract']['use'] = 'historical_forecasting'
        _, r = self.checks()
        self.assertFalse(r.ok)

    def test_every_shipped_input_including_ids_needs_evidence(self):
        del self.q['evaluation_contract']['feature_evidence']['id']
        checks, _ = self.checks()
        self.assertFalse(checks['contract.every_input_has_availability_evidence']['ok'])

    def test_full_ledger_detects_training_target_horizon_overlap(self):
        self.ledger(late=True)
        checks, _ = self.checks()
        self.assertFalse(checks['contract.label_availability']['ok'])
        self.assertIn('train outcomes unavailable', checks['contract.label_availability']['detail'])

    def test_full_ledger_is_hashed_and_complete(self):
        self.ledger()
        checks, r = self.checks()
        self.assertTrue(checks['contract.label_availability']['ok'])
        self.assertIn('availability_ledger', r.artifact)
        p = self.root/'availability.csv'
        p.write_text('\n'.join(p.read_text().splitlines()[:-1])+'\n')
        checks, _ = self.checks()
        self.assertFalse(checks['contract.label_availability']['ok'])

    def test_ledger_feature_delay_is_not_hidden_by_earlier_observation_date(self):
        self.ledger()
        p=self.root/'availability.csv'
        s=p.read_text().replace('train,train,2020-01-01T00:00:00Z,2020-01-01', 'train,train,2020-01-01T00:00:00Z,2020-01-02')
        p.write_text(s)
        checks,_=self.checks()
        self.assertFalse(checks['contract.label_availability']['ok'])

    def test_reverse_history_is_detected_without_reading_donor_targets(self):
        rows = [{'entity':'a','date':'2020-01-01','prev':0,'days':1,'y':1},
                {'entity':'a','date':'2020-01-02','prev':1,'days':1,'y':0}]
        probe={'entity_columns':['entity'],'time_column':'date','left':'prev','operation':'copy','lag_days_column':'days'}
        result=gate.cross_row_probe({'eval':columns(rows)},self.q,probe)['eval']
        self.assertEqual((result['covered'],result['mismatches']),(1,0))
        rows[1]['y']=1
        self.assertEqual(gate.cross_row_probe({'eval':columns(rows)},self.q,probe)['eval'],result)
        probe['left']='y'
        with self.assertRaises(ValueError): gate.cross_row_probe({'eval':columns(rows)},self.q,probe)

    def test_duplicate_target_keys_are_excluded(self):
        rows=[{'entity':'a','date':'2020-01-01','prev':0,'y':1},
              {'entity':'a','date':'2020-01-01','prev':0,'y':0},
              {'entity':'a','date':'2020-01-02','prev':1,'y':0}]
        p={'entity_columns':['entity'],'time_column':'date','left':'prev','operation':'copy','offset_days':1}
        self.assertEqual(gate.cross_row_probe({'eval':columns(rows)},self.q,p)['eval']['covered'],0)

    def test_month_and_year_reverse_lags(self):
        for offset, later in [(1,'2020-02'),(12,'2021-01')]:
            rows=[{'entity':'a','date':'2020-01','prev':0,'y':1}, {'entity':'a','date':later,'prev':1,'y':0}]
            p={'entity_columns':['entity'],'time_column':'date','left':'prev','operation':'copy','offset_months':offset}
            self.assertEqual(gate.cross_row_probe({'eval':columns(rows)},self.q,p)['eval']['mismatches'],0)

    def test_batch_contract_refuses_recoverable_history_but_research_rows_can_qualify(self):
        self.rows={'eval':columns([{'id':'a','date':'2020-01-01','x':0,'y':1},
                                  {'id':'a','date':'2020-01-02','x':1,'y':0}])}
        c=self.q['evaluation_contract'];c['access']='common_cutoff_batch'
        c['cross_row_audit']['probes']=[{'entity_columns':['id'],'time_column':'date','left':'x','operation':'copy','offset_days':1}]
        checks,_=self.checks()
        self.assertFalse(checks['contract.cross_row_probe_0']['ok'])
        c['access']='isolated_rows'
        checks,_=self.checks()
        self.assertTrue(checks['contract.cross_row_probe_0']['ok'])

    def test_cross_split_donor_and_price_operand(self):
        rows={'train':columns([{'entity':'a','date':'2020-01-08','price':3,'y':0}]),
              'eval':columns([{'entity':'a','date':'2020-01-01','price':2,'y':1}])}
        p={'entity_columns':['entity'],'time_column':'date','left':'price','right':'price',
           'right_row':'earlier','operation':'gt','offset_days':7}
        result=gate.cross_row_probe(rows,self.q,p)
        self.assertEqual((result['eval']['covered'],result['eval']['mismatches']),(1,0))
        self.assertEqual(result['train']['covered'],0)

    def test_noaa_approximate_recovery_still_requires_restriction(self):
        self.rows={'eval':columns([{'id':'a','date':'2020-01-01','x':0,'y':0},
                                  {'id':'a','date':'2020-01-02','x':0.011,'y':0}])}
        c=self.q['evaluation_contract'];c['access']='common_cutoff_batch'
        c['cross_row_audit']['probes']=[{'entity_columns':['id'],'time_column':'date','left':'x',
                                       'operation':'gt','threshold':0,'offset_days':1}]
        checks,_=self.checks()
        check=checks['contract.cross_row_probe_0']
        self.assertFalse(check['ok'])
        self.assertEqual(check['evidence']['eval']['mismatches'],1)
