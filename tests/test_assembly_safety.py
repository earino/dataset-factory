"""Assembling model-authored descriptors must never erase coordinator work."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factory.common import FactoryError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('safe_assemble', ROOT / 'scripts/assemble-job.py')
assembler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembler)


class AssemblySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'candidates/example/source'
        self.source.mkdir(parents=True)
        self.job = {'id': 'example-001', 'candidate': 'example'}
        self.job_path = self.source / 'job.json'
        self.job_path.write_text(json.dumps(self.job))
        (self.source / 'build.py').write_text('print("assembly fixture")\n')
        self.declaration = {'job_file': 'candidates/example/source/job.json', 'overrides': {},
                            'files': [['build.py', 'candidates/example/source/build.py']]}
        self.target = self.root / '.factory/jobs/example-001'
        self.root_patch = patch.object(assembler, 'ROOT', self.root)
        self.bundles_patch = patch.object(assembler, 'BUNDLES', {'example': self.declaration})
        self.root_patch.start(); self.bundles_patch.start()
        self.addCleanup(self.root_patch.stop); self.addCleanup(self.bundles_patch.stop)

    def run_assembly(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return assembler.main(['example'])

    def snapshot(self):
        return {p.relative_to(self.target).as_posix(): p.read_bytes()
                for p in self.target.rglob('*') if p.is_file()}

    def test_identical_repeat_is_noop_and_owned(self):
        self.assertEqual(0, self.run_assembly())
        before = self.snapshot()
        stamp = (self.target / 'build.py').stat().st_mtime_ns
        self.assertEqual(0, self.run_assembly())
        self.assertEqual(before, self.snapshot())
        self.assertEqual(stamp, (self.target / 'build.py').stat().st_mtime_ns)
        owner = json.loads((self.target / assembler.OWNER_FILE).read_text())
        self.assertEqual('example-001', owner['job_id'])

    def test_existing_unowned_directory_is_preserved(self):
        self.target.mkdir(parents=True)
        (self.target / 'notes.md').write_text('irreplaceable work')
        before = self.snapshot()
        with self.assertRaisesRegex(SystemExit, 'not owned'):
            self.run_assembly()
        self.assertEqual(before, self.snapshot())

    def test_changed_sources_require_new_job_id(self):
        self.run_assembly()
        before = self.snapshot()
        (self.source / 'build.py').write_text('print("changed")\n')
        with self.assertRaisesRegex(SystemExit, 'different source bytes'):
            self.run_assembly()
        self.assertEqual(before, self.snapshot())

    def test_modified_generated_file_is_preserved(self):
        self.run_assembly()
        (self.target / 'build.py').write_text('manual edit\n')
        before = self.snapshot()
        with self.assertRaisesRegex(SystemExit, 'directory changed'):
            self.run_assembly()
        self.assertEqual(before, self.snapshot())

    def test_unexpected_file_is_not_deleted(self):
        self.run_assembly()
        (self.target / 'notes.md').write_text('keep this')
        with self.assertRaisesRegex(SystemExit, 'directory changed'):
            self.run_assembly()
        self.assertEqual('keep this', (self.target / 'notes.md').read_text())

    def test_missing_source_does_not_leave_partial_target(self):
        self.declaration['files'].append(['missing.py', 'candidates/example/source/missing.py'])
        with self.assertRaisesRegex(SystemExit, 'canonical source is missing'):
            self.run_assembly()
        self.assertFalse(self.target.exists())
        self.assertEqual([], list(self.target.parent.glob('.assembling-*')))

    def test_invalid_job_id_cannot_traverse_to_repository_data(self):
        for bad in ('../../../candidates', '/tmp', '..', 'wrong/id'):
            with self.subTest(id=bad):
                self.job_path.write_text(json.dumps({**self.job, 'id': bad}))
                with self.assertRaises(FactoryError):
                    self.run_assembly()
                self.assertTrue((self.source / 'build.py').is_file())

    def test_output_traversal_is_refused_before_copy(self):
        self.declaration['files'][0][0] = '../overwrite.py'
        with self.assertRaisesRegex(SystemExit, 'unsafe bundle path'):
            self.run_assembly()
        self.assertFalse((self.target.parent / 'overwrite.py').exists())
        self.assertFalse(self.target.exists())

    def test_source_link_cannot_exfiltrate_outside_file(self):
        external = self.root / 'private.txt'
        external.write_text('must stay outside bundle')
        source = self.source / 'build.py'
        source.unlink()
        source.symlink_to(external)
        with self.assertRaisesRegex(SystemExit, 'symlink'):
            self.run_assembly()
        self.assertFalse(self.target.exists())
        self.assertEqual('must stay outside bundle', external.read_text())

    def test_symlink_output_root_is_refused(self):
        external = self.root / 'unrelated'
        external.mkdir()
        (external / 'keep.txt').write_text('keep')
        (self.root / '.factory').symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(SystemExit, 'symlink'):
            self.run_assembly()
        self.assertEqual(['keep.txt'], [p.name for p in external.iterdir()])

    def test_reserved_and_duplicate_outputs_are_refused(self):
        for name in ('job.json', 'bundle-owner.json', 'job_id.txt'):
            with self.subTest(name=name):
                self.declaration['files'][0][0] = name
                with self.assertRaisesRegex(SystemExit, 'reserved'):
                    self.run_assembly()
        self.declaration['files'] = [['build.py', 'candidates/example/source/build.py']]*2
        with self.assertRaisesRegex(SystemExit, 'duplicate'):
            self.run_assembly()

    def test_invalid_ownership_record_does_not_destroy_target(self):
        self.run_assembly()
        (self.target / assembler.OWNER_FILE).write_text('[]')
        before = self.snapshot()
        with self.assertRaises(SystemExit):
            self.run_assembly()
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
