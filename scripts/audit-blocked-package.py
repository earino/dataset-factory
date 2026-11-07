#!/usr/bin/env python3
"""Read-only worker acceptance of every current gate on original blocked packages.

An expected refusal is a completed observation, never release clearance. Errors
leave the experiment incomplete. Historical code is only copied and inspected.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), result.__dict__)
    return result


transport = module('historical_transport', Path(__file__).with_name('historical-recovery-audit.py'))


def package_binding(case, package):
    manifest_path = transport.contained(package, 'MANIFEST.json')
    if transport.digest(manifest_path) != case['manifest_sha256']:
        raise ValueError('blocked package manifest differs from pinned audit')
    manifest = json.loads(manifest_path.read_text())
    if (manifest['dataset'] != case['dataset'] or manifest['artifact_version'] != case['artifact_version']
            or manifest.get('published') is not False):
        raise ValueError('blocked package identity/publication state differs from audit')
    expected = {'MANIFEST.json': case['manifest_sha256']}
    for name, entry in manifest['package_files'].items():
        expected[name] = entry if isinstance(entry, str) else entry['sha256']
    for name, entry in manifest['assets'].items():
        if name in expected and expected[name] != entry['sha256']:
            raise ValueError('manifest inventories disagree')
        expected[name] = entry['sha256']
        path = transport.contained(package, name)
        if path.stat().st_size != entry['bytes']:
            raise ValueError('blocked package asset size differs: ' + name)
    actual = {}
    for path in package.rglob('*'):
        if path.is_symlink():
            raise ValueError('blocked package contains a symlink')
        if path.is_file():
            actual[path.relative_to(package).as_posix()] = transport.digest(path)
    if actual != expected:
        raise ValueError('blocked package inventory differs from the exact shipped manifest')
    return manifest, actual


def refusal_for_missing(package, names):
    missing = [name for name in names if not (package / name).is_file()]
    return {'ok': False, 'problems': ['Required current evidence missing: ' + ', '.join(missing)]} if missing else None


def run_stages(package, output, scratch):
    from factory.artifact_scrub import scan_tree
    from factory.asset_integrity import check as integrity
    from factory.claim_facts import measure
    from factory.claim_checks import inspect
    from factory.claim_contract import qualification_binding, validate as validate_claims
    from factory.license_contract import validate as validate_license
    from factory.qualification_receipt import check as qualification_receipt

    gate = module('current_qualification', ROOT / 'skills/dataset-qualification/scripts/qualify_dataset.py')
    packaging = module('current_package_check', ROOT / 'scripts/check-package.py')
    manifest = json.loads((package / 'MANIFEST.json').read_text())
    stages = {}

    def stage(name, operation):
        started = time.monotonic()
        try:
            report = operation()
            transport.write_report(output / (name + '.json'), report)
            stages[name] = {'completed': True, 'ok': report['ok'], 'report': name + '.json'}
        except Exception as exc:
            stages[name] = {'completed': False, 'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        stages[name]['elapsed_seconds'] = round(time.monotonic() - started, 3)

    stage('qualification', lambda: gate.qualify(package, battery_output=scratch / 'vectors').as_dict())
    stage('scrub', lambda: scan_tree(package, dataset=package))

    def claims():
        qualification_binding(package, output / 'qualification.json', historical=True)
        facts = measure(package)
        facts['historical_only'] = True
        transport.write_report(output / 'claims-facts.json', facts)
        return inspect(package, facts)

    stage('claims', claims)

    def assets():
        problems, notes = integrity(package, manifest, require_loader=True)
        return {'ok': not problems, 'problems': problems, 'notes': notes}

    stage('asset_integrity', assets)
    stage('qualification_admission', lambda: problems_report(qualification_receipt(package, manifest)))

    def claims_admission():
        missing = refusal_for_missing(package, ('CLAIMS.json', 'claims-facts.json'))
        if missing:
            return missing
        try:
            return validate_claims(package, json.loads((package / 'claims-facts.json').read_text()), manifest=manifest)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return problems_report([str(exc)])

    stage('claims_admission', claims_admission)

    def licensing():
        missing = refusal_for_missing(package, ('LICENSE-EVIDENCE.json', 'license-receipt.json', 'card.md'))
        if missing:
            return missing
        try:
            validate_license(package, manifest=manifest)
            return problems_report([])
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return problems_report([str(exc)])

    stage('license_admission', licensing)

    def package_check():
        problems, notes = packaging.check_package(package)
        return {'ok': not problems, 'problems': problems, 'notes': notes}

    stage('package_admission', package_check)
    # Retain bounded aggregate diagnostics; prediction vectors remain private worker scratch.
    vectors = scratch / 'vectors'
    if (vectors / 'battery.json').is_file():
        transport.write_report(output / 'battery.json', json.loads((vectors / 'battery.json').read_text()))
    diagnostics = sorted(vectors.glob('results-*.jsonl'))
    if sum(path.stat().st_size for path in diagnostics) > 8 * 1024 * 1024:
        raise ValueError('diagnostics exceed bounded per-case collection limit')
    for path in diagnostics:
        shutil.copyfile(path, output / path.name)
    return stages


def problems_report(problems):
    return {'ok': not problems, 'problems': problems}


def audit(case, data, output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {'case': case['id'], 'dataset': case['dataset'], 'artifact_version': case['artifact_version'],
              'manifest_sha256': case['manifest_sha256'], 'ok': False, 'release_eligible': False,
              'scope': 'Full original manifest-listed package, all asset rows, current gates; no reconstruction',
              'model_audit': 'Not run: deterministic original-package acceptance only; R5 remains separate',
              'disposition': 'Recorded gate outcomes for operator disposition; never package repair or publication'}
    try:
        with tempfile.TemporaryDirectory(prefix='blocked-package-audit-') as folder:
            scratch = Path(folder); package = scratch / 'package'
            transport.prepare(case, data, package)
            _, before = package_binding(case, package)
            result['stages'] = run_stages(package, output, scratch)
            _, after = package_binding(case, package)
            if before != after:
                raise ValueError('audit mutated historical package')
            result.update(unchanged=True, inputs=before,
                          ok=all(stage['completed'] for stage in result['stages'].values()))
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    result['peak_rss_kib_linux'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result['implementation'] = {p.relative_to(ROOT).as_posix(): transport.digest(p)
                                for directory in ('factory', 'scripts', 'skills/dataset-qualification/scripts')
                                for p in sorted((ROOT / directory).glob('*.py')) if p.is_file()}
    transport.write_report(output / 'acceptance.json', result)
    print(json.dumps({key: result[key] for key in ('case', 'ok', 'elapsed_seconds')}), flush=True)
    return 0 if result['ok'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT / 'cases.json')
    parser.add_argument('--data', type=Path, default=Path('/data'))
    parser.add_argument('--output', type=Path, default=Path('/output'))
    parser.add_argument('--case')
    args = parser.parse_args(); plan = json.loads(args.plan.read_text())
    if args.case:
        case = next(c for c in plan['cases'] if c['id'] == args.case)
        return audit(case, args.data, transport.contained(args.output, case['id']))
    results = []
    for case in plan['cases']:
        run = subprocess.run([sys.executable, '-B', __file__, '--plan', str(args.plan),
                              '--data', str(args.data), '--output', str(args.output), '--case', case['id']])
        results.append({'case': case['id'], 'exit_code': run.returncode})
    ok = all(r['exit_code'] == 0 for r in results)
    transport.write_report(args.output / 'acceptance-summary.json', {
        'ok': ok, 'cases': results, 'plan_sha256': transport.digest(args.plan), 'release_eligible': False})
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
