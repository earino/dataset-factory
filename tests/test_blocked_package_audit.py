"""Transport and orchestration tests; these are not historical acceptance results."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), result.__dict__)
    return result


audit = load('audit-blocked-package')
prepare = load('prepare-blocked-audit')


class BlockedPackageTests(unittest.TestCase):
    def make(self, root):
        shutil.copytree(ROOT / 'skills/dataset-qualification/fixtures/corrected', root)
        quality = json.loads((root / 'quality.json').read_text())
        assets = {name: {'sha256': audit.transport.digest(root / name), 'bytes': (root / name).stat().st_size,
                         'asset_name': name.replace('/', '-')}
                  for name in ('meta.json', 'quality.json', *quality['splits'].values())}
        components = {split: assets[name]['sha256'] for split, name in quality['splits'].items()}
        components.update({name: assets[name]['sha256'] for name in ('meta.json', 'quality.json')})
        version = hashlib.sha256(''.join(sorted(k + ':' + v for k, v in components.items())).encode()).hexdigest()
        (root / 'README.md').write_text('Original test document.\n')
        (root / 'code').mkdir()
        (root / 'code/build.py').write_text('raise RuntimeError("Historical source must never execute")\n')
        files = {p.relative_to(root).as_posix(): audit.transport.digest(p)
                 for p in root.rglob('*') if p.is_file() and p.suffix != '.csv'}
        manifest = {'dataset': 'example', 'artifact_version': version, 'published': False,
                    'release_tag': 'v1', 'assets': assets, 'files': assets, 'package_files': files}
        (root / 'MANIFEST.json').write_text(json.dumps(manifest))
        return {'dataset': 'example', 'artifact_version': version,
                'manifest_sha256': audit.transport.digest(root / 'MANIFEST.json')}

    def test_exact_package_binding_refuses_changes_additions_and_publication(self):
        for flaw in ('change', 'add', 'published'):
            with self.subTest(flaw=flaw), tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'package'; case = self.make(root)
                audit.package_binding(case, root)
                if flaw == 'change': (root / 'README.md').write_text('Changed')
                if flaw == 'add': (root / 'extra.txt').write_text('Unexpected')
                if flaw == 'published':
                    path = root / 'MANIFEST.json'; value = json.loads(path.read_text()); value['published'] = True
                    path.write_text(json.dumps(value)); case['manifest_sha256'] = audit.transport.digest(path)
                with self.assertRaises(ValueError): audit.package_binding(case, root)

    def test_all_gates_run_after_expected_refusal_without_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder); root = parent / 'package'; case = self.make(root)
            _, before = audit.package_binding(case, root)
            output = parent / 'out'; output.mkdir(); scratch = parent / 'scratch'; scratch.mkdir()
            stages = audit.run_stages(root, output, scratch)
            self.assertEqual(9, len(stages))
            self.assertTrue(all(v['completed'] for v in stages.values()), stages)
            self.assertFalse(stages['license_admission']['ok'])
            self.assertFalse(stages['qualification_admission']['ok'])
            self.assertTrue(stages['claims']['completed'])
            self.assertFalse(stages['suitability_admission']['ok'])
            self.assertEqual(before, audit.package_binding(case, root)[1])
            self.assertFalse(any(p.stat().st_size >= 256 * 1024 for p in output.iterdir()))

    def test_failed_measurement_is_incomplete_not_a_successful_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder); root = parent / 'package'; self.make(root)
            output = parent / 'out'; output.mkdir(); scratch = parent / 'scratch'; scratch.mkdir()
            with patch('factory.claim_facts.measure', side_effect=RuntimeError('test interrupted measurement')):
                stages = audit.run_stages(root, output, scratch)
            self.assertFalse(stages['claims']['completed'])
            self.assertTrue(stages['license_admission']['completed'])

    def test_document_archive_is_deterministic_and_refuses_bulk_changed_or_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder); root = parent / 'example/repository'; root.parent.mkdir()
            case = self.make(root); plan = {'datasets': [case]}
            a = prepare.prepare(parent, plan, parent / 'one')
            b = prepare.prepare(parent, plan, parent / 'two')
            self.assertEqual(a, b)
            self.assertNotIn('.csv', str(a))
            with self.assertRaises(FileExistsError): prepare.prepare(parent, plan, parent / 'one')
            (root / 'README.md').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'changed'): prepare.prepare(parent, plan, parent / 'three')
            (root / 'README.md').write_text('Original test document.\n')
            path = root / 'MANIFEST.json'; manifest = json.loads(path.read_text())
            manifest['package_files']['public/train.csv'] = manifest['assets']['public/train.csv']['sha256']
            path.write_text(json.dumps(manifest)); case['manifest_sha256'] = audit.transport.digest(path)
            with self.assertRaisesRegex(ValueError, 'only compact'): prepare.prepare(parent, plan, parent / 'four')

    def test_all_four_real_plans_pin_every_original_document_and_asset(self):
        inventory = json.loads((ROOT / 'audits/resilience/2026-11-07-a4-document-inventory.json').read_text())
        parent = ROOT / 'candidates/cpcb-aqi-exceedance/resilience-a4'
        cases = json.loads((parent / 'cases.json').read_text())['cases']
        fetch = {e['dest']: e for e in json.loads((parent / 'job.json').read_text())['fetch']['assets']}
        self.assertEqual({e['dataset'] for e in inventory['datasets']}, {c['dataset'] for c in cases})
        self.assertEqual(4, len(cases))
        for case in cases:
            docs = next(e for e in inventory['datasets'] if e['dataset'] == case['dataset'])
            self.assertEqual(docs['manifest_sha256'], case['manifest_sha256'])
            self.assertEqual(docs['members'], case['archives'][0]['members'])
            components = {e['path']: e['sha256'] for e in case['files']}
            components.update({e['path']: e['sha256'] for e in docs['members']
                               if e['path'] in ('meta.json', 'quality.json')})
            self.assertEqual(5, len(components))
            components = { {'public/train.csv': 'train', 'public/eval.csv': 'eval',
                            'private/holdout.csv': 'holdout'}.get(k, k): v for k, v in components.items()}
            version = hashlib.sha256(''.join(sorted(k + ':' + v for k, v in components.items())).encode()).hexdigest()
            self.assertEqual(case['artifact_version'], version)
            for entry in case['files'] + case['archives']:
                source = fetch[entry['fetch_dest']]
                self.assertEqual((entry['sha256'], entry['size']), (source['sha256'], source['size']))
            review = case['review_archive']
            source = fetch[review['fetch_dest']]
            self.assertEqual((review['sha256'], review['size']), (source['sha256'], source['size']))
            self.assertIn('suitability/'+case['dataset']+'.json', {e['path'] for e in review['members']})
            evidence = json.loads((ROOT/'audits/resilience/2026-11-07-a4-review-evidence.json').read_text())
            self.assertEqual(review['members'], evidence['members'])
            self.assertTrue(all(e['size'] < 256 * 1024 for e in review['members']))


if __name__ == '__main__': unittest.main()
