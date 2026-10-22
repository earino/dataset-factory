"""Runtime drift is reported without executing code, disclosing values or changing the host."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_audit', ROOT/'scripts/check-runtime.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class RuntimeAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'repo'
        self.home = Path(self.tmp.name)/'home'
        self.source = self.root/'ops/shims/example.py'
        self.target = self.home/'scripts/example.py'
        self.source.parent.mkdir(parents=True)
        self.target.parent.mkdir(parents=True)
        (self.root/'skills/dataset-qualification').mkdir(parents=True)
        (self.root/'skills/dataset-qualification/SKILL.md').write_text('canonical')
        self.source.write_text('reviewed')
        self.target.write_text('reviewed')
        self.rows = [{'source':'ops/shims/example.py', 'target':'scripts/example.py',
                      'sha256':hashlib.sha256(b'reviewed').hexdigest()}]
        self.write_contract()

    def write_contract(self):
        (self.root/'ops/runtime-files.json').write_text(json.dumps({'schema_version':1,'files':self.rows}))

    def test_committed_recovery_inventory_matches_all_sources(self):
        self.assertTrue(checker.audit(ROOT)['ok'])

    def test_new_uninventoried_source_is_refused(self):
        (self.source.parent/'extra.py').write_text('new code')
        self.assertFalse(checker.audit(self.root)['ok'])

    def test_uncommitted_project_skill_edit_is_detected(self):
        project = self.home/'dataset-factory'
        skill = project/'skills/dataset-qualification/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('unreviewed curator edit')
        result = checker.audit(self.root,self.home,project)
        self.assertFalse(result['ok'])
        self.assertTrue(result['project_skills_checked'])
        self.assertTrue(any('project:skills/dataset-qualification/SKILL.md' in p
                            for p in result['problems']))
        self.assertEqual('unreviewed curator edit',skill.read_text())

    def test_identical_copies_pass_without_mutation(self):
        stamp = self.target.stat().st_mtime_ns
        self.assertTrue(checker.audit(self.root,self.home)['ok'])
        self.assertEqual(stamp,self.target.stat().st_mtime_ns)

    def test_changed_live_file_is_reported_without_contents(self):
        self.target.write_text('private-runtime-value')
        result = checker.audit(self.root,self.home)
        self.assertFalse(result['ok'])
        self.assertNotIn('private-runtime-value',json.dumps(result))
        self.assertEqual('private-runtime-value',self.target.read_text())

    def test_missing_live_file_fails_but_source_only_still_passes(self):
        self.target.unlink()
        self.assertFalse(checker.audit(self.root,self.home)['ok'])
        self.assertTrue(checker.audit(self.root)['ok'])

    def test_profile_gate_skill_shadow_is_reported(self):
        path = self.home/'skills/research/dataset-qualification/SKILL.md'
        path.parent.mkdir(parents=True)
        path.write_text('different procedure')
        result = checker.audit(self.root,self.home)
        self.assertFalse(result['ok'])
        self.assertTrue(any('shadows project skill dataset-qualification' in x for x in result['problems']))

    def test_source_change_requires_reviewed_inventory_update(self):
        self.source.write_text('changed')
        self.assertFalse(checker.audit(self.root)['ok'])

    def test_traversal_and_duplicate_targets_are_refused(self):
        self.rows[0]['target'] = '../private.txt'
        self.write_contract()
        self.assertFalse(checker.audit(self.root,self.home)['ok'])
        self.rows[0]['target'] = 'scripts/example.py'
        self.rows.append(dict(self.rows[0]))
        self.write_contract()
        self.assertFalse(checker.audit(self.root,self.home)['ok'])

    def test_symlink_is_not_followed_or_read(self):
        self.target.unlink()
        self.target.symlink_to(self.source)
        self.assertFalse(checker.audit(self.root,self.home)['ok'])

    def test_oversized_live_file_is_refused(self):
        self.target.write_bytes(b'x'*(checker.LIMIT+1))
        self.assertFalse(checker.audit(self.root,self.home)['ok'])


if __name__ == '__main__':
    unittest.main()
