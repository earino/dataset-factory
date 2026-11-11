import json
from pathlib import Path
import tempfile
import unittest

from factory.site_state import publication_matches, read_candidates, snapshot
from factory.state import Store


class ModernSiteStateTests(unittest.TestCase):
    def test_missing_database_is_unavailable_and_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            result = snapshot(folder)
            self.assertEqual(result['status'], 'unavailable')
            self.assertIsNone(result['counts'])
            self.assertFalse((Path(folder) / '.factory').exists())

    def test_read_only_projection_excludes_private_candidate_and_attempt_data(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            store.add('example', {'source': {'dataset_id': 'real-task'}, 'token': 'PRIVATE_MARKER'})
            with store.connect() as db:
                db.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)",
                           ('attempt1', 'example', 'discover', 1, 'running', 1, None,
                            json.dumps({'diagnostic': 'PRIVATE_MARKER'})))
            # Display reads leave private candidate/attempt payloads out of output.
            result = snapshot(folder)
            self.assertEqual(result['status'], 'ok')
            self.assertEqual(result['counts'], {'discover': 1})
            self.assertTrue(result['candidates'][0]['running'])
            self.assertNotIn('PRIVATE_MARKER', json.dumps(result))
            self.assertEqual(read_candidates(folder)[0]['data']['token'], 'PRIVATE_MARKER')

    def test_corrupt_database_is_not_reported_as_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.factory'
            path.mkdir()
            (path / 'pipeline.sqlite3').write_bytes(b'not sqlite')
            self.assertIsNone(snapshot(folder)['counts'])

    def test_publication_receipt_must_match_artifact_and_both_consumers(self):
        manifest = {'dataset': 'example', 'version': 'v1', 'artifact_version': 'digest',
                    'rows': {'train': 20}}
        receipt = {**manifest, 'ok': True,
                   'github': {'repo': 'owner/example'}, 'huggingface': {'repo': 'owner/example'}}
        receipt['consumers'] = {p: {'ok': True, 'authentication': 'none', 'version': 'v1',
                                   'repo': 'owner/example', 'rows_loaded': {'train': 20}}
                                for p in ('github', 'huggingface')}
        data = {'evidence': {'MANIFEST.json': manifest}, 'publication': receipt}
        self.assertTrue(publication_matches(data))
        receipt['consumers']['github']['rows_loaded'] = {'train': 19}
        self.assertFalse(publication_matches(data))


if __name__ == '__main__':
    unittest.main()
