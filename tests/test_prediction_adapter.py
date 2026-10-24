"""Protocol/software tests only; not substitute benchmark acceptance tasks."""
import importlib.util
from pathlib import Path
import sys
import subprocess
import time
import tempfile
import unittest

PATH=Path(__file__).resolve().parents[1]/'adapters/score_holdout.py'
spec=importlib.util.spec_from_file_location('stream_adapter',PATH)
adapter=importlib.util.module_from_spec(spec)
exec(compile(PATH.read_bytes(),str(PATH),'exec'),adapter.__dict__)

class AdapterTests(unittest.TestCase):
    def test_scored_rows_cannot_be_mounted_even_after_renaming(self):
        with tempfile.TemporaryDirectory() as tmp:
            scored=Path(tmp)/'test.csv'; dev=Path(tmp)/'development.csv'
            scored.write_text('id,x,target\na,1,0\nb,2,1\n')
            dev.write_text('id,x,target\nb,2,1\na,1,0\n')
            with self.assertRaisesRegex(ValueError,'overlap'):
                adapter.assert_scoring_separate(scored,[dev],['id'])
            dev.write_text('id,x,target\nc,3,0\n')
            adapter.assert_scoring_separate(scored,[dev],['id'])
            with self.assertRaisesRegex(ValueError,'id_columns'):
                adapter.assert_scoring_separate(scored,[dev],[])

    def test_inference_has_no_network_or_holdout_mount(self):
        command=adapter.docker_command('/worker/whitelist','trusted-image:local','test',2)
        self.assertEqual(command[command.index('--network')+1],'none')
        self.assertIn('--read-only',command)
        self.assertIn('/app/data:ro,size=1m',command)
        self.assertEqual(command.count('--mount'),1)
        self.assertNotIn('holdout', ' '.join(command))
        self.assertNotIn('TOKEN',' '.join(command))

    def test_image_must_be_explicit(self):
        for value in (None,'--privileged','name --network host'):
            with self.assertRaises(ValueError):adapter.docker_command('/tmp',value,'x',1)

    def test_protocol_reads_one_committed_response(self):
        proc=subprocess.Popen([sys.executable,'-u','-c','print("FACTORY_READY"); input(); print("0.25"); input()'],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(adapter.receive(proc,time.monotonic()+3),'FACTORY_READY')
            proc.stdin.write('one row\n');proc.stdin.flush()
            self.assertEqual(adapter.receive(proc,time.monotonic()+3),'0.25')
            with self.assertRaises(TimeoutError):adapter.receive(proc,time.monotonic()+.02)
        finally:
            proc.kill();proc.wait();proc.stdin.close();proc.stdout.close()

    def test_partial_line_cannot_bypass_protocol_deadline(self):
        proc=subprocess.Popen([sys.executable,'-u','-c','import sys; sys.stdout.write("0."); sys.stdout.flush(); input()'],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        try:
            with self.assertRaises(TimeoutError):adapter.receive(proc,time.monotonic()+.2)
        finally:
            proc.kill();proc.wait();proc.stdin.close();proc.stdout.close()
