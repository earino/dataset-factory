"""Version-bound editorial suitability, separate from immutable dataset artifacts."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ENUMS = {
    'decision': {'retain', 'retain_restricted', 'rebuild_before_use', 'retire'},
    'evaluation_access': {'isolated_rows', 'chronological', 'common_cutoff_batch'},
    'historical_availability': {'verified', 'partial', 'assumed', 'unverified'},
    'training_label_timing': {'verified', 'partial', 'assumed', 'unverified'},
    'vintage': {'as_of', 'current_snapshot', 'mixed', 'unverified'},
    'selection': {'prediction_time', 'outcome_conditioned', 'unverified'},
}
AUDITS = {'recovery_demonstrated', 'bounded_no_recovery', 'untested'}


def validate(record, manifest, root=None):
    errors = []
    if not isinstance(record, dict):
        return ['suitability must be an object']
    if record.get('schema_version') != 1:
        errors.append('unsupported suitability schema')
    for key in ('dataset', 'release_tag', 'artifact_version'):
        if record.get(key) != manifest.get(key):
            errors.append(f'{key}: suitability describes another artifact')
    for key, values in ENUMS.items():
        if record.get(key) not in values:
            errors.append(f'{key}: expected one of {sorted(values)}')
    for key in ('reviewer', 'summary'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f'{key}: required text')
    try:
        date.fromisoformat(record.get('reviewed_on', ''))
    except (TypeError, ValueError):
        errors.append('reviewed_on: expected ISO date')
    for key in ('supported_uses', 'unsupported_uses', 'limitations', 'required_actions', 'corrections'):
        value = record.get(key)
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
            errors.append(f'{key}: expected a list of nonempty text')
    for key in ('supported_uses', 'limitations', 'required_actions'):
        if not record.get(key) and record.get('decision') != 'retire':
            errors.append(f'{key}: must state scope, limitations and next action')
    audit = record.get('cross_row_audit', {})
    if not isinstance(audit, dict):
        audit = {}
    if audit.get('status') not in AUDITS or not audit.get('scope'):
        errors.append('cross_row_audit: status and explicit tested scope required')
    if audit.get('status') != 'untested' and not audit.get('evidence'):
        errors.append('cross_row_audit: tested claim requires evidence')
    if audit.get('status') == 'recovery_demonstrated' and record.get('evaluation_access') == 'common_cutoff_batch' and record.get('decision') not in ('rebuild_before_use', 'retire'):
        errors.append('recovery demonstrated: cannot approve the artifact for batch access')
    evidence = record.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        errors.append('evidence: at least one specific source required')
    else:
        for item in evidence:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip()
                                                    for k in ('claim', 'source', 'detail')):
                errors.append('evidence: each item needs claim, source and detail')
                continue
            source = item['source'].split('#')[0]
            if root and not source.startswith('https://'):
                path = (Path(root) / source).resolve()
                if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
                    errors.append(f'evidence source not found inside repository: {source}')
    # Strong claims require a coherent evidence status; validation itself does not prove them.
    if record.get('decision') == 'retain' and any(record.get(k) != v for k, v in
            [('historical_availability', 'verified'), ('training_label_timing', 'verified'),
             ('vintage', 'as_of'), ('selection', 'prediction_time')]):
        errors.append('unrestricted retain requires verified availability/labels, as-of vintage and prediction-time selection')
    return errors


def load(package):
    package = Path(package)
    root = package.parent.parent
    path = root / 'suitability' / (package.name + '.json')
    if not path.is_file():
        return None
    record = json.loads(path.read_text())
    errors = validate(record, json.loads((package / 'MANIFEST.json').read_text()), root)
    if errors:
        raise ValueError('; '.join(errors))
    return record


def public_projection(record):
    """Do not copy private review paths, audit links, or operational actions to public sites."""
    keys = ('schema_version', 'dataset', 'release_tag', 'artifact_version', 'reviewed_on',
            'decision', 'summary', 'supported_uses', 'unsupported_uses', 'evaluation_access',
            'historical_availability', 'training_label_timing', 'vintage', 'selection',
            'limitations', 'corrections')
    result = {key: record[key] for key in keys}
    result['cross_row_audit'] = {key: record['cross_row_audit'][key] for key in ('status', 'scope')}
    return result


def markdown(record):
    """One current notice for GitHub and Hub; historical release documents stay unchanged."""
    text = ['### Suitability and evaluation requirements', '', record['summary'], '',
            '**Supported uses:** ' + '; '.join(record['supported_uses']), '',
            '**Not supported:** ' + '; '.join(record['unsupported_uses']), '',
            f"**Evaluation access:** {record['evaluation_access'].replace('_', ' ')}. "
            'The labeled eval split is development/validation data. Keep the final holdout outside '
            'agent development; prevent later rows from influencing earlier predictions.', '',
            f"**Historical availability:** {record['historical_availability']}. "
            f"**Training-label timing:** {record['training_label_timing']}. "
            f"**Vintage:** {record['vintage'].replace('_', ' ')}. "
            f"**Selection:** {record['selection'].replace('_', ' ')}.", '',
            '**Cross-row audit:** ' + record['cross_row_audit']['status'].replace('_', ' ') + '. '
            + record['cross_row_audit']['scope'], '',
            'Structural qualification and baseline scores do not certify operational forecasting validity.', '']
    text += ['- ' + value for value in record['limitations']]
    if record['corrections']:
        text += ['', '**Corrections to the historical documentation:**', '']
        text += ['- ' + value for value in record['corrections']]
    text += ['', f"Review: {record['reviewed_on']}; applies to {record['release_tag']} / "
             f"`{record['artifact_version']}`. Frozen data and tags are unchanged."]
    return '\n'.join(text)
