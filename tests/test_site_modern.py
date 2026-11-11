import copy
import json
from pathlib import Path
import runpy
import unittest

from factory.common import FactoryError
from factory.site_modern import project
from factory.site_model import check_manifest

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


if __name__ == '__main__':
    unittest.main()
