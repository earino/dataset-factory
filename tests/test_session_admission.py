"""Real subprocess admission tests; only local stubs, never Hermes or a worker."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'scripts/scout_research_session.py'
spec = importlib.util.spec_from_file_location('session_admission_wrapper', PATH)
wrapper = importlib.util.module_from_spec(spec)
exec(compile(PATH.read_bytes(), str(PATH), 'exec'), wrapper.__dict__)
ALLOW = '{"researchBudget": {"allowed": true, "reasons": []}}'
HOLD = '{"researchBudget": {"allowed": false, "reasons": ["cap reached"]}}'


class GateResponseTests(unittest.TestCase):
    def decision(self, text, code=0):
        result = subprocess.CompletedProcess([], code, text, 'private diagnostic')
        with patch.object(wrapper.subprocess, 'run', return_value=result):
            return wrapper.run_gate()

    def test_only_explicit_success_admits(self):
        self.assertEqual((True, 'context', 'clear'), self.decision('context\n' + ALLOW))

    def test_false_directive_and_budget_hold_are_accepted_in_either_order(self):
        for text in (HOLD + '\n{"wakeAgent": false}', '{"wakeAgent": false}\n' + HOLD):
            self.assertEqual((False, '', 'cap reached'), self.decision(text))

    def test_nonzero_exit_never_admits_even_with_valid_allow(self):
        with self.assertRaisesRegex(wrapper.AdmissionError, 'exited 1'):
            self.decision(ALLOW, 1)

    def test_missing_malformed_ambiguous_and_conflicting_decisions_refuse(self):
        invalid = ['', 'context', '{"wakeAgent": {}}', '{"wakeAgent": true}',
                   '{"researchBudget": null}', '{"researchBudget": []}',
                   '{"researchBudget": {"allowed": 1, "reasons": []}}',
                   '{"researchBudget": {"allowed": "true", "reasons": []}}',
                   '{"researchBudget": {"allowed": true}}',
                   '{"researchBudget": {"allowed": true, "reasons": ["cap"]}}',
                   '{"researchBudget": {"allowed": false, "reasons": []}}',
                   '{"researchBudget": {"allowed": true, "allowed": false, "reasons": []}}',
                   ALLOW + '\n' + ALLOW, ALLOW + '\n' + HOLD,
                   ALLOW + '\n{"wakeAgent": false}', HOLD + '\n{"wakeAgent": true}',
                   ALLOW + '\n{"wakeAgent": true}\n{"wakeAgent": true}',
                   ALLOW + '\n{"broken":', ALLOW + '\n{"unknown": true}']
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(wrapper.AdmissionError):
                self.decision(text)

    def test_timeouts_and_spawn_failures_refuse_without_private_stderr(self):
        for exc in (FileNotFoundError('secret'), subprocess.TimeoutExpired([], 120)):
            with patch.object(wrapper.subprocess, 'run', side_effect=exc):
                with self.assertRaises(wrapper.AdmissionError) as raised:
                    wrapper.run_gate()
                self.assertNotIn('secret', str(raised.exception))

    def test_gate_uses_this_checkout_config_and_same_marker(self):
        with patch.object(wrapper.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 0, ALLOW, '')) as run:
            wrapper.run_gate(4)
        command = run.call_args.args[0]
        self.assertEqual(str(wrapper.REPO / 'config/research-budget.json'),
                         command[command.index('--config') + 1])
        self.assertEqual(str(wrapper.LOCK), run.call_args.kwargs['env']['SCOUT_BUDGET_LOCK'])
        self.assertEqual('4', command[-1])


class SessionOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for key, value in {'FACTORY_DIR': root, 'LOCK': root / 'marker',
                           'LOG': root / 'log'}.items():
            patcher = patch.object(wrapper, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_session(self, result=None, error=None):
        with patch.object(wrapper, 'run_gate', return_value=(True, '', 'clear')), \
                patch.object(wrapper, 'run_agent', return_value=result, side_effect=error), \
                contextlib.redirect_stdout(io.StringIO()):
            code = wrapper.main([])
        self.assertFalse(wrapper.LOCK.exists())
        return code, json.loads(wrapper.LOG.read_text().splitlines()[-1])

    def test_agent_failure_is_failure_not_completed_scheduler_tick(self):
        code, entry = self.run_session(subprocess.CompletedProcess([], 7, '', ''))
        self.assertEqual(7, code)
        self.assertEqual('exit 7', entry['outcome'])

    def test_agent_success_is_zero(self):
        self.assertEqual(0, self.run_session(subprocess.CompletedProcess([], 0, 'done', ''))[0])

    def test_timeout_returns_124(self):
        self.assertEqual(124, self.run_session(error=subprocess.TimeoutExpired([], 1))[0])

    def test_missing_agent_returns_2(self):
        self.assertEqual(2, self.run_session(error=FileNotFoundError())[0])

    def test_gate_failure_starts_no_agent(self):
        with patch.object(wrapper, 'run_gate', side_effect=wrapper.AdmissionError('bad gate')), \
                patch.object(wrapper, 'run_agent') as run, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, wrapper.main([]))
        run.assert_not_called()
        self.assertEqual('admission_failed', json.loads(wrapper.LOG.read_text())['event'])

    def test_nonpositive_runtime_limits_are_rejected(self):
        for args in (['--run-budget', '0'], ['--max-turns', '-1']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                wrapper.main(args)

    def test_mutex_is_not_unlinked_and_reacquires_after_release(self):
        with wrapper.admission_lock():
            inode = (wrapper.FACTORY_DIR / 'research-session.mutex').stat().st_ino
            with self.assertRaises(wrapper.SessionBusy):
                with wrapper.admission_lock():
                    self.fail('admitted twice')
        with wrapper.admission_lock():
            self.assertEqual(inode, (wrapper.FACTORY_DIR / 'research-session.mutex').stat().st_ino)

    def test_busy_checkpoint_keeps_deterministic_fallback_report(self):
        with wrapper.admission_lock(), patch.object(wrapper.subprocess, 'run') as run, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, wrapper.main(['--fallback-report']))
        self.assertIn('--digest', run.call_args.args[0])
        self.assertIn('Held, so no model work ran', output.getvalue())

    def test_replacement_marker_is_preserved(self):
        from argparse import Namespace
        args = Namespace(max_turns=1, run_budget=1)
        with wrapper.session_marker(args):
            payload = json.loads(wrapper.LOCK.read_text())
            self.assertEqual(os.getpid(), payload['pid'])
            self.assertIn('written_at', payload)
            wrapper.LOCK.write_text('replacement evidence')
        self.assertEqual('replacement evidence', wrapper.LOCK.read_text())

    def test_dry_run_does_not_write_marker_or_start_agent(self):
        with patch.object(wrapper, 'run_gate', return_value=(True, '', 'clear')), \
                patch.object(wrapper, 'run_agent') as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, wrapper.main(['--dry-run']))
        run.assert_not_called()
        self.assertFalse(wrapper.LOCK.exists())

    def test_symlink_mutex_refuses_without_modifying_target(self):
        target = wrapper.FACTORY_DIR / 'unrelated'
        target.write_text('preserve')
        (wrapper.FACTORY_DIR / 'research-session.mutex').symlink_to(target)
        with self.assertRaises(OSError):
            with wrapper.admission_lock():
                self.fail('admitted')
        self.assertEqual('preserve', target.read_text())


class ProcessAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.processes = []
        self.addCleanup(self.stop_processes)
        # The gate pauses before its decision so another wrapper contests the
        # exact old check-then-write race window, not merely an existing marker.
        (self.root / 'gate.py').write_text(
            'from pathlib import Path\nimport time\n'
            'Path("gate-entered").touch()\n'
            'while not Path("gate-release").exists(): time.sleep(.01)\n'
            f'print({ALLOW!r})\n')
        (self.root / 'agent.py').write_text(
            'from pathlib import Path\nimport os,time\n'
            'Path("agent-pid").write_text(str(os.getpid()))\n'
            'while not Path("agent-release").exists(): time.sleep(.01)\n'
            'print("stub completed")\n')
        (self.root / 'driver.py').write_text(
            'import runpy,sys\nfrom pathlib import Path\n'
            f'm = runpy.run_path({str(PATH)!r})\n'
            'g = m["main"].__globals__\nr=Path.cwd()\n'
            'g.update(REPO=r, FACTORY_DIR=r/"state", LOCK=r/"state/marker", '
            'LOG=r/"state/log", BUDGET=r/"gate.py", HERMES_PYTHON=sys.executable, '
            'HERMES_CLI=str(r/"agent.py"))\n'
            'sys.exit(m["main"]([]))\n')

    def stop_processes(self):
        pid_path = self.root / 'agent-pid'
        if pid_path.exists():
            try:
                os.killpg(int(pid_path.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)

    def spawn(self):
        p = subprocess.Popen([sys.executable, str(self.root / 'driver.py')], cwd=self.root,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(p)
        return p

    def wait_for(self, name):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if (self.root / name).exists():
                return
            time.sleep(.01)
        self.fail(f'local fixture never wrote {name}')

    def test_competing_tick_is_held_before_first_gate_finishes(self):
        first = self.spawn()
        self.wait_for('gate-entered')
        second = self.spawn()
        second.communicate(timeout=10)
        self.assertEqual(0, second.returncode)
        self.assertFalse((self.root / 'agent-pid').exists())
        self.assertIn('admission lock', (self.root / 'state/log').read_text())
        (self.root / 'gate-release').touch()
        self.wait_for('agent-pid')
        (self.root / 'agent-release').touch()
        out, err = first.communicate(timeout=10)
        self.assertEqual(0, first.returncode, err)
        self.assertIn('stub completed', out)

    def test_wrapper_death_does_not_unlock_its_still_running_agent(self):
        (self.root / 'gate-release').touch()
        first = self.spawn()
        self.wait_for('agent-pid')
        first.kill()
        first.wait(timeout=10)
        second = self.spawn()
        second.communicate(timeout=10)
        self.assertEqual(0, second.returncode)
        self.assertIn('admission lock', (self.root / 'state/log').read_text())
        (self.root / 'agent-release').touch()

    def test_completed_agent_does_not_signal_a_recyclable_group_id(self):
        script = self.root / 'complete.py'
        script.write_text('print("finished")\n')
        with patch.object(wrapper, 'FACTORY_DIR', self.root / 'state'):
            with wrapper.admission_lock() as fd:
                with patch.object(wrapper.os, 'killpg') as kill:
                    result = wrapper.run_agent([sys.executable, str(script)], 5, fd)
        self.assertEqual(0, result.returncode)
        self.assertEqual('finished\n', result.stdout)
        kill.assert_not_called()

    def test_outer_timeout_terminates_agent_process_group(self):
        script = self.root / 'hang.py'
        script.write_text('import time\ntime.sleep(60)\n')
        with patch.object(wrapper, 'FACTORY_DIR', self.root / 'state'):
            with wrapper.admission_lock() as fd:
                with self.assertRaises(subprocess.TimeoutExpired):
                    wrapper.run_agent([sys.executable, str(script)], .1, fd)
            with wrapper.admission_lock():
                pass


if __name__ == '__main__':
    unittest.main()
