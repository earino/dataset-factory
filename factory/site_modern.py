"""Project accepted factory-1 releases into the existing website record contract."""
import json
import re
from pathlib import PurePosixPath

from .site_model import digest, dump, encoded, pages_url, repository, require, slug, SHA
from .site_state import publication_matches


def project(manifest, receipt, documents, release_date, config):
    """Documents are exact pinned bytes, not current editorial copies or local CSVs."""
    from datetime import date
    require(manifest.get('schema') == 'factory-1', 'Expected a factory-1 manifest')
    require(publication_matches({'evidence': {'MANIFEST.json': manifest}, 'publication': receipt}),
            'Publication receipt does not verify this artifact on both platforms')
    require(manifest.get('qualification', {}).get('ok') is True,
            'Accepted manifest has no passing qualification')
    require(manifest.get('source', {}).get('redistribution') is True,
            'Source distribution rights are missing')
    date.fromisoformat(release_date)
    name, tag = slug(manifest['dataset']), slug(manifest['version'])
    require(SHA.fullmatch(manifest['artifact_version']), 'Invalid artifact digest')
    gh, hf = (repository(receipt[p]['repo']) for p in ('github', 'huggingface'))
    catalog = repository(config['catalog_repository'])
    require(config.get('schema_version') == 1 and config.get('hosting') == 'github-project-pages',
            'Unsupported website configuration')
    require(gh != catalog, 'Dataset and catalogue repositories must differ')
    assets = {}
    for path, entry in sorted(manifest['assets'].items()):
        require(not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts,
                'Unsafe release asset path')
        filename = slug(entry['asset_name'])
        require(filename not in assets and SHA.fullmatch(entry['sha256'])
                and type(entry['bytes']) is int and entry['bytes'] >= 0, 'Invalid release asset')
        assets[filename] = {**{k: entry[k] for k in ('bytes', 'sha256')}, 'hf_path': path,
                            'download': f'https://github.com/{gh}/releases/download/{encoded(tag)}/{encoded(filename)}'}
    require(bool(assets), 'No release assets')
    for path in ('README.md', 'evaluation.json', 'LICENSE.md'):
        raw = documents.get(path)
        expected = manifest['assets'].get(path, {})
        require(isinstance(raw, bytes) and len(raw) <= 256 * 1024
                and len(raw) == expected.get('bytes') and digest(raw) == expected.get('sha256'),
                'Pinned metadata missing or differs from manifest: ' + path)
    evaluation = json.loads(documents['evaluation.json'])
    require(evaluation.get('rows') == manifest['rows']['eval'], 'Baseline rows differ from validation split')
    metrics = {}
    for model, values in evaluation['metrics'].items():
        for metric, value in values.items():
            require(type(value) in (float, int) and 0 <= value <= 1, 'Invalid measured baseline metric')
            metrics[f'Validation {model} {metric}'] = value
    task, source = manifest['task'], manifest['source']
    # A benchmark's short name is distinct from its prediction question. Source
    # builders often use that question as their README heading.
    acronyms = {'cfpb', 'fdic', 'nih', 'nhtsa', 'pfas', 'ucmr', 'epa', 'r01'}
    words = name.replace('_', '-').split('-')
    title = ' '.join(word.upper() if word in acronyms or any(c.isdigit() for c in word)
                     else word.capitalize() for word in words)
    title = re.sub(r'\bUCMR(\d+)\b', r'UCMR \1', title)
    paragraphs = [task['question']]
    for key, label in (('population', 'Population'), ('target', 'Target'),
                       ('prediction_time', 'Prediction time'), ('split_policy', 'Splits'),
                       ('outcome_horizon', 'Outcome horizon')):
        if task.get(key):
            paragraphs.append(label + ': ' + task[key])
    features = task.get('features', [])
    if features:
        paragraphs.append('Inputs: ' + '; '.join(f['name'] + ': ' + f.get('meaning', '') for f in features))
    splits = {key: {'rows': count} for key, count in manifest['rows'].items()}
    require(bool(splits) and all(type(s['rows']) is int and s['rows'] > 0 for s in splits.values()),
            'Invalid split counts')
    source_url = source.get('documentation_url') or source['urls'][0]
    require(source_url.startswith('https://'), 'Source reference must use HTTPS')
    urls = {'catalog': pages_url(catalog), 'website': pages_url(gh),
            'version': pages_url(gh) + 'versions/' + encoded(tag) + '/',
            'github': 'https://github.com/' + gh,
            'github_release': f'https://github.com/{gh}/releases/tag/{encoded(tag)}',
            'huggingface': 'https://huggingface.co/datasets/' + hf,
            'huggingface_version': f'https://huggingface.co/datasets/{hf}/tree/{encoded(tag)}'}
    record = {'schema_version': 1, 'release_schema': 'factory-1', 'site_revision': 1,
              'dataset': name, 'release_tag': tag, 'artifact_version': manifest['artifact_version'],
              'github_repository': gh, 'hf_repository': hf, 'urls': urls,
              'title': title, 'summary': task['question'], 'task_type': 'binary-classification',
              'domain': source['publisher'], 'release_date': release_date,
              'post': {'title': title, 'paragraphs': paragraphs},
              'limitations': manifest['limitations'], 'assets': assets, 'splits': splits,
              'configs': [], 'source': {'name': source['publisher'], 'url': source_url},
              'qualification': {'gate_version': manifest['qualification']['gate_version'], 'result': 'PASSED'},
              'baseline': {'metrics': metrics, 'scope': evaluation['protocol']},
              'evaluation_use': manifest['evaluation_contract']['use'],
              'publication_commits': {p: receipt[p]['commit'] for p in ('github', 'huggingface')},
              'licenses': {'code': 'MIT', 'data_compilation': 'CC0-1.0', 'source_data': source['license'],
                           'attribution': source['attribution'], 'citation': source['citation'],
                           'compilation_scope': 'Our additional compilation rights only; upstream terms remain in force.'},
              'documents': [['README.md', 'Loading and reproduction'], ['evaluation.json', 'Measured baseline'],
                            ['LICENSE.md', 'Licence and attribution']]}
    record['record_sha256'] = digest(dump(record))
    return record


def check_manifest(record, manifest):
    """Compare the pinned modern manifest without coercing it to the legacy schema."""
    require(manifest.get('schema') == 'factory-1' and manifest.get('dataset') == record['dataset']
            and manifest.get('version') == record['release_tag']
            and manifest.get('artifact_version') == record['artifact_version'], 'Pinned release identity differs')
    require({k: {'rows': v} for k, v in manifest['rows'].items()} == record['splits'], 'Pinned split counts differ')
    expected = {entry['asset_name']: {'bytes': entry['bytes'], 'sha256': entry['sha256'], 'hf_path': path}
                for path, entry in manifest['assets'].items()}
    require(expected == {name: {k: a[k] for k in ('bytes', 'sha256', 'hf_path')}
                         for name, a in record['assets'].items()}, 'Pinned release assets differ')
    source = manifest['source']
    require(all(record['licenses'][key] == source[key] for key in ('attribution', 'citation'))
            and record['licenses']['source_data'] == source['license'], 'Pinned source terms differ')
