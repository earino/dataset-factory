import copy
import json
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from factory.common import FactoryError
from factory.site_modern import project
from factory.site_model import check_manifest
from factory.site_pipeline import prepare_record, load_bundle
from factory.site_github import GitHub

ROOT = Path(__file__).resolve().parents[1]


class ModernSiteTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / 'tests/fixtures/modern-site'
        self.manifest = json.loads((folder / 'MANIFEST.json').read_bytes())
        self.documents = {name: (folder / name).read_bytes()
                          for name in ('README.md', 'evaluation.json', 'LICENSE.md')}
        self.receipt = json.loads((ROOT / 'audits/rewrite/ucmr-publication-success/publication.json').read_bytes())
        self.config = json.loads((ROOT / 'config/sites.json').read_bytes())

    def record(self):
        return project(self.manifest, self.receipt, self.documents, '2026-11-08', self.config)

    def test_real_release_renders_with_exact_measured_scope_and_actual_documents(self):
        record = self.record()
        self.assertEqual(record['title'], 'UCMR 5 First Sample PFAS')
        self.assertEqual(record['summary'], self.manifest['task']['question'])
        check_manifest(record, self.manifest)
        self.assertEqual(record['baseline']['metrics']['Validation full_model auc'], 0.7856421356421357)
        self.assertEqual(record['assets']['extract__public__train.csv']['hf_path'], 'extract/public/train.csv')
        runtime = runpy.run_path(str(ROOT / 'sites/runtime.py'))
        output = runtime['render']({'schema_version': 1, 'kind': 'dataset', 'title': 'Dataset Factory',
                                    'description': '', 'catalog_url': record['urls']['catalog']}, [record])
        html = output['index.html']
        self.assertIn('/blob/v-4a630108a6e75a6b/evaluation.json', html)
        self.assertNotIn('/DATA_DICTIONARY.md', html)
        self.assertIn('retrospective research', html)
        self.assertIn('public validation only; no holdout scoring', html)
        self.assertIn('Validation ROC AUC', html)
        self.assertNotIn('Validation calendar_identity brier', html)
        self.assertIn('Validation calendar_identity brier', record['baseline']['metrics'])

    def test_changed_metadata_is_rejected_before_quoting_baseline(self):
        self.documents['evaluation.json'] += b' '
        with self.assertRaisesRegex(FactoryError, 'Pinned metadata'):
            self.record()

    def test_wrong_consumer_artifact_is_not_a_website_release(self):
        self.receipt['artifact_version'] = '0' * 64
        with self.assertRaisesRegex(FactoryError, 'Publication receipt'):
            self.record()

    def test_remote_manifest_comparison_checks_paths_and_rights(self):
        record = self.record()
        other = copy.deepcopy(self.manifest)
        other['source']['citation'] = 'different'
        with self.assertRaisesRegex(FactoryError, 'source terms'):
            check_manifest(record, other)

    def test_modern_bundle_uses_standing_policy_and_stable_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            first = prepare_record(self.record(), self.config, Path(folder).resolve() / 'bundle')
            second = prepare_record(self.record(), self.config, Path(folder).resolve() / 'bundle')
            self.assertEqual(first['plan_sha256'], second['plan_sha256'])
            bundle = load_bundle(Path(folder).resolve() / 'bundle')
            self.assertEqual(bundle['standing_policy'], 'FACTORY-SITES-INTEGRATION-2026-11-11')
            self.assertNotIn('Operator approval required', bundle['publication'])

    def test_github_editorial_navigation_never_rewrites_modern_manifest(self):
        record = self.record()
        gh = GitHub()
        files = {'README.md': self.documents['README.md'].decode(),
                 'MANIFEST.json': json.dumps(self.manifest)}
        with patch.object(gh, 'file', side_effect=lambda repo, path: files[path]):
            updates, originals = gh.dataset_navigation(record)
            self.assertEqual(set(updates), {'README.md'})
            self.assertEqual(originals['MANIFEST.json'], files['MANIFEST.json'])

    def test_hub_modern_verification_uses_pinned_commit_without_bulk_reads(self):
        fn = runpy.run_path(str(ROOT / 'scripts/site-hf.py'))['modern']
        record = self.record()
        entries = [NS(rfilename=path, size=meta['bytes'], blob_id='blob:' + path)
                   for path, meta in self.manifest['assets'].items()]
        entries.append(NS(rfilename='MANIFEST.json', size=100, blob_id='manifest'))
        pinned = NS(sha=record['publication_commits']['huggingface'], siblings=entries, private=False)
        main = NS(sha='later-editorial-commit', siblings=entries)
        api = NS(dataset_info=lambda *a, **kw: main)
        reads = []
        def small(path, *args):
            reads.append(path)
            return json.dumps(self.manifest).encode() if path == 'MANIFEST.json' else self.documents[path]
        result = fn({'record': record, 'action': 'read'}, api, pinned, small, None)
        self.assertEqual(result['bulk_downloads'], 0)
        self.assertEqual(reads, ['MANIFEST.json', 'README.md'])
        pinned.sha = 'different'
        with self.assertRaisesRegex(FactoryError, 'publication commit'):
            fn({'record': record, 'action': 'read'}, api, pinned, small, None)


if __name__ == '__main__':
    unittest.main()
