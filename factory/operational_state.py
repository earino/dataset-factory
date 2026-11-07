"""Append-only operational evidence and a deterministic, bounded repository view.

Events record observations, not authorization. Candidate/job records remain the
source of current state; provider status cannot be inferred from a generated file.
"""
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

LIMIT = 20_000
HEX = re.compile(r'^[0-9a-f]{64}$')
ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def path_in(root, name):
    if not isinstance(name, str) or not name or name.startswith('/') or any(
            p in ('', '.', '..') or p.startswith('.') for p in name.split('/')):
        raise ValueError('evidence path must be an explicit nonhidden repository path')
    path = Path(root) / name
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('operational evidence path is a symlink')
        if parent == Path(root): break
    return path


def validate_body(event):
    fields = {'id', 'actor', 'time', 'candidate', 'job', 'kind', 'outcome', 'evidence', 'commit'}
    if set(event) != fields or not isinstance(event['id'], str) or not ID.fullmatch(event['id']):
        raise ValueError('event requires the exact operational schema and a stable id')
    if not re.fullmatch(r'[0-9a-f]{40}', event['commit']):
        raise ValueError('event requires a full existing source/evidence commit identity')
    for field in ('actor', 'kind', 'outcome'):
        if not isinstance(event[field], str) or not 1 <= len(event[field]) <= 1600:
            raise ValueError('event text missing or exceeds its bound: ' + field)
    for field in ('candidate', 'job'):
        if event[field] is not None and (not isinstance(event[field], str) or not ID.fullmatch(event[field])):
            raise ValueError('invalid candidate/job identifier')
    stamp = event['time']
    if not isinstance(stamp, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', stamp):
        raise ValueError('event time must be UTC with second precision')
    datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
    if not isinstance(event['evidence'], list) or not 1 <= len(event['evidence']) <= 16:
        raise ValueError('event requires one to sixteen bounded evidence references')
    for item in event['evidence']:
        if set(item) != {'path', 'sha256'} or not HEX.fullmatch(item['sha256']):
            raise ValueError('event evidence needs an exact path and SHA256')
        path_in(Path('/validation-root'), item['path'])
    if len(canonical(event)) > 16 * 1024:
        raise ValueError('event exceeds bounded record size')


def events(root):
    previous = '0' * 64; seen = set(); result = []
    directory = path_in(root, 'events')
    for path in sorted(directory.glob('*.jsonl')):
        path_in(root, path.relative_to(root).as_posix())
        if not re.fullmatch(r'\d{4}-\d{2}\.jsonl', path.name):
            raise ValueError('event log must be partitioned by UTC month')
        with path.open('rb') as stream:
            for line in stream:
                if len(line) > 20 * 1024 or not line.endswith(b'\n'):
                    raise ValueError('event line is oversized or incomplete')
                row = json.loads(line); body = row['event']; validate_body(body)
                if (set(row) != {'event', 'previous', 'sha256'} or row['previous'] != previous
                        or row['sha256'] != digest(canonical({'event': body, 'previous': previous}))
                        or body['id'] in seen or body['time'][:7] != path.stem):
                    raise ValueError('operational event chain is changed, duplicated or out of order')
                if result and body['time'] < result[-1]['time']:
                    raise ValueError('event observation times must be append ordered')
                if line != canonical(row) + b'\n':
                    raise ValueError('event encoding is not canonical')
                previous = row['sha256']; seen.add(body['id']); result.append(body)
    return result, previous


def append(root, event):
    root = Path(root); validate_body(event)
    directory = path_in(root, 'events'); directory.mkdir(exist_ok=True)
    lock = root / '.factory/state-events.lock'; lock.parent.mkdir(exist_ok=True)
    if lock.parent.is_symlink() or lock.is_symlink(): raise ValueError('state lock is a symlink')
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'r+') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        old, previous = events(root)
        for item in old:
            if item['id'] == event['id']:
                if item != event: raise ValueError('event id already names a different observation')
                return False
        if old and event['time'] < old[-1]['time']: raise ValueError('backdated append refused; record current observation time')
        for item in event['evidence']:
            path = path_in(root, item['path'])
            if not path.is_file() or path.stat().st_size >= 256 * 1024 or digest(path.read_bytes()) != item['sha256']:
                raise ValueError('event evidence is missing, oversized or changed: ' + item['path'])
        row = {'event': event, 'previous': previous}
        row['sha256'] = digest(canonical(row))
        path = path_in(root, 'events/' + event['time'][:7] + '.jsonl')
        out = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(out, 'ab') as stream:
            stream.write(canonical(row) + b'\n'); stream.flush(); os.fsync(stream.fileno())
    return True


def archive(root):
    root = Path(root); original = path_in(root, 'STATE.md').read_bytes()
    directory = path_in(root, 'docs/state-archive'); directory.mkdir(parents=True, exist_ok=False)
    matches = list(re.finditer(rb'^#{1,6}[^\n]*?(20\d{2}-\d{2})[^\n]*$', original, re.M))
    boundaries = [(0, 'undated')] + [(m.start(), m[1].decode()) for m in matches if m.start() > 0]
    if matches and matches[0].start() == 0: boundaries[0] = (0, matches[0][1].decode())
    buffers = {}; parts = []
    for i, (start, month) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(original)
        payload = original[start:end]; prior = buffers.setdefault(month, bytearray())
        parts.append({'source_offset': start, 'month': month, 'archive_offset': len(prior),
                      'bytes': len(payload), 'sha256': digest(payload)})
        prior.extend(payload)
    for month, payload in buffers.items(): (directory / (month + '.md')).write_bytes(payload)
    manifest = {'version': 1, 'source': 'STATE.md', 'bytes': len(original), 'sha256': digest(original),
                'parts': parts, 'files': {month + '.md': digest(payload) for month, payload in sorted(buffers.items())}}
    (directory / 'MANIFEST.json').write_bytes(json.dumps(manifest, indent=2).encode() + b'\n')
    verify_archive(root)
    return manifest


def verify_archive(root):
    directory = path_in(root, 'docs/state-archive')
    manifest = json.loads((directory / 'MANIFEST.json').read_text()); pieces = []; offset = 0
    files = {name: path_in(directory, name).read_bytes() for name in manifest['files']}
    for name, payload in files.items():
        if digest(payload) != manifest['files'][name]: raise ValueError('historical archive changed: ' + name)
    for part in manifest['parts']:
        payload = files[part['month'] + '.md'][part['archive_offset']:part['archive_offset'] + part['bytes']]
        if part['source_offset'] != offset or len(payload) != part['bytes'] or digest(payload) != part['sha256']:
            raise ValueError('historical archive partition is inconsistent')
        pieces.append(payload); offset += len(payload)
    original = b''.join(pieces)
    if len(original) != manifest['bytes'] or digest(original) != manifest['sha256']:
        raise ValueError('historical narrative does not reconstruct byte for byte')
    return manifest


def brief(value, limit=280):
    if not isinstance(value, str): value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    value = re.sub(r'\s+', ' ', value).replace('|', '/').replace('`', "'").strip()
    return value if len(value) <= limit else value[:limit-1] + '…'


def render(root):
    root = Path(root); log, _ = events(root); history = verify_archive(root)
    inputs = {}; records = []; jobs = []
    def read(path):
        payload = path.read_bytes(); inputs[path.relative_to(root).as_posix()] = digest(payload)
        return json.loads(payload)
    policy = read(path_in(root, 'config/admission.json'))
    for path in sorted(root.glob('candidates/*/record.json')):
        path_in(root, path.relative_to(root).as_posix()); records.append((path.parent.name, read(path)))
    for path in sorted(root.glob('jobs/*.json')):
        path_in(root, path.relative_to(root).as_posix()); jobs.append((path.stem, read(path)))
    inputs['events'] = digest(canonical(log)); inputs['history'] = history['sha256']
    active = [(name, item) for name, item in jobs if item.get('status') != 'deleted']
    waiting = [(name, item) for name, item in records if item.get('awaiting_operator') is True
               or item.get('operator_decision_pending')]
    actionable = [(name, item) for name, item in records if item.get('status') not in ('published', 'dropped', 'parked')
                  and not item.get('awaiting_operator')]
    priority = {'packaged': 0, 'ready': 1, 'investigating': 2}
    actionable.sort(key=lambda pair: (priority.get(pair[1].get('status'), 3), pair[0]))
    lines = ['# Factory current state', '', '<!-- Generated by scripts/operational-state.py; do not hand-edit. -->',
             '', 'Input digest: `' + digest(canonical(inputs)) + '`.',
             'This is repository state, not a live provider query or publication approval. Run the check on resume.',
             '', '## Admission', '', '**Hold: ' + str(policy['hold']).lower() + '.** ' + brief(policy['reason'], 600),
             'No ordinary discovery/construction proceeds while held. Remediation requires its exact configured bundle pin.',
             '', '## Workers', '', f'Ledger entries not marked deleted: {len(active)}. Provider cleanup requires live readback.']
    for name, item in active[:8]:
        lines.append(f"- `{name}`: {brief(item.get('status'))}; expires {brief(item.get('expires'))}; `jobs/{name}.json`.")
    if len(active) > 8: lines.append(f'- {len(active)-8} additional entries: inspect `jobs/` before any launch.')
    lines += ['', '## Operator decisions', '', f'{len(waiting)} records request operator action; flags are claims, not approvals.']
    for name, item in waiting[:8]:
        lines.append(f"- `{name}`: {brief(item.get('next_action', 'Inspect candidate record'))} (`candidates/{name}/record.json`).")
    if len(waiting) > 8: lines.append(f'- {len(waiting)-8} additional decisions are recorded under `candidates/`.')
    lines += ['', '## Next work', '', 'Records below remain subject to the admission hold and current gate results.']
    for name, item in actionable[:8]:
        lines.append(f"- `{name}` ({brief(item.get('status'))}): {brief(item.get('next_action', 'Inspect candidate record'))}")
    if len(actionable) > 8: lines.append(f'- {len(actionable)-8} additional actionable records: inspect `candidates/`.')
    lines += ['', '## Recent recorded observations', '']
    for item in log[-5:][::-1]:
        lines.append(f"- {item['time']} / {brief(item['actor'], 60)} / {brief(item['kind'], 60)}: {brief(item['outcome'], 400)}")
        lines.append(f"  Evidence: `{brief(item['evidence'][0]['path'], 180)}`; event `{item['id']}`.")
    lines += ['', 'Full append-only observations: `events/`. Historical narrative: `docs/state-archive/`.',
              f"Archive reconstructs {history['bytes']:,} original bytes, SHA256 `{history['sha256']}`.",
              'Resilience implementation and acceptance: `docs/FACTORY-RESILIENCE-IMPLEMENTATION.md`.', '']
    payload = '\n'.join(lines).encode()
    if len(payload) >= LIMIT: raise ValueError('generated state exceeds 20 KB; reduce bounded view entries')
    return payload
