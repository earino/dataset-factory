"""Explicit publication authority, bound to current evidence on both destinations.

Records preserve an operator's words; they cannot authenticate who typed them.
A draft, historical record or passing audit alone never authorizes a flip.
"""
from copy import deepcopy
from contextlib import contextmanager
import fcntl
from datetime import datetime, timezone
from pathlib import Path
import re

from . import adversarial_execution as execution
from . import audit_workflow, release_audit
from .asset_integrity import safe_path, sha256
from .common import write_json
from .leakage_battery import digest

VERSION = 1


def require(condition, message):
    if not condition: raise ValueError(message)


def timestamp(value):
    require(isinstance(value, str), 'approval needs an actual timestamp')
    try: parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError: raise ValueError('invalid approval timestamp') from None
    require(parsed.tzinfo is not None and parsed <= datetime.now(timezone.utc),
            'approval timestamp must be timezone-aware and not in the future')
    return parsed


def evidence(root, value):
    require(isinstance(value, dict) and set(value) == {'path', 'sha256', 'quote'},
            'evidence needs a path, hash and exact quote')
    path = safe_path(Path(root), value['path'])
    require(path.stat().st_size < execution.LIMIT and sha256(path) == value['sha256'],
            'approval/review evidence changed or exceeds compact limit')
    quote = value['quote']
    require(isinstance(quote, str) and 0 < len(quote) <= 12000 and quote in path.read_text(),
            'approval/review quote is missing from its source')
    return value


def independent_review(root, dataset, binding):
    name = f'candidates/{dataset}/independent-audit.json'
    path = safe_path(root, name); review = execution.bounded_json(path)
    require(set(review) == {'schema_version', 'dataset', 'artifact_version', 'manifest_sha256',
                            'binding_digest', 'verdict', 'unresolved_findings', 'conditions',
                            'auditor', 'reviewed_at', 'report', 'operator_relay'},
            'independent review has an invalid schema')
    require(review['schema_version'] == VERSION and review['dataset'] == dataset
            and review['artifact_version'] == binding['artifact_version']
            and review['manifest_sha256'] == binding['manifest_sha256']
            and review['binding_digest'] == digest(binding), 'independent review names different bytes/evidence')
    require(review['verdict'] == 'pass' and review['unresolved_findings'] == []
            and review['conditions'] == [], 'independent review must have no unresolved findings or conditions')
    require(isinstance(review['auditor'], str) and review['auditor'].strip(), 'independent auditor is missing')
    timestamp(review['reviewed_at'])
    evidence(root, review['report']); evidence(root, review['operator_relay'])
    return {'path': name, 'sha256': sha256(path), 'report': review['report'],
            'operator_relay': review['operator_relay']}


def plan(root, dataset):
    root = Path(root)
    binding = release_audit.staged_binding(root, dataset)
    record = execution.bounded_json(root/f'candidates/{dataset}/record.json')
    require(audit_workflow.queue_ready(root, record), 'current passing autonomous audit is required')
    pointer = record['autonomous_audit']
    verdict = safe_path(root, pointer['directory'] + '/verdict.json')
    review = independent_review(root, dataset, binding)
    destinations = execution.bounded_json(root/f'release/{dataset}/DESTINATIONS.json')
    targets = {}
    for name, commit_key, tag_key in (('github', 'target_commit', 'release_tag'),
                                      ('huggingface', 'commit', 'revision')):
        entry = destinations['destinations'][name]
        targets[name] = {'repository': entry['repo'], 'commit': entry[commit_key],
                         'tag': entry[tag_key], 'from': 'private', 'to': 'public'}
    implementation = {name: sha256(root/name) for name in (
        'factory/publication.py', 'factory/publication_remote.py',
        'scripts/publish-dataset.py', 'scripts/hf-publish.py')}
    return {'schema_version': VERSION, 'dataset': dataset, 'release_tag': binding['release_tag'],
            'artifact_version': binding['artifact_version'], 'manifest_sha256': binding['manifest_sha256'],
            'binding': binding, 'targets': targets, 'independent_review': review,
            'autonomous_verdict': {'path': verdict.relative_to(root).as_posix(), 'sha256': sha256(verdict)},
            'implementation': implementation,
            'scope': 'Make these two existing staged repositories public; preserve every artifact, manifest and tag. Website publication is separate.'}


def review_plan(root, dataset):
    value = plan(root, dataset)
    return {'plan': value, 'plan_sha256': digest(value),
            'approval_status': 'not granted by this plan; record the operator response separately'}


def approval(root, dataset, current_plan):
    path = safe_path(Path(root), f'candidates/{dataset}/approval.json')
    value = execution.bounded_json(path)
    require(set(value) == {'schema_version', 'kind', 'dataset', 'release_tag', 'artifact_version',
                          'manifest_sha256', 'plan_sha256', 'independent_review_sha256',
                          'decision', 'waived_rules', 'operator', 'approved_at', 'operator_words', 'source'},
            'publication approval has an invalid schema; drafts/history are not authority')
    require(value['schema_version'] == VERSION and value['kind'] == 'publication_approval'
            and value['decision'] == 'approve_both_public' and value['waived_rules'] == [],
            'explicit approval for both destinations is required; hard gates cannot be waived')
    for key in ('dataset', 'release_tag', 'artifact_version', 'manifest_sha256'):
        require(value[key] == current_plan[key], 'approval names a different ' + key)
    require(value['plan_sha256'] == digest(current_plan)
            and value['independent_review_sha256'] == current_plan['independent_review']['sha256'],
            'publication plan or accepted independent verdict changed')
    approved_at = timestamp(value['approved_at'])
    review = execution.bounded_json(safe_path(Path(root), current_plan['independent_review']['path']))
    require(approved_at >= timestamp(review['reviewed_at']), 'approval predates the independent review')
    require(isinstance(value['operator'], str) and value['operator'].strip(), 'approval operator is missing')
    source = evidence(root, value['source'])
    require(value['operator_words'] == source['quote'], 'verbatim operator words must match source')
    # A transcript must actually contain the presented plan identity. Broad historical
    # standing instructions cannot be silently transplanted onto a new release.
    source_text = safe_path(Path(root), source['path']).read_text()
    require(value['plan_sha256'] in source_text, 'approval source must include the plan presented to the operator')
    return value


def approved_plan(root, dataset):
    # Refuse absent/draft authorization before network calls or mutation.
    path = safe_path(Path(root), f'candidates/{dataset}/approval.json')
    require(path.is_file(), 'explicit digest-bound publication approval is missing')
    value = execution.bounded_json(path)
    require(value.get('kind') == 'publication_approval' and value.get('decision') == 'approve_both_public',
            'an explicit publication approval is required')
    current = plan(root, dataset)
    approval(root, dataset, current)
    return current


def finish_recorded(root, dataset, previous, remote):
    """Recover only the final local write after already proven external visibility."""
    current = previous['plan']; binding = current['binding']
    require(current['dataset'] == dataset, 'saved publication identifies another dataset')
    require(previous['plan_sha256'] == digest(current), 'saved publication plan changed')
    require(sha256(root/f'candidates/{dataset}/approval.json') == previous['approval_sha256'],
            'completed publication approval changed')
    approval(root, dataset, current)
    require(independent_review(root, dataset, binding) == current['independent_review'],
            'independent review changed after publication')
    require(release_audit.implementation(root) == binding['implementation'], 'audited implementation changed')
    for name, expected in current['implementation'].items():
        require(sha256(safe_path(root, name)) == expected, 'publication implementation changed')
    package = root/'release'/dataset
    # External CSVs remain commit/digest-bound and are checked by the provider reader.
    for name, expected in binding['files'].items():
        if name == 'DESTINATIONS.json': continue
        path = safe_path(package, name)
        if name.endswith('.csv') and not path.exists(): continue
        require(sha256(path) == expected, 'published input changed: ' + name)
    for name, expected in binding['review_files'].items():
        from hashlib import sha256 as hash_bytes
        require(hash_bytes(release_audit.review_input(root, dataset, name)).hexdigest() == expected,
                'published review evidence changed')
    require(sha256(safe_path(root, current['autonomous_verdict']['path'])) == current['autonomous_verdict']['sha256'],
            'autonomous verdict changed')
    destination_path = package/'DESTINATIONS.json'
    require(execution.bounded_json(destination_path) == previous['public_destinations'],
            'completed destination record differs from the approved transition')
    proof = remote.inspect(anonymous=True)
    require(set(proof) == {'github', 'huggingface'} and all(
        p.get('private') is False and p.get('anonymous') is True and p.get('assets_verified') is True
        for p in proof.values()), 'anonymous publication readback failed')
    previous.update(completed=True, destinations_sha256=sha256(destination_path))
    write_json(root/f'candidates/{dataset}/publication-attempt.json', previous)
    return {'ok': True, 'dataset': dataset, 'already_completed': True,
            'receipt': f'candidates/{dataset}/publication-attempt.json'}


@contextmanager
def publication_lock(root, dataset):
    folder = safe_path(root, '.factory'); folder.mkdir(exist_ok=True)
    # Visibility verification can take minutes; never hold the worker/cleanup lock.
    path = safe_path(root, f'.factory/publication-{dataset}.lock')
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def execute(root, dataset, *, remote=None):
    """Resume one approved flip; never roll back visibility or alter a release tag.

    Keep DESTINATIONS private until both anonymous checks pass. The durable intent
    allows recovery when the first platform changed but the second call failed.
    """
    root = Path(root)
    # Syntax/path validation occurs before constructing a credential-using client.
    require(isinstance(dataset, str) and re.fullmatch('[a-z0-9][a-z0-9-]*', dataset), 'invalid dataset')
    with publication_lock(root, dataset):
        destination_path = safe_path(root, f'release/{dataset}/DESTINATIONS.json')
        receipt_path = safe_path(root, f'candidates/{dataset}/publication-attempt.json')
        previous = execution.bounded_json(receipt_path) if receipt_path.exists() else None
        if previous and previous.get('public_destinations') == execution.bounded_json(destination_path):
            if remote is None:
                from .publication_remote import Remote
                remote = Remote(root, dataset, previous['plan'])
            return finish_recorded(root, dataset, previous, remote)
        current = approved_plan(root, dataset)
        approval_sha = sha256(root/f'candidates/{dataset}/approval.json')
        identity = {'plan': current, 'plan_sha256': digest(current), 'approval_sha256': approval_sha}
        if previous:
            require(all(previous.get(k) == v for k, v in identity.items()), 'partial publication identity changed; reconcile before resuming')
        if remote is None:
            from .publication_remote import Remote
            remote = Remote(root, dataset, current)
        before = remote.inspect(anonymous=False)
        require(set(before) == {'github', 'huggingface'}, 'both destinations require readback')
        for name in before:
            require(type(before[name].get('private')) is bool, 'unknown destination visibility')
            require(previous is not None or before[name]['private'] is True,
                    'a destination was already public without this recorded flip intent')
        attempt = {**identity, 'schema_version': VERSION, 'completed': False,
                   'started_at': previous['started_at'] if previous else datetime.now(timezone.utc).isoformat(),
                   'before': before}
        write_json(receipt_path, attempt)  # persisted before the first external mutation
        for name in ('github', 'huggingface'):
            # Revalidate local evidence before each independent mutation.
            require(approved_plan(root, dataset) == current
                    and sha256(root/f'candidates/{dataset}/approval.json') == approval_sha,
                    'approval or artifact changed during publication')
            remote.inspect(anonymous=False)
            if before[name]['private']:
                remote.make_public(name)
        proof = remote.inspect(anonymous=True)
        require(set(proof) == {'github', 'huggingface'} and all(
            p.get('private') is False and p.get('anonymous') is True and p.get('assets_verified') is True
            for p in proof.values()), 'publication is incomplete: anonymous verification failed')
        require(approved_plan(root, dataset) == current
                and sha256(root/f'candidates/{dataset}/approval.json') == approval_sha,
                'local evidence changed before publication was recorded')
        destinations = execution.bounded_json(destination_path)
        changed = deepcopy(destinations)
        when = datetime.now(timezone.utc).isoformat()
        for name in proof:
            changed['destinations'][name].update(private=False, public=True, verified=True, verified_at=when,
                                                anonymous_verification=proof[name])
        changed['publication'] = {'published_at': when, 'plan_sha256': digest(current),
                                  'approval_sha256': approval_sha, 'anonymous_verified': True}
        # Record the proof before the visibility record. A crash here leaves an
        # incomplete attempt that can safely repeat readback with unchanged inputs.
        attempt.update(anonymous_proof=proof, verified_at=when, public_destinations=changed)
        write_json(receipt_path, attempt)
        write_json(destination_path, changed)
        attempt.update(completed=True, destinations_sha256=sha256(destination_path))
        write_json(receipt_path, attempt)
        return {'ok': True, 'dataset': dataset, 'receipt': receipt_path.relative_to(root).as_posix(),
                'next_action': 'Refresh current editorial card, LOADING.md, README and release notes; preserve frozen bytes and tags. Prepare the separate website plan for review.'}
