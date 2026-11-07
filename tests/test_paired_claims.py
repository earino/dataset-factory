import csv
import json
from pathlib import Path
import tempfile
import unittest

from factory.asset_integrity import sha256
from factory.paired_claims import interval, from_evidence, ranking, weighted_auc


class PairedClaimsTests(unittest.TestCase):
    def test_auc_ties_and_reversing_comparison_reverses_interval(self):
        labels=[0,1]*30
        left=[float(y) for y in labels]
        right=[.5]*len(labels)
        clusters=[str(i//2) for i in range(len(labels))]
        self.assertEqual(.5,weighted_auc(labels,ranking(right),[1]*len(labels)))
        a=interval(labels,left,right,clusters,resamples=150)
        b=interval(labels,right,left,clusters,resamples=150)
        self.assertEqual('positive',a['direction'])
        self.assertEqual('negative',b['direction'])
        self.assertAlmostEqual(a['observed_difference'],-b['observed_difference'])
        self.assertAlmostEqual(a['ci95_low'],-b['ci95_high'])
        self.assertAlmostEqual(a['ci95_high'],-b['ci95_low'])

    def test_zero_interval_is_inconclusive_not_equivalence(self):
        labels=[0,1]*30;scores=[.2,.7]*30
        result=interval(labels,scores,scores,[str(i//2) for i in range(60)],resamples=100)
        self.assertEqual('inconclusive',result['direction'])
        self.assertIn('does not establish equivalence',result['meaning'])

    def test_evidence_alignment_and_labels_must_match_accepted_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'quality.json').write_text(json.dumps({'target':'label','splits':{'eval':'eval.csv'}}))
            (root/'meta.json').write_text(json.dumps({'id_columns':['id']}))
            with (root/'eval.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['id','label','group'])
                w.writerows([[str(i),i%2,str(i//2)] for i in range(60)])
            def scores(wrong=False):
                with (root/'scores.csv').open('w',newline='') as f:
                    w=csv.writer(f);w.writerow(['id','label','left','right'])
                    w.writerows([[str(i),1-i%2 if wrong else i%2,i%2,.5] for i in range(60)])
            scores()
            spec={'file':'scores.csv','sha256':sha256(root/'scores.csv'),'split':'eval',
                  'left':'left','right':'right','cluster_columns':['group'],'resamples':100}
            self.assertEqual('positive',from_evidence(root,root,spec)['direction'])
            scores(True);spec['sha256']=sha256(root/'scores.csv')
            with self.assertRaisesRegex(ValueError,'label differs'):
                from_evidence(root,root,spec)
            spec['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'digest mismatch'):
                from_evidence(root,root,spec)


if __name__=='__main__':
    unittest.main()
