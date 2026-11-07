"""Freeze model-proposed feature-only attacks before any scored-label access.

This worker component is separate from the fixed construction battery. Its compact
receipt is evidence for the autonomous audit; it cannot by itself authorize a release.
"""
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

from . import adversarial_programs as programs
from . import leakage_battery as battery

VERSION = '1.0.0'
LIMIT = 256 * 1024


def code_identity():
    return {**battery.code_identity(), **{name:battery.sha256(Path(__file__).with_name(name))
            for name in ('adversarial_execution.py', 'adversarial_programs.py')}}


def artifact_identity(dataset):
    """Every byte, including the construction report; no mutable receipt exclusions."""
    if Path(dataset).is_symlink(): raise ValueError('artifact root symlink refused')
    result = {}
    for path in sorted(Path(dataset).rglob('*')):
        if path.is_symlink(): raise ValueError('artifact symlink refused')
        if path.is_file(): result[path.relative_to(dataset).as_posix()] = battery.sha256(path)
    if not result: raise ValueError('empty artifact')
    return result


def bounded_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size >= LIMIT:
        raise ValueError('audit JSON must be a bounded regular file')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('duplicate audit JSON key')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def write_json(path, value):
    data = battery.canonical(value)+b'\n'
    if len(data) >= LIMIT: raise ValueError('audit receipt exceeds compact report limit')
    with Path(path).open('xb') as handle: handle.write(data)


def freeze(dataset, output, proposal):
    if Path(dataset).is_symlink(): raise ValueError('artifact root symlink refused')
    dataset, output = Path(dataset).resolve(), Path(output)
    if output.resolve().is_relative_to(dataset):
        raise ValueError('audit scratch must be outside artifact')
    inputs = artifact_identity(dataset)
    quality = bounded_json(dataset/'quality.json')
    proposal = bounded_json(proposal)
    if (not isinstance(proposal, dict) or set(proposal) != {'version','artifact_digest','programs'}
            or proposal['version'] != VERSION or proposal['artifact_digest'] != battery.digest(inputs)):
        raise ValueError('proposal does not bind this complete staged artifact')
    panel = battery.load_features(dataset, quality)
    programs.validate(proposal['programs'], panel.cols, panel.target)
    output.mkdir(parents=True, exist_ok=False)  # No stale vectors, overwrite or destructive cleanup.
    records = []
    with zipfile.ZipFile(output/'predictions.zip', 'x') as archive:
        for record, values in programs.predictions(panel, proposal['programs']):
            vector = array('d', values)
            if sys.byteorder != 'little': vector.byteswap()
            payload = vector.tobytes(); member = str(len(records))+'.bin'
            info = zipfile.ZipInfo(member, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
            records.append({**record, 'member':member, 'rows':len(values),
                            'sha256':hashlib.sha256(payload).hexdigest()})
    if inputs != artifact_identity(dataset):
        raise ValueError('artifact changed while freezing model attacks')
    manifest = {'version':VERSION, 'code':code_identity(), 'inputs':inputs,
                'artifact_digest':battery.digest(inputs), 'proposal':proposal,
                'proposal_sha256':battery.digest(proposal), 'vectors':records,
                'predictions_sha256':battery.sha256(output/'predictions.zip'),
                'label_access':'none before all predictions sealed'}
    write_json(output/'freeze.json', manifest)
    return manifest


def score(dataset, output):
    dataset, output = Path(dataset), Path(output)
    frozen = bounded_json(output/'freeze.json')
    if frozen['version'] != VERSION or frozen['code'] != code_identity():
        raise ValueError('audit implementation changed after freeze')
    if frozen['inputs'] != artifact_identity(dataset):
        raise ValueError('artifact changed after freeze')
    if (frozen['artifact_digest'] != battery.digest(frozen['inputs'])
            or frozen['proposal_sha256'] != battery.digest(frozen['proposal'])
            or frozen['proposal']['artifact_digest'] != frozen['artifact_digest']
            or frozen['predictions_sha256'] != battery.sha256(output/'predictions.zip')):
        raise ValueError('frozen attack evidence changed')
    quality = bounded_json(dataset/'quality.json')
    panel = battery.load_features(dataset, quality)
    programs.validate(frozen['proposal']['programs'], panel.cols, panel.target)
    expected_records = [(a['name'], scope, split, len(rows))
                        for scope, split, rows, _ in panel.scopes()
                        for a in frozen['proposal']['programs']]
    actual_records = [(r['name'],r['scope'],r['split'],r['rows']) for r in frozen['vectors']]
    if actual_records != expected_records:
        raise ValueError('frozen attack coverage differs from proposed programs')
    del panel
    if (output/'predictions.zip').is_symlink(): raise ValueError('prediction archive symlink refused')
    # No proposal selection or vector evaluation takes place after this boundary.
    labels = {s:battery.read_labels(dataset, quality, s) for s in ('eval', 'holdout')}
    results, findings = [], []
    with zipfile.ZipFile(output/'predictions.zip') as archive:
        expected = [r['member'] for r in frozen['vectors']]
        if archive.namelist() != expected or len(expected) != len(set(expected)):
            raise ValueError('prediction archive inventory mismatch')
        for record in frozen['vectors']:
            info = archive.getinfo(record['member'])
            if info.file_size != len(labels[record['split']])*8:
                raise ValueError('prediction size does not align with scored rows')
            payload = archive.read(record['member'])
            if hashlib.sha256(payload).hexdigest() != record['sha256']:
                raise ValueError('frozen attack vector changed')
            vector = array('d'); vector.frombytes(payload)
            if sys.byteorder != 'little': vector.byteswap()
            if len(vector) != record['rows'] or any(math.isinf(v) for v in vector):
                raise ValueError('invalid frozen vector')
            result = {**record, **battery.metric(labels[record['split']], vector)}
            results.append(result)
            if result['covered'] and result['errors'] == 0:
                findings.append({k:result[k] for k in ('name','scope','split','covered','errors')})
    if frozen['inputs'] != artifact_identity(dataset):
        raise ValueError('artifact changed during attack scoring')
    result = {'version':VERSION, 'completed':True, 'code':frozen['code'],
              'artifact_digest':frozen['artifact_digest'], 'proposal_sha256':frozen['proposal_sha256'],
              'freeze_sha256':battery.sha256(output/'freeze.json'),
              'predictions_sha256':frozen['predictions_sha256'], 'results':results,
              'requires_semantic_review':findings, 'release_authorized':False,
              'scope':'A zero-error hypothesis is not automatically an algebraic identity; '
                      'unresolved findings block queue admission. No claim of exhaustive search.'}
    write_json(output/'model-attacks.json', result)
    return result
