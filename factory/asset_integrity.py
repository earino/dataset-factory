"""Verify every release asset, including assets omitted from package_files.

External mode proves metadata agreement only. It never claims to have inspected
absent data and cannot exempt a locally present, altered file from hashing.
"""
import ast
import hashlib
from pathlib import Path
import re

HEX = re.compile(r'[0-9a-f]{64}')


def safe_path(root, name):
    if not isinstance(name, str) or not name or name.startswith('/') or any(
            part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('unsafe asset path')
    path = root / name
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('asset path is a symlink')
        if part == root:
            break
    return path


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checksums(path):
    result = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not HEX.fullmatch(parts[0]):
            raise ValueError('malformed SHA256SUMS line')
        name = parts[1].strip().removeprefix('*')
        if name in result:
            raise ValueError('duplicate SHA256SUMS entry: ' + name)
        result[name] = parts[0]
    return result


def check(package, manifest, *, external_assets=False, require_loader=True):
    package = Path(package)
    problems, notes = [], []
    try:
        assets, files = manifest.get('assets'), manifest.get('files')
        if not isinstance(assets, dict) or not assets or not isinstance(files, dict):
            raise ValueError('manifest assets/files must be nonempty objects')
        if set(assets) != set(files):
            problems.append('Manifest assets and files inventories differ')
        sums = checksums(safe_path(package, 'SHA256SUMS'))
        used, aliases = set(), set()
        for name, entry in assets.items():
            path = safe_path(package, name)
            if not isinstance(entry, dict):
                raise ValueError('invalid asset record: ' + name)
            digest, size = entry.get('sha256'), entry.get('bytes')
            if not isinstance(digest, str) or not HEX.fullmatch(digest) or type(size) is not int or size < 0:
                raise ValueError('invalid asset digest/size: ' + name)
            other = files.get(name, {})
            if other.get('sha256') != digest or other.get('bytes') != size:
                problems.append(name + ': asset digest/size disagrees with files inventory')
            alias = entry.get('asset_name')
            if not isinstance(alias, str) or not alias or '/' in alias or alias in aliases:
                raise ValueError('invalid or duplicate flat asset name')
            aliases.add(alias)
            matches = [key for key in set((name, alias)) if key in sums]
            if len(matches) != 1:
                problems.append(name + ': must have exactly one checksum entry')
            for key in matches:
                used.add(key)
                if sums[key] != digest:
                    problems.append(name + ': checksum disagrees with release asset digest')
            if path.is_file():
                if path.stat().st_size != size or sha256(path) != digest:
                    problems.append(name + ': actual release asset bytes disagree with manifest')
            elif external_assets and (name.endswith('.csv') or path.name in ('meta.json', 'quality.json')):
                notes.append(name + ': external asset metadata only; bytes NOT verified here')
            else:
                problems.append(name + ': release asset is absent; full verification requires its bytes')
        if set(sums) != used:
            problems.append('SHA256SUMS has unrecognized or duplicate logical asset coverage')

        # Read literals only; a loader must never run during package inspection.
        loader = safe_path(package, 'get_dataset.py')
        literals = {}
        for node in ast.parse(loader.read_text()).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ('EXPECTED', 'LAYOUT', 'TAG'):
                        literals[target.id] = ast.literal_eval(node.value)
        expected = {entry['asset_name']: {'bytes': entry['bytes'], 'sha256': entry['sha256']}
                    for entry in assets.values()}
        layout = {entry['asset_name']: name for name, entry in assets.items()}
        if 'EXPECTED' in literals or require_loader:
            if literals.get('EXPECTED') != expected:
                problems.append('get_dataset.py EXPECTED differs from accepted asset digests/sizes')
            if literals.get('LAYOUT') != layout:
                problems.append('get_dataset.py LAYOUT differs from manifest logical assets')
            if literals.get('TAG') != manifest.get('release_tag'):
                problems.append('get_dataset.py TAG differs from manifest release tag')
    except (OSError, ValueError, TypeError, AttributeError, SyntaxError, KeyError) as exc:
        problems.append('Asset integrity inspection incomplete: ' + str(exc))
    return problems, notes
