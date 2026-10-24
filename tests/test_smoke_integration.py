"""Worker orchestration software tests; real-data acceptance runs only on a worker."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from workers import executor, smoke_runner as runner


class RuntimeTests(unittest.TestCase):
    def test_process_output_and_deadline_are_bounded(self):
        self.assertEqual(runner.checked_run([sys.executable,'-c','print("ok")'],3),'ok\n')
        with self.assertRaisesRegex(RuntimeError,'output limit'):
            runner.checked_run([sys.executable,'-c','print("x"*100000)'],3,limit=100)
        with self.assertRaises(TimeoutError):
            runner.checked_run([sys.executable,'-u','-c','import time; print("partial",end=""); time.sleep(10)'],.1)
        with self.assertRaisesRegex(RuntimeError,'exit 2'):
            runner.checked_run([sys.executable,'-c','raise SystemExit(2)'],3)

    def test_preserves_all_existing_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            owned=runner.owned_directory(base,'owned')
            (owned/'evidence').write_text('retain')
            foreign=base/'foreign';foreign.mkdir();(foreign/'important').write_text('retain')
            for name in ('owned','foreign','../escape'):
                with self.assertRaises(ValueError):runner.owned_directory(base,name)
            self.assertEqual((owned/'evidence').read_text(),'retain')
            self.assertEqual((foreign/'important').read_text(),'retain')

    def test_failed_build_diagnostics_are_private_bounded_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'diagnostic.log'
            command=[sys.executable,'-c','import sys; print("x"*50000); print("build error",file=sys.stderr); raise SystemExit(2)']
            with self.assertRaisesRegex(RuntimeError,'exit 2'):
                runner.checked_run(command,3,diagnostic_path=path)
            raw=path.read_bytes()
            self.assertIn(b'build error',raw)
            self.assertLessEqual(len(raw),65700)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):
                runner.checked_run(command,3,diagnostic_path=path)
            self.assertEqual(path.read_bytes(),raw)
            success=Path(tmp)/'success.log'
            runner.checked_run([sys.executable,'-c','print("ok")'],3,diagnostic_path=success)
            self.assertFalse(success.exists())

    def test_image_bootstrap_pin_preserves_original_and_refuses_unknown_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir();work=root/'work';work.mkdir()
            original='ARG HERMES_COMMIT='+ 'a'*40 +'\nRUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash\n'
            (source/'Dockerfile').write_text(original);(source/'uv.lock').write_text('unchanged')
            context,receipt=runner.prepare_image_context(source,work)
            self.assertEqual((source/'Dockerfile').read_text(),original)
            self.assertEqual((context/'uv.lock').read_text(),'unchanged')
            self.assertIn('${HERMES_COMMIT}/scripts/install.sh', (context/'Dockerfile').read_text())
            self.assertNotEqual(receipt['original_dockerfile_sha256'],receipt['execution_dockerfile_sha256'])
            self.assertEqual(receipt['hermes_commit'],'a'*40)
            with self.assertRaises(ValueError):runner.prepare_image_context(source,work)
            (source/'Dockerfile').write_text(original.replace('ARG HERMES_COMMIT=', 'ARG UNKNOWN='))
            with self.assertRaisesRegex(ValueError,'explicit review'):runner.prepare_image_context(source,work)

    def test_pinned_source_materialization_verifies_bytes_commit_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'source').mkdir();dest=base/'dest';dest.mkdir()
            raw=b'original source\n';digest=hashlib.sha256(raw).hexdigest();commit='a'*40
            name='image/bench/train.py'
            entry={'base64':base64.b64encode(raw).decode(),'sha256':digest}
            manifest={'harness_commit':commit,'files':{name:entry}}
            job={'smoke':{'harness_commit':commit,'pinned_sources':{name:digest}}}
            path=base/'source/pinned.json';path.write_text(json.dumps(manifest))
            runner.materialize_pinned(base,job,dest)
            self.assertEqual((dest/name).read_bytes(),raw)
            entry['base64']=base64.b64encode(b'changed').decode();path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):runner.materialize_pinned(base,job,dest)
            manifest['harness_commit']='b'*40;path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):runner.materialize_pinned(base,job,dest)
            manifest={'harness_commit':commit,'files':{'../escape':entry}}
            job['smoke']['pinned_sources']={'../escape':digest};path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):runner.materialize_pinned(base,job,dest)
            self.assertFalse((base/'escape').exists())

    def test_agreement_rejects_invalid_or_different_vectors(self):
        self.assertTrue(runner.assert_agreement([.1,.9],[.1,.9],1e-12)['passed'])
        for actual,expected in (([],[]),([.1],[.1,.2]),([float('nan')],[.1]),([True],[1]),([.1],[.2])):
            with self.assertRaises(ValueError):runner.assert_agreement(actual,expected,1e-12)

    def test_docker_ownership_requires_empty_daemon_and_exact_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);job={'id':'smoke-1'}
            with patch.object(runner,'docker_ids',return_value=['a'*12]):
                with self.assertRaises(ValueError):runner.establish_docker_ownership(base,job)
            self.assertFalse((base/'smoke-docker-owner.json').exists())
            with patch.object(runner,'docker_ids',return_value=[]):runner.establish_docker_ownership(base,job)
            with self.assertRaises(ValueError):runner.cleanup_owned_docker(base,{'id':'other'})
            with patch.object(runner,'docker_ids',side_effect=[['a'*12],[]]), patch.object(runner,'checked_run') as run:
                self.assertEqual(runner.cleanup_owned_docker(base,job),['a'*12])
                run.assert_called_once_with(['docker','rm','-f','a'*12],30)

    def test_actual_host_dispatch_records_failure_and_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'job.json').write_text(json.dumps({'id':'smoke-1','smoke_adapter':True}))
            receipt=base/'receipt.json'
            def fail(base,job,report):
                report['stage']='qualification';raise ValueError('sensitive details excluded')
            with patch.object(runner,'smoke_run',side_effect=fail):executor.host_child(base,'smoke_adapter',receipt)
            result=json.loads(receipt.read_text())
            self.assertEqual(result['status'],'failed');self.assertEqual(result['stage'],'qualification')
            self.assertNotIn('sensitive',receipt.read_text())

    def test_supervisor_cleans_daemon_containers_after_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with patch.object(executor,'supervise_host',return_value={'status':'failed','failure':'timeout','host_cleanup_complete':True}), patch.object(runner,'cleanup_owned_docker',return_value=['a'*12]) as cleanup:
                result=executor.execute_host(base,{'id':'smoke-1'},'smoke_adapter',time.monotonic())
                cleanup.assert_called_once_with(base,{'id':'smoke-1'})
                self.assertEqual(result['supervisor_containers_removed'],['a'*12])
            with patch.object(executor,'supervise_host',return_value={'status':'succeeded','host_cleanup_complete':True}), patch.object(runner,'cleanup_owned_docker',side_effect=ValueError):
                result=executor.execute_host(base,{'id':'smoke-1'},'smoke_adapter',time.monotonic())
                self.assertFalse(result['host_cleanup_complete']);self.assertEqual(result['status'],'failed')


class JobValidationTests(unittest.TestCase):
    def test_actual_worker_plan_requires_complete_pins_and_safe_modes(self):
        import copy
        from factory import worker
        from factory.common import FactoryError
        root=Path(__file__).resolve().parents[1]
        job=json.loads((root/'ops/smoke/austin-adapter-smoke-001.job.json').read_text())
        config=json.loads((root/'config/worker.example.json').read_text())
        config.update(server_types={job['server_type']:'0.0179'},allowed_locations=[job['location']],max_job_minutes=200,max_lifetime_minutes=240)
        required=('image/Dockerfile','image/.dockerignore','image/uv.lock','image/pyproject.toml',
                  'image/task_template/train.py','image/bench/score_holdout.py','adapter/score_holdout.py','gate/qualify_dataset.py','workers/smoke_artifact.py')
        job['smoke']['pinned_sources']={name:'a'*64 for name in required}
        self.assertEqual(worker.validate(job,config)['job']['id'],job['id'])
        for mutate in (
            lambda j:j['smoke'].update(pinned_sources={}),
            lambda j:j['smoke']['pinned_sources'].update({'../escape':'a'*64}),
            lambda j:j.update(transfer={'source_repo':'unexpected'}),
            lambda j:j.update(dataset='unreviewed'),
            lambda j:j['smoke'].update(score_timeout=0),
            lambda j:j['smoke'].update(tolerance=float('nan')),
        ):
            bad=copy.deepcopy(job);mutate(bad)
            with self.assertRaises(FactoryError):worker.validate(bad,config)
