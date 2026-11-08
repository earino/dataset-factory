"""Exercise real uploader, ledger collection and cleanup together; transport is fake."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from factory import reconciliation, worker, worker_artifacts, audit_workflow
from factory.common import write_json, FactoryError
from tests.test_workers import FakeCloud
from workers.upload import publish


class Staging:
    repo = 'owner/private'
    def __init__(self):
        self.release = None; self.files = {}; self.entries = {}

    def request(self, method, path, body=None, **kw):
        path = path.lstrip('/')
        if path == 'repos/owner/private': return {'private': True}
        if method == 'POST':
            self.release = {'id': 7, 'tag_name': body['tag_name'], 'html_url': 'https://example.invalid/7'}
            return self.release
        if '/assets?' in path: return list(self.entries.values())
        if '/releases?' in path: return [self.release] if self.release else []
        if path.endswith('/releases/7'): return self.release
        raise AssertionError(path)

    def ensure_asset(self, release_id, path, name, offset, size, sha256):
        raw = path.read_bytes()[offset:offset+size]
        if hashlib.sha256(raw).hexdigest() != sha256: raise AssertionError('bad producer digest')
        self.files[name] = raw
        self.entries[name] = {'id': list(self.files).index(name)+1, 'name': name, 'size': size,
                              'digest': 'sha256:'+sha256, 'browser_download_url': 'https://example.invalid/'+name}
        return self.entries[name]


class Cloud(FakeCloud):
    def request(self, method, path, body=None):
        if path.startswith('primary_ips?'): return {'primary_ips': [], 'meta': {'pagination': {'next_page': None}}}
        return super().request(method, path, body)


class WorkerPipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); base = self.root/'worker'; base.mkdir()
        (base/'output').mkdir(); self.job = {'id': 'example', 'max_artifact_mb': 10}
        for name in ('autonomous-audit.json','battery.json','model-attacks.json','model-freeze.json'):
            write_json(base/'output'/name, {'unit_fixture': True})
        (base/'source.tar').write_bytes(b'unit construction source')
        (base/'container.log').write_text('finished')
        write_json(base/'credentials.json', {'token':'fixture','repo':'owner/private'})
        self.api = Staging(); self.report = {'job_id':'example','status':'succeeded','exit_code':0}
        self.report.update(publish(base, self.job, self.report, self.api))
        self.cloud = Cloud()
        self.cloud.servers = [{'id':123,'labels':{'factory':'project','job':'example'},
                              'public_net':{'ipv4':{'ip':'192.0.2.1'}}}]
        self.record = {'job':self.job,'project':'project','status':'running','server_id':123,
                       'ipv4':'192.0.2.1','expires':time.time()+600,'cleanup_grace_minutes':60,
                       'staging_repo':'owner/private','source_sha256':'f'*64}
        write_json(self.root/'jobs/example.json',self.record)
        self.config = {'project':'project','max_report_bytes':262144,'max_coordinator_reports_bytes':20971520}
        self.runtime = self.root/'.factory/example'; self.runtime.mkdir(parents=True)
        # Cached downloaded bytes originate from the actual uploader's manifest.
        (self.runtime/'staging-manifest.json').write_bytes(self.api.files['manifest.json'])

    def advance(self):
        with patch.object(worker,'remote',return_value=json.dumps(self.report).encode()), \
                patch.object(worker,'github',return_value=self.api):
            return reconciliation.advance_worker(self.root,'example',self.config,cloud=self.cloud,api=self.api)

    def test_collect_delete_and_resume_without_git_or_model(self):
        self.assertFalse((self.root/'.git').exists())
        result = self.advance(); self.assertTrue(result['ok']); self.assertTrue(result['cleanup_verified'])
        self.assertEqual([123],self.cloud.deleted)
        self.assertEqual(result,self.advance()); self.assertEqual([123],self.cloud.deleted)
        self.assertEqual('deleted',worker.load_record(self.root,'example')['status'])

    def test_failed_job_is_preserved_and_cleaned(self):
        self.report.update(status='failed',exit_code=1)
        result=self.advance(); self.assertFalse(result['ok']); self.assertEqual([123],self.cloud.deleted)

    def test_bad_upload_never_deletes_unexpired_worker(self):
        self.api.entries['manifest.json']['digest']='sha256:'+'0'*64
        with self.assertRaisesRegex(FactoryError,'digest mismatch'): self.advance()
        self.assertEqual([],self.cloud.deleted)

    def test_expired_worker_recovers_complete_upload_after_lost_collection(self):
        self.cloud.servers=[]
        result=self.advance(); self.assertTrue(result['ok']); self.assertTrue(result['cleanup_verified'])
        self.assertEqual('succeeded',worker.load_record(self.root,'example')['result']['status'])

    def test_upload_failure_retries_twice_without_rebuilding_or_deleting(self):
        self.report['uploaded'] = False
        with patch.object(worker, 'retry_upload') as retry:
            for _ in range(3):
                self.assertEqual('waiting', self.advance()['status'])
            self.assertEqual(2, retry.call_count)
        self.assertEqual([], self.cloud.deleted)
        self.report['uploaded'] = True
        self.assertTrue(self.advance()['ok'])
        self.assertEqual([123], self.cloud.deleted)

    def test_actual_uploader_output_satisfies_audit_collection_contract(self):
        self.advance(); record=worker.load_record(self.root,'example')
        directory=self.root/'audit-evidence';directory.mkdir()
        (self.root/'cleanup.json').write_text('{}')
        def downloaded(repo,entry,path):
            raw=next(self.api.files[n] for n,a in self.api.entries.items() if a['id']==entry['id'])
            self.assertEqual(entry['size'],len(raw));self.assertEqual(entry['sha256'],hashlib.sha256(raw).hexdigest())
            path.write_bytes(raw);return json.loads(raw)
        with patch.object(audit_workflow,'committed_record',return_value=(record,'a'*64,'b'*40)), \
                patch.object(audit_workflow,'bookkeep',return_value={'handled':True,'live_verified':True,'receipt':'cleanup.json'}), \
                patch.object(audit_workflow,'download_report',side_effect=downloaded):
            evidence=audit_workflow.collect_evidence(self.root,'example',directory,self.config)
        self.assertEqual(4,len(evidence['files']))

    def test_legacy_nameless_ledger_still_resolves_through_provider_inventory(self):
        self.advance();record=worker.load_record(self.root,'example')
        for entry in record['result']['assets']:entry.pop('name')
        raw=worker_artifacts.manifest(self.root,record,self.api)
        self.assertEqual('example',raw['job']['id'])


if __name__ == '__main__': unittest.main()
