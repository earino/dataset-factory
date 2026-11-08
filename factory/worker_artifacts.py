"""Read only compact, digest-verified worker metadata; bulk stays on workers."""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from .common import FactoryError, write_json
from .http import secret
from .publication_remote import SafeRedirect

LIMIT = 256 * 1024


def assets(api, repo, release_id):
    found = []
    for page in range(1, 12):
        batch = api.request('GET', f'repos/{repo}/releases/{release_id}/assets?per_page=100&page={page}')
        found.extend(batch)
        if len(batch) < 100:
            return found
    raise FactoryError('Staging asset inventory exceeds limit')


def download_json(repo, entry, path):
    if (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
            or type(entry.get('id')) is not int or type(entry.get('size')) is not int
            or not 0 < entry['size'] < LIMIT
            or not re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256', ''))):
        raise FactoryError('Invalid or oversized compact artifact')
    path = Path(path)
    if path.is_symlink():
        raise FactoryError('Compact artifact path is a symlink')
    if path.exists():
        if path.stat().st_size >= LIMIT:
            raise FactoryError('Cached artifact exceeds limit')
        data = path.read_bytes()
    else:
        request = urllib.request.Request(
            f'https://api.github.com/repos/{repo}/releases/assets/{entry["id"]}',
            headers={'Accept': 'application/octet-stream', 'User-Agent': 'dataset-factory',
                     'Authorization': 'Bearer ' + secret('FACTORY_GITHUB_TOKEN')})
        with urllib.request.build_opener(SafeRedirect()).open(request, timeout=45) as response:
            data = response.read(LIMIT)
    if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise FactoryError('Compact artifact digest/size mismatch')
    value = json.loads(data)
    if not isinstance(value, dict):
        raise FactoryError('Compact artifact must be an object')
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # Preserve original bytes; a JSON re-encoding would change the digest.
        temporary = path.with_suffix('.part')
        if temporary.is_symlink():
            raise FactoryError('Compact artifact temporary path is a symlink')
        temporary.write_bytes(data); temporary.replace(path)
    return value


def manifest(root, record, api):
    report = record['result']; repo = record['staging_repo']
    remote = assets(api, repo, report['release_id'])
    matches = [a for a in remote if a['name'] == 'manifest.json']
    if len(matches) != 1:
        raise FactoryError('Staging manifest missing or ambiguous')
    actual = matches[0]
    pins = [a for a in report['assets'] if a['id'] == actual['id']]
    if (len(pins) != 1 or actual['size'] != pins[0]['size']
            or actual.get('digest') != 'sha256:' + pins[0]['sha256']):
        raise FactoryError('Staging manifest differs from collected result')
    path = Path(root) / '.factory' / record['job']['id'] / 'staging-manifest.json'
    value = download_json(repo, pins[0], path)
    if value.get('job', {}).get('id') != record['job']['id']:
        raise FactoryError('Staging manifest belongs to another job')
    return value


def collect_json(root, record, logical, api):
    if not logical.startswith('output/') or not logical.endswith('.json'):
        raise FactoryError('Only compact output JSON may be collected')
    from .asset_integrity import safe_path
    raw = manifest(root, record, api)
    entries = [a for a in raw['assets'] if a.get('file') == logical]
    if len(entries) != 1 or entries[0].get('offset') != 0:
        raise FactoryError('Compact output is missing, duplicated or chunked')
    entry = entries[0]
    pins = [a for a in record['result']['assets'] if a['id'] == entry['id']]
    if len(pins) != 1 or any(pins[0][k] != entry[k] for k in ('size', 'sha256')):
        raise FactoryError('Compact output differs from collected result')
    path = safe_path(Path(root) / '.factory' / record['job']['id'], logical)
    return download_json(record['staging_repo'], entry, path)


def recover(root, record, api):
    """Recover a complete upload after worker expiry or a lost collection reply."""
    repo = record['staging_repo']; job_id = record['job']['id']; release = None
    # Draft staging releases do not resolve through the tags endpoint.
    for page in range(1, 21):
        batch = api.request('GET', f'repos/{repo}/releases?per_page=100&page={page}')
        matches = [r for r in batch if r['tag_name'] == 'job-' + job_id]
        if matches:
            release = matches[0]; break
        if len(batch) < 100:
            return None
    if release is None:
        raise FactoryError('Staging release history exceeds recovery limit')
    remote = assets(api, repo, release['id'])
    found = [a for a in remote if a['name'] == 'manifest.json']
    if len(found) != 1:
        return None  # Upload never completed; retain diagnostics, retry construction separately.
    entry = found[0]
    pin = {'id': entry['id'], 'name': entry['name'], 'size': entry['size'],
           'sha256': entry.get('digest', '').removeprefix('sha256:')}
    raw = download_json(repo, pin, Path(root) / '.factory' / job_id / 'staging-manifest.json')
    if raw.get('job') != record['job'] or raw.get('result', {}).get('job_id') != job_id:
        raise FactoryError('Recovery manifest does not match launched job')
    report = {**raw['result'], 'uploaded': True, 'repo': repo, 'release_id': release['id'],
              'release_url': release.get('html_url'), 'manifest_url': entry.get('browser_download_url'),
              'assets': [{k: a[k] for k in ('id', 'name', 'size', 'sha256')} for a in raw['assets']] + [pin],
              'skipped_empty': raw.get('skipped_empty', [])}
    from .worker import verify_preserved_report
    verify_preserved_report(record, report, api)
    write_json(Path(root) / '.factory' / job_id / 'result.json', report)
    return report
