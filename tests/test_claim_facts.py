"""Algorithm checks, not measurements on the real acceptance artifacts."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from factory.claim_facts import measure, population_claims
from factory.claim_checks import inspect, text_claims


class ClaimFactsTests(unittest.TestCase):
    def make(self, root, *, swapped=False, duplicate=False):
        quality = {'target':'label','time_column':'date','splits':{s:s+'.csv' for s in ('train','eval','holdout')}}
        (root/'quality.json').write_text(json.dumps(quality))
        (root/'meta.json').write_text(json.dumps({'id_columns':['id']}))
        for split,year in [('train',2020),('eval',2021),('holdout',2022)]:
            with (root/(split+'.csv')).open('w',newline='') as stream:
                writer=csv.writer(stream)
                writer.writerow(['id','date','label','pm25_min','pm25_max','beds_bucket'])
                for i in range(4):
                    writer.writerow([split+str(0 if duplicate else i),f'{year}-01-0{i+1}',i%2,
                                     10 if swapped else 1,1 if swapped else 10,'1-3' if i%2 else '4-10'])

    def test_full_rows_count_grain_years_and_minmax(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root)
            facts=measure(root)
            self.assertTrue(facts['ok'])
            self.assertEqual(4,facts['splits']['eval']['rows'])
            self.assertEqual(.5,facts['splits']['eval']['positive_rate'])
            self.assertEqual([2021],facts['splits']['eval']['columns']['date']['years'])
            self.assertEqual(5,len(facts['inputs']))

    def test_minmax_and_declared_grain_fail_without_builder_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root,swapped=True,duplicate=True)
            facts=measure(root)
            self.assertFalse(facts['ok'])
            self.assertEqual({'min_le_max','declared_grain_unique'},{p['rule'] for p in facts['problems']})
            self.assertEqual(4,next(p['violations'] for p in facts['problems'] if p['rule']=='min_le_max'))

    def test_dictionary_and_rounded_prevalence_are_recomputed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root);facts=measure(root)
            text='| `beds_bucket` | category | 1-9, 10-24, 25-49, 50+ |\nThe positive rate is train (49.99%) and eval (50.00%).'
            findings=text_claims(text,facts)
            self.assertIn('dictionary_bins',{f['rule'] for f in findings})
            p=[f for f in findings if f['rule']=='prevalence_prose']
            self.assertEqual(['train'],[f['split'] for f in p])
            self.assertEqual([],text_claims('Positive rate: 50.0% eval.',facts))

    def test_metadata_population_claims_are_automatic(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root);facts=measure(root)
            value={'rows':{'train':3},'splits':{'eval':{'positives':1,'positive_rate':.5}}}
            self.assertEqual(2,len(population_claims(value,facts)))

    def test_honest_negation_does_not_waive_later_guarantees(self):
        self.assertEqual([],text_claims('The runner does not enforce holdout isolation. No scoring guarantee is made.'))
        findings=text_claims('The runner does not enforce isolation. However, the benchmark keeps the holdout outside agents workspaces.')
        self.assertEqual(['unsupported_scoring_guarantee'],[f['rule'] for f in findings])
        self.assertTrue(text_claims('The holdout stays outside evaluated agents workspaces.'))

    def test_interval_sign_and_equivalence_language(self):
        self.assertTrue(text_claims('Its edge over persistence is measured: difference [-0.10, -0.07].'))
        self.assertEqual([],text_claims('Persistence minus ratio: [-0.10, -0.07]. An interval spanning zero does not establish equivalence.'))
        self.assertTrue(text_claims('The interval spans zero, so the two are inseparable.'))
        self.assertTrue(text_claims('Every per-page sha256 is pinned in code; the build fails if publisher bytes change.'))
        self.assertEqual([],text_claims('The builder records source hashes but does not enforce expected digests.'))

    def test_wrong_training_years_in_literal_scorer_note(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root);facts=measure(root)
            (root/'score.py').write_text('NOTE="Training rows cover 2016-2022."\nraise RuntimeError("never run")\n')
            result=inspect(root,facts)
            self.assertIn('split_year_range',{f['rule'] for f in result['findings']})

    def test_inspects_all_named_documents_and_nested_json_strings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root);facts=measure(root)
            (root/'README.md').write_text('The runner guarantees holdout isolation.')
            (root/'measurements.json').write_text(json.dumps({'nested':{'claim':'The holdout remains sealed until design is frozen.'}}))
            report=inspect(root,facts)
            self.assertFalse(report['ok'])
            self.assertEqual({'README.md','measurements.json'},{r['file'] for r in report['findings']})


if __name__=='__main__':
    unittest.main()
