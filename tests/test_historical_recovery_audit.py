"""Transport and acceptance assertions, not real-artifact acceptance measurements."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('historical_audit', ROOT / 'scripts/historical-recovery-audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class HistoricalAuditTests(unittest.TestCase):
    def archive(self, data, *, link=False, duplicate=False):
        payload = b'raise RuntimeError("historical code must never execute")\n'
        path = data / 'source.tar'
        with tarfile.open(path, 'w') as tar:
            for _ in range(2 if duplicate else 1):
                member = tarfile.TarInfo('source/build.py')
                member.size = len(payload)
                if link:
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/etc/passwd'
                tar.addfile(member, io.BytesIO(payload))
        return {'fetch_dest': 'source.tar', 'size': path.stat().st_size,
                'sha256': audit.digest(path), 'members': [{'member': 'source/build.py',
                'path': 'code/build.py', 'size': len(payload),
                'sha256': hashlib.sha256(payload).hexdigest()}]}, payload

    def test_original_code_is_copied_as_data_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            source, payload = self.archive(data)
            audit.prepare({'files': [], 'archives': [source]}, data, data / 'artifact')
            self.assertEqual(payload, (data / 'artifact/code/build.py').read_bytes())

    def test_links_duplicates_changed_members_and_escape_refuse(self):
        for flaw in ('link', 'duplicate', 'digest', 'escape'):
            with self.subTest(flaw=flaw), tempfile.TemporaryDirectory() as folder:
                data = Path(folder)
                source, _ = self.archive(data, link=flaw == 'link', duplicate=flaw == 'duplicate')
                if flaw == 'digest':
                    source['members'][0]['sha256'] = '0' * 64
                if flaw == 'escape':
                    source['members'][0]['path'] = '../escaped.py'
                with self.assertRaises(ValueError):
                    audit.prepare({'files': [], 'archives': [source]}, data, data / 'artifact')
                self.assertFalse((data / 'escaped.py').exists())

    def test_missing_or_degraded_recovery_is_not_passing_acceptance(self):
        expected = {'name': 'rule', 'split': 'eval', 'min_covered': 20}
        for results in ([], [{**expected, 'covered': 19, 'errors': 0}],
                        [{**expected, 'covered': 20, 'errors': 1}]):
            self.assertFalse(audit.expectations({'expectations': [expected]}, {'exact': results})[0]['ok'])
        self.assertTrue(audit.expectations({'expectations': [expected]}, {'exact': [
            {**expected, 'covered': 21, 'errors': 0}]})[0]['ok'])

    def test_plan_pins_reconstruct_original_core_versions_and_fetches(self):
        root = ROOT / 'candidates/nz-ea-wholesale-price-exceedance/resilience-a1'
        cases = json.loads((root / 'cases.json').read_text())['cases']
        fetch = {a['dest']: a for a in json.loads((root / 'job.json').read_text())['fetch']['assets']}
        for case in cases:
            components = {}
            for entry in case['files']:
                key = {'public/train.csv': 'train', 'public/eval.csv': 'eval',
                       'private/holdout.csv': 'holdout'}.get(entry['path'], entry['path'])
                components[key] = entry['sha256']
            identity = hashlib.sha256(''.join(sorted(k + ':' + v for k, v in components.items())).encode()).hexdigest()
            self.assertEqual(case['artifact_version'], identity)
            for entry in case['files'] + case.get('archives', []):
                actual = fetch[entry['fetch_dest']]
                self.assertEqual((entry['size'], entry['sha256']), (actual['size'], actual['sha256']))

    def test_reports_enforce_collection_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'collection limit'):
                audit.write_report(Path(folder) / 'large.json', {'text': 'a' * (256 * 1024)})


if __name__ == '__main__':
    unittest.main()
