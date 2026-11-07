"""Bounded provider operations for an approved visibility change, never bulk transfers."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from .asset_integrity import sha256
from .site_github import GitHub
from .publication import require, approved_plan
from .leakage_battery import digest

LIMIT = 4 * 1024 * 1024


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(urlsplit(newurl).scheme == 'https', 'non-HTTPS publication readback redirect')
        request = super().redirect_request(req, fp, code, msg, headers, newurl)
        if request and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            request.remove_header('Authorization')
        return request


def read_url(url, limit, *, token=None, ranged=False):
    require(urlsplit(url).scheme == 'https', 'non-HTTPS publication readback')
    headers = {'User-Agent': 'dataset-factory-publication-check', 'Accept': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if ranged: headers['Range'] = 'bytes=0-0'
    # A new opener has no cookie jar, netrc handler or cached authorization.
    with build_opener(SafeRedirect()).open(Request(url, headers=headers), timeout=30) as response:
        if ranged:
            require(response.status == 206 and response.headers.get('Content-Range', '').startswith('bytes 0-0/'),
                    'anonymous range read did not prove file access')
        data = response.read(limit + 1)
    require(len(data) <= limit, 'publication readback exceeded its byte bound')
    return data


class AnonymousGitHub(GitHub):
    def request(self, method, path, body=None, missing_ok=False):
        require(method == 'GET' and body is None and path.startswith('repos/'), 'anonymous readback is GET-only')
        return json.loads(read_url('https://api.github.com/' + path, LIMIT))


def hub_operation(root, payload):
    interpreter = Path('/opt/data/.venvs/hf/bin/python')
    require(interpreter.is_file(), 'existing Hugging Face publishing environment is unavailable')
    result = subprocess.run([str(interpreter), '-m', 'factory.publication_remote'],
                            input=json.dumps(payload), text=True, capture_output=True, cwd=root, timeout=180)
    require(result.returncode == 0 and len(result.stdout) < 256 * 1024,
            'Hugging Face publication operation failed; preserve partial intent and inspect provider state')
    return json.loads(result.stdout)


def hub_main(value):
    from huggingface_hub import HfApi, hf_hub_url
    from .http import secret
    from .hub_integrity import refs, verify_revision, load_worker_receipt
    root = Path.cwd(); anonymous = value['anonymous']; target = value['target']
    if value['action'] == 'make_public':
        approved = approved_plan(root, value['dataset'])
        require(digest(approved) == value['plan_sha256'] and approved['targets']['huggingface'] == target,
                'Hub mutation has no matching approval')
    token = False if anonymous else secret('FACTORY_HF_WRITE_TOKEN')
    api = HfApi(endpoint='https://huggingface.co', token=token)
    repo = target['repository']; main, tags = refs(api, repo)
    require(main == target['commit'] == tags.get(target['tag']), 'Hub tag/main changed since approval')
    if value['action'] == 'make_public':
        require(anonymous is False, 'anonymous mutation refused')
        api.update_repo_settings(repo_id=repo, repo_type='dataset', private=False)
        return {'requested_public': True}
    expected = {k: tuple(v) for k, v in value['expected'].items()}
    receipt = load_worker_receipt(root, value['worker_job'], repo, expected) if value.get('worker_job') else None
    def small(path, commit, limit):
        return read_url(hf_hub_url(repo, path, repo_type='dataset', revision=commit), limit,
                        token=token if isinstance(token, str) else None)
    result = verify_revision(api, repo, expected, target['commit'], small, receipt)
    require(result['ok'], 'Hub accepted-asset verification failed or incomplete')
    require(hashlib.sha256(small('MANIFEST.json', target['commit'], value['manifest_bytes'])).hexdigest()
            == value['manifest_sha256'], 'Hub manifest differs from approved manifest')
    if anonymous:
        require(result['repo_private'] is False, 'Hub repository is not public')
        for path in expected:
            read_url(hf_hub_url(repo, path, repo_type='dataset', revision=target['tag']), 1, ranged=True)
    final_main, final_tags = refs(api, repo)
    require(final_main == target['commit'] == final_tags.get(target['tag']), 'Hub refs changed during verification')
    return {'private': result['repo_private'], 'anonymous': anonymous, 'assets_verified': True,
            'commit': target['commit'], 'tag': target['tag'], 'asset_count': len(expected)}


class Remote:
    def __init__(self, root, dataset, plan):
        self.root = Path(root); self.plan = plan; self.dataset = dataset
        self.package = self.root/'release'/dataset
        self.manifest = json.loads((self.package/'MANIFEST.json').read_text())
        self.destinations = json.loads((self.package/'DESTINATIONS.json').read_text())['destinations']
        self.api = GitHub()
        spec = importlib.util.spec_from_file_location('publication_hf_layout', self.root/'scripts/hf-publish.py')
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        self.expected = {helper.asset_target(self.manifest, name): (info['bytes'], info['sha256'])
                         for name, info in self.manifest['assets'].items()}
        require(len(self.expected) == len(self.manifest['assets']), 'duplicate Hub asset mapping')

    def github(self, anonymous):
        api = AnonymousGitHub() if anonymous else self.api
        target = self.plan['targets']['github']; repo = target['repository']
        info = api.request('GET', f'repos/{repo}')
        require(not anonymous or info.get('private') is False, 'GitHub repository is not public')
        for ref in (target['tag'], info['default_branch']):
            require(api.request('GET', f'repos/{repo}/commits/{quote(ref, safe="")}')['sha'] == target['commit'],
                    'GitHub refs changed since approval')
        manifest = api.file(repo, 'MANIFEST.json', ref=target['commit'])
        require(hashlib.sha256(manifest.encode()).hexdigest() == self.plan['manifest_sha256'],
                'GitHub manifest differs from approved manifest')
        checked_bytes = len(manifest.encode())
        for name, expected in self.manifest.get('package_files', {}).items():
            if name.endswith('.csv'): continue
            content = api.file(repo, name, ref=target['commit'])
            checked_bytes += len(content.encode())
            require(checked_bytes <= 2*1024*1024, 'GitHub compact package verification exceeds bound')
            wanted = expected if isinstance(expected, str) else expected['sha256']
            require(hashlib.sha256(content.encode()).hexdigest() == wanted,
                    'GitHub document differs from approved package: ' + name)
        release = api.request('GET', f'repos/{repo}/releases/tags/{quote(target["tag"], safe="")}')
        require(release.get('id') == self.destinations['github']['release_id'] and release.get('draft') is False,
                'GitHub release identity changed or remains a draft')
        assets = []
        for page in range(1, 12):
            batch = api.request('GET', f'repos/{repo}/releases/{release["id"]}/assets?per_page=100&page={page}')
            assets += batch
            if len(batch) < 100: break
        else: raise ValueError('release asset listing exceeds bound')
        for entry in self.manifest['assets'].values():
            matches = [a for a in assets if a.get('name') == entry['asset_name']]
            require(len(matches) == 1 and matches[0].get('size') == entry['bytes']
                    and matches[0].get('digest') == 'sha256:' + entry['sha256'],
                    'GitHub asset digest/size changed since approval')
            if anonymous:
                read_url(f'https://github.com/{repo}/releases/download/{quote(target["tag"], safe="")}/'
                         + quote(entry['asset_name'], safe=''), 1, ranged=True)
        return {'private': info['private'], 'anonymous': anonymous, 'assets_verified': True,
                'commit': target['commit'], 'tag': target['tag'], 'asset_count': len(self.manifest['assets'])}

    def hub(self, anonymous, action='inspect'):
        return hub_operation(self.root, {'action': action, 'anonymous': anonymous,
            'dataset': self.dataset, 'plan_sha256': digest(self.plan),
            'target': self.plan['targets']['huggingface'], 'expected': self.expected,
            'manifest_sha256': self.plan['manifest_sha256'],
            'manifest_bytes': (self.package/'MANIFEST.json').stat().st_size,
            'worker_job': self.destinations['huggingface'].get('worker_job')})

    def inspect(self, *, anonymous):
        return {'github': self.github(anonymous), 'huggingface': self.hub(anonymous)}

    def make_public(self, destination):
        require(approved_plan(self.root, self.dataset) == self.plan, 'publication approval changed before mutation')
        if destination == 'github':
            self.api.request('PATCH', 'repos/' + self.plan['targets']['github']['repository'], {'private': False})
        elif destination == 'huggingface': self.hub(False, 'make_public')
        else: raise ValueError('unknown publication destination')


if __name__ == '__main__':
    try:
        payload = sys.stdin.read(256 * 1024 + 1)
        require(len(payload) <= 256 * 1024, 'oversized publication input')
        print(json.dumps(hub_main(json.loads(payload))))
    except Exception as exc:
        # Provider exceptions may contain signed URLs: never echo their text.
        print(json.dumps({'ok': False, 'error_type': type(exc).__name__}))
        sys.exit(1)
