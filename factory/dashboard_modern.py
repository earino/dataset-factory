"""Map modern facts to existing dashboard components, retaining labelled history."""
from .site_state import snapshot, read_candidates, stamp, publication_matches


def collect(root, legacy_candidates, legacy_releases):
    try:
        rows = read_candidates(root)
    except Exception:
        rows = None
    modern = snapshot(root, rows=rows)
    if modern['status'] != 'ok':
        legacy_candidates = {**legacy_candidates, 'workflow': 'legacy',
                             'scope': 'Legacy history; modern state unavailable'}
        return legacy_candidates, legacy_releases, modern
    public = {r['id']: r for r in modern['candidates']}
    records, releases = [], []
    for row in rows or []:
        data = row['data']
        source = data.get('source') or {}
        source = source if isinstance(source, dict) else {}
        task = source.get('task') or {}
        evidence = data.get('evidence') or {}
        manifest = evidence.get('MANIFEST.json') or {}
        item = public.get(row['id'], {})
        # One dashboard refresh can race a newly inserted candidate. Include it
        # on the next refresh rather than mixing it with an earlier observation.
        if not item:
            continue
        state = row['stage']
        record = {'id': row['id'], 'dataset': source.get('dataset_id'), 'status': state,
                  'workflow': 'modern', 'country': source.get('country') or 'unknown',
                  'path': '.factory/pipeline.sqlite3', 'question': task.get('question', ''),
                  'target': task.get('target', ''), 'prediction_time': task.get('prediction_time', ''),
                  'split_strategy': task.get('split_policy', ''), 'domain': 'Modern factory',
                  'next_action': 'Stage ' + state,
                  'reason': row['reason'][:240], 'next_run_at': stamp(row['next_run']),
                  'release_splits': {k: {'rows': n} for k, n in manifest.get('rows', {}).items()},
                  'release_baseline': {'display': 'See versioned evaluation.json; public validation only'}
                                      if manifest else {},
                  'sources': [{'name': manifest.get('source', {}).get('publisher', ''),
                               'url': manifest.get('source', {}).get('documentation_url', '')}] if manifest else []}
        if record['reason']:
            record['next_action'] += ': ' + record['reason']
        if record['next_run_at']:
            record['next_action'] += ' · next attempt ' + record['next_run_at']
        if state == 'published':
            record['next_action'] = 'Dataset publication complete; website synchronization is shown in Releases.'
        records.append(record)
        if state == 'published' and publication_matches(data):
            receipt = data['publication']
            releases.append({'dataset': manifest['dataset'], 'detail_id': row['id'],
                             'release_tag': manifest['version'], 'artifact_version': manifest['artifact_version'],
                             'workflow': 'modern', 'published': True, 'disposition': 'public',
                             'rows': sum(manifest['rows'].values()), 'splits': record['release_splits'],
                             'assets': len(manifest['assets']), 'verified_all': True,
                             'verified': {'github': True, 'huggingface': True},
                             'verified_at': stamp(row['updated']),
                             'baseline_display': record['release_baseline']['display'],
                             'destinations': {p: receipt[p]['url'] for p in ('github', 'huggingface')}})
    modern_keys = {(r['dataset'], r['release_tag']) for r in releases}
    releases += [{**r, 'workflow': 'legacy',
                  'publication_note': 'Legacy history. ' + r.get('publication_note', '')}
                 for r in legacy_releases['releases'] if (r['dataset'], r['release_tag']) not in modern_keys]
    active = [r for r in records if r['status'] in ('discover', 'build', 'evaluate', 'publish')]
    candidates = {'workflow': 'modern', 'scope': 'Modern factory', 'counts': modern['counts'],
                  'live': active, 'errors': [], 'countries': {}, 'non_us_share': None,
                  'release': {'pending': [], 'awaiting': [], 'packaged': []},
                  'records': records + [{**r, 'workflow': 'legacy'} for r in legacy_candidates['records']],
                  'legacy_counts': legacy_candidates['counts']}
    return candidates, {'releases': releases, 'errors': legacy_releases['errors']}, modern


def admission_tokens(decision):
    return decision.get('normal_operation_tokens_last_7_days', decision.get('research_tokens_last_7_days'))
