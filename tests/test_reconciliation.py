import json
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from factory.reconciliation import bookkeep, committed_record
from factory.common import write_json


class CloudFixture:
    def __init__(self): self.live = None; self.ips = []; self.calls = []
    def server(self, ident): self.calls.append(('server', ident)); return self.live
    def list_resources(self, resource, project): self.calls.append((resource, project)); return []
    def request(self, method, path):
        self.calls.append((method, path))
        if method != 'GET': raise AssertionError('Bookkeeping must be read-only at the provider')
        return {'primary_ips': self.ips, 'meta': {'pagination': {'next_page': None}}}


class StagingFixture:
    def __init__(self): self.bad_digest = False; self.calls = []
    def request(self, method, path):
        self.calls.append((method, path))
        if method != 'GET': raise AssertionError('Bookkeeping must not modify staging')
        if '/assets?' in path:
            return [{'id': 123, 'size': 456, 'digest': 'sha256:' + ('b' if self.bad_digest else 'a') * 64}]
        return {'tag_name': 'job-test-job'}


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.cloud = CloudFixture(); self.api = StagingFixture()
        self.record = {'job': {'id': 'test-job'}, 'project': 'test-project', 'status': 'deleted',
                       'server_id': 999, 'ipv4': '192.0.2.1', 'collected_at': '2026-11-07T18:00:00Z',
                       'deleted_at': '2026-11-07T18:01:00Z', 'staging_repo': 'owner/private',
                       'result': {'job_id': 'test-job', 'status': 'succeeded', 'exit_code': 0,
                                  'repo': 'owner/private', 'uploaded': True, 'release_id': 12,
                                  'assets': [{'id': 123, 'size': 456, 'sha256': 'a' * 64}]}}
        self.path = self.root / 'jobs/test-job.json'; write_json(self.path, self.record)
        self.git('init'); self.git('add', 'jobs'); self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.DEVNULL).decode().strip()

    def commit(self): self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-am', 'Recorded outcome')
    def run_bookkeeping(self):
        return bookkeep(self.root, 'test-job', {'project': 'test-project'}, cloud=self.cloud, api=self.api)

    def test_repeated_closeout_rechecks_every_external_boundary_without_rewriting_ledger(self):
        original = self.path.read_bytes(); first = self.run_bookkeeping()
        self.assertTrue(first['handled'], first)
        receipt = self.root / first['receipt']; initial = receipt.read_bytes()
        self.cloud.calls.clear(); self.api.calls.clear()
        second = self.run_bookkeeping(); self.assertTrue(second['handled'], second)
        self.assertEqual(first, second); self.assertEqual(original, self.path.read_bytes())
        self.assertEqual(initial, receipt.read_bytes())
        self.assertTrue(self.api.calls); self.assertIn(('server', 999), self.cloud.calls)
        self.assertTrue((self.root / '.factory/test-job/handled').is_file())

    def test_missing_uncommitted_or_inconsistent_outcomes_need_model_before_network(self):
        for flaw in ('uncommitted', 'uncollected', 'exit-code'):
            with self.subTest(flaw=flaw):
                value = json.loads(json.dumps(self.record))
                if flaw == 'uncommitted': value['note'] = 'new uncommitted result'
                elif flaw == 'uncollected': value.pop('collected_at')
                else: value['result']['exit_code'] = 1
                write_json(self.path, value)
                if flaw != 'uncommitted': self.commit()
                result = self.run_bookkeeping(); self.assertFalse(result['handled'], result)
                self.assertFalse(self.cloud.calls); self.assertFalse(self.api.calls)
                write_json(self.path, self.record)
                if flaw != 'uncommitted': self.commit()

    def test_staging_digest_live_server_and_leftover_ip_never_mark_handled(self):
        for flaw in ('staging', 'server', 'ip'):
            with self.subTest(flaw=flaw):
                self.api.bad_digest = flaw == 'staging'
                self.cloud.live = {'id': 999} if flaw == 'server' else None
                self.cloud.ips = [{'ip': '192.0.2.1', 'labels': {}, 'assignee_id': None}] if flaw == 'ip' else []
                result = self.run_bookkeeping(); self.assertFalse(result['handled'], result)
                self.assertFalse((self.root / '.factory/test-job/handled').exists())

    def test_local_report_disagreement_and_symlink_refuse(self):
        local = self.root / '.factory/test-job/result.json'; write_json(local, {'status': 'running'})
        self.assertFalse(self.run_bookkeeping()['handled'])
        self.assertFalse(self.api.calls)
        local.unlink(); local.symlink_to(self.path)
        self.assertFalse(self.run_bookkeeping()['handled'])

    def test_old_manual_handled_note_is_preserved_after_live_reverification(self):
        marker = self.root / '.factory/test-job/handled'; marker.parent.mkdir(parents=True)
        marker.write_text('Original Scout close-out note\n')
        self.assertTrue(self.run_bookkeeping()['handled'])
        self.assertEqual('Original Scout close-out note\n', marker.read_text())

    def test_ipv4_reuse_on_a_different_server_is_not_old_job_residue(self):
        self.cloud.ips = [{'ip': '192.0.2.1', 'labels': {'job': 'different-job'}, 'assignee_id': 1000}]
        self.assertTrue(self.run_bookkeeping()['handled'])

    def test_replay_never_uses_new_ledger_or_substantive_work_as_a_skippable_session(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/replay-worker-followups.py'
        spec = importlib.util.spec_from_file_location('followup_replay', path)
        replay = importlib.util.module_from_spec(spec); spec.loader.exec_module(replay)
        commit = 'b' * 40; parent = 'a' * 40
        changed = ['STATE.md']; record = self.record
        def git(*args):
            if args[0] == 'ls-tree': return b'jobs/test-job.json\n'
            if args[0] == 'log':
                return ('\0'.join([commit, 'Scout (Hermes)', '2026-11-07T19:00:00Z',
                                   'Follow-up: test-job handled']) + '\n').encode()
            if args[0] == 'diff-tree': return ('\n'.join(changed) + '\n').encode()
            if args[0] == 'rev-parse': return parent.encode()
            if args[0] == 'diff': return b'+test-job previously recorded\n'
            if args[0] == 'show':
                self.assertEqual(parent + ':jobs/test-job.json', args[1])
                return json.dumps(record).encode()
            raise AssertionError(args)
        with patch.object(replay, 'git', side_effect=git):
            result = replay.replay(commit, '2026-10-31', '2026-11-08')
            self.assertEqual(1, result['eligible_if_live_checks_pass'])
            self.assertIsNone(result['actual_model_sessions_saved'])
            changed.append('candidates/example/record.json')
            self.assertEqual(0, replay.replay(commit, '2026-10-31', '2026-11-08')['eligible_if_live_checks_pass'])
            changed.pop(); record = dict(self.record, status='running')
            self.assertEqual(0, replay.replay(commit, '2026-10-31', '2026-11-08')['eligible_if_live_checks_pass'])


if __name__ == '__main__': unittest.main()
