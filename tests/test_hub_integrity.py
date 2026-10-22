import hashlib
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from contextlib import redirect_stdout

from factory.hub_integrity import HubIntegrityError, verify_revision, tag_verified_commit, SMALL_LIMIT

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40
OTHER = 'b' * 40
DATA = b'{"accepted":true}'
DIGEST = hashlib.sha256(DATA).hexdigest()


class FakeHub:
    def __init__(self, tags=None, lfs=True):
        self.main = SHA
        self.tags = dict(tags or {})
        self.created = []
        self.sibling = NS(rfilename='meta.json', size=len(DATA),
                          lfs={'sha256': DIGEST} if lfs else None)
        self.endpoint = 'https://huggingface.co'

    def whoami(self):
        return {'name': 'test'}

    def repo_info(self, repo_id, **kwargs):
        self.revision_read = kwargs['revision']
        return NS(sha=kwargs['revision'], private=True, siblings=[self.sibling])

    def list_repo_refs(self, repo_id, **kwargs):
        return NS(branches=[NS(name='main', target_commit=self.main)],
                  tags=[NS(name=k, target_commit=v) for k, v in self.tags.items()])

    def create_tag(self, repo_id, **kwargs):
        self.created.append(kwargs)
        if kwargs['tag'] in self.tags:
            raise RuntimeError('concurrent tag exists')
        self.tags[kwargs['tag']] = kwargs['revision']

    def delete_tag(self, *args, **kwargs):
        raise AssertionError('release tags must never be deleted')


class HubIntegrityTests(unittest.TestCase):
    def verify(self, api=None, reader=None, expected=None):
        return verify_revision(api or FakeHub(), 'owner/data',
                               expected or {'meta.json': (len(DATA), DIGEST)}, SHA,
                               reader or Mock(side_effect=AssertionError('unexpected download')))

    def test_lfs_digest_needs_no_download(self):
        result = self.verify()
        self.assertTrue(result['ok'])
        self.assertEqual(['meta.json'], result['digest_verified'])

    def test_plain_metadata_is_hashed_at_exact_commit(self):
        reader = Mock(return_value=DATA)
        self.assertTrue(self.verify(FakeHub(lfs=False), reader)['ok'])
        reader.assert_called_once_with('meta.json', SHA, len(DATA))

    def test_same_size_wrong_bytes_fail(self):
        result = self.verify(FakeHub(lfs=False), Mock(return_value=b'x' * len(DATA)))
        self.assertFalse(result['ok'])
        self.assertEqual([], result['digest_verified'])

    def test_unknown_size_fails_without_download(self):
        api = FakeHub(); api.sibling.size = None
        self.assertFalse(self.verify(api)['ok'])

    def test_lfs_digest_mismatch_fails(self):
        api = FakeHub(); api.sibling.lfs = {'sha256': 'f' * 64}
        self.assertFalse(self.verify(api)['ok'])

    def test_lfs_object_metadata_supported(self):
        api = FakeHub(); api.sibling.lfs = NS(sha256=DIGEST)
        self.assertTrue(self.verify(api)['ok'])

    def test_bulk_plain_blob_is_never_downloaded(self):
        api = FakeHub(lfs=False); api.sibling.rfilename = 'data.csv'
        result = self.verify(api, expected={'data.csv': (len(DATA), DIGEST)})
        self.assertFalse(result['ok'])
        self.assertEqual(['data.csv'], result['files']['digest_unverified'])

    def test_oversize_metadata_is_never_downloaded(self):
        api = FakeHub(lfs=False); api.sibling.size = SMALL_LIMIT + 1
        self.assertFalse(self.verify(api, expected={'meta.json': (SMALL_LIMIT + 1, DIGEST)})['ok'])

    def test_missing_asset_fails(self):
        api = FakeHub(); api.sibling.rfilename = 'another.json'
        self.assertFalse(self.verify(api)['ok'])

    def test_empty_expected_assets_refused(self):
        with self.assertRaises(HubIntegrityError):
            verify_revision(FakeHub(), 'owner/data', {}, SHA, Mock())

    def test_no_tag_on_failed_verification(self):
        api = FakeHub()
        with self.assertRaises(HubIntegrityError):
            tag_verified_commit(api, 'owner/data', 'v1', {'ok': False, 'commit': SHA})
        self.assertEqual([], api.created)

    def test_existing_tag_never_moves(self):
        api = FakeHub({'v1': OTHER})
        with self.assertRaises(HubIntegrityError):
            tag_verified_commit(api, 'owner/data', 'v1', self.verify(api))
        self.assertEqual({'v1': OTHER}, api.tags)
        self.assertEqual([], api.created)

    def test_existing_matching_tag_is_idempotent(self):
        api = FakeHub({'v1': SHA})
        self.assertFalse(tag_verified_commit(api, 'owner/data', 'v1', self.verify(api))['tag_created'])
        self.assertEqual([], api.created)

    def test_new_tag_pins_verified_commit(self):
        api = FakeHub()
        result = tag_verified_commit(api, 'owner/data', 'v1', self.verify(api))
        self.assertTrue(result['tag_matches_main'])
        self.assertEqual(SHA, api.created[0]['revision'])
        self.assertFalse(api.created[0]['exist_ok'])

    def test_main_race_before_tag_refuses(self):
        api = FakeHub(); verification = self.verify(api); api.main = OTHER
        with self.assertRaises(HubIntegrityError):
            tag_verified_commit(api, 'owner/data', 'v1', verification)
        self.assertEqual([], api.created)

    def test_main_race_after_tag_fails_without_deleting_tag(self):
        api = FakeHub(); create = api.create_tag
        def raced(*args, **kwargs):
            create(*args, **kwargs); api.main = OTHER
        api.create_tag = raced
        with self.assertRaises(HubIntegrityError):
            tag_verified_commit(api, 'owner/data', 'v1', self.verify(api))
        self.assertEqual({'v1': SHA}, api.tags)

    def test_cli_failed_verify_does_not_tag_or_record_completion(self):
        spec = importlib.util.spec_from_file_location('hf_integrity_cli', ROOT/'scripts/hf-publish.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        api = FakeHub(); api.sibling.lfs = {'sha256': 'f' * 64}
        fake_sdk = NS(HfApi=lambda **kwargs: api, create_repo=Mock(), upload_folder=Mock())
        manifest = NS(tag='v1', metadata={'assets': {'meta.json': {'bytes': len(DATA), 'sha256': DIGEST}}})
        with patch.dict('sys.modules', {'huggingface_hub': fake_sdk}), \
                patch.object(module, 'resolve_candidate', return_value='example'), \
                patch.object(module, 'descriptor', return_value={'repository': 'https://github.com/owner/data'}), \
                patch.object(module, 'manifest', return_value=manifest), \
                patch.object(module, 'asset_target', side_effect=lambda m, name: name), \
                patch.object(module, 'reexec_in_venv'), \
                patch.object(module, 'load_token', return_value='private-test-token'), \
                patch.object(module, 'small_reader', return_value=Mock()), \
                patch.object(module, 'record_attempt'), \
                patch.object(module, 'record_destination') as record, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(1, module.main(['--tag', '--verify', '--candidate', 'example']))
        self.assertEqual([], api.created)
        record.assert_not_called()
        self.assertNotIn('private-test-token', output.getvalue())

    def test_redirect_drops_auth_when_origin_changes(self):
        spec = importlib.util.spec_from_file_location('hf_redirect', ROOT/'scripts/hf-publish.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        request = module.Request('https://huggingface.co/file', headers={'Authorization': 'Bearer private-test-token'})
        redirected = module._SafeHubRedirect().redirect_request(
            request, None, 302, 'redirect', {}, 'https://cdn.example/file')
        self.assertIsNone(redirected.get_header('Authorization'))
        with self.assertRaises(HubIntegrityError):
            module._SafeHubRedirect().redirect_request(request, None, 302, 'redirect', {}, 'http://cdn.example/file')


class WorkerEvidenceTests(unittest.TestCase):
    def receipt(self):
        return {'schema_version': 1, 'ok': True, 'repo': 'owner/data', 'commit': SHA,
                'files': {'data.csv': {'bytes': len(DATA), 'sha256': DIGEST, 'blob_id': 'c' * 40}}}

    def test_plain_bulk_verified_by_worker_and_remote_blob_without_download(self):
        api = FakeHub(lfs=False); api.sibling.rfilename = 'data.csv'; api.sibling.blob_id = 'c' * 40
        result = verify_revision(api, 'owner/data', {'data.csv': (len(DATA), DIGEST)}, SHA,
                                 Mock(side_effect=AssertionError('no coordinator bulk')), self.receipt())
        self.assertTrue(result['ok'])

    def test_stale_worker_commit_refused(self):
        receipt = self.receipt(); receipt['commit'] = OTHER
        with self.assertRaises(HubIntegrityError):
            verify_revision(FakeHub(), 'owner/data', {'data.csv': (len(DATA), DIGEST)}, SHA,
                            Mock(), receipt)

    def test_changed_remote_blob_invalidates_receipt(self):
        api = FakeHub(lfs=False); api.sibling.rfilename = 'data.csv'; api.sibling.blob_id = 'd' * 40
        result = verify_revision(api, 'owner/data', {'data.csv': (len(DATA), DIGEST)}, SHA,
                                 Mock(side_effect=AssertionError('no coordinator bulk')), self.receipt())
        self.assertFalse(result['ok'])

    def ledger(self, root):
        import json
        record = {'status': 'deleted', 'collected_at': '2026-10-22T00:00:00Z',
                  'job': {'id': 'publish-1', 'hf_publish': {'repo': 'owner/data', 'assets': [
                      {'target': 'data.csv', 'size': len(DATA), 'sha256': DIGEST}]}},
                  'result': {'job_id': 'publish-1', 'status': 'succeeded', 'uploaded': True,
                             'hf_loading': {'ok': True}, 'hf_verification': self.receipt()}}
        (root/'jobs').mkdir()
        (root/'jobs/publish-1.json').write_text(json.dumps(record))
        return record

    def test_only_successful_collected_ledger_can_supply_evidence(self):
        import json
        import tempfile
        from factory.hub_integrity import load_worker_receipt
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); record = self.ledger(root)
            self.assertEqual(self.receipt(), load_worker_receipt(root, 'publish-1', 'owner/data',
                                                               {'data.csv': (len(DATA), DIGEST)}))
            for invalid in ('failed', 'running'):
                record['result']['status'] = invalid
                (root/'jobs/publish-1.json').write_text(json.dumps(record))
                with self.assertRaises(HubIntegrityError):
                    load_worker_receipt(root, 'publish-1', 'owner/data', {'data.csv': (len(DATA), DIGEST)})

    def test_loading_failure_or_changed_manifest_cannot_be_blessed(self):
        import json
        import tempfile
        from factory.hub_integrity import load_worker_receipt
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); record = self.ledger(root)
            with self.assertRaises(HubIntegrityError):
                load_worker_receipt(root, 'publish-1', 'owner/data', {'data.csv': (len(DATA), 'd'*64)})
            record['result']['hf_loading']['ok'] = False
            (root/'jobs/publish-1.json').write_text(json.dumps(record))
            with self.assertRaises(HubIntegrityError):
                load_worker_receipt(root, 'publish-1', 'owner/data', {'data.csv': (len(DATA), DIGEST)})

    def test_worker_helper_hashes_blob_and_pins_download(self):
        import os
        import json
        import tempfile
        import subprocess
        import sys
        from workers.hf_publish import RECEIPT_HELPER
        stub = '''\
import hashlib
from pathlib import Path
from types import SimpleNamespace as N
DATA = b'{"accepted":true}'
SHA = 'a' * 40
class HfApi:
    def __init__(self, **kw): pass
    def repo_info(self, *a, **kw):
        blob = hashlib.sha1(('blob ' + str(len(DATA)) + chr(0)).encode() + DATA).hexdigest()
        return N(sha=SHA, siblings=[N(rfilename='data.csv', size=len(DATA), lfs=None, blob_id=blob)])
def hf_hub_download(**kw):
    assert kw['revision'] == SHA
    path = Path(kw['cache_dir'])/'file'; path.write_bytes(DATA); return str(path)
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'huggingface_hub.py').write_text(stub)
            (root/'helper.py').write_text(RECEIPT_HELPER)
            (root/'expected.json').write_text(json.dumps([{'target': 'data.csv', 'size': len(DATA), 'sha256': DIGEST}]))
            result = subprocess.run([sys.executable, str(root/'helper.py'), 'owner/data', 'main',
                                     str(root/'expected.json'), str(64 * 1024 * 1024)], cwd=root, capture_output=True, text=True,
                                    env={**os.environ, 'HF_WRITE_TOKEN': 'private-test-token'})
            self.assertEqual(0, result.returncode, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertTrue(receipt['ok'])
            self.assertEqual(DIGEST, receipt['files']['data.csv']['sha256'])
            self.assertNotIn('private-test-token', result.stdout)

    def test_incomplete_cli_preserves_existing_receipt_and_records_separate_attempt(self):
        import json
        import tempfile
        spec = importlib.util.spec_from_file_location('hf_partial_cli', ROOT/'scripts/hf-publish.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        api = FakeHub(tags={'v1': SHA}, lfs=False); api.sibling.rfilename = 'data.csv'
        sdk = NS(HfApi=lambda **kwargs: api, create_repo=Mock(), upload_folder=Mock())
        manifest = NS(tag='v1', metadata={'assets': {'data.csv': {'bytes': len(DATA), 'sha256': DIGEST}}})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = root/'release/example'; package.mkdir(parents=True)
            prior = b'{"prior":"strong verified evidence"}\n'
            (package/'DESTINATIONS.json').write_bytes(prior)
            with patch.dict('sys.modules', {'huggingface_hub': sdk}), \
                    patch.object(module, 'REPO_ROOT', root), \
                    patch.object(module, 'resolve_candidate', return_value='example'), \
                    patch.object(module, 'descriptor', return_value={'repository': 'https://github.com/owner/data'}), \
                    patch.object(module, 'manifest', return_value=manifest), \
                    patch.object(module, 'asset_target', side_effect=lambda m, name: name), \
                    patch.object(module, 'reexec_in_venv'), \
                    patch.object(module, 'load_token', return_value='private-test-token'), \
                    patch.object(module, 'small_reader', return_value=Mock(side_effect=AssertionError('bulk download'))), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(2, module.main(['--verify', '--candidate', 'example']))
            self.assertEqual(prior, (package/'DESTINATIONS.json').read_bytes())
            attempt = json.loads((root/'.factory/hub-verification/example/latest.json').read_text())
            self.assertEqual('incomplete', attempt['status'])
            self.assertFalse(attempt['ok'])
            self.assertEqual([], api.created)

    def test_verify_only_worker_never_enters_upload_path(self):
        import json
        import tempfile
        from workers import hf_publish as worker_hf
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'credentials.json').write_text(json.dumps({'hf_write_token':'test', 'token':'test'}))
            job = {'timeout_minutes':10, 'hf_publish': {'repo':'owner/data', 'revision':'v1',
                   'source_repo':'owner/data', 'verify_only':True,
                   'assets':[{'target':'data.csv','size':len(DATA),'sha256':DIGEST}],
                   'verify_loading':{'splits':{}}}}
            calls = []
            def command(args, **kwargs):
                calls.append(args)
                if '.hf-receipt.py' in ' '.join(map(str,args)):
                    return NS(returncode=0,stdout=json.dumps(self.receipt()),stderr='')
                return NS(returncode=0,stdout='{"ok":true}',stderr='')
            source = Mock(); source.download.side_effect = AssertionError('verify-only fetched upload source')
            with patch.object(worker_hf, 'ensure_client', return_value=Path('python')), \
                    patch.object(worker_hf.subprocess, 'run', side_effect=command), \
                    patch.object(worker_hf, 'already_published', side_effect=AssertionError('upload loop')), \
                    patch.object(worker_hf.shutil, 'which', return_value=None):
                report = worker_hf.hf_publish(root, job, {}, client=source)
            self.assertEqual([], report['hf_publish']['uploads'])
            self.assertEqual([], report['hf_publish']['failures'])
            self.assertTrue(report['hf_verification']['ok'])
            loading = next(c for c in calls if '.hf-verify.py' in ' '.join(map(str,c)))
            self.assertEqual(SHA, loading[3])
            source.download.assert_not_called()
            self.assertFalse(any('.hf-upload-' in ' '.join(map(str,c)) for c in calls))

    def test_verify_only_mode_rejects_string_boolean_before_provisioning(self):
        from test_hf_publish_job import hf_job, POLICY
        from factory import worker
        from factory.common import FactoryError
        job = hf_job(); job['hf_publish']['verify_only'] = 'true'
        with patch.object(worker, 'credential_status', return_value={'ready':True}):
            with self.assertRaisesRegex(FactoryError, 'verify_only must be a boolean'):
                worker.validate(job, POLICY)

    def test_worker_plain_blob_cache_is_owned_and_removed(self):
        import tempfile
        from workers import hf_publish as worker_hf
        observed = []
        def command(args, **kwargs):
            cache = Path(args[-1]); self.assertTrue(cache.is_dir())
            observed.append(cache); (cache/'payload').write_bytes(b'small synthetic check')
            return NS(stdout=DIGEST+'\n', returncode=0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); old = root/'hf-cache'; old.mkdir(); (old/'keep').write_text('unrelated old work')
            with patch.object(worker_hf.subprocess, 'run', side_effect=command):
                self.assertEqual(DIGEST, worker_hf.hub_digest_by_download(root, 0, 'owner/data', SHA,
                                                                        'data.csv', Path('python'), 'test'))
            self.assertTrue(all(not p.exists() for p in observed))
            self.assertEqual('unrelated old work', (old/'keep').read_text())

    def test_receipt_helper_accepts_the_observed_nine_megabyte_plain_blob(self):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        from workers.hf_publish import RECEIPT_HELPER, SMALL_BLOB_BYTES
        size = 9421952
        wanted = hashlib.sha256(b'x' * size).hexdigest()
        stub = '''\
import hashlib
from pathlib import Path
from types import SimpleNamespace as N
DATA = b'x' * 9421952
SHA = 'a' * 40
class HfApi:
    def __init__(self, **kw): pass
    def repo_info(self, *a, **kw):
        blob = hashlib.sha1(('blob ' + str(len(DATA)) + chr(0)).encode() + DATA).hexdigest()
        return N(sha=SHA, siblings=[N(rfilename='data.csv', size=len(DATA), lfs=None, blob_id=blob)])
def hf_hub_download(**kw):
    assert kw['revision'] == SHA
    path = Path(kw['cache_dir'])/'file'; path.write_bytes(DATA); return str(path)
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'huggingface_hub.py').write_text(stub)
            (root/'helper.py').write_text(RECEIPT_HELPER)
            (root/'expected.json').write_text(json.dumps([{'target':'data.csv','size':size,'sha256':wanted}]))
            result = subprocess.run([sys.executable, str(root/'helper.py'), 'owner/data', 'main',
                                     str(root/'expected.json'), str(SMALL_BLOB_BYTES)], cwd=root,
                                    capture_output=True, text=True,
                                    env={**os.environ,'HF_WRITE_TOKEN':'private-test-token'})
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(wanted, json.loads(result.stdout)['files']['data.csv']['sha256'])


class ManifestPathAuthorityTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('hf_manifest_paths', ROOT/'scripts/hf-publish.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_candidate_edit_cannot_redirect_a_frozen_release(self):
        from factory.release_schema import load_release
        module = self.module()
        release = load_release(ROOT/'release/tsb-railway-occurrence-casualty')
        changed_descriptor = {'repository':'https://github.com/owner/data',
                              'hf_paths':{'public/train.csv':'public/train.csv'}}
        targets = {}
        def inspect_plan(record, repo):
            targets['train'] = module.asset_target(record, 'public/train.csv')
            return {}
        with patch.object(module, 'resolve_candidate', return_value=release.dataset), \
                patch.object(module, 'descriptor', return_value=changed_descriptor), \
                patch.object(module, 'manifest', return_value=release), \
                patch.object(module, 'plan', side_effect=inspect_plan), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(0, module.main(['--plan']))
        self.assertEqual('data/public-train.csv', targets['train'])

    def test_explicit_manifest_paths_preserve_structured_release_layout(self):
        from factory.release_schema import load_release
        module = self.module()
        release = load_release(ROOT/'release/noaa-tide-flooding')
        for logical, target in release.metadata['hub_paths'].items():
            self.assertEqual(target, module.asset_target(release, logical))
