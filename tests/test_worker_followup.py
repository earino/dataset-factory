"""Watcher and research must not write concurrently; tests use no provider or worker."""
import contextlib
import fcntl
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    import scout_worker_followup as followup
finally:
    sys.path.pop(0)


class WorkerFollowupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        self.paths = patch.multiple(followup.session, FACTORY_DIR=self.state,
                                   LOCK=self.state / 'marker', LOG=self.state / 'log')
        self.paths.start()

    def tearDown(self):
        self.paths.stop()
        self.temp.cleanup()

    def test_empty_and_running_ticks_start_no_agent(self):
        for jobs in ([], ['running-job']):
            with self.subTest(jobs=jobs), patch.object(followup.watch, 'watchlist', return_value=jobs), \
                    patch.object(followup.watch, 'state_of', return_value={'job':'running-job','state':'running'}), \
                    patch.object(followup.session, 'run_session') as run, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(0, followup.main())
                run.assert_not_called()
                self.assertEqual('', output.getvalue())

    def test_shared_lock_covers_collection_and_entire_followup(self):
        def assert_locked():
            fd = os.open(self.state / 'research-session.mutex', os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)
        def collect(job):
            assert_locked()
            return {'job':job,'state':'failed','exit_code':1}
        def run(args, fd):
            assert_locked()
            self.assertIn('job-one: failed', args.extra)
            self.assertEqual('docs/worker-watch-prompt.md', args.prompt_file)
            self.assertFalse(args.if_work)
            self.assertLessEqual(args.run_budget, 5400)
            return 7
        with patch.object(followup.watch, 'watchlist', return_value=['job-one']), \
                patch.object(followup.watch, 'state_of', side_effect=collect), \
                patch.object(followup.session, 'run_session', side_effect=run):
            self.assertEqual(7, followup.main())
        with followup.session.admission_lock():
            pass  # automatically released after the follow-up returned

    def test_an_actual_competing_process_neither_collects_nor_launches(self):
        script = self.root / 'compete.py'
        touched = self.root / 'touched'
        script.write_text(
            'import sys\nfrom pathlib import Path\n'
            f'sys.path.insert(0, {str(ROOT / "scripts")!r})\n'
            'import scout_worker_followup as f\n'
            f'f.session.FACTORY_DIR=Path({str(self.state)!r})\n'
            f'f.watch.watchlist=lambda: Path({str(touched)!r}).write_text("bad")\n'
            'sys.exit(f.main())\n')
        with followup.session.admission_lock():
            result = subprocess.run([sys.executable, str(script)], capture_output=True,
                                    text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('', result.stdout)
        self.assertFalse(touched.exists())

    def test_held_budget_never_starts_model_or_acknowledges_event(self):
        with patch.object(followup.watch, 'watchlist', return_value=['job-one']), \
                patch.object(followup.watch, 'state_of', return_value={'job':'job-one','state':'failed'}), \
                patch.object(followup.session, 'run_gate', return_value=(False,'context','token ceiling')), \
                patch.object(followup.session, 'run_agent') as agent:
            self.assertEqual(0, followup.main())
            agent.assert_not_called()
        self.assertFalse((self.state / 'job-one' / 'handled').exists())

    def test_invalid_accounting_is_reported_as_failure(self):
        with patch.object(followup.watch, 'watchlist', return_value=['job-one']), \
                patch.object(followup.watch, 'state_of', return_value={'job':'job-one','state':'gone'}), \
                patch.object(followup.session, 'run_gate', side_effect=followup.session.AdmissionError('missing ledger')), \
                patch.object(followup.session, 'run_agent') as agent, \
                contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(2, followup.main())
            self.assertIn('missing ledger', error.getvalue())
            agent.assert_not_called()

    def test_unknown_collection_is_not_silently_treated_as_running(self):
        with patch.object(followup.watch, 'watchlist', return_value=['job-one']), \
                patch.object(followup.watch, 'state_of', return_value={'job':'job-one','state':'unknown','detail':'timeout'}), \
                patch.object(followup.session, 'run_session', return_value=124) as run:
            self.assertEqual(124, followup.main())
            self.assertIn('unknown', run.call_args.args[0].extra)


if __name__ == '__main__':
    unittest.main()
