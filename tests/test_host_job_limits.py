"""Worker-host supervisor regressions: local subprocesses, no Docker or network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from workers import executor


class HostSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.receipt = self.base / 'receipt.json'
        self.job = {'id': 'fixture', 'timeout_minutes': 1, 'max_disk_mb': 8}
        self.script = self.base / 'operation.py'
        from collections import namedtuple
        usage = namedtuple('usage', 'total used free')(4*1024**3, 2*1024**3, 2*1024**3)
        space = patch.object(executor.shutil, 'disk_usage', return_value=usage)
        space.start()
        self.addCleanup(space.stop)
        # du -sb is the deployed Linux command. Portable measurement for local
        # tests retains actual file-size observations instead of mocked counters.
        measure = patch.object(executor, 'disk_bytes', side_effect=lambda base:
                               sum(p.stat().st_size for p in base.rglob('*') if p.is_file()))
        measure.start()
        self.addCleanup(measure.stop)

    def run_operation(self, source, timeout=5):
        self.script.write_text(source)
        return executor.supervise_host(
            self.base, self.job, [sys.executable, str(self.script), str(self.receipt)],
            self.receipt, time.monotonic() + timeout, interval=.01)

    def success_source(self):
        return ('import json,sys\nfrom pathlib import Path\n'
                'Path(sys.argv[1]).write_text(json.dumps({"job_id":"fixture",'
                '"status":"succeeded","uploaded":False}))\n')

    def test_successful_operation_returns_compact_result(self):
        result = self.run_operation(self.success_source())
        self.assertEqual('succeeded', result['status'])
        self.assertFalse(result['uploaded'])

    def test_timeout_stops_actual_child_and_reports_failure(self):
        result = self.run_operation(
            'import os,time\nfrom pathlib import Path\n'
            f'Path({str(self.base / "pid")!r}).write_text(str(os.getpid()))\n'
            'time.sleep(60)\n', timeout=.2)
        self.assertEqual('runtime-limit', result['failure'])
        pid = int((self.base / 'pid').read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_disk_growth_is_detected_and_stopped(self):
        self.job['max_disk_mb'] = 1
        result = self.run_operation(
            'import time\nfrom pathlib import Path\n'
            f'Path({str(self.base / "large")!r}).write_bytes(b"x" * (2*1024*1024))\n'
            'time.sleep(60)\n')
        self.assertEqual('disk-limit', result['failure'])
        # Evidence remains on the worker for collection; no blanket cleanup.
        self.assertTrue((self.base / 'large').exists())

    def test_completed_operation_still_fails_if_it_exceeded_disk_limit(self):
        self.job['max_disk_mb'] = 1
        source = (self.success_source() +
                  f'Path({str(self.base / "large")!r}).write_bytes(b"x" * (2*1024*1024))\n')
        result = self.run_operation(source)
        self.assertEqual('disk-limit', result['failure'])
        self.assertEqual('failed', result['status'])

    def test_failed_child_receipt_preserves_diagnostics(self):
        source = ('import json,sys\nfrom pathlib import Path\n'
                  'Path(sys.argv[1]).write_text(json.dumps({"job_id":"fixture",'
                  '"status":"failed","uploaded":False,"failure":"provider-refused"}))\n')
        result = self.run_operation(source)
        self.assertEqual('failed', result['status'])
        self.assertEqual('provider-refused', result['failure'])

    def test_symlink_receipt_is_refused(self):
        target = self.base / 'unrelated'
        target.write_text('{"job_id":"fixture","status":"succeeded","uploaded":false}')
        self.receipt.symlink_to(target)
        result = self.run_operation('pass\n')
        self.assertEqual('invalid-host-receipt', result['failure'])
        self.assertTrue(self.receipt.is_symlink())

    def test_existing_disk_excess_refuses_before_starting(self):
        self.job['max_disk_mb'] = 1
        (self.base / 'existing').write_bytes(b'x' * (2*1024*1024))
        with patch.object(executor.subprocess, 'Popen') as spawn:
            result = self.run_operation(self.success_source())
        spawn.assert_not_called()
        self.assertEqual('disk-limit', result['failure'])

    def test_low_free_space_refuses_before_starting(self):
        from collections import namedtuple
        usage = namedtuple('usage', 'total used free')(100, 90, 10)
        with patch.object(executor.shutil, 'disk_usage', return_value=usage), \
                patch.object(executor.subprocess, 'Popen') as spawn:
            result = self.run_operation(self.success_source())
        spawn.assert_not_called()
        self.assertEqual('disk-limit', result['failure'])

    def test_monitor_error_refuses_before_starting(self):
        with patch.object(executor, 'disk_bytes', side_effect=OSError('secret path')), \
                patch.object(executor.subprocess, 'Popen') as spawn:
            result = self.run_operation(self.success_source())
        spawn.assert_not_called()
        self.assertEqual('resource-monitor-failed:OSError', result['failure'])
        self.assertNotIn('secret', json.dumps(result))

    def test_nonzero_exit_cannot_use_a_success_receipt(self):
        result = self.run_operation(self.success_source() + 'raise SystemExit(7)\n')
        self.assertEqual('host-operation-failed', result['failure'])
        self.assertEqual(7, result['exit_code'])

    def test_invalid_oversized_or_wrong_job_receipt_is_not_success(self):
        for body in ['{}', 'not json', 'x' * (executor.REPORT_LIMIT + 1),
                     '{"job_id":"other","status":"succeeded","uploaded":false}']:
            with self.subTest(size=len(body)):
                self.receipt.write_text(body)
                result = self.run_operation('pass\n')
                self.assertEqual('invalid-host-receipt', result['failure'])

    def test_client_caches_and_temporary_files_are_inside_budget_scope(self):
        source = ('import os,json,sys\nfrom pathlib import Path\n'
                  'keys=["TMPDIR","XDG_CACHE_HOME","UV_CACHE_DIR","PIP_CACHE_DIR",'
                  '"HF_HOME","HF_HUB_CACHE","HF_DATASETS_CACHE"]\n'
                  'Path(sys.argv[1]).write_text(json.dumps({"job_id":"fixture",'
                  '"status":"succeeded","uploaded":False,'
                  '"paths":{k:os.environ[k] for k in keys}}))\n')
        result = self.run_operation(source)
        for path in result['paths'].values():
            self.assertTrue(Path(path).is_relative_to(self.base))

    def test_normal_exit_kills_remaining_group_before_reaping_leader(self):
        # The grandchild has closed stdout/stderr and would escape a pipe-based
        # wait. Its heartbeat must stop even when the direct child exits 0.
        heartbeat = self.base / 'heartbeat'
        child = self.base / 'tool.py'
        child.write_text('import time\nfrom pathlib import Path\n'
                         f'p=Path({str(heartbeat)!r})\n'
                         'while True:\n p.write_text(str(time.monotonic()))\n time.sleep(.01)\n')
        source = (self.success_source() + 'import subprocess,time\n'
                  f'p=subprocess.Popen([sys.executable,{str(child)!r}])\n'
                  f'while not Path({str(heartbeat)!r}).exists(): time.sleep(.01)\n')
        result = self.run_operation(source)
        self.assertEqual('succeeded', result['status'])
        first = heartbeat.read_text()
        time.sleep(.05)
        self.assertEqual(first, heartbeat.read_text())

    def test_host_execute_does_not_run_docker_cleanup(self):
        for operation in ['transfer', 'hf_publish']:
            with patch.object(executor, 'execute_host', return_value=
                              {'job_id':'fixture','status':'succeeded','uploaded':False}) as host, \
                    patch.object(executor, 'stop_and_capture') as stop:
                result = executor.execute(self.base, {**self.job, operation: {'fixture': True}})
            self.assertEqual(operation, host.call_args.args[2])
            self.assertEqual('succeeded', result['status'])
            self.assertIn('elapsed_seconds', result)
            stop.assert_not_called()

    def test_filesystem_growth_outside_base_is_charged(self):
        from collections import namedtuple
        usage = namedtuple('usage', 'total used free')
        initial_free = 2 * 1024**3
        with patch.object(executor, 'disk_bytes', return_value=1024), \
                patch.object(executor.shutil, 'disk_usage', return_value=
                             usage(4*1024**3, 0, initial_free - 9*1024**2)):
            reason = executor.host_limit_reason(self.base, self.job,
                                               time.monotonic() + 5, (1024, initial_free))
        self.assertEqual('disk-limit', reason)

    def test_permission_error_with_live_group_member_is_not_ignored(self):
        from types import SimpleNamespace
        with patch.object(executor.os, 'killpg', side_effect=PermissionError()), \
                patch.object(executor, 'live_group_members', return_value=True):
            with self.assertRaises(PermissionError):
                executor.stop_unreaped_group(SimpleNamespace(pid=123))

    def test_standalone_worker_child_round_trip_for_both_modes(self):
        # Use the real executor entrypoint from the bundle, with fake local
        # provider modules. This exercises argv, imports, receipt and monitoring.
        source = self.base / 'bundle'
        source.mkdir()
        entrypoint = source / 'executor.py'
        entrypoint.write_bytes(Path(executor.__file__).read_bytes())
        (source / 'upload.py').write_text(
            'class UploadError(Exception): pass\n'
            'def publish(*args): pass\n'
            'def fetch(*args): pass\n'
            'def transfer(base,job,report): report["transfer"]={"failures":[]}\n')
        (source / 'hf_publish.py').write_text(
            'def hf_publish(base,job,report): report["hf_publish"]={"failures":[]}\n')
        for mode in ['transfer', 'hf_publish']:
            with self.subTest(mode=mode):
                job = {**self.job, mode: {'fixture': True}}
                (self.base / 'job.json').write_text(json.dumps(job))
                with patch.object(executor, '__file__', str(entrypoint)):
                    result = executor.execute(self.base, job)
                self.assertEqual('succeeded', result['status'], result)
                self.assertEqual([], result[mode]['failures'])
                self.assertFalse(result['uploaded'])
                self.assertFalse(list(self.base.glob('.host-operation-*')))

    def test_procfs_handles_parentheses_in_comm_and_ignores_zombies(self):
        root = self.base / 'proc'
        (root / '100').mkdir(parents=True)
        (root / '100/stat').write_text('100 (name ) with () parens) Z 1 123 123 0')
        self.assertFalse(executor.live_group_members(123, root))
        (root / '101').mkdir()
        (root / '101/stat').write_text('101 (worker) S 1 123 123 0')
        self.assertTrue(executor.live_group_members(123, root))
        self.assertFalse(executor.live_group_members(124, root))

    def test_missing_process_observation_refuses_before_spawn(self):
        with patch.object(executor, 'live_group_members', side_effect=FileNotFoundError()), \
                patch.object(executor.subprocess, 'Popen') as spawn:
            result = self.run_operation(self.success_source())
        spawn.assert_not_called()
        self.assertEqual('resource-monitor-failed:FileNotFoundError', result['failure'])

    def test_group_cleanup_resignals_late_arrivals(self):
        from types import SimpleNamespace
        with patch.object(executor.os, 'killpg') as kill, \
                patch.object(executor, 'live_group_members', side_effect=[True, False]), \
                patch.object(executor.time, 'sleep'):
            executor.stop_unreaped_group(SimpleNamespace(pid=123))
        self.assertEqual(2, kill.call_count)

    def test_uninterruptible_child_has_bounded_wait_and_unverified_cleanup(self):
        from unittest.mock import MagicMock
        process = MagicMock(pid=123, returncode=None)
        process.wait.side_effect = subprocess.TimeoutExpired([], 10)
        with patch.object(executor.subprocess, 'Popen', return_value=process), \
                patch.object(executor.os, 'waitid', return_value=object()), \
                patch.object(executor, 'live_group_members', return_value=False), \
                patch.object(executor, 'stop_unreaped_group', side_effect=ValueError()):
            result = self.run_operation(self.success_source())
        process.wait.assert_called_once_with(timeout=10)
        self.assertEqual('host-cleanup-incomplete', result['failure'])
        self.assertFalse(result['host_cleanup_complete'])

    def test_unverified_cleanup_cannot_publish_or_repeat_the_operation(self):
        (self.base / 'job.json').write_text(json.dumps(self.job))
        report = {'job_id':'fixture', 'status':'failed', 'uploaded':False,
                  'host_cleanup_complete':False, 'failure':'host-cleanup-incomplete'}
        (self.base / 'execution.json').write_text(json.dumps(report))
        with patch.object(executor, 'execute') as execute, \
                patch.object(executor, 'publish') as publish:
            self.assertEqual(1, executor.main(self.base))
        execute.assert_not_called()
        publish.assert_not_called()
        result = json.loads((self.base / 'result.json').read_text())
        self.assertFalse(result['uploaded'])
        self.assertIn('cleanup incomplete', result['upload_error'])

    def test_child_exception_has_no_raw_secret_in_report(self):
        (self.base / 'job.json').write_text(json.dumps({**self.job, 'transfer': {'fixture': True}}))
        with patch.object(executor, 'transfer', side_effect=RuntimeError('secret-token')):
            executor.host_child(self.base, 'transfer', self.receipt)
        result = json.loads(self.receipt.read_text())
        self.assertEqual('RuntimeError', result['failure'])
        self.assertNotIn('secret-token', self.receipt.read_text())


if __name__ == '__main__':
    unittest.main()


class DiskObservationTests(unittest.TestCase):
    def test_du_transient_race_is_retried_and_persistent_failure_fails_closed(self):
        """A file vanishing mid-walk makes du exit 1 after printing its total.

        Measured on job nz-ea-hf-002: `pip install datasets` churns the venv while the
        supervisor samples disk once a second, one du lost the race and the whole
        verify-only job was killed as resource-monitor-failed:CalledProcessError at
        46 s. One lost race must be retried, not read as a monitor failure; a
        persistent observation error still fails closed.
        """
        calls = []

        def fake_run(cmd, capture_output=True, timeout=None):
            calls.append(cmd)
            if len(calls) < 3:
                return subprocess.CompletedProcess(cmd, 1, b"", b"du: cannot access: No such file")
            return subprocess.CompletedProcess(cmd, 0, b"4096\t/opt/scout\n", b"")

        with patch.object(executor.subprocess, "run", side_effect=fake_run), \
             patch.object(executor.time, "sleep") as slept:
            self.assertEqual(executor.disk_bytes(Path("/opt/scout")), 4096)
            self.assertEqual(len(calls), 3)
            self.assertEqual(slept.call_count, 2)

        persistent = subprocess.CompletedProcess(["du"], 1, b"", b"du: cannot access")
        with patch.object(executor.subprocess, "run", return_value=persistent), \
             patch.object(executor.time, "sleep"):
            with self.assertRaises(subprocess.CalledProcessError):
                executor.disk_bytes(Path("/opt/scout"))
