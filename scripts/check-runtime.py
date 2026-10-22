#!/usr/bin/env python3
"""Check reviewed runtime files and live copies without exporting their contents or running them.

--source-only checks the versioned recovery inventory in CI.
--home /opt/data additionally checks deployed shims/custom skills and profile skill shadows.
A mismatch is an inspection task, never permission to overwrite the live file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 256 * 1024


class RuntimeContractError(Exception):
    pass


def contained(root, relative):
    if (not isinstance(relative, str) or not relative or relative.startswith('/')
            or any(p in ('', '.', '..') for p in relative.split('/'))):
        raise RuntimeContractError('invalid relative inventory path')
    path = root / relative
    for entry in (path, *path.parents):
        if entry.is_symlink():
            raise RuntimeContractError('inventory path contains a symlink')
        if entry == root:
            break
    return path


def digest(path):
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise RuntimeContractError('missing, non-regular or oversized file')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract(root):
    path = contained(root, 'ops/runtime-files.json')
    try:
        if path.stat().st_size > LIMIT:
            raise RuntimeContractError('runtime inventory is oversized')
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        raise RuntimeContractError('cannot read ops/runtime-files.json') from None
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise RuntimeContractError('unsupported runtime inventory')
    entries = data.get('files')
    if not isinstance(entries, list) or not entries:
        raise RuntimeContractError('runtime inventory has no files')
    sources, destinations = set(), set()
    for row in entries:
        if not isinstance(row, dict) or set(row) != {'source', 'target', 'sha256'}:
            raise RuntimeContractError('invalid runtime file entry')
        source, target = row['source'], row['target']
        contained(root, source)
        contained(root, target)  # syntax check; live containment is checked before any read
        if not source.startswith(('ops/shims/', 'ops/skills/')) or not target.startswith(('scripts/', 'skills/')):
            raise RuntimeContractError('runtime file outside reviewed shim/skill roots')
        if source in sources or target in destinations:
            raise RuntimeContractError('duplicate source or target in runtime inventory')
        if not isinstance(row['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256']):
            raise RuntimeContractError('invalid runtime file digest')
        sources.add(source); destinations.add(target)
    reviewed = set()
    for folder in (root / 'ops/shims', root / 'ops/skills'):
        for candidate in folder.rglob('*'):
            if candidate.is_symlink():
                raise RuntimeContractError('reviewed runtime tree contains a symlink')
            if candidate.is_file() and candidate != folder / 'README.md':
                reviewed.add(candidate.relative_to(root).as_posix())
    if sources != reviewed:
        raise RuntimeContractError('runtime inventory does not cover exactly the reviewed files')
    project_files = data.get('project_skills')
    if not isinstance(project_files, list) or not project_files:
        raise RuntimeContractError('runtime inventory has no reviewed project skills')
    project_sources = set()
    for row in project_files:
        if not isinstance(row, dict) or set(row) != {'source', 'sha256'}:
            raise RuntimeContractError('invalid project skill entry')
        contained(root, row['source'])
        if (not row['source'].startswith('skills/') or row['source'] in project_sources
                or not isinstance(row['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256'])):
            raise RuntimeContractError('invalid or duplicate project skill identity')
        project_sources.add(row['source'])
    expected_sources = {p.relative_to(root).as_posix() for p in (root/'skills').rglob('*')
                        if p.is_file() and p.suffix in ('.md', '.py')}
    if expected_sources != project_sources:
        raise RuntimeContractError('inventory does not cover exactly the project skill procedures/code')
    return entries, project_files


def audit(root, home=None, project=None):
    root = Path(root).resolve()
    problems, checked = [], 0
    try:
        rows, project_files = contract(root)
    except RuntimeContractError as exc:
        return {'ok': False, 'scope': 'source', 'checked_files': 0, 'problems': [str(exc)]}
    for row in rows:
        for scope, base, relative in [('source', root, row['source'])] + (
                [('deployed', Path(home).resolve(), row['target'])] if home is not None else []):
            try:
                actual = digest(contained(base, relative))
                checked += 1
                if actual != row['sha256']:
                    problems.append(f'{scope}:{relative}: digest differs from reviewed inventory')
            except (RuntimeContractError, OSError):
                problems.append(f'{scope}:{relative}: missing, unsafe or oversized file')
    for row in project_files:
        for scope, base in [('source', root)] + ([('project', Path(project).resolve())] if project is not None else []):
            try:
                actual = digest(contained(base, row['source']))
                checked += 1
                if actual != row['sha256']:
                    problems.append(f"{scope}:{row['source']}: differs from reviewed inventory")
            except (RuntimeContractError, OSError):
                problems.append(f"{scope}:{row['source']}: missing, unsafe or oversized file")
    if home is not None:
        # A duplicate profile skill can make a model load a different gate procedure even when
        # the repository itself is unchanged. No precedence assumptions or automatic repair.
        profiles = Path(home).resolve() / 'skills'
        if profiles.is_symlink():
            problems.append('deployed:skills: symlink root requires explicit inspection')
        elif profiles.is_dir():
            external = {p.name for p in (root / 'skills').iterdir() if (p / 'SKILL.md').is_file()}
            for path in profiles.rglob('*'):
                if path.name in external and (path / 'SKILL.md').is_file():
                    problems.append(f'deployed:skills: profile copy shadows project skill {path.name}')
    return {'ok': not problems, 'scope': 'source+deployed' if home is not None else 'source',
            'project_skills_checked': project is not None,
            'checked_files': checked, 'problems': problems,
            'next_action': 'inspect differences; do not overwrite live files automatically' if problems else
                           'reviewed file copies agree; schedules, credentials and runtime behavior are separate checks'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--source-only', action='store_true')
    modes.add_argument('--home', type=Path)
    parser.add_argument('--project', type=Path,
                        help='live project checkout (default: <home>/dataset-factory)')
    args = parser.parse_args(argv)
    if args.source_only and args.project:
        parser.error('--project requires --home')
    project = args.project or (args.home / 'dataset-factory' if args.home else None)
    result = audit(ROOT, args.home, project)
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
