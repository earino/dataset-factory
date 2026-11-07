import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from factory.claim_contract import compute, render, validate

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('claims_gate',ROOT/'skills/dataset-qualification/scripts/qualify_dataset.py')
gate=importlib.util.module_from_spec(spec)
exec(compile(spec.loader.get_source(spec.name),str(spec.origin),'exec'),gate.__dict__)


class ClaimContractTests(unittest.TestCase):
    def make(self,root):
        shutil.copytree(ROOT/'skills/dataset-qualification/fixtures/corrected',root,dirs_exist_ok=True)
        report=gate.qualify(root,record_battery=True).as_dict()
        self.assertTrue(report['ok'],report['failed_checks'])
        (root/'qualification.json').write_text(json.dumps(report))
        claim={'id':'eval-population','kind':'population','split':'eval'}
        (root/'CLAIMS.json').write_text(json.dumps({'version':1,'claims':[claim]}))
        facts=compute(root,qualification=root/'qualification.json')
        (root/'README.md').write_text('Dataset description.\n\n<!-- FACTORY-CLAIM eval-population -->\n'+
                                     render(claim,facts)+'\n<!-- /FACTORY-CLAIM -->\n')
        assets={v['file']:{'sha256':v['sha256']} for k,v in report['artifact'].items()
                if k in ('train','eval','holdout','meta.json','quality.json')}
        (root/'MANIFEST.json').write_text(json.dumps({'artifact_version':report['artifact']['artifact_version']['digest'],
                                                    'assets':assets}))
        return facts

    def test_generated_population_is_bound_to_qualified_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);facts=self.make(root)
            self.assertTrue(validate(root,facts)['ok'])
            (root/'public/eval.csv').write_text((root/'public/eval.csv').read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'input changed'):
                validate(root,facts)

    def test_numeric_prose_cannot_bypass_claim_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);facts=self.make(root)
            p=root/'README.md';p.write_text(p.read_text()+'\nThe positive rate is 98.1%.\n')
            result=validate(root,facts)
            self.assertFalse(result['ok'])
            self.assertIn('unbound_numeric_prose',{f['rule'] for f in result['findings']})

    def test_changed_rendered_claim_and_declaration_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);facts=self.make(root)
            p=root/'README.md';p.write_text(p.read_text().replace(' rows;',' false rows;'))
            self.assertIn('claim_block_mismatch',{f['rule'] for f in validate(root,facts)['findings']})
            p=root/'CLAIMS.json';p.write_text(p.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'stale'):
                validate(root,facts)

    def test_historical_or_changed_report_does_not_clear_a_new_package(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);facts=self.make(root)
            facts['historical_only']=True
            with self.assertRaisesRegex(ValueError,'historical'):
                validate(root,facts)
            facts['historical_only']=False
            p=root/'qualification.json';p.write_text(p.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'qualification'):
                validate(root,facts)

    def test_failed_gate_cannot_generate_new_claims_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.make(root)
            p=root/'qualification.json';report=json.loads(p.read_text());report['results'][0]['ok']=False
            p.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'passing gate'):
                compute(root,qualification=p)


if __name__=='__main__':
    unittest.main()
