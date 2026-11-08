import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

from factory import automatic_publication, construction, worker
from factory.common import FactoryError, read_json, write_json
from workers import dataset_package, dataset_run, executor, get_dataset, release_publish, source_io

ROOT = Path(__file__).resolve().parents[1]


class Response(io.BytesIO):
    url = 'https://publisher.example/data.csv'


class RewriteWorkerTests(unittest.TestCase):
    def test_terms_quote_is_checked_against_preserved_publisher_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = {'terms_url': 'https://publisher.example/terms',
                      'documentation_url': 'https://publisher.example/docs',
                      'terms_excerpt': 'You may redistribute & adapt.'}
            with patch.object(source_io.urllib.request, 'urlopen', side_effect=[
                    Response(b'<p>You may <b>redistribute</b> &amp; adapt.</p>'), Response(b'Field documentation')]):
                receipt = source_io.capture_terms(source, tmp)
            self.assertTrue(receipt['ok'])
            self.assertEqual(source_io.sha(Path(tmp) / 'publisher-terms.snapshot'), receipt['terms_sha256'])
            source['terms_excerpt'] = 'Invented permission'
            with self.assertRaises(source_io.TermsEvidenceError):
                source_io.capture_terms(source, tmp)

    def test_host_outcome_has_explicit_exit_status_without_changing_os_status(self):
        self.assertEqual(0, executor.operation_status({'status': 'succeeded'})['exit_code'])
        self.assertEqual(1, executor.operation_status({'status': 'failed'})['exit_code'])
        self.assertEqual(137, executor.operation_status({'status': 'failed', 'exit_code': 137})['exit_code'])

    def test_terms_excerpts_allow_html_spacing_and_explicit_omissions_only(self):
        text = 'You may copy , publish and adapt the Information ; You must acknowledge the source.'
        quote = 'You may copy, publish ... You must acknowledge the source.'
        self.assertEqual('ordered-verbatim-spans-with-explicit-omissions', source_io.excerpt_match(text, quote))
        self.assertIsNone(source_io.excerpt_match(text, quote.replace('may', 'own')))
        self.assertIsNone(source_io.excerpt_match(text, 'You must acknowledge the source. ... You may copy'))
        self.assertIsNone(source_io.excerpt_match(text, '...'))

    def test_source_transport_retry_preserves_exact_bytes_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(source_io.urllib.request, 'urlopen', side_effect=[
                    urllib.error.HTTPError('https://publisher.example', 503, 'temporary', {}, None), Response(b'a,b\n1,2\n')]), \
                    patch.object(source_io.time, 'sleep'):
                path = source_io.fetch('https://publisher.example/data.csv', tmp, 'source.csv')
            lock = read_json(Path(tmp) / 'sources.json')
            self.assertEqual(2, lock['source.csv']['transport_attempts'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), lock['source.csv']['sha256'])
            with patch.object(source_io.urllib.request, 'urlopen', side_effect=AssertionError('must replay cached bytes')):
                self.assertEqual(path, source_io.fetch('https://publisher.example/data.csv', tmp, 'source.csv'))
            path.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Cached source changed'):
                source_io.fetch('https://publisher.example/data.csv', tmp, 'source.csv')

    def test_package_and_public_consumer_share_exact_manifest_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / 'output'; out.mkdir()
            workspace = root / 'workspace'; workspace.mkdir()
            cache = root / 'raw'; cache.mkdir()
            extract = out / 'extract'
            shutil.copytree(ROOT / 'skills/dataset-qualification/fixtures/corrected', extract)
            quality = read_json(extract / 'quality.json')
            source = {'dataset_id': 'unit-fixture', 'title': 'Software fixture, not a real dataset',
                      'source': {'publisher': 'Software fixture', 'license': 'CC0-1.0',
                        'terms_url': 'https://example.invalid/terms', 'terms_excerpt': 'Unit fixture',
                        'attribution': 'Unit fixture', 'redistribution': True},
                      'task': {'question': 'Software fixture', 'prediction_time': 'Synthetic',
                               'split_policy': 'Synthetic fixed windows'}, 'limitations': ['Synthetic test only']}
            descriptor = {'quality': quality, 'references': {}}
            dataset_run.finalize(extract, descriptor, source)
            gate = ROOT / 'skills/dataset-qualification/scripts/qualify_dataset.py'
            result = subprocess.run([sys.executable, str(gate), str(extract), '--record-battery', '--json',
                                     '--report', str(out / 'qualification.json')], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout[-3000:] + result.stderr)
            write_json(out / 'evaluation.json', {'protocol': 'Synthetic software test only',
                       'metrics': {}, 'limitations': ['No empirical measurement']})
            for name in dataset_package.REPRODUCTION:
                (workspace / name).write_text('# Unit fixture content\n')
            shutil.copyfile(ROOT / 'workers/get_dataset.py', workspace / 'get_dataset.py')
            (cache / 'raw.csv').write_text('raw,fixture\n1,2\n')
            write_json(cache / 'sources.json', {'raw.csv': {'sha256': source_io.sha(cache / 'raw.csv')}})
            dataset_package.package(workspace, out, cache, source, descriptor)
            manifest = read_json(out / 'MANIFEST.json')
            # Exercise the real qualification receipt boundary used by automatic
            # publishing, with only the remote transport replaced.
            report = read_json(out / 'qualification.json')
            data = {'source': source, 'job': {'id': 'fixture-build'},
                    'review': {'verdict': 'accept', 'findings': []},
                    'evidence': {'MANIFEST.json': manifest, 'qualification.json': report,
                                 'LICENSE-EVIDENCE.json': {'ok': True}}}
            record = {'status': 'deleted', 'job': {'id': 'fixture-build'},
                      'result': {'exit_code': 0, 'release_id': 1}, 'staging_repo': 'owner/staging'}
            raw = {'assets': [{'file': 'output/' + str(p.relative_to(out)), 'offset': 0,
                              'size': p.stat().st_size, 'sha256': source_io.sha(p), 'id': i + 1}
                             for i, p in enumerate(out.rglob('*')) if p.is_file()]}
            def collect(root, record, logical, api):
                dest = root / '.factory/fixture-build' / logical
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(out / logical.removeprefix('output/'), dest)
            with patch.object(worker, 'load_record', return_value=record), \
                    patch.object(worker, 'verify_preserved_report'), \
                    patch.object(automatic_publication.worker_artifacts, 'collect_small', side_effect=collect), \
                    patch.object(automatic_publication.worker_artifacts, 'manifest', return_value=raw):
                spec = automatic_publication.publication_spec(root, {'publication': {
                    'github_owner': 'owner', 'hf_owner': 'owner', 'repo_prefix': 'factory-'}}, data, None)
            self.assertEqual('owner/factory-unit-fixture', spec['github_repo'])
            verification = subprocess.run([sys.executable, str(out / 'verify_dataset.py')], capture_output=True, text=True)
            self.assertEqual(0, verification.returncode, verification.stderr)
            by_asset = {entry['asset_name']: (out / name).read_bytes() for name, entry in manifest['assets'].items()}
            by_asset['MANIFEST.json'] = (out / 'MANIFEST.json').read_bytes()
            def public_open(request, timeout):
                self.assertNotIn('Authorization', request.headers)
                response = Response(by_asset[request.full_url.rsplit('/', 1)[1]])
                response.url = request.full_url
                return response
            with patch.object(get_dataset.urllib.request, 'urlopen', side_effect=public_open):
                loaded = get_dataset.retrieve('owner/unit-fixture', manifest['version'], root / 'consumer', 'github')
            self.assertEqual(manifest, loaded)
            subprocess.run([sys.executable, str(root / 'consumer/verify_dataset.py')], check=True, capture_output=True)
            by_asset[manifest['assets']['extract/public/train.csv']['asset_name']] = b'corrupt'
            with patch.object(get_dataset.urllib.request, 'urlopen', side_effect=public_open), self.assertRaises(ValueError):
                get_dataset.retrieve('owner/unit-fixture', manifest['version'], root / 'corrupt-consumer', 'github')

    def test_release_policy_rejects_unsafe_or_incomplete_spec_before_cloud(self):
        with self.assertRaises(ValueError):
            release_publish.validate({'policy': 'unapproved'})
        spec = {'policy': 'FACTORY-REWRITE-2026-11-08', 'source_repo': 'owner/staging',
                'github_repo': 'owner/factory-test', 'hf_repo': 'owner/factory-test',
                'dataset': 'test', 'artifact_version': 'a' * 64, 'version': 'v-' + 'b' * 16,
                'assets': [{'path': '../escape', 'target_name': 'data', 'source_asset_id': 1,
                            'size': 1, 'sha256': 'c' * 64}]}
        with self.assertRaisesRegex(ValueError, 'Invalid release asset'):
            release_publish.validate(spec)


if __name__ == '__main__':
    unittest.main()
