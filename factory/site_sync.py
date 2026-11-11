"""One deterministic, bounded catch-up pass for modern published dataset websites."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import time

from .site_github import GitHub
from .site_model import digest, dump, read, require
from .site_modern import project
from .site_pipeline import Hub, ROOT, prepare_record, load_bundle, reconcile, verify
from .site_state import read_candidates, publication_matches


def release_record(candidate, config, gh):
    data = candidate['data']
    require(publication_matches(data), 'Published candidate lacks matching public verification')
    receipt = data['publication']
    repo, tag = receipt['github']['repo'], receipt['version']
    manifest = json.loads(gh.file(repo, 'MANIFEST.json', ref=tag))
    require(manifest == data['evidence']['MANIFEST.json'], 'Pinned public manifest differs from accepted evidence')
    documents = {name: gh.file(repo, name, ref=tag).encode()
                 for name in ('README.md', 'evaluation.json', 'LICENSE.md')}
    # The successful publish attempt is stable even if later bookkeeping changes updated.
    finished = [a['finished'] for a in candidate['attempts']
                if a['stage'] == 'publish' and a['status'] == 'done' and a['finished']]
    published = max(finished) if finished else candidate['updated']
    released = datetime.fromtimestamp(published, timezone.utc).date().isoformat()
    record = project(manifest, receipt, documents, released, config)
    path = f".dataset-site/records/{record['dataset']}/{record['release_tag']}.json"
    previous = gh.file(config['catalog_repository'], path, missing_ok=True)
    if previous:
        previous = json.loads(previous)
        def content(value):
            return {k: v for k, v in value.items() if k not in ('site_revision', 'record_sha256')}
        record['site_revision'] = previous['site_revision'] + (content(previous) != content(record))
        record.pop('record_sha256')
        record['record_sha256'] = digest(dump(record))
    return record


def run(root=ROOT, seconds=300, gh=None, hub=None, clock=time.monotonic):
    """A failure affects one site; a restart resumes the same immutable bundle."""
    root = Path(root).resolve()
    gh, hub = gh or GitHub(), hub or Hub()
    folder = root / '.factory/sites'
    require(not folder.is_symlink(), 'Sites state folder cannot be a symlink')
    folder.mkdir(parents=True, exist_ok=True)
    summary = {'observed_at': datetime.now(timezone.utc).isoformat(), 'status': 'ok', 'releases': []}
    with (folder / 'sync.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {**summary, 'status': 'busy'}
        deadline = clock() + seconds
        config = read(root / 'config/sites.json')
        candidates = [c for c in read_candidates(root) if c['stage'] == 'published']
        prior = read(folder / 'status.json') if (folder / 'status.json').is_file() else {}
        outcomes = {r['candidate']: r for r in prior.get('releases', [])}
        candidates.sort(key=lambda c: outcomes.get(c['id'], {}).get('observed_at', ''))
        for candidate in candidates:
            if clock() >= deadline:
                summary['status'] = 'pending'
                break
            outcome = {'candidate': candidate['id'], 'status': 'failed',
                       'observed_at': datetime.now(timezone.utc).isoformat()}
            try:
                record = release_record(candidate, config, gh)
                outcome.update(dataset=record['dataset'], version=record['release_tag'])
                # Include implementation bytes: a renderer/workflow change gets a new
                # bundle without overwriting a previous plan or editorial edition.
                key = digest(dump(record) + (ROOT / 'sites/runtime.py').read_text()
                             + (ROOT / 'sites/pages.yml').read_text())[:24]
                bundle = folder / key
                prepare_record(record, config, bundle)
                plan = load_bundle(bundle)
                with (bundle / 'publish.lock').open('w') as publishing:
                    fcntl.flock(publishing, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    saved = read(bundle / 'receipt.json') if (bundle / 'receipt.json').is_file() else {}
                    if saved.get('status') == 'complete':
                        # Read back live state, but do not create commits or dispatches.
                        verify(plan, gh, hub)
                        result = saved
                    else:
                        result = reconcile(plan, bundle, gh, hub)
                outcome.update(status=result['status'], bundle=key,
                               plan_sha256=plan['plan_sha256'])
            except Exception as exc:
                # Never serialize raw SDK errors or candidate data into dashboard input.
                outcome['error'] = type(exc).__name__
            outcomes[candidate['id']] = outcome
        summary['releases'] = [outcomes[c['id']] for c in candidates if c['id'] in outcomes]
        if any(r['status'] == 'failed' for r in summary['releases']):
            summary['status'] = 'failed'
        elif any(r['status'] == 'pending' for r in summary['releases']):
            summary['status'] = 'pending'
        temporary = folder / 'status.json.tmp'
        temporary.write_text(dump(summary))
        temporary.replace(folder / 'status.json')
    return summary
