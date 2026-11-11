"""Read modern factory state without creating it or changing candidate state.

The private rows are for local publication adapters. Only ``snapshot`` is suitable
for public dashboard output; it deliberately does not serialize candidate data.
"""
from datetime import datetime, timezone
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value else None


def read_candidates(root):
    """Return a consistent read-only view, including attempts, or raise on no data."""
    path = Path(root).resolve() / '.factory/pipeline.sqlite3'
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError('Modern pipeline database is unavailable')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        rows = [dict(row) for row in db.execute('SELECT * FROM candidates ORDER BY created,id')]
        attempts = {}
        for row in db.execute('SELECT * FROM attempts ORDER BY started,id'):
            attempts.setdefault(row['candidate'], []).append(dict(row))
        for row in rows:
            row['data'] = json.loads(row['data'])
            row['attempts'] = attempts.get(row['id'], [])
        return rows


def publication_matches(data):
    """A published stage alone is insufficient evidence of public release identity."""
    manifest = data.get('evidence', {}).get('MANIFEST.json', {})
    receipt = data.get('publication', {})
    if not manifest or receipt.get('ok') is not True:
        return False
    if any(receipt.get(key) != manifest.get(key) for key in ('dataset', 'version', 'artifact_version')):
        return False
    consumers = receipt.get('consumers', {})
    if set(consumers) != {'github', 'huggingface'}:
        return False
    return all(c.get('ok') is True and c.get('authentication') == 'none'
               and c.get('version') == manifest['version']
               and c.get('repo') == receipt.get(platform, {}).get('repo')
               and bool(c.get('repo')) and c.get('rows_loaded') == manifest.get('rows')
               for platform, c in consumers.items())


def snapshot(root):
    """Compact public projection; errors do not impersonate an empty factory."""
    observed = datetime.now(timezone.utc).isoformat()
    result = {'source': '.factory/pipeline.sqlite3', 'observed_at': observed,
              'status': 'unavailable', 'candidates': [], 'counts': None}
    try:
        rows = read_candidates(root)
        counts = {}
        candidates = []
        for row in rows:
            counts[row['stage']] = counts.get(row['stage'], 0) + 1
            data = row['data']
            source = data.get('source') or {}
            if not isinstance(source, dict):
                source = {}
            attempts = row['attempts']
            last = attempts[-1] if attempts else {}
            item = {'id': row['id'], 'dataset': source.get('dataset_id'),
                    'stage': row['stage'], 'created_at': stamp(row['created']),
                    'updated_at': stamp(row['updated']), 'next_run_at': stamp(row['next_run']),
                    'running': any(a['status'] == 'running' for a in attempts),
                    'attempt': {k: last.get(k) for k in ('id', 'stage', 'status', 'ordinal')},
                    'published_verified': row['stage'] == 'published' and publication_matches(data)}
            if item['published_verified']:
                receipt = data['publication']
                item['publication'] = {k: receipt[k] for k in ('dataset', 'version', 'artifact_version')}
                item['publication']['repositories'] = {
                    p: receipt[p]['repo'] for p in ('github', 'huggingface')}
            candidates.append(item)
        result.update(status='ok', candidates=candidates, counts=counts)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        # Raw exception text may contain stored/private data. The operator can
        # inspect the local database; the public page needs only input health.
        result['error'] = 'Modern pipeline state could not be read'
    return result
