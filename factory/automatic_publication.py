"""Standing-policy publication dispatch, bound to the accepted construction job."""
from pathlib import Path

from .common import FactoryError, read_json, write_json
from . import worker, worker_artifacts
from .reconciliation import advance_worker


def publication_spec(root, policy, data, api):
    manifest = data['evidence']['MANIFEST.json']
    qualification = data['evidence']['qualification.json']
    if (qualification.get('ok') is not True or data['evidence'].get('LICENSE-EVIDENCE.json', {}).get('ok') is not True
            or data.get('review', {}).get('verdict') != 'accept'
            or data['review'].get('findings')
            or manifest['artifact_version'] != qualification['artifact']['artifact_version']['digest']
            or manifest['dataset'] != data['source']['dataset_id']
            or manifest['source'].get('redistribution') is not True):
        raise FactoryError('Publication requires accepted exact-artifact evidence and resolved semantic review')
    for component in qualification['artifact'].values():
        if isinstance(component, dict) and 'file' in component and 'sha256' in component:
            published = manifest['assets'].get('extract/' + component['file'], {})
            if published.get('sha256') != component['sha256'] or published.get('bytes') != component['bytes']:
                raise FactoryError('Published data differs from qualified bytes: ' + component['file'])
    record = worker.load_record(root, data['job']['id'])
    if record['status'] != 'deleted' or record['result']['exit_code'] != 0:
        raise FactoryError('Construction must be durably collected and cleaned before publication')
    worker.verify_preserved_report(record, record['result'], api)
    # Reuse the existing exact-byte qualification receipt checker. Only compact
    # metadata is local; CSV identities come from the verified staging manifest.
    from .qualification_receipt import check
    package = Path(root) / '.factory' / record['job']['id'] / 'output/extract'
    inventory = qualification['artifact']['scanned_files']
    for name in inventory:
        if not name.endswith('.csv'):
            worker_artifacts.collect_small(root, record, 'output/extract/' + name, api)
    write_json(package / 'qualification.json', qualification)
    adapted = {**manifest, 'assets': {name.removeprefix('extract/'): entry
                                     for name, entry in manifest['assets'].items() if name.startswith('extract/')}}
    problems = check(package, adapted, external_assets=True)
    if problems:
        raise FactoryError('; '.join(problems))
    raw = worker_artifacts.manifest(root, record, api)
    indexed = {}
    for entry in raw['assets']:
        logical = entry.get('file', '')
        if logical in indexed:
            raise FactoryError('Publication requires unchunked individual assets within the artifact limit')
        indexed[logical] = entry
    selected = []
    expected = dict(manifest['assets'])
    for name in ('MANIFEST.json', 'SHA256SUMS'):
        entry = indexed['output/' + name]
        expected[name] = {'bytes': entry['size'], 'sha256': entry['sha256'], 'asset_name': name}
    for name, pin in expected.items():
        entry = indexed['output/' + name]
        if entry.get('offset') != 0 or entry['size'] != pin['bytes'] or entry['sha256'] != pin['sha256']:
            raise FactoryError('Release manifest differs from actual staged bytes: ' + name)
        selected.append({'source_asset_id': entry['id'], 'target_name': pin['asset_name'],
                         'path': name, 'size': pin['bytes'], 'sha256': pin['sha256']})
    namespace = policy['publication']
    return {'policy': 'FACTORY-REWRITE-2026-11-08', 'dataset': manifest['dataset'],
            'artifact_version': manifest['artifact_version'], 'version': manifest['version'],
            'source_repo': record['staging_repo'], 'source_release': record['result']['release_id'],
            'github_repo': namespace['github_owner'] + '/' + namespace['repo_prefix'] + manifest['dataset'],
            'hf_repo': namespace['hf_owner'] + '/' + namespace['repo_prefix'] + manifest['dataset'],
            'assets': selected}


def publish(root, policy, candidate, attempt, data, save):
    root = Path(root)
    config = read_json(root / 'config/local.json')
    config['release_preempts'] = False
    job_id = attempt['id']
    folder = root / '.factory/job-sources' / job_id
    job_file = folder / 'job.json'
    if not job_file.exists():
        spec = publication_spec(root, policy, data, worker.github(config))
        job = {**policy['worker'], 'id': job_id, 'candidate': spec['dataset'],
               'location': config['allowed_locations'][0], 'release': True, 'release_publish': spec,
               'timeout_minutes': min(60, config['max_job_minutes']),
               'lifetime_minutes': min(90, config['max_lifetime_minutes']), 'max_artifact_mb': 16}
        job.pop('image', None)
        worker.validate(job, config)
        folder.mkdir(parents=True, exist_ok=True)
        write_json(job_file, job)
    data['publication_job'] = {'id': job_id, 'file': str(job_file.relative_to(root))}; save(data)
    if not (root / 'jobs' / (job_id + '.json')).exists():
        worker.launch(root, job_file, config)
    result = advance_worker(root, job_id, config, job_file=job_file)
    if result['status'] == 'waiting':
        return result
    if result['status'] == 'lost' or not result.get('ok'):
        data['publication_failure'] = result; save(data)
        return {'status': 'retry', 'reason': 'Publication incomplete; retry reconciles destination files and tags'}
    record = worker.load_record(root, job_id)
    receipt = worker_artifacts.collect_json(root, record, 'output/publication.json', worker.github(config))
    spec = read_json(job_file)['release_publish']
    if (receipt.get('ok') is not True or receipt.get('artifact_version') != spec['artifact_version']
            or set(receipt.get('consumers', {})) != {'github', 'huggingface'}
            or any(v.get('ok') is not True for v in receipt['consumers'].values())):
        raise FactoryError('Anonymous consumer verification did not establish this release')
    for platform, repo in [('github', spec['github_repo']), ('huggingface', spec['hf_repo'])]:
        consumer = receipt['consumers'][platform]
        if (consumer.get('repo') != repo or consumer.get('version') != spec['version']
                or consumer.get('authentication') != 'none'
                or consumer.get('rows_loaded') != data['evidence']['MANIFEST.json']['rows']):
            raise FactoryError('Consumer verification differs from the intended public release')
    data['publication'] = receipt; save(data)
    return {'status': 'done', 'reason': 'Published and anonymously verified on GitHub and Hugging Face'}
