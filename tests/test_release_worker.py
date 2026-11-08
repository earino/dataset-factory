"""Real transfer/consumer functions with provider boundaries replaced in memory."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import types
import unittest
import urllib.error
from unittest.mock import patch

from workers import get_dataset, release_publish, upload


class GitHub(upload.GitHub):
    repos = {}

    def request(self, method, path, body=None, upload=None):
        if path == '/user': return {'login': 'owner'}
        if path == '/user/repos':
            self.repos[self.repo] = {**body, 'default_branch': 'main', 'files': {}, 'head': '1'*40,
                                    'assets': {}, 'release': None}
            return self.repos[self.repo]
        repo = self.repos.get(self.repo)
        if path == '/repos/' + self.repo:
            if method == 'PATCH': repo.update(body)
            return repo
        tail = path.removeprefix('/repos/' + self.repo)
        if tail.startswith('/git/ref/heads/'): return {'object': {'sha': repo['head']}}
        if tail.startswith('/git/commits/') and method == 'GET': return {'tree': {'sha': '2'*40}}
        if tail.startswith('/git/trees/'):
            return {'tree': [{'path': p, 'sha': hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
                             for p,b in repo['files'].items()]}
        if tail == '/git/trees':
            for entry in body['tree']: repo['files'][entry['path']] = entry['content'].encode()
            return {'sha': '3'*40}
        if tail == '/git/commits': return {'sha': '4'*40}
        if tail.startswith('/git/refs/heads/'):
            repo['head'] = body['sha']; return {}
        if tail.startswith('/git/ref/tags/'):
            return {'object': {'type': 'commit', 'sha': repo['release']['target_commitish']}}
        if tail == '/releases' and method == 'POST':
            repo['release'] = {**body, 'id': 7}; return repo['release']
        if tail.startswith('/releases?'): return [repo['release']] if repo['release'] else []
        if tail == '/releases/7':
            if method == 'PATCH': repo['release'].update(body)
            return repo['release']
        if tail.startswith('/releases/7/assets'):
            if method == 'GET': return list(repo['assets'].values())
            from urllib.parse import parse_qs, urlsplit
            name = parse_qs(urlsplit(path).query)['name'][0]
            file, offset, size = upload; data = file.read_bytes()[offset:offset+size]
            entry = {'id': len(repo['assets'])+1, 'name': name, 'size': size, 'state': 'uploaded',
                     'digest': 'sha256:'+hashlib.sha256(data).hexdigest(), 'bytes': data}
            repo['assets'][name] = entry
            return {k:v for k,v in entry.items() if k != 'bytes'}
        raise AssertionError((method, path))

    def download(self, asset_id, dest, sha256, size=None):
        entry = next(a for a in self.repos[self.repo]['assets'].values() if a['id'] == asset_id)
        data = entry['bytes']
        if hashlib.sha256(data).hexdigest() != sha256 or (size is not None and len(data) != size):
            raise upload.UploadError('bad digest')
        dest.write_bytes(data); return len(data)


class ReleaseWorkerTests(unittest.TestCase):
    def test_two_destinations_are_verified_privately_then_loaded_anonymously_and_retry_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); (base/'cache').mkdir(); (base/'output').mkdir()
            (base/'credentials.json').write_text(json.dumps({'token':'fixture', 'publish_token':'fixture-write',
                                                            'hf_write_token':'fixture-hf'}))
            payload = {'README.md': b'Unit fixture; no empirical result',
                       'extract/meta.json': json.dumps({'columns':['id','label'],'rows':{'train':1,'eval':1,'holdout':1}}).encode()}
            payload.update({p:b'id,label\nfixture,1\n' for p in
                            ('extract/public/train.csv','extract/public/eval.csv','extract/private/holdout.csv')})
            assets = {p:{'asset_name':p.replace('/','__'),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
                      for p,b in payload.items()}
            version = 'v-'+hashlib.sha256(json.dumps(assets,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
            manifest = {'assets':assets,'dataset':'fixture','artifact_version':'a'*64,'version':version}
            payload['MANIFEST.json'] = json.dumps(manifest).encode(); payload['SHA256SUMS'] = b'unit-fixture'
            staged = {p:{'id':i+1,'name':p,'size':len(b),'bytes':b,'digest':'sha256:'+hashlib.sha256(b).hexdigest()}
                      for i,(p,b) in enumerate(payload.items())}
            GitHub.repos = {'owner/staging': {'assets': staged}}
            spec = {'policy':'FACTORY-REWRITE-2026-11-08','dataset':'fixture','artifact_version':'a'*64,
                    'version':version,'source_repo':'owner/staging','source_release':1,
                    'github_repo':'owner/factory-fixture','hf_repo':'owner/factory-fixture',
                    'assets':[{'path':p,'target_name':p.replace('/','__'),'source_asset_id':a['id'],
                               'size':a['size'],'sha256':a['digest'][7:]} for p,a in staged.items()]}
            hub = {'public':False,'files':{}}
            transient = [True]
            def hf(base, job, report):
                for item in job['hf_publish']['assets']:
                    entry = next(a for a in GitHub.repos['owner/factory-fixture']['assets'].values() if a['id']==item['asset_id'])
                    self.assertEqual(item['sha256'], hashlib.sha256(entry['bytes']).hexdigest())
                    hub['files'][item['target']] = entry['bytes']
                report['hf_publish'] = {'failures': []}; report['hf_verification'] = {'ok':True,'commit':'5'*40}
            def control(base, python, token, action, spec, commit='none', **kwargs):
                if action == 'publish':
                    self.assertEqual('5'*40,commit); self.assertIn('MANIFEST.json',hub['files']); hub['public']=True
                return {'public':hub['public'],'commit':'5'*40,'tag_matches_main':True}
            def anonymous(request, timeout):
                self.assertNotIn('Authorization', request.headers)
                if transient.pop() if transient else False:
                    raise urllib.error.HTTPError(request.full_url, 503, 'temporary', {}, None)
                if request.full_url.startswith('https://github.com/'):
                    repo = GitHub.repos['owner/factory-fixture']
                    self.assertFalse(repo['private']); self.assertFalse(repo['release']['draft'])
                    data = repo['assets'][request.full_url.rsplit('/',1)[1]]['bytes']
                else:
                    self.assertTrue(hub['public'])
                    data = hub['files'][request.full_url.split('/'+version+'/')[1]]
                response = io.BytesIO(data); response.url = request.full_url
                return response
            with patch.object(release_publish,'GitHub',GitHub), patch.object(upload,'GitHub',GitHub), \
                    patch.object(release_publish,'ensure_client',return_value=Path('/fixture/python')), \
                    patch.object(release_publish,'hf_publish',side_effect=hf), \
                    patch.object(release_publish,'hub_control',side_effect=control), \
                    patch.object(get_dataset.urllib.request,'urlopen',side_effect=anonymous), \
                    patch.object(get_dataset.time,'sleep'):
                def failed_hub(base, job, report):
                    report['hf_publish'] = {'failures': ['temporary provider failure']}
                with patch.object(release_publish, 'hf_publish', side_effect=failed_hub), self.assertRaises(upload.UploadError):
                    release_publish.release_publish(base, {'release_publish':spec}, {})
                self.assertTrue(GitHub.repos['owner/factory-fixture']['private'])
                self.assertFalse(hub['public'])
                for _ in range(2):
                    report = {}
                    release_publish.release_publish(base, {'release_publish':spec}, report)
                    self.assertTrue(report['publication']['ok'])
                    self.assertEqual({'github','huggingface'},set(report['publication']['consumers']))
            self.assertEqual(len(payload),len(GitHub.repos['owner/factory-fixture']['assets']))


class HubFailureEvidenceTests(unittest.TestCase):
    def test_publish_helper_uses_keyword_only_tag_and_checks_public_revision(self):
        class Api:
            private = True
            tagged = None
            def list_repo_refs(self, repo, *, repo_type):
                return types.SimpleNamespace(branches=[types.SimpleNamespace(name='main',target_commit='commit')], tags=[])
            # Matches the public huggingface_hub HfApi.create_tag signature.
            def create_tag(self, repo, *, tag, revision, repo_type, exist_ok):
                self.tagged = (tag,revision)
            def update_repo_settings(self, *, repo_id, repo_type, private): self.private = private
            def repo_info(self, repo, *, repo_type, revision):
                return types.SimpleNamespace(private=self.private, sha='commit')
        api = Api(); hub = types.ModuleType('huggingface_hub'); hub.HfApi = lambda **kw: api
        hub.hf_hub_download = lambda *a, **k: None
        errors = types.ModuleType('huggingface_hub.errors'); errors.RepositoryNotFoundError = FileNotFoundError
        with patch.dict(sys.modules, {'huggingface_hub':hub, 'huggingface_hub.errors':errors}), \
                patch.dict('os.environ', {'HF_WRITE_TOKEN':'fixture-secret'}), \
                patch.object(sys, 'argv', ['helper','publish','owner/repo','dataset','v-tag','commit']), \
                patch.object(sys, 'excepthook'), patch('sys.stdout', new_callable=io.StringIO) as output:
            exec(release_publish.HUB_CONTROL, {})
        self.assertEqual(('v-tag','commit'),api.tagged)
        self.assertFalse(api.private)
        self.assertTrue(json.loads(output.getvalue())['tag_matches_main'])

    def test_helper_reports_only_operation_class_and_http_status(self):
        class ProviderError(Exception):
            response = types.SimpleNamespace(status_code=403)
        api = types.SimpleNamespace(list_repo_refs=lambda *a, **k: (_ for _ in ()).throw(
            ProviderError('secret token must not appear')))
        hub = types.ModuleType('huggingface_hub'); hub.HfApi = lambda **kw: api
        hub.hf_hub_download = lambda *a, **k: None
        errors = types.ModuleType('huggingface_hub.errors'); errors.RepositoryNotFoundError = FileNotFoundError
        namespace = {}
        with patch.dict(sys.modules, {'huggingface_hub':hub, 'huggingface_hub.errors':errors}), \
                patch.dict('os.environ', {'HF_WRITE_TOKEN':'fixture-secret'}), \
                patch.object(sys, 'argv', ['helper','publish','owner/repo','dataset','v-tag','commit']), \
                patch.object(sys, 'excepthook'):
            with self.assertRaises(ProviderError) as caught:
                exec(release_publish.HUB_CONTROL, namespace)
            with patch('sys.stdout', new_callable=io.StringIO) as output:
                namespace['report_failure'](ProviderError, caught.exception, None)
        self.assertEqual({'ok':False,'stage':'list-refs','error':'ProviderError','http_status':403},
                         json.loads(output.getvalue()))
        self.assertNotIn('secret', output.getvalue())

    def test_worker_retains_safe_helper_details_in_failure_receipt(self):
        result = subprocess.CompletedProcess([], 1,
            json.dumps({'ok':False,'stage':'create-tag','error':'HfHubHTTPError','http_status':403}),
            'secret URL and credential must never be retained')
        with tempfile.TemporaryDirectory() as tmp, patch.object(release_publish.subprocess, 'run', return_value=result):
            report = {}
            with self.assertRaises(upload.UploadError):
                release_publish.hub_control(Path(tmp),Path('/fixture/python'),'secret','publish',
                    {'hf_repo':'owner/repo','dataset':'dataset','version':'v-tag'}, 'commit', report=report)
        self.assertEqual({'action':'publish','exit_code':1,'stage':'create-tag',
                          'error':'HfHubHTTPError','http_status':403}, report['hub_control'])
        self.assertNotIn('secret', json.dumps(report))


if __name__ == '__main__': unittest.main()
