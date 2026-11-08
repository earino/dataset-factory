import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from factory import audit_model_session as session
from factory.common import FactoryError


class SessionEvidenceTests(unittest.TestCase):
    def connect(self):
        con=sqlite3.connect(self.db)
        self.addCleanup(con.close)
        return con

    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.db=self.root/'state.db'
        with self.connect() as con:
            con.executescript('CREATE TABLE sessions(id TEXT,source TEXT,tool_names TEXT);'
                'CREATE TABLE messages(session_id TEXT,role TEXT,tool_calls TEXT);'
                'CREATE TABLE system_prompts(hash TEXT,prompt TEXT);'
                'CREATE TABLE session_model_usage(session_id TEXT,task TEXT,model TEXT,billing_provider TEXT,'
                'api_call_count INTEGER,input_tokens INTEGER,output_tokens INTEGER,cache_read_tokens INTEGER,cache_write_tokens INTEGER);')
            con.execute('INSERT INTO sessions VALUES (?,?,?)',('s','oneshot',None))
            con.execute('INSERT INTO messages VALUES (?,?,?)',('s','assistant',None))
            con.execute('INSERT INTO session_model_usage VALUES (?,?,?,?,?,?,?,?,?)',
                        ('s','','configured-model','configured-provider',1,100,20,10,0))

    def test_measurement_uses_actual_session_usage_including_cache(self):
        self.assertEqual({'s'},session.sessions(self.db,'oneshot'))
        value=session.measured(self.db,'s','oneshot')
        self.assertEqual(130,value['tokens'])
        self.assertEqual('unrecorded',value['tool_pin'])
        self.assertEqual(0,value['attempted_tool_calls'])

    def test_tool_call_or_offered_tools_or_missing_accounting_refuses(self):
        for sql in ("UPDATE messages SET tool_calls='[{\"name\":\"terminal\"}]'",
                    "UPDATE messages SET role='tool'",
                    "UPDATE sessions SET tool_names='[\"terminal\"]'",
                    "DELETE FROM session_model_usage"):
            with self.connect() as con:
                con.execute(sql)
            with self.assertRaises(ValueError):session.measured(self.db,'s','oneshot')
            with self.connect() as con:
                con.execute("UPDATE messages SET role='assistant',tool_calls=NULL")
                con.execute('UPDATE sessions SET tool_names=NULL')

    def test_hash_tool_pin_is_resolved_instead_of_assumed_empty(self):
        with self.connect() as con:
            con.execute('UPDATE sessions SET tool_names=?',('a'*64,))
            con.execute('INSERT INTO system_prompts VALUES (?,?)',('a'*64,json.dumps({'tools':[]})))
        self.assertEqual('verified_empty',session.measured(self.db,'s','oneshot')['tool_pin'])

    def test_hold_blocks_before_any_model_or_budget_process(self):
        (self.root/'config').mkdir()
        (self.root/'config/admission.json').write_text(json.dumps({'version':1,'hold':True,
             'reason':'remediation','allowed_worker_bundles':{}}))
        with patch.object(session,'wrapper') as wrapper:
            with self.assertRaises(FactoryError):session.run(self.root,'dataset',self.root/'out')
            wrapper.assert_not_called()

    def test_runtime_pin_and_live_zero_tool_probe_both_required(self):
        root=self.root;hermes=root/'hermes';hermes.mkdir();(root/'config').mkdir()
        for name in session.RUNTIME_FILES:
            path=hermes/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('reviewed source')
        policy={'reviewed':True,'source_sha256':{n:session.sha256(hermes/n) for n in session.RUNTIME_FILES}}
        (root/'config/adversarial-runtime.json').write_text(json.dumps(policy))
        runner=Mock(return_value=subprocess.CompletedProcess([],0,b'',b''))
        with patch.dict('os.environ',{},clear=True):
            self.assertTrue(session.preflight(root,hermes,runner)['preflight_empty_definitions'])
            runner.return_value=subprocess.CompletedProcess([],1,b'',b'')
            with self.assertRaisesRegex(ValueError,'zero-tool capability failed'):session.preflight(root,hermes,runner)
            (hermes/'model_tools.py').write_text('upgraded source')
            runner.reset_mock()
            with self.assertRaisesRegex(ValueError,'runtime changed'):session.preflight(root,hermes,runner)
            runner.assert_not_called()


if __name__=='__main__':unittest.main()
