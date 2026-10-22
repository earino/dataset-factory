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
