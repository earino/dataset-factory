"""Verify a pinned Hub commit and create immutable tags, without downloading bulk data.

The client is injected so refusal paths can be tested without credentials or network.
"""
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import PurePosixPath, Path

SMALL_LIMIT = 256 * 1024
TOTAL_SMALL_LIMIT = 2 * 1024 * 1024


class HubIntegrityError(ValueError):
    """A remote release cannot be proved to match its declared bytes or revision."""


def value(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, Mapping) else getattr(obj, key, default)


def refs(api, repo_id):
    result = api.list_repo_refs(repo_id, repo_type='dataset')
    tags = {r.name: r.target_commit for r in (result.tags or [])}
    main = next((r.target_commit for r in (result.branches or []) if r.name == 'main'), None)
    if not isinstance(main, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', main):
        raise HubIntegrityError('Hub main has no full commit identity')
    return main, tags


def verify_revision(api, repo_id, expected, revision, read_small, worker_receipt=None):
    """LFS SHA-256 or bounded small-file bytes; size-only evidence never passes.

    read_small(path, commit, limit) must return at most limit bytes. CSVs and other bulk
    formats without LFS digests are refused: verification belongs on the worker.
    """
    if not expected:
        raise HubIntegrityError('manifest has no expected Hub assets')
    info = api.repo_info(repo_id, repo_type='dataset', revision=revision, files_metadata=True)
    commit = value(info, 'sha')
    if not isinstance(commit, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit):
        raise HubIntegrityError('Hub metadata has no full commit identity')
    if re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', revision) and revision != commit:
        raise HubIntegrityError('Hub metadata identifies a different commit')
    if worker_receipt is not None and (worker_receipt.get('repo') != repo_id
            or worker_receipt.get('commit') != commit or worker_receipt.get('ok') is not True):
        raise HubIntegrityError('worker evidence identifies a different repository or commit')
    siblings = {s.rfilename: s for s in (info.siblings or [])}
    present, missing, mismatched, unverified = [], [], [], []
    small_total = 0
    for path, (size, digest) in sorted(expected.items()):
        if (not isinstance(path, str) or not path or path.startswith('/')
                or any(p in ('', '.', '..') for p in path.split('/'))
                or '\\' in path or any(ord(c) < 32 for c in path)
                or type(size) is not int or size < 0
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise HubIntegrityError('manifest has an invalid Hub asset declaration')
        sibling = siblings.get(path)
        if sibling is None:
            missing.append(path)
            continue
        if value(sibling, 'size') != size:
            mismatched.append({'path': path, 'reason': 'remote size missing or differs'})
            continue
        lfs_digest = value(value(sibling, 'lfs') or {}, 'sha256')
        if lfs_digest:
            actual = lfs_digest
        elif worker_receipt is not None:
            evidence = worker_receipt.get('files', {}).get(path, {})
            blob_id = value(sibling, 'blob_id')
            if (not isinstance(blob_id, str) or not re.fullmatch(r'[0-9a-f]{40}', blob_id)
                    or evidence.get('blob_id') != blob_id or evidence.get('bytes') != size
                    or evidence.get('sha256') != digest):
                mismatched.append({'path': path, 'reason': 'worker evidence differs from pinned Hub blob'})
                continue
            actual = evidence['sha256']
        else:
            if (PurePosixPath(path).suffix.lower() not in ('.json', '.md', '.txt')
                    or size > SMALL_LIMIT or small_total + size > TOTAL_SMALL_LIMIT):
                unverified.append(path)
                continue
            small_total += size
            content = read_small(path, commit, size)
            if not isinstance(content, bytes) or len(content) != size:
                mismatched.append({'path': path, 'reason': 'downloaded size differs'})
                continue
            actual = hashlib.sha256(content).hexdigest()
        if actual != digest:
            mismatched.append({'path': path, 'reason': 'SHA-256 differs'})
        else:
            present.append(path)
    status = 'failed' if missing or mismatched else ('incomplete' if unverified else 'verified')
    return {'ok': status == 'verified', 'status': status,
            'commit': commit, 'repo_private': info.private,
            'digest_verified': present,
            'files': {'present': present, 'missing': missing, 'size_mismatch': mismatched,
                      'digest_unverified': unverified}}


def tag_verified_commit(api, repo_id, tag, verification):
    """No delete path. A tag is created only at the exact verified current main commit."""
    if verification.get('ok') is not True:
        raise HubIntegrityError('refusing to tag: asset verification did not pass')
    commit = verification.get('commit')
    main, tags = refs(api, repo_id)
    if commit != main:
        raise HubIntegrityError('main changed after verification; verify the new head before tagging')
    if tag in tags and tags[tag] != commit:
        raise HubIntegrityError('existing release tag names another commit; preserve it and use a new reviewed version')
    created = tag not in tags
    if created:
        # Do not swallow API errors as "tag absent" or delete a concurrent writer's tag.
        api.create_tag(repo_id, tag=tag, revision=commit, repo_type='dataset', exist_ok=False)
    after_main, after_tags = refs(api, repo_id)
    if after_tags.get(tag) != commit or after_main != commit:
        raise HubIntegrityError('tag/main changed during tagging; preserved all tags, inspect remote refs')
    return {'tagged': tag, 'tag_created': created, 'tag_commit': commit,
            'main_commit': after_main, 'tag_matches_main': True}


def load_worker_receipt(root, job_id, repo_id, expected):
    """Accept only a collected successful worker result whose declared assets match this release.

    The existing coordinator job ledger/collection mechanism supplies provenance; arbitrary
    supplied JSON reports are not accepted as authority. Remote commit/blob identities are
    independently compared by verify_revision before this evidence can count.
    """
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', job_id or ''):
        raise HubIntegrityError('invalid worker job identifier')
    root = Path(root).resolve()
    path = root / 'jobs' / (job_id + '.json')
    if path.is_symlink() or path.parent.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise HubIntegrityError('worker ledger record is unsafe or oversized')
    record = json.loads(path.read_text())
    report = record.get('result') or {}
    job = record.get('job') or {}
    spec = job.get('hf_publish') or {}
    if (record.get('status') not in ('collected', 'deleted') or not record.get('collected_at')
            or job.get('id') != job_id or report.get('job_id') != job_id
            or report.get('status') != 'succeeded' or report.get('uploaded') is not True
            or spec.get('repo') != repo_id or (report.get('hf_loading') or {}).get('ok') is not True
            or (report.get('hf_publish') or {}).get('failures')):
        raise HubIntegrityError('require a collected successful publishing job with a passing loading check')
    assets = spec.get('assets') or []
    declared = {a['target']: (a['size'], a['sha256']) for a in assets}
    if len(declared) != len(assets) or declared != expected:
        raise HubIntegrityError('worker job assets differ from this release manifest')
    receipt = report.get('hf_verification') or {}
    if (receipt.get('schema_version') != 1 or receipt.get('ok') is not True
            or receipt.get('repo') != repo_id or set(receipt.get('files') or {}) != set(expected)):
        raise HubIntegrityError('worker job has no complete pinned verification receipt; preserve legacy reports')
    return receipt
