"""Publication authority and crash recovery; fake providers never publish fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from factory import publication, approval_history
from factory import audit_workflow, release_audit
from factory.asset_integrity import sha256
from factory.common import write_json
from factory.leakage_battery import digest
from tests import test_audit_workflow as fixtures
ROOT = fixtures.ROOT


class FakeRemote:
    def __init__(self):
        self.private = {'github': True, 'huggingface': True}; self.calls = []
        self.fail_hub = False; self.fail_anonymous = False
    def inspect(self, *, anonymous):
        if anonymous and self.fail_anonymous: raise ValueError('anonymous unavailable')
        return {n: {'private': p, 'anonymous': anonymous, 'assets_verified': True}
                for n, p in self.private.items()}
    def make_public(self, name):
        self.calls.append(name)
        if name == 'huggingface' and self.fail_hub: raise ValueError('provider unavailable')
        self.private[name] = False


class PublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.WorkflowTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.root = fixture.root; self.package = fixture.package
        for name in ('factory/publication.py', 'factory/publication_remote.py',
                     'scripts/publish-dataset.py', 'scripts/hf-publish.py'):
            dest = self.root/name; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/name, dest)
        self.folder = self.root/'candidates/example'; self.folder.mkdir(parents=True)
        verdict = self.folder/'verdict.json'; verdict.write_text('{"unit_fixture":true}\n')
        write_json(self.folder/'record.json', {'id':'example', 'status':'packaged', 'awaiting_operator':True,
            'autonomous_audit':{'directory':'candidates/example', 'sha256':sha256(verdict)}})
        # The complete real audit receipt chain has its own integration tests. Here
        # isolate the new human authority boundary while keeping actual package gates.
        mock = patch.object(audit_workflow, 'queue_ready', return_value=True); mock.start(); self.addCleanup(mock.stop)
        binding = release_audit.staged_binding(self.root, 'example')
        report = self.folder/'independent-report.md'; report.write_text('UNIT FIXTURE ONLY: independent pass with no open conditions.\n')
        relay = self.folder/'review-relay.md'; relay.write_text('UNIT FIXTURE ONLY: operator relayed the independent report.\n')
        def ref(path): return {'path':path.relative_to(self.root).as_posix(), 'sha256':sha256(path), 'quote':path.read_text().strip()}
        write_json(self.folder/'independent-audit.json', {'schema_version':1, 'dataset':'example',
            'artifact_version':binding['artifact_version'], 'manifest_sha256':binding['manifest_sha256'],
            'binding_digest':digest(binding), 'verdict':'pass', 'unresolved_findings':[], 'conditions':[],
            'auditor':'unit fixture, not a real auditor', 'reviewed_at':'2026-11-06T00:00:00Z',
            'report':ref(report), 'operator_relay':ref(relay)})
        self.current = publication.plan(self.root, 'example')
        words = 'UNIT FIXTURE ONLY: approve this exact plan for both destinations.'
        source = self.folder/'approval-source.md'; source.write_text('Presented plan: '+digest(self.current)+'\n'+words+'\n')
        self.value = {'schema_version':1, 'kind':'publication_approval', 'dataset':'example',
            'release_tag':self.current['release_tag'], 'artifact_version':self.current['artifact_version'],
            'manifest_sha256':self.current['manifest_sha256'], 'plan_sha256':digest(self.current),
            'independent_review_sha256':self.current['independent_review']['sha256'],
            'decision':'approve_both_public', 'waived_rules':[], 'operator':'unit fixture',
            'approved_at':'2026-11-06T01:00:00Z', 'operator_words':words,
            'source':{'path':source.relative_to(self.root).as_posix(), 'sha256':sha256(source), 'quote':words}}
        self.remote = FakeRemote()
    def approve(self): write_json(self.folder/'approval.json', self.value)
    def test_missing_approval_refuses_before_any_network_or_mutation(self):
        with patch('factory.publication_remote.Remote') as client:
            with self.assertRaisesRegex(ValueError, 'approval is missing'): publication.execute(self.root, 'example')
            client.assert_not_called()
    def test_matching_approval_passes_but_draft_history_waiver_or_other_digest_refuses(self):
        self.approve(); self.assertEqual(publication.approved_plan(self.root,'example'), self.current)
        for key, wrong in [('kind','historical_publication_record'), ('decision','draft'),
                           ('waived_rules',['exact_label_recovery']), ('artifact_version','e'*64),
                           ('plan_sha256','f'*64), ('approved_at','2026-11-05T00:00:00Z')]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.value); changed[key] = wrong
                write_json(self.folder/'approval.json',changed)
                with self.assertRaises(ValueError): publication.execute(self.root, 'example', remote=self.remote)
        self.assertEqual(self.remote.calls, [])
    def test_changed_quoted_words_or_source_plan_refuses(self):
        self.approve(); source=self.folder/'approval-source.md'
        source.write_text('Generic ship it, without a presented plan.')
        self.value['source']['sha256']=sha256(source);self.approve()
        with self.assertRaises(ValueError): publication.approved_plan(self.root,'example')
    def test_stale_independent_review_and_bare_queue_cannot_be_approved(self):
        self.approve()
        with patch.object(audit_workflow,'queue_ready',return_value=False):
            with self.assertRaisesRegex(ValueError,'autonomous audit'): publication.approved_plan(self.root,'example')
        path=self.folder/'independent-audit.json';review=json.loads(path.read_text());review['conditions']=['fix later']
        write_json(path,review)
        with self.assertRaisesRegex(ValueError,'conditions'): publication.approved_plan(self.root,'example')
    def test_strict_recovery_gate_survives_a_human_approval_record(self):
        self.approve();path=self.root/'suitability/example.json';review=json.loads(path.read_text())
        review['cross_row_audit']['status']='recovery_demonstrated';write_json(path,review)
        with self.assertRaisesRegex(ValueError,'exact label recovery'): publication.execute(self.root,'example',remote=self.remote)
        self.assertEqual(self.remote.calls,[])
    def test_two_platform_flip_preserves_manifest_tags_and_repeats_without_mutations(self):
        self.approve();before=(self.package/'MANIFEST.json').read_bytes()
        self.assertTrue(publication.execute(self.root,'example',remote=self.remote)['ok'])
        self.assertEqual(self.remote.calls,['github','huggingface'])
        self.assertEqual(before,(self.package/'MANIFEST.json').read_bytes())
        dest=json.loads((self.package/'DESTINATIONS.json').read_text())
        self.assertFalse(dest['destinations']['github']['private']);self.assertFalse(dest['destinations']['huggingface']['private'])
        self.assertEqual(dest['destinations']['github']['target_commit'],'a'*40)
        self.assertEqual(dest['destinations']['huggingface']['commit'],'b'*40)
        self.assertTrue(publication.execute(self.root,'example',remote=self.remote)['already_completed'])
        self.assertEqual(self.remote.calls,['github','huggingface'])
    def test_second_provider_failure_preserves_partial_intent_and_only_resumes_missing_flip(self):
        self.approve();self.remote.fail_hub=True
        with self.assertRaisesRegex(ValueError,'provider unavailable'): publication.execute(self.root,'example',remote=self.remote)
        self.assertFalse(self.remote.private['github']);self.assertTrue(self.remote.private['huggingface'])
        self.assertTrue(json.loads((self.package/'DESTINATIONS.json').read_text())['destinations']['github']['private'])
        self.remote.fail_hub=False
        self.assertTrue(publication.execute(self.root,'example',remote=self.remote)['ok'])
        self.assertEqual(self.remote.calls,['github','huggingface','huggingface'])
    def test_anonymous_failure_does_not_record_publication_complete(self):
        self.approve();self.remote.fail_anonymous=True
        with self.assertRaisesRegex(ValueError,'anonymous unavailable'): publication.execute(self.root,'example',remote=self.remote)
        attempt=json.loads((self.folder/'publication-attempt.json').read_text())
        self.assertFalse(attempt['completed'])
        self.remote.fail_anonymous=False
        self.assertTrue(publication.execute(self.root,'example',remote=self.remote)['ok'])
        self.assertEqual(self.remote.calls,['github','huggingface'])
    def test_crash_after_destination_write_finishes_only_local_receipt(self):
        self.approve();real=publication.write_json
        def crash(path,value):
            if Path(path).name=='publication-attempt.json' and value.get('completed') is True: raise OSError('unit crash')
            return real(path,value)
        with patch.object(publication,'write_json',side_effect=crash):
            with self.assertRaisesRegex(OSError,'unit crash'): publication.execute(self.root,'example',remote=self.remote)
        self.assertTrue(publication.execute(self.root,'example',remote=self.remote)['already_completed'])
        self.assertEqual(self.remote.calls,['github','huggingface'])
    def test_external_public_repository_without_intent_is_refused(self):
        self.approve();self.remote.private['github']=False
        with self.assertRaisesRegex(ValueError,'already public'): publication.execute(self.root,'example',remote=self.remote)
        self.assertEqual(self.remote.calls,[])
    def test_changed_approval_cannot_resume_partial_flip(self):
        self.approve();self.remote.fail_hub=True
        with self.assertRaises(ValueError): publication.execute(self.root,'example',remote=self.remote)
        self.value['operator']='different recorder';self.approve();self.remote.fail_hub=False
        with self.assertRaisesRegex(ValueError,'identity changed'): publication.execute(self.root,'example',remote=self.remote)
        self.assertTrue(self.remote.private['huggingface'])
    def test_both_supported_entrypoints_use_shared_guard_before_credentials(self):
        for script,argv,root_name in [('publish-dataset.py',['example','--flip'],'ROOT'),
                                      ('hf-publish.py',['--candidate','example','--flip'],'REPO_ROOT')]:
            spec=importlib.util.spec_from_file_location('test_publication_cli',ROOT/'scripts'/script)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);setattr(module,root_name,self.root)
            with patch('sys.argv',[script]+argv),patch('factory.publication_remote.Remote') as remote:
                with self.assertRaisesRegex(ValueError, 'approval is missing'): module.main()
                remote.assert_not_called()


class HistoricalApprovalsTests(unittest.TestCase):
    def test_all_frozen_releases_have_bound_history_without_new_authority(self):
        self.assertEqual(approval_history.check(ROOT),{'ok':True,'historical_releases':14,'authorizes_new_publication':False})


class ProviderBoundaryTests(unittest.TestCase):
    def test_anonymous_http_has_no_authorization_and_a_bounded_read(self):
        from factory import publication_remote as remote
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=b'x';response.status=206;response.headers={'Content-Range':'bytes 0-0/100'}
        opener=MagicMock();opener.open.return_value=response
        with patch.object(remote,'build_opener',return_value=opener):
            self.assertEqual(remote.read_url('https://example.invalid/data',1,ranged=True),b'x')
        request=opener.open.call_args.args[0]
        self.assertNotIn('Authorization',request.headers)
        self.assertEqual(request.headers['Range'],'bytes=0-0');response.read.assert_called_once_with(2)
    def test_ignored_range_or_oversized_response_is_not_anonymous_proof(self):
        from factory import publication_remote as remote
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value=response
        response.status=200;response.read.return_value=b'xx';response.headers={}
        opener=MagicMock();opener.open.return_value=response
        with patch.object(remote,'build_opener',return_value=opener):
            with self.assertRaisesRegex(ValueError,'range read'):remote.read_url('https://example.invalid/data',1,ranged=True)
            with self.assertRaisesRegex(ValueError,'byte bound'):remote.read_url('https://example.invalid/data',1)
    def test_github_manifest_asset_and_document_drift_refuse_before_flip(self):
        from factory import publication_remote as remote
        from hashlib import sha256 as hash_bytes
        target={'repository':'owner/example','commit':'a'*40,'tag':'v1'}
        raw='{"unit":true}\n';doc='unit document\n'
        class API:
            wrong=None
            def file(self,repo,path,ref=None):
                if path=='MANIFEST.json':return raw+'x' if self.wrong=='manifest' else raw
                return doc+'x' if self.wrong=='document' else doc
            def request(self,method,path):
                if path=='repos/owner/example':return {'private':True,'default_branch':'main'}
                if '/commits/' in path:return {'sha':'b'*40 if self.wrong=='commit' else 'a'*40}
                if '/releases/tags/' in path:return {'id':1,'draft':False}
                if '/assets?' in path:return [{'name':'eval.csv','size':10,'digest':'sha256:'+('f'*64 if self.wrong=='asset' else 'e'*64)}]
                raise AssertionError(path)
        instance=object.__new__(remote.Remote);instance.api=API()
        instance.plan={'targets':{'github':target},'manifest_sha256':hash_bytes(raw.encode()).hexdigest()}
        instance.manifest={'assets':{'eval.csv':{'asset_name':'eval.csv','bytes':10,'sha256':'e'*64}},
                           'package_files':{'README.md':hash_bytes(doc.encode()).hexdigest()}}
        instance.destinations={'github':{'release_id':1}}
        self.assertTrue(instance.github(False)['assets_verified'])
        for wrong in ('manifest','document','asset','commit'):
            instance.api.wrong=wrong
            with self.subTest(wrong=wrong),self.assertRaises(ValueError):instance.github(False)
