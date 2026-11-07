#!/usr/bin/env python3
"""Worker-only acceptance of pinned historical artifacts, without rebuilding them.

Old source archives are data: only explicitly pinned regular members are copied,
never imported or executed. The new gate and its dependencies come from the clean
reviewed bundle. Full prediction vectors stay in worker scratch, never a release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def contained(root, name):
    if not isinstance(name, str) or not name or name.startswith('/') or any(
            p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('unsafe historical path')
    path = root / name
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('historical path is a symlink')
        if parent == root:
            break
    return path


def verify(path, entry):
    if not path.is_file() or path.stat().st_size != entry['size'] or digest(path) != entry['sha256']:
        raise ValueError('historical input digest/size mismatch: ' + str(path))


def prepare(case, data, artifact):
    artifact.mkdir()
    for entry in case['files']:
        source = contained(data, entry['fetch_dest'])
        verify(source, entry)
        destination = contained(artifact, entry['path'])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError('duplicate historical destination')
        shutil.copyfile(source, destination)
    for source in case.get('archives', []):
        archive_path = contained(data, source['fetch_dest'])
        verify(archive_path, source)
        with tarfile.open(archive_path, 'r:') as archive:
            members = archive.getmembers()
            names = [m.name for m in members]
            if len(names) != len(set(names)):
                raise ValueError('duplicate archive member')
            for entry in source['members']:
                member = archive.getmember(entry['member'])
                if not member.isfile() or member.size != entry['size'] or member.size > 2 * 1024 * 1024:
                    raise ValueError('historical member must be a bounded regular file')
                # No extractall, links, permissions, executable imports or unlisted files.
                payload = archive.extractfile(member).read()
                if hashlib.sha256(payload).hexdigest() != entry['sha256']:
                    raise ValueError('historical member digest mismatch')
                destination = contained(artifact, entry['path'])
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ValueError('duplicate historical destination')
                destination.write_bytes(payload)


def write_report(path, value):
    payload = (json.dumps(value, sort_keys=True, indent=1, allow_nan=False) + '\n').encode()
    if len(payload) >= 256 * 1024:
        raise ValueError('report exceeds coordinator collection limit')
    path.write_bytes(payload)


def expectations(case, battery):
    actual = {(r['name'], r['split']): r for r in battery['exact']}
    results = []
    for expected in case['expectations']:
        result = actual.get((expected['name'], expected['split']))
        ok = bool(result and result['errors'] == 0 and result['covered'] >= expected['min_covered'])
        results.append({'expected': expected, 'observed': result, 'ok': ok})
    return results


def published_binding(case, artifact, registry):
    """A comparison mode must name an actually frozen release, not waive a new one."""
    binding=case['published_binding']
    entry=next((e for e in registry['releases'] if e['dataset']==binding['dataset']),None)
    manifest_path=contained(artifact,'package/MANIFEST.json')
    if (entry is None or digest(manifest_path)!=entry['manifest_sha256']
            or binding.get('manifest_sha256')!=entry['manifest_sha256']):
        raise ValueError('published comparison lacks an exact frozen manifest binding')
    manifest=json.loads(manifest_path.read_text())
    level=binding.get('level')
    version=manifest['levels'][level]['artifact_version'] if level else manifest['artifact_version']
    if version!=case['artifact_version'] or manifest['release_tag']!=entry['release_tag']:
        raise ValueError('published comparison artifact/level does not match frozen release')
    for name,expected in entry['editorial_files'].items():
        if digest(contained(artifact,'package/'+name))!=expected:
            raise ValueError('published comparison editorial bytes changed: '+name)
    return {'dataset':binding['dataset'],'level':level,'release_tag':entry['release_tag'],
            'manifest_sha256':entry['manifest_sha256'],'artifact_version':version,
            'disposition':'Frozen historical warnings for review only; never new-release clearance'}


def audit(case, data, output):
    import qualify_dataset as gate
    import leakage_battery as battery_module

    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = {'case': case['id'], 'artifact_version': case['artifact_version'],
              'scope': 'historical core artifact plus explicitly pinned original source members',
              'disposition': 'acceptance experiment only; no publication or requalification',
              'ok': False}
    try:
        with tempfile.TemporaryDirectory(prefix='historical-audit-') as temporary:
            scratch = Path(temporary)
            artifact = scratch / 'artifact'
            prepare(case, data, artifact)
            mode=case.get('mode','recovery_acceptance')
            if mode not in ('recovery_acceptance','published_comparison'):
                raise ValueError('unknown historical audit mode')
            if mode=='published_comparison':
                registry=json.loads(Path(__file__).with_name('frozen-releases.json').read_text())
                result['published_binding']=published_binding(case,artifact,registry)
                result['scope']='Frozen published core artifact/level and exact registered code/documents'
                result['disposition']='Comparison completed is not qualification or release approval'
            before = battery_module.input_identity(artifact)
            report = gate.qualify(artifact, battery_output=scratch / 'vectors').as_dict()
            write_report(output / 'qualification.json', report)
            if report['artifact']['artifact_version']['digest'] != case['artifact_version']:
                raise ValueError('historical artifact version differs from audited identity')
            if before != battery_module.input_identity(artifact):
                raise ValueError('audit changed the historical inputs')
            battery = json.loads((scratch / 'vectors' / 'battery.json').read_text())
            write_report(output / 'battery.json', battery)
            checks = expectations(case, battery) if mode=='recovery_acceptance' else []
            result.update({'expectations': checks, 'failed_checks': report['failed_checks'],
                           'gate_version': report['gate_version'], 'code': battery['code'],
                           'inputs': before, 'input_digest': battery['input_digest'],
                           'unchanged': True, 'strict_gate_refused': not report['ok']})
            # Keep the full compact diagnostics, subject to an explicit per-case cap.
            diagnostics = sorted((scratch / 'vectors').glob('results-*.jsonl'))
            if sum(p.stat().st_size for p in diagnostics) > 8 * 1024 * 1024:
                raise ValueError('diagnostics exceed per-case collection budget')
            for path in diagnostics:
                shutil.copyfile(path, output / path.name)
            result['ok'] = bool(checks and all(r['ok'] for r in checks)
                                and not report['ok'] and not battery['ok'])
            if mode=='published_comparison':
                required={'battery.exact_recovery','battery.recorded_in_quality','artifacts.no_shipped_answers'}
                if not required <= {r['check'] for r in report['results']}:
                    raise ValueError('published comparison did not complete the full new gate')
                result.update(ok=True,comparison_completed=True,release_eligible=False,
                              battery_passed=battery['ok'],review_required=True)
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    result['peak_rss_kib_linux'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_report(output / 'acceptance.json', result)
    print(json.dumps({k: result[k] for k in ('case', 'ok', 'elapsed_seconds')}, sort_keys=True), flush=True)
    return 0 if result['ok'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=Path('/workspace/cases.json'))
    parser.add_argument('--data', type=Path, default=Path('/data'))
    parser.add_argument('--output', type=Path, default=Path('/output'))
    parser.add_argument('--case')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if args.case:
        case = next(c for c in plan['cases'] if c['id'] == args.case)
        return audit(case, args.data, contained(args.output, case['id']))
    results = []
    for case in plan['cases']:
        # Release all memory between datasets. No historical code is executed.
        run = subprocess.run([sys.executable, '-B', __file__, '--plan', str(args.plan),
                              '--data', str(args.data), '--output', str(args.output), '--case', case['id']])
        results.append({'case': case['id'], 'exit_code': run.returncode})
    write_report(args.output / 'acceptance-summary.json', {'cases': results,
                 'ok': all(r['exit_code'] == 0 for r in results), 'plan_sha256': digest(args.plan)})
    return 0 if all(r['exit_code'] == 0 for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
