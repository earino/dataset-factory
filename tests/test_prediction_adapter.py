"""Protocol/software tests only; not substitute benchmark acceptance tasks."""
import importlib.util
from pathlib import Path
import sys
import subprocess
import time
import unittest

PATH=Path(__file__).resolve().parents[1]/'adapters/score_holdout.py'
spec=importlib.util.spec_from_file_location('stream_adapter',PATH)
adapter=importlib.util.module_from_spec(spec)
exec(compile(PATH.read_bytes(),str(PATH),'exec'),adapter.__dict__)

class AdapterTests(unittest.TestCase):
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
