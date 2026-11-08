from contextlib import closing, nullcontext
from pathlib import Path
import sqlite3
import subprocess
import json
import tempfile
import unittest
from unittest.mock import patch, Mock

from factory.model_tasks import ModelTasks, TaskFailure, parse_response, usage, startup_diagnostic, runtime_session


class ModelTaskTests(unittest.TestCase):
    def test_exit_one_retains_construction_or_negative_research_but_not_acceptance(self):
        from factory.common import write_json, read_json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / 'config/research-budget.json', {'session_max_turns': 6, 'session_max_minutes': 5})
            with closing(sqlite3.connect(root / 'state.db')) as db:
                db.execute('CREATE TABLE sessions(id,source)')
            w = Mock(); w.SessionBusy = RuntimeError
            w.admission_lock.return_value = nullcontext(42)
            w.session_marker.return_value = nullcontext()
            w.run_gate.return_value = (True, '', '')
            w.strip_footer.side_effect = lambda value: value
            quality = read_json(Path(__file__).resolve().parents[1] /
                                'skills/dataset-qualification/fixtures/corrected/quality.json')
            proposal = {'build_py': 'def build(output, cache):\n    pass\n', 'references': {}, 'quality': quality}
            measured = {'tasks': [{'task': '', 'model': 'requested'}], 'tool_results': 0}
            model = ModelTasks(root, {'model': 'requested', 'research_toolset': 'web', 'code_turns': 6,
                                     'research_turns': 12, 'task_seconds': 300}, hermes_home=root)
            with patch('factory.model_tasks.wrapper', return_value=w), \
                    patch('factory.model_tasks.subprocess.run') as preflight, \
                    patch('factory.model_tasks.usage', return_value=measured):
                preflight.return_value.returncode = 0
                w.run_agent.return_value = subprocess.CompletedProcess('hermes', 1, json.dumps(proposal), '')
                self.assertEqual(proposal, model.run('produced', 'builder', construction=True))
                self.assertIn(str(root.resolve() / 'factory/hermes_write_task.py'), w.run_agent.call_args.args[0])
                self.assertEqual([], read_json(root / '.factory/model-tasks/produced/attempt.json')['toolsets'])
                # The same exit code and JSON are not enough to accept a review.
                with self.assertRaises(TaskFailure): model.run('review', 'review prompt')
                w.run_agent.return_value = subprocess.CompletedProcess('hermes', 1, '{"error":"gave up"}', '')
                with self.assertRaises(TaskFailure): model.run('failed', 'builder', construction=True)
                for verdict in ('defer', 'reject'):
                    negative = {'verdict': verdict, 'reason': 'No readable applicable source terms'}
                    w.run_agent.return_value = subprocess.CompletedProcess('hermes', 1, json.dumps(negative), '')
                    self.assertEqual(negative, model.run(verdict, 'terms review', research=True))
                    self.assertTrue(read_json(root / '.factory/model-tasks' / verdict /
                                              'failure.json')['usable_negative_verdict'])
                for verdict in ('ready', 'accept'):
                    positive = {'verdict': verdict, 'reason': 'claimed success', 'findings': []}
                    w.run_agent.return_value = subprocess.CompletedProcess('hermes', 1, json.dumps(positive), '')
                    with self.assertRaises(TaskFailure): model.run(verdict, 'review', research=True)
                w.run_agent.return_value = subprocess.CompletedProcess('hermes', 1, '{"verdict":"defer"}', '')
                with self.assertRaises(TaskFailure): model.run('missing-reason', 'review', research=True)
            folder = root / '.factory/model-tasks/produced'
            self.assertTrue(read_json(folder / 'failure.json')['usable_construction_proposal'])
            self.assertEqual(1, read_json(folder / 'usage.json')['completion_exit_code'])
            self.assertTrue((folder / 'response.json').is_file())
            self.assertFalse((root / '.factory/model-tasks/failed/response.json').exists())

    def test_timeout_retains_actual_partial_usage_and_diagnostic(self):
        from factory.common import write_json, read_json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / 'config/research-budget.json', {'session_max_turns': 3, 'session_max_minutes': 5})
            path = root / 'state.db'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('''CREATE TABLE sessions(id,source);
                    CREATE TABLE messages(session_id,role);
                    CREATE TABLE session_model_usage(session_id,task,model,billing_provider,
                        api_call_count,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens);''')
            w = Mock()
            w.admission_lock.return_value = nullcontext(42)
            w.run_gate.return_value = (True, '', '')
            w.session_marker.return_value = nullcontext()
            w.SessionBusy = RuntimeError
            def timed_out(*args):
                with closing(sqlite3.connect(path)) as db:
                    db.execute("INSERT INTO sessions VALUES('new','oneshot')")
                    db.execute("INSERT INTO session_model_usage VALUES('new',NULL,'requested','nous',2,100,20,0,0)")
                    db.commit()
                raise subprocess.TimeoutExpired('hermes', 330, stderr=b'provider stalled\nsession_id: new\n')
            w.run_agent.side_effect = timed_out
            policy = {'model': 'requested', 'research_toolset': 'web', 'code_turns': 2, 'task_seconds': 300}
            model = ModelTasks(root, policy, hermes_home=root)
            with patch('factory.model_tasks.wrapper', return_value=w), patch('factory.model_tasks.subprocess.run') as preflight:
                preflight.return_value.returncode = 0
                with self.assertRaisesRegex(TaskFailure, 'wall-clock'):
                    model.run('bounded-task', 'test prompt')
            folder = root / '.factory/model-tasks/bounded-task'
            self.assertEqual('timeout', read_json(folder / 'failure.json')['error'])
            actual = read_json(folder / 'usage.json')
            self.assertTrue(actual['partial'])
            self.assertEqual(2, actual['tasks'][0]['calls'])
            self.assertFalse((folder / 'response.json').exists())

    def test_startup_failure_keeps_cause_without_credentials(self):
        with patch.dict('os.environ', {'PROVIDER_API_KEY': 'short-private-value'}):
            result = startup_diagnostic('RuntimeError: unavailable\n' +
                'https://service.example/?token=secret Bearer credentials\n' +
                'api_key="another-secret" short-private-value hf_hiddencredential')
        self.assertIn('RuntimeError: unavailable', result)
        for secret in ('service.example', 'credentials', 'another-secret', 'short-private-value', 'hf_hiddencredential'):
            self.assertNotIn(secret, result)

    def test_structured_response_and_malformed_failure(self):
        self.assertEqual(parse_response('```json\n{"verdict":"ready"}\n```'), {'verdict': 'ready'})
        self.assertEqual(parse_response('Warning: Unknown toolsets: __none__\n{"ok":true}'), {'ok': True})
        for raw in ('ready', '[]', '{"code":"' + 'x' * (256 * 1024) + '"}'):
            with self.assertRaises(TaskFailure):
                parse_response(raw)

    def test_completed_task_reused_without_model_or_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / '.factory/model-tasks/example'
            folder.mkdir(parents=True)
            (folder / 'prompt.txt').write_text('original')
            (folder / 'response.json').write_text('{"code":"pass"}')
            model = ModelTasks(tmp, {})
            self.assertEqual(model.run('example', 'original'), {'code': 'pass'})
            with self.assertRaises(TaskFailure):
                model.run('example', 'changed')

    def test_usage_includes_failed_calls_and_tool_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.db'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('''CREATE TABLE sessions(id,source);
                    CREATE TABLE messages(session_id,role);
                    CREATE TABLE session_model_usage(session_id,task,model,billing_provider,
                        api_call_count,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens);
                    INSERT INTO sessions VALUES('old','oneshot'),('new','oneshot');
                    INSERT INTO messages VALUES('new','tool');
                    INSERT INTO session_model_usage VALUES('new',NULL,'requested','nous',2,100,20,0,0);''')
                db.commit()
            actual = usage(path, ['old'])
            self.assertEqual(actual['session_id'], 'new')
            self.assertEqual(actual['tasks'][0]['input_tokens'], 100)
            self.assertEqual(actual['tool_results'], 1)
            with self.assertRaises(TaskFailure):
                usage(path, [])
            with closing(sqlite3.connect(path)) as db:
                db.execute("INSERT INTO sessions VALUES('unrelated','oneshot')")
                db.commit()
            self.assertEqual('new', runtime_session('notice\nsession_id: new\n'))
            self.assertEqual('new', usage(path, ['old'], 'new')['session_id'])
            with self.assertRaises(TaskFailure):
                usage(path, ['old'], 'old')


if __name__ == '__main__':
    unittest.main()
