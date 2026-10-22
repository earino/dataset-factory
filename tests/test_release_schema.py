"""Release contract: real historical fixtures, fail-closed writes and read-only projections."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from factory.release_schema import (Release, ReleaseShapeError, load_release, from_manifest,
                                    normalise_baseline, normalise_splits,
                                    normalise_destinations, record_destination)

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hashes(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


class ReleaseConformanceTests(unittest.TestCase):
    def test_every_release_directory_conforms_without_modifying_published_bytes(self):
        before = hashes(ROOT / 'release')
        folders = [p for p in (ROOT / 'release').iterdir() if p.is_dir()]
        self.assertGreaterEqual(len(folders), 10)
        for folder in folders:
            with self.subTest(dataset=folder.name):
                release = load_release(folder)
                self.assertIsInstance(release, Release)
                self.assertTrue(release.splits)
                self.assertFalse(release.problems)
                if release.published:
                    self.assertTrue(any(d.verified and d.verified_at and d.locator
                                        for d in release.destinations.values()))
                    self.assertTrue(release.baseline_current)
                    if release.baseline:
                        # NOAA reports separate evaluation protocols; aggregation would fabricate a result.
                        self.assertTrue(release.baseline.eval_auc is not None or release.baseline.per_config)
                    else:
                        self.assertIsNone(release.metadata['baseline'])
                        self.assertTrue(release.baseline_reason)
        self.assertEqual(before, hashes(ROOT / 'release'))

    def test_suite_median_retains_its_scope(self):
        r = load_release(ROOT / 'release/chicago-food-inspections')
        self.assertEqual(.7208, r.baseline.eval_auc)
        self.assertEqual('median of 40 configs', r.baseline.scope)
        self.assertEqual(226417, r.rows)

    def test_protocols_are_not_collapsed_to_the_best_score(self):
        r = load_release(ROOT / 'release/noaa-tide-flooding')
        self.assertIsNone(r.baseline.eval_auc)
        self.assertEqual({'temporal': .8633, 'station_disjoint': .869}, r.baseline.per_config)
        self.assertEqual({'temporal', 'station_disjoint'}, set(r.configs))
        self.assertTrue(all(s.positives is None for s in r.splits.values()))

    def test_shared_pool_is_counted_once_and_single_config_measurement_is_labelled(self):
        r = load_release(ROOT / 'release/msha-enforcement-citations')
        self.assertEqual(45, len(r.configs))
        self.assertEqual(497897, r.rows)
        self.assertEqual('config sec_56_12004', r.baseline.scope)

    def test_historical_nhs_result_is_not_claimed_for_current_artifact(self):
        r = load_release(ROOT / 'release/nhs-ae-four-hour-decline')
        self.assertFalse(r.published)
        self.assertEqual('dropped', r.disposition)
        self.assertFalse(r.baseline_current)
        self.assertIn('historical artifact', r.baseline_display)

    def test_every_public_package_has_a_recorded_site(self):
        for p in (ROOT / 'release').iterdir():
            if p.is_dir():
                r = load_release(p)
                if r.published:
                    self.assertTrue(r.destination('site').verified, p.name)

    def test_dashboard_uses_the_same_scoped_display_for_every_package(self):
        dashboard = script('build-dashboard')
        result = dashboard.collect_releases()
        self.assertFalse(result['errors'])
        for row in result['releases']:
            r = load_release(ROOT / 'release' / row['dataset'])
            self.assertEqual(r.split_counts(), row['splits'])
            self.assertEqual(r.baseline_display, row['baseline_display'])
            self.assertEqual(set(r.destinations), set(row['verified']))

    def test_site_and_hub_consume_typed_releases(self):
        from factory.site_model import dataset_config_splits
        hf = script('hf-publish')
        r = load_release(ROOT / 'release/noaa-tide-flooding')
        self.assertEqual(set(r.configs), set(dataset_config_splits(r)))
        card = hf.render_card_template('{ROWS_TOTAL} | {BASELINE_AUC}', r)
        self.assertIn('1,396,692', card)
        self.assertIn('temporal: 0.8633', card)
        self.assertIn('station_disjoint: 0.8690', card)


class ShapeFailuresTests(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(load_release(ROOT / 'release/austin-911-response').metadata)
        self.data['published'] = False

    def test_missing_and_null_baselines_require_explicit_reason(self):
        for value in ({}, None):
            with self.subTest(value=value):
                self.data['baseline'] = value
                with self.assertRaisesRegex(ReleaseShapeError, 'MANIFEST.json: baseline'):
                    from_manifest(self.data, path='example/MANIFEST.json')
        self.data['baseline_reason'] = 'No baseline run; awaiting worker allocation.'
        r = from_manifest(self.data)
        self.assertIsNone(r.baseline)
        self.assertEqual(self.data['baseline_reason'], r.baseline_display)

    def test_missing_splits_are_named(self):
        self.data['splits'] = {}
        with self.assertRaisesRegex(ReleaseShapeError, 'MANIFEST.json: splits'):
            from_manifest(self.data, path='example/MANIFEST.json')

    def test_quality_paths_are_not_counts_but_summary_is(self):
        self.data['splits'] = {}
        r = from_manifest(self.data, split_sources=[
            ({'train': 'public/train.csv'}, 'quality.json', 'splits'),
            ({'train': {'rows': 11}}, 'summary.json', 'splits')])
        self.assertEqual(11, r.rows)
        self.assertIn('summary.json', r.splits['train'].evidence)

    def test_invalid_counts_are_not_coerced(self):
        for rows in (True, -1, 0, 1.2, '10'):
            with self.subTest(rows=rows), self.assertRaisesRegex(ReleaseShapeError, 'splits.train.rows'):
                normalise_splits({'train': {'rows': rows}})

    def test_unknown_positive_count_is_never_backfilled_from_a_rate(self):
        splits = normalise_splits({'eval': {'rows': 31, 'positive_rate': .5}})
        self.assertIsNone(splits['eval'].positives)
        self.assertNotIn('positives', splits['eval'].counts())

    def test_auc_rejects_nonfinite_bool_out_of_range_and_conflict(self):
        for value in (float('nan'), float('inf'), True, -.1, 1.1, 'oops'):
            with self.subTest(value=value), self.assertRaises(ReleaseShapeError):
                normalise_baseline({'eval_auc': value})
        with self.assertRaisesRegex(ReleaseShapeError, 'conflicting'):
            normalise_baseline({'result': {'eval_auc': .6}, 'contract': {'eval_auc': .7}})

    def test_superseded_and_reference_numbers_are_not_evaluation_results(self):
        self.assertIsNone(normalise_baseline({'superseded': {'eval_auc': .99},
                                             'references': {'persistence': .8}}))

    def test_malformed_nested_objects_raise_named_errors(self):
        for key in ('artifact', 'qualification_report', 'summary', 'result', 'contract', 'levels'):
            with self.subTest(key=key), self.assertRaisesRegex(ReleaseShapeError, 'baseline.' + key):
                normalise_baseline({key: ['not an object']}, 'baseline_result.json')

    def test_published_release_requires_verified_destination(self):
        self.data['published'] = True
        with self.assertRaisesRegex(ReleaseShapeError, 'destinations'):
            from_manifest(self.data)

    def test_legacy_site_receipt_is_read_without_inventing_verification(self):
        raw = {'publication': {'site': {'version_page': 'https://example.org/v1/',
               'status': 'verified', 'verified_at': '2026-10-22T00:00:00Z'}}}
        d = normalise_destinations(raw)['site']
        self.assertTrue(d.verified)
        self.assertEqual('https://example.org/v1/', d.locator)
        raw['publication']['site']['status'] = 'pending'
        self.assertFalse(normalise_destinations(raw)['site'].verified)

    def test_corrupt_destination_record_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'DESTINATIONS.json'
            path.write_text('{broken')
            with self.assertRaises(ReleaseShapeError):
                record_destination(path, 'site', {'verified': True})
            self.assertEqual('{broken', path.read_text())

    def test_destination_updates_preserve_other_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'DESTINATIONS.json'
            path.write_text(json.dumps({'destinations': {'github': {'private': False},
                'site': {'verified': False, 'operator_note': 'retain'}}}))
            record_destination(path, 'site', {'verified': True})
            data = json.loads(path.read_text())
            self.assertEqual('retain', data['destinations']['site']['operator_note'])
            self.assertEqual({'private': False}, data['destinations']['github'])


class ManifestWriterTests(unittest.TestCase):
    def test_published_manifest_command_is_read_only(self):
        writer = script('release-manifest')
        before = hashes(ROOT / 'release')
        with patch.object(sys, 'argv', ['release-manifest', 'austin-911-response']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, writer.main())
        self.assertEqual(before, hashes(ROOT / 'release'))

    def test_missing_canonical_fields_fail_before_any_output_is_changed(self):
        writer = script('release-manifest')
        source = ROOT / 'candidates/austin-911-response'
        for missing in ('splits', 'baseline'):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                candidate = root / 'candidates/example'
                (candidate / 'baseline').mkdir(parents=True)
                package = root / 'release/example'
                package.mkdir(parents=True)
                (package / 'SHA256SUMS').write_text('preserve on failure\n')
                for name in ('release.json', 'license.json'):
                    (candidate / name).write_bytes((source / name).read_bytes())
                descriptor = {'release_version': '1', 'release_tag': 'v1',
                              'repository': 'https://github.com/example/example',
                              'construction_commit': 'b'*40, 'source': {},
                              'commands': {'gate': 'existing gate', 'baseline': 'existing runner',
                                           'get_dataset': 'download'}}
                (candidate / 'release.json').write_text(json.dumps(descriptor))
                expected = {'job': 'example', 'artifact_version': 'a'*64, 'files': {}}
                (candidate / 'baseline/expected_artifact.json').write_text(json.dumps(expected))
                record = {'construction_output': {'splits': {'train': {'rows': 20}}}}
                if missing == 'splits':
                    record['construction_output']['splits'] = {}
                    (candidate / 'baseline/baseline_result.json').write_text('{"eval_auc": 0.6}')
                (candidate / 'record.json').write_text(json.dumps(record))
                before = hashes(package)
                with patch.object(writer, 'ROOT', root), patch.object(sys, 'argv', ['release-manifest', 'example']):
                    with self.assertRaisesRegex(ReleaseShapeError, missing):
                        writer.main()
                self.assertEqual(before, hashes(package))


if __name__ == '__main__':
    unittest.main()
