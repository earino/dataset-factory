"""The optional hosted decision experiment must not reset or omit its spend."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

PATH=Path(__file__).resolve().parents[1]/'evals/research-prompts/run_one.py'
spec=importlib.util.spec_from_file_location('prompt_eval',PATH)
eval_run=importlib.util.module_from_spec(spec)
exec(compile(PATH.read_bytes(),str(PATH),'exec'),eval_run.__dict__)


class PromptEvalAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_missing_corrupt_pending_and_inconsistent_ledgers_never_become_zero(self):
        path=self.root/'ledger.json'
        with self.assertRaises(FileNotFoundError): eval_run.read_ledger(path)
        path.write_text('{')
        with self.assertRaises(ValueError): eval_run.read_ledger(path)
        for data in ({'schema':1,'calls':1,'tokens':0,'runs':[{'status':'pending','tokens':None}]},
                     {'schema':1,'calls':1,'tokens':0,'runs':[]},
                     {'schema':1,'calls':1,'tokens':0,'runs':[{'status':'ok','tokens':100}]}):
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): eval_run.read_ledger(path)

    def database(self, pin=None):
        path=self.root/'state.db'; con=sqlite3.connect(path)
        con.executescript('CREATE TABLE sessions(id TEXT, source TEXT, tool_names TEXT);'
                          'CREATE TABLE messages(session_id TEXT, role TEXT);'
                          'CREATE TABLE system_prompts(hash TEXT, prompt TEXT);'
                          'CREATE TABLE session_model_usage(session_id TEXT, task TEXT, api_call_count INT, input_tokens INT, output_tokens INT);')
        con.execute('INSERT INTO sessions VALUES (?,?,?)',('case','scout-research',pin))
        con.executemany('INSERT INTO session_model_usage VALUES (?,?,?,?,?)',
                        [('case','',1,1000,200),('case','title_generation',1,100,20)])
        con.commit(); con.close(); return path

    def test_auxiliary_tokens_count_and_unrecorded_tools_stay_unrecorded(self):
        result=eval_run.measured_session(self.database(),'case')
        self.assertEqual(1320,result['tokens'])
        self.assertEqual(2,result['calls'])
        self.assertEqual('unrecorded',result['recorded_tool_pin'])

    def test_hashed_empty_tool_pin_is_resolved(self):
        pin='a'*64; db=self.database(pin); con=sqlite3.connect(db)
        con.execute('INSERT INTO system_prompts VALUES (?,?)',(pin,json.dumps({'tools':[]})))
        con.commit(); con.close()
        self.assertEqual('verified_empty',eval_run.measured_session(db,'case')['recorded_tool_pin'])

    def test_nonempty_tools_and_tool_execution_refuse(self):
        db=self.database('["terminal"]')
        with self.assertRaises(ValueError): eval_run.measured_session(db,'case')
        con=sqlite3.connect(db); con.execute('UPDATE sessions SET tool_names=NULL')
        con.execute('INSERT INTO messages VALUES (?,?)',('case','tool')); con.commit(); con.close()
        with self.assertRaises(ValueError): eval_run.measured_session(db,'case')

    def test_invalid_usage_and_wrong_source_refuse(self):
        db=self.database(); con=sqlite3.connect(db)
        con.execute('UPDATE sessions SET source="scout-eval"');con.commit()
        with self.assertRaises(ValueError): eval_run.measured_session(db,'case')
        con.execute('UPDATE sessions SET source="scout-research"')
        con.execute('UPDATE session_model_usage SET input_tokens=-1');con.commit();con.close()
        with self.assertRaises(ValueError): eval_run.measured_session(db,'case')

    def test_context_marker_in_any_parent_refuses(self):
        (self.root/'AGENTS.md').write_text('parent instructions')
        child=self.root/'nested'; child.mkdir()
        with self.assertRaises(ValueError): eval_run.neutral(child)


if __name__=='__main__': unittest.main()
