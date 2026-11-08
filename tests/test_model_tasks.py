from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from factory.model_tasks import ModelTasks, TaskFailure, parse_response, usage


class ModelTaskTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
