#!/usr/bin/env python3
"""Archive pinned original package documents offline, without reading dataset rows."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.asset_integrity import safe_path, sha256


def prepare(source, plan, output):
    source = Path(source); output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'audit-evidence-owner.json').write_text(json.dumps({
        'owner': 'dataset-factory/prepare-blocked-audit', 'version': 1}) + '\n')
    inventory = {'version': 1, 'scope': 'Original manifest-bound code and documents only; no row reads', 'datasets': []}
    for entry in plan['datasets']:
        dataset = entry['dataset']; package = safe_path(source, dataset + '/repository')
        manifest_path = safe_path(package, 'MANIFEST.json')
        if sha256(manifest_path) != entry['manifest_sha256']:
            raise ValueError('original manifest differs from independent audit: ' + dataset)
        manifest = json.loads(manifest_path.read_text())
        if manifest['dataset'] != dataset or manifest['artifact_version'] != entry['artifact_version']:
            raise ValueError('original package identity differs from independent audit')
        names = dict(manifest['package_files'], **{'MANIFEST.json': entry['manifest_sha256']})
        members = []; archive_path = safe_path(output, dataset + '.tar')
        with tarfile.open(archive_path, 'x:') as archive:
            for name, expected in sorted(names.items()):
                if Path(name).suffix.lower() not in ('.md', '.txt', '.json', '.py', '.sh') and name != 'SHA256SUMS':
                    raise ValueError('only compact code/documents may enter the coordinator archive: ' + name)
                path = safe_path(package, name)
                if path.stat().st_size >= 256 * 1024:
                    raise ValueError('original document exceeds compact input limit: ' + name)
                payload = path.read_bytes(); digest = hashlib.sha256(payload).hexdigest()
                expected = expected if isinstance(expected, str) else expected['sha256']
                if digest != expected:
                    raise ValueError('original package file changed: ' + name)
                member = tarfile.TarInfo(name); member.size = len(payload); member.mode = 0o600
                archive.addfile(member, io.BytesIO(payload))
                members.append({'member': name, 'path': name, 'size': len(payload), 'sha256': digest})
        if archive_path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError('original document archive exceeds bounded transfer limit')
        inventory['datasets'].append(dict(entry, archive=archive_path.name,
            size=archive_path.stat().st_size, sha256=sha256(archive_path), members=members))
    payload = json.dumps(inventory, indent=2) + '\n'
    if len(payload.encode()) >= 256 * 1024:
        raise ValueError('original document inventory exceeds collection limit')
    (output / 'inventory.json').write_text(payload)
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('plan', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args(); result = prepare(args.source, json.loads(args.plan.read_text()), args.output)
    print(json.dumps({'datasets': len(result['datasets']),
                      'archive_bytes': sum(d['size'] for d in result['datasets']), 'bulk_data_read': False}))


if __name__ == '__main__':
    main()
