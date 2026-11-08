"""Packaging admission for the full-artifact gate 1.6 receipt (no data downloads)."""
import json
from pathlib import Path

from .artifact_scrub import sha256
from .leakage_battery import VERSION, code_identity, digest, safe_file

GATE_VERSION = '1.6.1'
MANDATORY = {'battery.exact_recovery','battery.recorded_in_quality','artifacts.no_shipped_answers'}


def check(package, manifest, *, external_assets=False):
    package = Path(package)
    problems = []
    try:
        report = json.loads(safe_file(package,'qualification.json').read_text())
        quality = json.loads(safe_file(package,'quality.json').read_text())
        checks = report.get('results',[])
        if (report.get('gate_version') != GATE_VERSION or report.get('ok') is not True
                or report.get('failed_checks') != [] or not checks
                or any(r.get('ok') is not True for r in checks)
                or not MANDATORY <= {r.get('check') for r in checks}):
            problems.append('Current complete passing gate 1.6 qualification is required')
        receipt = quality.get('adversarial_battery',{})
        measured = next((r.get('evidence') for r in checks if r.get('check') == 'battery.exact_recovery'),None)
        if (not receipt or receipt != measured or receipt.get('ok') is not True
                or receipt.get('version') != VERSION or receipt.get('code') != code_identity()
                or receipt.get('failures') != []):
            problems.append('Passing computed recovery receipt must match quality.json and current battery code')
        artifact = report.get('artifact',{})
        if (artifact.get('artifact_version',{}).get('digest') != manifest.get('artifact_version')
                or not manifest.get('artifact_version')):
            problems.append('Qualification artifact version does not match the release manifest')
        inventory = artifact.get('scanned_files',{})
        required = {'meta.json','quality.json',*(quality.get('splits') or {}).values()}
        if len(quality.get('splits',{})) != 3 or not required <= set(inventory):
            problems.append('Qualification lacks the full inspected core artifact inventory')
        inputs = dict(inventory)
        clean_quality = dict(quality); clean_quality.pop('adversarial_battery',None)
        inputs['quality.json'] = digest(clean_quality)
        if receipt.get('input_digest') != digest(inputs):
            problems.append('Recovery receipt input digest does not match the inspected artifact inventory')
        for name, expected in inventory.items():
            path = package/name
            asset = (manifest.get('assets') or {}).get(name,{})
            if not path.is_file() and external_assets and name.endswith('.csv') and asset.get('sha256') == expected:
                continue
            try:
                if sha256(safe_file(package,name)) != expected:
                    problems.append(f'{name}: differs from the qualified inspected bytes')
            except ValueError:
                problems.append(f'{name}: qualified inspected file is missing or unsafe')
        for key in ('train','eval','holdout','meta.json','quality.json'):
            entry = artifact.get(key,{})
            name = entry.get('file')
            if not name or inventory.get(name) != entry.get('sha256'):
                problems.append(f'{key}: qualification hashes disagree with inspected inventory')
            asset = (manifest.get('assets') or {}).get(name,{})
            if asset.get('sha256') != entry.get('sha256') or not asset.get('sha256'):
                problems.append(f'{key}: release asset digest differs from qualified bytes')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        problems.append('Full-artifact qualification receipt is missing or invalid: '+str(exc))
    return problems
