"""Assemble the canonical worker pipeline around bounded generated construction."""
import ast
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess

from .common import FactoryError, read_json, write_json
from .asset_integrity import sha256
from . import worker

REQUIREMENTS = '''numpy==1.26.4
pandas==2.2.3
xgboost==3.0.2
scikit-learn==1.6.1
requests==2.32.3
beautifulsoup4==4.13.3
lxml==5.3.1
openpyxl==3.1.5
pyarrow==19.0.1
pypdf==5.4.0
'''
FILES = ('source_io.py', 'dataset_run.py', 'dataset_package.py', 'get_dataset.py')


def merge_repair(previous, response):
    """Omitted top-level construction fields retain their exact saved values."""
    if previous is None:
        return response
    allowed = {'build_py', 'quality', 'references', 'construction_notes', 'source_access_recipe'}
    if not isinstance(response, dict) or not response or set(response) - allowed:
        raise FactoryError('Repair must return changed construction fields only')
    return {**copy.deepcopy(previous), **copy.deepcopy(response)}


def describe_task(source, response):
    """Carry construction's corrected descriptions into review and the package."""
    updated = copy.deepcopy(source)
    if 'source_access_recipe' in response:
        recipe = response['source_access_recipe']
        if not isinstance(recipe, str) or not recipe.strip():
            raise FactoryError('Source access recipe must be nonempty text')
        updated.setdefault('construction', {})['access_recipe'] = recipe
    quality = response['quality']
    descriptions = quality.get('task', {})
    if not isinstance(descriptions, dict):
        raise FactoryError('Construction task descriptions must be an object')
    for name in ('population', 'prediction_time', 'usefulness', 'simple_references'):
        if name in descriptions:
            value = descriptions[name]
            if not isinstance(value, str) or not value.strip():
                raise FactoryError('Task description must be nonempty text: ' + name)
            updated['task'][name] = value
    features = updated['task'].get('features')
    indexed = {f['name']: f for f in features if isinstance(f, dict) and 'name' in f} if isinstance(features, list) else {}
    clarified = descriptions.get('features', [])
    if not isinstance(clarified, list):
        raise FactoryError('Feature descriptions must be a list')
    seen = set()
    for feature in clarified:
        if not isinstance(feature, dict) or feature.get('name') not in indexed or feature['name'] in seen:
            raise FactoryError('Feature descriptions may only name distinct existing source features')
        name = feature['name']; seen.add(name)
        for field in ('meaning', 'availability'):
            if field in feature:
                value = feature[field]
                if not isinstance(value, str) or not value.strip():
                    raise FactoryError('Feature description must be nonempty text: ' + name)
                indexed[name][field] = value
    contract = quality.get('evaluation_contract', {})
    if not isinstance(contract, dict):
        raise FactoryError('Evaluation contract must be an object')
    availability = contract.get('feature_evidence', {})
    if not isinstance(availability, dict):
        raise FactoryError('Feature availability descriptions must be an object')
    for name, feature in indexed.items():
        evidence = availability.get(name, {})
        if not isinstance(evidence, dict):
            raise FactoryError('Feature availability evidence must be an object: ' + name)
        if isinstance(evidence.get('availability'), str) and evidence['availability'].strip():
            feature['availability'] = evidence['availability']
    return updated


def validate(response):
    code = response.get('build_py')
    if not isinstance(code, str) or not code.strip() or len(code.encode()) > 48 * 1024:
        raise FactoryError('Construction needs bounded Python source')
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise FactoryError(f'Construction Python does not parse at line {exc.lineno}, '
                           f'column {exc.offset}: {exc.msg}') from exc
    if not any(isinstance(n, ast.FunctionDef) and n.name == 'build' for n in tree.body):
        raise FactoryError('Construction must define build(output, cache)')
    quality = response.get('quality', {})
    for name in ('target', 'features', 'id_columns', 'time_column', 'event_key_column',
                 'split_windows', 'timing', 'evaluation_contract', 'measurements'):
        if name not in quality:
            raise FactoryError('Construction descriptor lacks ' + name)
    if not isinstance(response.get('references'), dict):
        raise FactoryError('Construction must declare fixed baseline references')
    return response


def assemble(root, job_id, source, response, settings, worker_config):
    root = Path(root)
    validate(response)
    target = root / '.factory/job-sources' / job_id
    if (target / 'job.json').exists():
        return target / 'job.json'
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        # An interrupted assembly contains only files from this exact attempt.
        # Complete it by replacing known files; never clear a directory tree.
        owner = read_json(target / 'bundle-owner.json')
        if owner != {'pipeline_job': job_id}:
            raise FactoryError('Unrecognized construction bundle directory')
    write_json(target / 'bundle-owner.json', {'pipeline_job': job_id})
    (target / 'build.py').write_text(response['build_py'])
    write_json(target / 'construction.json', {k: v for k, v in response.items() if k != 'build_py'})
    write_json(target / 'source.json', source)
    (target / 'requirements.txt').write_text(REQUIREMENTS)
    for name in FILES:
        shutil.copyfile(root / 'workers' / name, target / name)
    shutil.copyfile(root / 'skills/dataset-qualification/scripts/qualify_dataset.py', target / 'qualify_dataset.py')
    for name in ('artifact_scrub.py', 'leakage_battery.py', 'recovery_recipes.py'):
        shutil.copyfile(root / 'factory' / name, target / name)
    harness = Path(os.environ.get('FACTORY_BENCHMARK_ROOT', '/opt/data/harness_benchmark'))
    for name in ('train.py', 'validate.py', 'validate.sh'):
        original = harness / 'task_template' / name
        if not original.is_file():
            raise FactoryError('Existing benchmark runner is unavailable; no substitute is used')
        shutil.copyfile(original, target / name)
    for name in ('LICENSE-MIT.txt', 'LICENSE-CC0-1.0.txt'):
        shutil.copyfile(root / 'release/austin-911-response' / name, target / name)
    write_json(target / 'provenance.json', {
        'factory_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'harness_repository': 'earino/harness_benchmark',
        'harness_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=harness, text=True).strip(),
        'runner_files': {name: sha256(target / name) for name in ('train.py', 'validate.py', 'validate.sh')},
        'permission': 'Copyright holder permission for MIT distribution confirmed 2026-09-19; credits preserved'})
    (target / 'run.sh').write_text('''#!/bin/sh
set -eu
python3 -m pip install --no-cache-dir --quiet -r /workspace/requirements.txt
python3 /workspace/dataset_run.py --workspace /workspace --output /output
''')
    job = {**settings, 'id': job_id, 'candidate': source['dataset_id'],
           'location': worker_config['allowed_locations'][0], 'command': ['sh', '/workspace/run.sh'],
           'source_files': {p.name: sha256(p) for p in sorted(target.iterdir()) if p.is_file()}}
    worker.validate(job, worker_config)
    write_json(target / 'job.json', job)
    worker.source_bundle(target / 'job.json', job)
    return target / 'job.json'
