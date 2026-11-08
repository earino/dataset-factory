"""One deterministic release worker: existing transfers, tag, publish, consume."""
import base64
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

try:
    from .upload import GitHub, UploadError, transfer
    from .hf_publish import hf_publish, ensure_client, hub_env, write_helper
    from .get_dataset import retrieve
except ImportError:
    from upload import GitHub, UploadError, transfer
    from hf_publish import hf_publish, ensure_client, hub_env, write_helper
    from get_dataset import retrieve


def validate(spec):
    if spec.get('policy') != 'FACTORY-REWRITE-2026-11-08':
        raise ValueError('Standing publication policy is missing')
    for key in ('source_repo', 'github_repo', 'hf_repo'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', spec.get(key, '')):
            raise ValueError('Invalid repository identity')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', spec.get('dataset', '')):
        raise ValueError('Invalid dataset identity')
    if not re.fullmatch(r'[0-9a-f]{64}', spec.get('artifact_version', '')):
        raise ValueError('Missing exact-artifact identity')
    if not re.fullmatch(r'v-[0-9a-f]{16}', spec.get('version', '')):
        raise ValueError('Version is not bound to accepted artifact')
    seen = set(); names = set()
    for entry in spec.get('assets', []):
        path = entry.get('path', '')
        if (not path or path.startswith('/') or any(p in ('', '.', '..') for p in path.split('/'))
                or '\\' in path or path in seen or entry.get('target_name') in names
                or not re.fullmatch(r'[A-Za-z0-9_.-]+', entry.get('target_name', ''))
                or type(entry.get('source_asset_id')) is not int or entry['source_asset_id'] <= 0
                or type(entry.get('size')) is not int or not 0 <= entry['size'] < 1024**3
                or not re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256', ''))):
            raise ValueError('Invalid release asset binding')
        seen.add(path); names.add(entry['target_name'])
    if not {'MANIFEST.json', 'SHA256SUMS', 'README.md', 'extract/meta.json',
            'extract/public/train.csv', 'extract/public/eval.csv', 'extract/private/holdout.csv'} <= seen:
        raise ValueError('Release is incomplete')


def commit_files(client, files):
    """Same atomic Git-tree procedure as the existing site publisher; no gh install."""
    prefix = '/repos/' + client.repo
    info = client.request('GET', prefix)
    branch = info['default_branch']
    head = client.request('GET', prefix + '/git/ref/heads/' + quote(branch, safe=''))['object']['sha']
    base = client.request('GET', prefix + '/git/commits/' + head)['tree']['sha']
    tree = client.request('GET', prefix + '/git/trees/' + base + '?recursive=1')
    if tree.get('truncated'):
        raise UploadError('Repository tree is too large to reconcile')
    current = {entry['path']: entry for entry in tree['tree']}
    changes = []
    for path, content in sorted(files.items()):
        raw = content.encode()
        digest = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if current.get(path, {}).get('sha') != digest:
            changes.append({'path': path, 'mode': '100644', 'type': 'blob', 'content': content})
    if not changes:
        return head
    tree = client.request('POST', prefix + '/git/trees', {'base_tree': base, 'tree': changes})['sha']
    commit = client.request('POST', prefix + '/git/commits',
                            {'message': 'Publish accepted Dataset Factory artifact', 'tree': tree, 'parents': [head]})['sha']
    client.request('PATCH', prefix + '/git/refs/heads/' + quote(branch, safe=''), {'sha': commit, 'force': False})
    return commit


HUB_CONTROL = '''import json, os, sys
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.errors import RepositoryNotFoundError
from pathlib import Path
api = HfApi(token=os.environ['HF_WRITE_TOKEN'])
action, repo, dataset, tag, commit = sys.argv[1:]
stage = 'repo-info'
def report_failure(kind, value, traceback):
    result = {'ok':False, 'stage':stage, 'error':kind.__name__}
    status = getattr(getattr(value, 'response', None), 'status_code', None)
    if type(status) is int: result['http_status'] = status
    print(json.dumps(result))
sys.excepthook = report_failure
if action == 'prepare':
    try:
        info = api.repo_info(repo, repo_type='dataset', files_metadata=True)
    except RepositoryNotFoundError:
        api.create_repo(repo, repo_type='dataset', private=True, exist_ok=False)
        info = api.repo_info(repo, repo_type='dataset', files_metadata=True)
    names = {s.rfilename for s in info.siblings or []}
    if 'MANIFEST.json' in names:
        path = hf_hub_download(repo, 'MANIFEST.json', repo_type='dataset', token=os.environ['HF_WRITE_TOKEN'])
        if json.loads(Path(path).read_text())['dataset'] != dataset: raise ValueError('Hub ownership mismatch')
    elif names - {'.gitattributes'}:
        raise ValueError('Existing Hub repository is not an owned factory release')
    print(json.dumps({'prepared':True,'private':info.private}))
else:
    stage = 'list-refs'
    refs = api.list_repo_refs(repo, repo_type='dataset')
    main = next(r.target_commit for r in refs.branches if r.name == 'main')
    tags = {r.name:r.target_commit for r in refs.tags}
    stage = 'verify-main'
    if main != commit: raise ValueError('Verified Hub main changed')
    stage = 'verify-existing-tag'
    if tag in tags and tags[tag] != commit: raise ValueError('Preserve existing different Hub tag')
    stage = 'create-tag'
    if tag not in tags: api.create_tag(repo, tag=tag, revision=commit, repo_type='dataset', exist_ok=False)
    stage = 'set-public'
    api.update_repo_settings(repo_id=repo, repo_type='dataset', private=False)
    stage = 'verify-public'
    info = api.repo_info(repo, repo_type='dataset', revision=tag)
    main_info = api.repo_info(repo, repo_type='dataset', revision='main')
    if info.private or info.sha != commit or main_info.sha != commit: raise ValueError('Hub public tag/main mismatch')
    print(json.dumps({'public':True,'commit':commit,'tag':tag,'tag_matches_main':True}))
'''


def hub_control(base, python, token, action, spec, commit='none', *, report=None):
    helper = write_helper(base, '.release-hub.py', HUB_CONTROL)
    result = subprocess.run([str(python), str(helper), action, spec['hf_repo'], spec['dataset'],
                             spec['version'], commit], capture_output=True, text=True,
                            env=hub_env(token), timeout=180)
    if report is not None:
        detail = {'action': action, 'exit_code': result.returncode}
        try:
            value = json.loads(result.stdout)
            for key in ('stage', 'error', 'http_status'):
                if key in value: detail[key] = value[key]
        except (ValueError, TypeError):
            pass
        report['hub_control'] = detail
    if result.returncode:
        raise UploadError('Hub ' + action + ' failed; remote state will be reconciled on retry')
    return json.loads(result.stdout)


def consumer(base, platform, repo, spec):
    with tempfile.TemporaryDirectory(prefix='consumer-', dir=base / 'cache') as tmp:
        out = Path(tmp) / 'download'
        manifest = retrieve(repo, spec['version'], out, platform)
        if manifest['artifact_version'] != spec['artifact_version']:
            raise UploadError('Anonymous consumer obtained a different artifact')
        meta = json.loads((out / 'extract/meta.json').read_text())
        rows = {}
        for split, name in [('train', 'public/train.csv'), ('eval', 'public/eval.csv'), ('holdout', 'private/holdout.csv')]:
            with (out / 'extract' / name).open(newline='') as stream:
                reader = csv.reader(stream)
                if next(reader) != meta['columns']:
                    raise UploadError('Consumer CSV schema differs')
                count = 0
                for row in reader:
                    if len(row) != len(meta['columns']):
                        raise UploadError('Consumer encountered a ragged CSV')
                    count += 1
                if count != meta['rows'][split]:
                    raise UploadError('Consumer row count differs')
                rows[split] = count
        return {'ok': True, 'authentication': 'none', 'repo': repo, 'version': spec['version'],
                'files_sha256_verified': len(manifest['assets']), 'rows_loaded': rows}


def release_publish(base, job, report):
    spec = job['release_publish']; validate(spec)
    credentials = json.loads((base / 'credentials.json').read_text())
    source = GitHub(credentials['token'], spec['source_repo'])
    target = GitHub(credentials['publish_token'], spec['github_repo'])
    prefix = '/repos/' + target.repo
    report['publication_stage'] = 'prepare'
    owner, name = target.repo.split('/')
    marker = 'Dataset Factory: ' + spec['dataset']
    info = target.request('GET', prefix)
    if info is None:
        who = target.request('GET', '/user')
        endpoint = '/user/repos' if who['login'].lower() == owner.lower() else '/orgs/' + owner + '/repos'
        target.request('POST', endpoint, {'name': name, 'private': True, 'auto_init': True, 'description': marker})
        info = target.request('GET', prefix)
    if info.get('description') != marker:
        raise UploadError('Existing GitHub repository is not owned by this publication path')
    (base / 'cache').mkdir(exist_ok=True)
    files = {}
    for index, item in enumerate(spec['assets']):
        if item['size'] > 256 * 1024 or not item['path'].endswith(('.py', '.sh', '.md', '.json', '.txt')):
            continue
        local = base / 'cache' / ('metadata-' + str(index))
        source.download(item['source_asset_id'], local, item['sha256'], item['size'])
        files[item['path']] = local.read_text()
        local.unlink()
    manifest = json.loads(files['MANIFEST.json'])
    version = 'v-' + hashlib.sha256(json.dumps(manifest['assets'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]
    if (manifest['version'] != version or version != spec['version']
            or manifest['artifact_version'] != spec['artifact_version']):
        raise UploadError('Release package identity differs from accepted manifest')
    commit = commit_files(target, files)
    python = ensure_client(base, report)
    hub_control(base, python, credentials['hf_write_token'], 'prepare', spec, report=report)
    releases = []
    for page in range(1, 11):
        batch = target.request('GET', prefix + f'/releases?per_page=100&page={page}')
        releases.extend(batch)
        if len(batch) < 100: break
    release = next((r for r in releases if r['tag_name'] == spec['version']), None)
    body = 'Accepted artifact SHA256: ' + spec['artifact_version']
    if release is None:
        release = target.request('POST', prefix + '/releases', {'tag_name': spec['version'],
                    'target_commitish': commit, 'name': spec['version'], 'body': body, 'draft': True})
    if release.get('body') != body:
        raise UploadError('Existing GitHub release has a different artifact binding')
    report['publication_stage'] = 'github-transfer'
    transferred = transfer(base, {**job, 'transfer': {'source_repo': spec['source_repo'],
        'source_release': spec['source_release'], 'target_repo': target.repo,
        'target_release': release['id'], 'allow_public': True, 'assets': spec['assets']}}, report)
    remote = {a['name']: a for a in target.assets(release['id'])}
    items = [{'asset_id': remote[a['target_name']]['id'], 'dest': f'hf-{i}', 'target': a['path'],
              'size': a['size'], 'sha256': a['sha256']} for i, a in enumerate(spec['assets'])]
    report['publication_stage'] = 'huggingface-transfer'
    hf_publish(base, {**job, 'hf_publish': {'repo': spec['hf_repo'], 'revision': 'main',
               'source_repo': target.repo, 'assets': items}}, report)
    if report['hf_publish']['failures'] or report.get('hf_verification', {}).get('ok') is not True:
        raise UploadError('Private Hub verification failed')
    report['publication_stage'] = 'huggingface-publish'
    hf = hub_control(base, python, credentials['hf_write_token'], 'publish', spec, report['hf_verification']['commit'], report=report)
    report['publication_stage'] = 'github-visibility'
    target.request('PATCH', prefix, {'private': False})
    report['publication_stage'] = 'github-release'
    target.request('PATCH', prefix + '/releases/' + str(release['id']), {'draft': False})
    report['publication_stage'] = 'github-tag-verify'
    tag = target.request('GET', prefix + '/git/ref/tags/' + spec['version'])['object']
    main = target.request('GET', prefix + '/git/ref/heads/' + quote(info['default_branch'], safe=''))['object']['sha']
    if tag.get('type') != 'commit' or tag['sha'] != commit or main != commit:
        raise UploadError('GitHub tag/main differs from accepted source commit')
    report['publication_stage'] = 'anonymous-consumers'
    consumers = {platform: consumer(base, platform, repo, spec) for platform, repo in
                 [('github', target.repo), ('huggingface', spec['hf_repo'])]}
    receipt = {'ok': True, 'dataset': spec['dataset'], 'artifact_version': spec['artifact_version'],
               'version': spec['version'], 'policy': spec['policy'], 'consumers': consumers,
               'github': {'repo': target.repo, 'commit': commit, 'tag_matches_main': True,
                          'url': f'https://github.com/{target.repo}/releases/tag/{spec["version"]}'},
               'huggingface': {**hf, 'repo': spec['hf_repo'], 'url': 'https://huggingface.co/datasets/' + spec['hf_repo']}}
    (base / 'output').mkdir(exist_ok=True)
    (base / 'output/publication.json').write_text(json.dumps(receipt, indent=2) + '\n')
    report['publication'] = receipt
    report['publication_stage'] = 'complete'
