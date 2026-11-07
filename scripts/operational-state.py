#!/usr/bin/env python3
"""Record observations, preserve historical prose and generate the small state view."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.operational_state import append, archive, events, render, verify_archive


def immutable_history(root, base):
    if not re.fullmatch(r'[0-9a-f]{40}', base): raise ValueError('history base must be a full commit SHA')
    if base == '0' * 40: return  # GitHub uses zero for a newly created branch.
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', base, '--',
                                     'events', 'docs/state-archive'], cwd=root, text=True).splitlines()
    for name in names:
        old = subprocess.check_output(['git', 'show', base + ':' + name], cwd=root)
        path = root / name
        if path.is_symlink() or not path.is_file(): raise ValueError('historical evidence removed: ' + name)
        new = path.read_bytes()
        if (not new.startswith(old) if name.startswith('events/') else new != old):
            raise ValueError('historical evidence rewritten: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--append', type=Path, help='JSON observation; an identical stable ID is a no-op')
    action.add_argument('--archive', action='store_true', help='One-time exact narrative archive; refuses existing archive')
    action.add_argument('--render', action='store_true', help='Refresh STATE.md from current records and observations')
    action.add_argument('--check', action='store_true', help='Verify history, event chain and generated view freshness')
    parser.add_argument('--base', help='Also refuse event rewrites and archive changes relative to this commit')
    args = parser.parse_args()
    try:
        if args.archive:
            committed = subprocess.check_output(['git', 'show', 'HEAD:STATE.md'], cwd=ROOT)
            if (ROOT / 'STATE.md').read_bytes() != committed:
                raise ValueError('commit the complete narrative before archiving it')
            value = archive(ROOT)
            print(json.dumps({'archived_bytes': value['bytes'], 'sha256': value['sha256']}))
        elif args.append:
            event = json.loads(args.append.read_text())
            # A syntactically valid but nonexistent commit cannot back an observation.
            if not re.fullmatch(r'[0-9a-f]{40}', event.get('commit', '')):
                raise ValueError('event commit must be a full SHA')
            subprocess.check_call(['git', 'cat-file', '-e', event['commit'] + '^{commit}'], cwd=ROOT)
            print(json.dumps({'appended': append(ROOT, event)}))
        elif args.render:
            payload = render(ROOT)
            path = ROOT / 'STATE.md'
            if path.is_symlink(): raise ValueError('STATE.md is a symlink')
            path.write_bytes(payload)
            print(json.dumps({'state_bytes': len(payload)}))
        else:
            events(ROOT); verify_archive(ROOT)
            if (ROOT / 'STATE.md').read_bytes() != render(ROOT):
                raise ValueError('STATE.md is stale or hand-edited; run --render after updating records/events')
            if args.base: immutable_history(ROOT, args.base)
            print(json.dumps({'ok': True, 'state_bytes': (ROOT / 'STATE.md').stat().st_size}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)})); return 1


if __name__ == '__main__': raise SystemExit(main())
