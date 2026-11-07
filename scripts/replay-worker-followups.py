#!/usr/bin/env python3
"""Conservative offline policy replay of recorded worker follow-up commits.

Eligibility is not a historical live-provider claim. Every eligible replay still
requires the same current staging and provider checks before a model can be skipped.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.common import FactoryError
from factory.reconciliation import terminal


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def replay(revision, since, until):
    if not re.fullmatch(r'[0-9a-f]{40}', revision): raise ValueError('replay revision must be a full SHA')
    identifiers = {Path(p).stem for p in git('ls-tree', '-r', '--name-only', revision, '--', 'jobs').decode().splitlines()}
    records = git('log', revision, '--since=' + since, '--until=' + until,
                  '--format=%H%x00%an%x00%aI%x00%s').decode().splitlines()
    sessions = []
    for line in records:
        commit, actor, stamp, subject = line.split('\0', 3)
        if 'Scout' not in actor or not re.search(r'follow-up', subject, re.I): continue
        files = git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()
        if 'STATE.md' not in files: continue
        parent = git('rev-parse', commit + '^').decode().strip()
        diff = git('diff', parent, commit, '--', 'STATE.md')
        added = '\n'.join(line[1:] for line in diff.decode().splitlines() if line.startswith('+') and not line.startswith('+++'))
        text = subject + '\n' + added
        names = [name for name in sorted(identifiers)
                 if re.search(r'(?<![a-z0-9-])' + re.escape(name) + r'(?![a-z0-9-])', text)]
        jobs = []
        for name in names:
            item = {'job': name, 'already_recorded_terminal': False}
            try:
                payload = git('show', parent + ':jobs/' + name + '.json'); record = json.loads(payload)
                item.update(ledger_sha256=hashlib.sha256(payload).hexdigest(), status=record.get('status'))
                terminal(record, name, {'project': record['project']})
                item['already_recorded_terminal'] = True
            except (subprocess.CalledProcessError, FactoryError, KeyError, ValueError) as exc:
                item['reason'] = 'No committed parent ledger' if isinstance(exc, subprocess.CalledProcessError) else str(exc)[:200]
            jobs.append(item)
        eligible = bool(jobs and files == ['STATE.md'] and all(j['already_recorded_terminal'] for j in jobs))
        sessions.append({'commit': commit, 'parent': parent, 'actor': actor, 'time': stamp,
                         'subject': subject[:160], 'subject_sha256': hashlib.sha256(subject.encode()).hexdigest(),
                         'state_diff_sha256': hashlib.sha256(diff).hexdigest(), 'changed_paths': files,
                         'jobs': jobs, 'eligible_if_live_checks_pass': eligible,
                         'decision': 'Mechanical verification can replace this bookkeeping-only session' if eligible
                         else 'Retain model: substantive edits, new/incomplete outcomes or ambiguous job context'})
    return {'version': 1, 'revision': revision, 'since': since, 'until': until,
            'scope': 'Recorded Scout follow-up commits with STATE edits; parent ledger replay, not a complete scheduler-event archive',
            'historical_provider_verification': 'Not rerun; eligibility is conditional on mandatory live checks',
            'sessions': sessions, 'session_count': len(sessions),
            'eligible_if_live_checks_pass': sum(s['eligible_if_live_checks_pass'] for s in sessions),
            'actual_model_sessions_saved': None,
            'mandatory_live_checks': ['Exact committed ledger unchanged', 'Local result agrees if present',
                                      'Staging release tag, membership, sizes and digests',
                                      'Exact server absent, job-label servers absent, job IPs absent'],
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True); parser.add_argument('--since', required=True)
    parser.add_argument('--until', required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = replay(args.revision, args.since, args.until)
    payload = (json.dumps(result, indent=2) + '\n').encode()
    if len(payload) >= 256 * 1024: raise ValueError('replay report exceeds compact evidence limit')
    with args.output.open('xb') as stream: stream.write(payload)
    print(json.dumps({k: result[k] for k in ('session_count', 'eligible_if_live_checks_pass', 'actual_model_sessions_saved')}))


if __name__ == '__main__': main()
