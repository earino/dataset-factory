"""Algorithm and phase-boundary tests; historical acceptance still runs on workers."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from factory import leakage_battery as battery
from factory.recovery_recipes import Panel, exact_recipes, fixture_recipes, integer_product


def panel(target, rows, split='eval'):
    columns = {c:[str(row[c]) for row in rows] for c in rows[0]}
    ranges = {'train':(0,0),'eval':(0,len(rows)),'holdout':(len(rows),len(rows))}
    if split == 'holdout': ranges = {'train':(0,0),'eval':(0,0),'holdout':(0,len(rows))}
    return Panel(columns,ranges,target)


def predictions(p, name):
    return next(values for key,kind,split,rows,values in exact_recipes(p)
                if key == 'self:'+name and split == 'eval')


class RecoveryAlgebraTests(unittest.TestCase):
    def test_rounded_rate_requires_a_unique_integer(self):
        self.assertEqual(1, integer_product('3','0.3333'))
        self.assertEqual(0, integer_product('0','-1'))
        self.assertIsNone(integer_product('100000','0.5000'))
        self.assertIsNone(integer_product('3','0.5000'))

    def test_target_column_cannot_enter_blind_panel(self):
        with self.assertRaisesRegex(ValueError,'target column'):
            Panel({'label':['1']},{'eval':(0,1)},'label')

    def test_future_mean_join_abstains_on_missing_or_duplicate_donor(self):
        p = panel('target_high_price',[
            {'island':'N','anchor_date':'2024-01-01','last_day_mean':5},
            {'island':'N','anchor_date':'2024-01-08','last_day_mean':150},
            {'island':'S','anchor_date':'2024-01-01','last_day_mean':5},
            {'island':'S','anchor_date':'2024-01-08','last_day_mean':50},
            {'island':'S','anchor_date':'2024-01-08','last_day_mean':50}])
        values = predictions(p,'price_successor_7d')
        self.assertEqual(1,values[0]); self.assertTrue(all(math.isnan(v) for v in values[1:]))

    def test_count_rate_subtraction_is_not_a_builder_declared_probe(self):
        rows=[]
        for i,positive in enumerate([0,1,1]):
            rows.append({'site_name':'A','issue_date':f'2024-01-0{i+1}',
                         'site_prior_advisories':i,'site_prior_resolved':i,
                         'site_prior_lift30_rate':positive/i if i else -1,'site_active_prior':0})
        values=predictions(panel('lift30',rows),'site_resolved_count_difference')
        self.assertEqual([1,0],values[:2]); self.assertTrue(math.isnan(values[2]))
        rows[0]['site_active_prior']=1
        self.assertTrue(math.isnan(predictions(panel('lift30',rows),'site_resolved_count_difference')[0]))

    def test_country_history_isolates_homogeneous_same_year_group(self):
        rows=[]
        for ident,year,count,rate,last in [('A',2020,0,-1,-1),('B',2020,0,-1,-1),
                                          ('C',2021,2,1,1),('D',2022,3,.666667,0)]:
            rows.append({'country_iso3':'ZZ','plan_year_id':ident,'plan_year':year,
                         'country_prior_appeals':count,'country_prior_covered_rate':rate,
                         'country_last_prior_covered':last,'years_since_country_prior':1})
        values=predictions(panel('reached_half',rows),'history_count_difference')
        self.assertEqual([1,1,0],values[:3]); self.assertTrue(math.isnan(values[-1]))

    def test_corridor_count_operand_can_come_from_two_years_later(self):
        rows=[{'origin':'A','asylum':'B','target_year':2020,'apps_d':10,'apps_d1':5,'surged_recently':1},
              {'origin':'A','asylum':'B','target_year':2022,'apps_d':5,'apps_d1':21,'surged_recently':0}]
        p=panel('doubled',rows)
        self.assertTrue(math.isnan(predictions(p,'successor_flag')[0]))
        self.assertEqual(1,predictions(p,'successor_count')[0])

    def test_rolling_mean_reconstruction_abstains_at_rounding_boundary(self):
        measurements=[40,120,70,160,90]*12; rows=[]
        for i,value in enumerate(measurements):
            row={'station_id':'S','date':(date(2024,1,1)+timedelta(days=i)).isoformat(),
                 'pm25_mean':value,'days_since_gt90':0 if value>90 else 1,
                 'exceed_count_30d':sum(v>90 for v in measurements[max(0,i-29):i+1])}
            for lag in (1,2,3): row[f'pm25_mean_lag{lag}']=measurements[i-lag] if i>=lag else -1
            for window in (7,30):
                history=measurements[max(0,i-window+1):i+1]
                row[f'pm25_mean_{window}d']=round(sum(history)/len(history),4)
                row[f'pm25_days_valid_{window}d']=len(history)
            rows.append(row)
        p=panel('exceeds',rows)
        for window in (7,30):
            values=predictions(p,f'count_times_mean_{window}d')
            covered=[(i,v) for i,v in enumerate(values[:-1]) if math.isfinite(v)]
            self.assertGreater(len(covered),15)
            self.assertTrue(all(v==int(measurements[i+1]>90) for i,v in covered))
            self.assertTrue(math.isnan(values[33]))  # next value is exactly 90

    def test_all_row_donors_are_separate_from_same_split_donors(self):
        p=Panel({'island':['N','N'],'anchor_date':['2024-01-01','2024-01-08'],
                 'last_day_mean':['5','150']}, {'train':(0,0),'eval':(0,1),'holdout':(1,2)},
                'target_high_price')
        result={(key,split):values for key,kind,split,rows,values in exact_recipes(p)}
        self.assertTrue(math.isnan(result['self:price_successor_7d','eval'][0]))
        self.assertEqual([1],result['all:price_successor_7d','eval'])

    def test_published_fixture_literal_is_read_without_executing_code(self):
        p=panel('escape',[{'fire_id':'2024-ABC123'},{'fire_id':'2024-DEF456'}])
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'build.py').write_text('raise RuntimeError("must not execute")\n'
                'FIXTURES = [("2024", "ABC123", "100", 1)]\n')
            records=list(fixture_recipes(p,Path(tmp)))
            values=records[0][-1]
            self.assertEqual(1,values[0]); self.assertTrue(math.isnan(values[1]))

    def test_recency_and_count_extremes_have_rounding_safe_abstentions(self):
        rows=[]
        for i in range(3):
            rows.append({'station_id':'S','date':f'2024-01-0{i+1}',
                'pm25_mean':-1,'pm25_mean_lag1':-1,'pm25_mean_lag2':-1,'pm25_mean_lag3':-1,
                'days_since_gt90':[5,0,1][i],'exceed_count_30d':[0,1,1][i],
                'pm25_mean_7d':-1,'pm25_days_valid_7d':0,'pm25_mean_30d':-1,'pm25_days_valid_30d':0})
        p=panel('exceeds',rows)
        self.assertEqual([1,0],predictions(p,'reverse_last_exceed_1')[:2])
        self.assertEqual(1,predictions(p,'count_delta_extremes')[0])
        self.assertTrue(math.isnan(predictions(p,'count_delta_extremes')[1]))
        self.assertTrue(all(math.isnan(v) for v in predictions(p,'count_times_mean_7d')))


class PhaseBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root=Path(temp.name); self.data=self.root/'data'; self.data.mkdir()
        self.quality={'target':'target_high_price','positive_label':1,'time_column':'anchor_date',
                      'splits':{s:s+'.csv' for s in ('train','eval','holdout')}}
        (self.data/'quality.json').write_text(json.dumps(self.quality))
        for split in ('train','eval','holdout'):
            (self.data/(split+'.csv')).write_text('island,anchor_date,last_day_mean,target_high_price\n'
                'N,2024-01-01,50,1\nN,2024-01-08,150,0\nN,2024-01-15,50,0\n')

    def test_every_prediction_is_sealed_before_scored_label_access(self):
        calls=[]; real=battery.read_labels
        def read(*args):
            calls.append(args[-1]); return real(*args)
        with patch.object(battery,'read_labels',side_effect=read):
            frozen=battery.freeze(self.data,self.root/'audit')
            self.assertEqual(['train'],calls)
            self.assertFalse(frozen['scope']['scored_labels_read'])
            result=battery.score(self.data,self.root/'audit')
        self.assertEqual(['train','eval','holdout'],calls)
        self.assertFalse(result['ok'])
        self.assertTrue(any(f['covered']==2 and f['errors']==0 for f in result['failures']))

    def test_scored_labels_cannot_change_frozen_predictions(self):
        one=battery.freeze(self.data,self.root/'first')
        path=self.data/'eval.csv'; path.write_text(path.read_text().replace(',50,1',',50,0'))
        two=battery.freeze(self.data,self.root/'second')
        self.assertEqual(one['blind_sha256'],two['blind_sha256'])
        self.assertEqual(one['controls_sha256'],two['controls_sha256'])
        self.assertNotEqual(one['input_digest'],two['input_digest'])
        with self.assertRaisesRegex(ValueError,'artifact changed'):
            battery.score(self.data,self.root/'first')

    def test_auxiliary_mutation_and_prediction_tampering_refuse(self):
        battery.freeze(self.data,self.root/'first')
        (self.data/'README.md').write_text('new answer material')
        with self.assertRaisesRegex(ValueError,'artifact changed'):
            battery.score(self.data,self.root/'first')
        battery.freeze(self.data,self.root/'second')
        (self.root/'second/blind.zip').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'prediction archive changed'):
            battery.score(self.data,self.root/'second')

    def test_statistical_accuracy_is_not_an_exact_identity(self):
        self.quality['target']='ordinary_label'
        (self.data/'quality.json').write_text(json.dumps(self.quality))
        for split in ('train','eval','holdout'):
            path=self.data/(split+'.csv'); path.write_text(path.read_text().replace('target_high_price','ordinary_label'))
        result=battery.run(self.data,self.root/'audit')
        self.assertTrue(result['ok']); self.assertEqual([],result['failures'])
        self.assertGreater(result['flag_count'],0)

    def test_audit_vectors_cannot_be_written_into_the_release(self):
        with self.assertRaisesRegex(ValueError,'outside the shipped'):
            battery.freeze(self.data,self.data/'predictions')


if __name__=='__main__':
    unittest.main()
