import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from factory.site_sync import release_record, run
from factory.site_model import digest, dump

ROOT = Path(__file__).resolve().parents[1]


class SiteSyncTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / 'tests/fixtures/modern-site'
        self.files = {p.name: p.read_text() for p in folder.iterdir()}
        self.manifest = json.loads(self.files['MANIFEST.json'])
        receipt = json.loads((ROOT / 'audits/rewrite/ucmr-publication-success/publication.json').read_text())
        self.candidate = {'id': 'source-example', 'stage': 'published', 'updated': 1794201000,
                          'attempts': [], 'data': {'evidence': {'MANIFEST.json': self.manifest},
                                                 'publication': receipt}}
        self.gh = Mock()
        self.gh.file.side_effect = lambda repo, path, **kw: self.files.get(path)
        self.config = json.loads((ROOT / 'config/sites.json').read_text())

    def test_projected_record_reads_only_compact_metadata_and_is_repeatable(self):
        first = release_record(self.candidate, self.config, self.gh)
        self.assertEqual(first, release_record(self.candidate, self.config, self.gh))
        self.assertTrue(all(not call.args[1].endswith('.csv') for call in self.gh.file.call_args_list))
        self.assertEqual(first['summary'], self.manifest['task']['question'])

    def test_catalogue_edition_is_reused_until_content_changes(self):
        first = release_record(self.candidate, self.config, self.gh)
        first['site_revision'] = 3
        first.pop('record_sha256')
        first['record_sha256'] = digest(dump(first))
        self.files[f".dataset-site/records/{first['dataset']}/{first['release_tag']}.json"] = dump(first)
        self.assertEqual(release_record(self.candidate, self.config, self.gh), first)

    def test_failure_isolated_and_completed_bundle_is_verified_without_republishing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / 'config').mkdir()
            (root / 'config/sites.json').write_text(dump(self.config))
            bad = copy.deepcopy(self.candidate)
            bad['id'] = 'bad'
            bad['data']['publication']['ok'] = False
            rows = [bad, self.candidate]
            before = copy.deepcopy(rows)
            def completed(plan, bundle, *args):
                receipt = {'status': 'complete', 'plan_sha256': plan['plan_sha256']}
                (bundle / 'receipt.json').write_text(dump(receipt))
                return receipt
            with patch('factory.site_sync.read_candidates', return_value=rows), \
                    patch('factory.site_sync.reconcile', side_effect=completed) as publish, \
                    patch('factory.site_sync.verify') as verify:
                one = run(root, gh=self.gh, hub=Mock())
                self.assertEqual([r['status'] for r in one['releases']], ['failed', 'complete'])
                two = run(root, gh=self.gh, hub=Mock())
                self.assertEqual(publish.call_count, 1)
                self.assertEqual(verify.call_count, 1)
                self.assertEqual(one['releases'][1]['bundle'], two['releases'][1]['bundle'])
                self.assertEqual(rows, before, 'Website synchronization must not advance candidate state')


if __name__ == '__main__':
    unittest.main()
