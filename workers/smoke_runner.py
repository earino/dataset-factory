"""Supervised worker-only integration of the real baseline and chronological adapter."""
from __future__ import annotations
import base64
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shutil
import subprocess
import sys
import time
import urllib.request


def sha256_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_run(command, timeout, *, env=None, cwd=None, limit=2*1024*1024, diagnostic_path=None):
    """Bound actual pipe output and elapsed time, not only the final read size."""
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd)
    buffers = {proc.stdout: bytearray(), proc.stderr: bytearray()}
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as ready:
            for stream in buffers: ready.register(stream, selectors.EVENT_READ)
            while ready.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise TimeoutError('smoke subprocess deadline exceeded')
                for key, _ in ready.select(min(remaining, .2)):
                    block = os.read(key.fileobj.fileno(), 8192)
                    if not block: ready.unregister(key.fileobj); continue
                    buffers[key.fileobj].extend(block)
                    if sum(map(len, buffers.values())) > limit:
                        raise RuntimeError('smoke subprocess output limit exceeded')
            proc.wait(timeout=max(.01, deadline-time.monotonic()))
        if proc.returncode:
            # Commands have no secret arguments, but arbitrary process output is not a receipt.
            raise RuntimeError(f'smoke subprocess failed: {Path(command[0]).name}, exit {proc.returncode}')
        return buffers[proc.stdout].decode()
    except Exception:
        if diagnostic_path is not None:
            # Opt-in only for the trusted, credential-free image build. Keep two
            # bounded tails on the worker, outside output/ and automatic uploads.
            fd = os.open(diagnostic_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as diagnostic:
                for label, stream in ((b'stdout', proc.stdout), (b'stderr', proc.stderr)):
                    diagnostic.write(label + b' (last 32768 bytes):\n')
                    diagnostic.write(buffers[stream][-32768:] + b'\n')
        raise
    finally:
        if proc.poll() is None: proc.kill(); proc.wait(timeout=10)
        proc.stdout.close(); proc.stderr.close()


def owned_directory(base, name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name):
        raise ValueError('unsafe smoke directory name')
    path = Path(base)/name
    if path.exists() or path.is_symlink():
        raise ValueError('smoke output already exists; preserve it and use a new job')
    path.mkdir(mode=0o700)
    (path/'.smoke-owned').write_text('smoke runner: preserve until worker destruction\n')
    return path


def materialize_pinned(base, job, destination):
    path = Path(base)/'source'/'pinned.json'
    if path.is_symlink() or path.stat().st_size > 2*1024*1024:
        raise ValueError('unsafe pinned source manifest')
    manifest = json.loads(path.read_text())
    files = manifest['files']
    expected = job['smoke']['pinned_sources']
    if not expected or set(files) != set(expected) or manifest['harness_commit'] != job['smoke']['harness_commit']:
        raise ValueError('source provenance differs from reviewed job')
    total = 0
    for name, entry in files.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')) or '\\' in name:
            raise ValueError('unsafe pinned source path')
        raw = base64.b64decode(entry['base64'], validate=True); total += len(raw)
        if total > 2*1024*1024 or hashlib.sha256(raw).hexdigest() != expected[name] or entry['sha256'] != expected[name]:
            raise ValueError('pinned source digest/size differs')
        target = destination/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return manifest


def public_readable(folder):
    folder.chmod(0o755)
    for path in folder.rglob('*'):
        if path.is_symlink(): raise ValueError('no symlinks in inference inputs')
        path.chmod(0o755 if path.is_dir() else 0o444)


def assert_agreement(actual, expected, tolerance):
    if not actual or len(actual) != len(expected): raise ValueError('prediction vector length differs')
    if any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in actual+expected):
        raise ValueError('invalid probability vector')
    maximum = max(abs(a-b) for a,b in zip(actual,expected))
    if maximum > tolerance: raise ValueError('prediction vector exceeds reviewed tolerance')
    return {'n':len(actual),'max_abs_delta':maximum,'tolerance':tolerance,'passed':True}


def docker_ids():
    values = checked_run(['docker','ps','-aq'],30).split()
    if len(values)>32 or any(not re.fullmatch(r'[a-f0-9]{12,64}',v) for v in values):
        raise ValueError('unexpected Docker inventory on dedicated smoke worker')
    return values


def establish_docker_ownership(base, job):
    # One freshly provisioned VM belongs to this one job; no shared Docker daemon is accepted.
    if docker_ids(): raise ValueError('smoke requires an empty dedicated worker Docker daemon')
    marker = base/'smoke-docker-owner.json'
    with marker.open('x') as stream: json.dump({'job_id':job['id'],'initial_containers':[]},stream)


def cleanup_owned_docker(base, job):
    marker = Path(base)/'smoke-docker-owner.json'
    if not marker.exists(): return []
    if marker.is_symlink() or marker.stat().st_size>1024 or json.loads(marker.read_text()) != {'job_id':job['id'],'initial_containers':[]}:
        raise ValueError('Docker ownership marker differs')
    removed = docker_ids()
    for identity in removed: checked_run(['docker','rm','-f',identity],30)
    if docker_ids(): raise ValueError('smoke containers remain after cleanup')
    return removed


def load_adapter(path):
    spec=importlib.util.spec_from_file_location('factory_stream_adapter',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


PROBE_TRAIN = r'''
import os, pathlib, select, socket
import numpy as np
calls=0
expected={'train.py','task.json','data/train.csv','data/eval.csv','factory_child.py'}
assert {str(p.relative_to('/work')) for p in pathlib.Path('/work').rglob('*') if p.is_file()} == expected
assert not list(pathlib.Path('/app/data').iterdir())
assert not pathlib.Path('/opt/scout/credentials.json').exists()
assert not any('TOKEN' in k or 'SECRET' in k for k in os.environ)
try:
    socket.create_connection(('1.1.1.1',53),timeout=1).close()
except OSError:
    pass
else:
    raise RuntimeError('unexpected outbound network')
def predict_proba(frame):
    global calls
    assert len(frame)==1
    assert not select.select([__import__('sys').stdin],[],[],0)[0], 'future row released before commitment'
    calls+=1
    return np.array([calls/10.0])
'''
REFERENCE = r'''
import contextlib,json,runpy,sys
import numpy as np
import pandas as pd
with contextlib.redirect_stdout(sys.stderr):
    ns=runpy.run_path('train.py',run_name='__train__')
    task=json.load(open('task.json'))
    frame=pd.read_csv('data/test.csv').drop(columns=[task['target']])
    p=np.asarray(ns['predict_proba'](frame),dtype=float).ravel()
print(json.dumps([float(v) for v in p]))
'''


def protocol_probe(work, adapter, image, job, dev, task):
    stage=owned_directory(work,'protocol-probe'); (stage/'data').mkdir()
    (stage/'train.py').write_text(PROBE_TRAIN)
    (stage/'factory_child.py').write_text(adapter.CHILD)
    (stage/'task.json').write_text(json.dumps(task))
    # This is a software protocol fixture, not an acceptance dataset or a performance score.
    for name in ('train','eval'): (stage/'data'/f'{name}.csv').write_text('probe\n')
    (stage/'.smoke-owned').unlink()  # Exact marker we just created; mount only protocol inputs.
    public_readable(stage)
    name='scout-probe-'+job['id']
    command=adapter.docker_command(str(stage), image, name, job['cpus'], job_id=job['id'])
    proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    deadline=time.monotonic()+120
    try:
        if adapter.receive(proc,deadline)!='FACTORY_READY':raise ValueError('probe initialization failed')
        details=json.loads(checked_run(['docker','inspect',name],30))[0]
        if details['HostConfig']['NetworkMode']!='none':raise ValueError('probe network mode differs')
        if details['HostConfig'].get('Binds'):raise ValueError('unexpected probe bind mount')
        # Feed three row-shaped protocol fixtures; require each commitment before sending the next.
        frame={'schema':{'fields':[{'name':'probe','type':'integer'}],'pandas_version':'1.4.0'},'data':[{'probe':1}]}
        for index in range(1,4):
            proc.stdin.write(json.dumps(frame)+'\n');proc.stdin.flush()
            if json.loads(adapter.receive(proc,deadline)) != index/10:raise ValueError('probe commitment differs')
        proc.stdin.close();proc.wait(timeout=30)
        if proc.returncode:raise ValueError('probe failed')
        return {'network_mode':'none','outbound_refused':True,'only_whitelisted_inputs':True,
                'no_credentials_or_image_data':True,'committed_before_next_row':True,'software_fixture_only':True}
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        proc.stdout.close()
        if not proc.stdin.closed:proc.stdin.close()
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)


def smoke_run(base, job, report):
    base=Path(base);smoke=job['smoke'];receipts={};report['smoke']=receipts
    work=owned_directory(base,'smoke-work')
    sources=owned_directory(work,'sources')
    manifest=materialize_pinned(base,job,sources)
    receipts['provenance']={'harness_commit':manifest['harness_commit'],'source_hashes':smoke['pinned_sources']}
    establish_docker_ownership(base,job)
    try:
        report['stage']='image_build'
        image=smoke['image_tag'];context=sources/'image'
        diagnostic = base/'smoke-build-diagnostic.log'
        try:
            checked_run(['docker','build','--quiet','--force-rm','-t',image,str(context)],3600,
                        env={**os.environ,'DOCKER_BUILDKIT':'0'}, diagnostic_path=diagnostic)
        except Exception:
            if diagnostic.is_file():
                receipts['build_diagnostic'] = {'worker_file':diagnostic.name,
                    'bytes':diagnostic.stat().st_size, 'sha256':sha256_file(diagnostic),
                    'automatically_uploaded':False}
            raise
        receipts['image_id']=json.loads(checked_run(['docker','image','inspect',image],30))[0]['Id']
        report['stage']='host_environment'
        extract='scout-extract-'+job['id']
        checked_run(['docker','create','--name',extract,image],30)
        uv=work/'uv'
        checked_run(['docker','cp',extract+':/home/bench/.local/bin/uv',str(uv)],30)
        checked_run(['docker','rm',extract],30);uv.chmod(0o755)
        host=owned_directory(work,'host-env')
        for filename in ('pyproject.toml','uv.lock'):shutil.copyfile(context/filename,host/filename)
        checked_run([str(uv),'sync','--frozen','--no-dev','--no-install-project','--python','3.13'],1200,cwd=host)
        python=host/'.venv/bin/python'
        receipts['host_lock_sha256']=sha256_file(host/'uv.lock')
        receipts['host_python']=checked_run([str(python),'--version'],30).strip()
        report['stage']='public_source_fetch'
        input_dir=owned_directory(work,'input')
        for logical,filename in [('public/train.csv','train.csv'),('public/eval.csv','eval.csv'),('meta.json','meta.json'),('quality.json','quality.json')]:
            url=f"https://github.com/earino/{job['dataset']}/releases/download/{smoke['release_tag']}/{filename}"
            with urllib.request.urlopen(url,timeout=120) as response, (input_dir/filename).open('xb') as output:
                shutil.copyfileobj(response,output,length=1024*1024)
            if sha256_file(input_dir/filename)!=smoke['expected_sha256'][logical]:raise ValueError('public source digest differs')
        report['stage']='derivative_and_gate'
        build_derivative=load_adapter(sources/'workers/smoke_artifact.py').build_derivative
        derivative=owned_directory(work,'derivative')
        receipts['derivative']=build_derivative(input_dir,derivative,smoke)
        gate=sources/'gate/qualify_dataset.py';gate_report=base/'output'/'smoke-qualification.json'
        checked_run([sys.executable,str(gate),str(derivative),'--report',str(gate_report)],1800)
        if json.loads(gate_report.read_text()).get('ok') is not True:raise ValueError('qualification did not pass')
        checked_run([sys.executable,str(gate),'--accept',str(gate_report),str(derivative)],1800)
        receipts['qualification']={'report_sha256':sha256_file(gate_report),'accepted':True}
        adapter_path=sources/'adapter/score_holdout.py';adapter=load_adapter(adapter_path)
        receipts['adapter_sha256']=sha256_file(adapter_path)
        receipts['original_scorer_sha256']=sha256_file(context/'bench/score_holdout.py')
        task_meta=json.loads((derivative/'meta.json').read_text())
        task={k:task_meta[k] for k in ('name','description','target','positive_label','id_columns','split','columns','rows') if k in task_meta}
        report['stage']='protocol_probe'
        receipts['protocol']=protocol_probe(work,adapter,image,job,derivative,task)
        stage=owned_directory(work,'baseline');(stage/'data').mkdir()
        (stage/'task.json').write_text(json.dumps(task))
        shutil.copyfile(context/'task_template/train.py',stage/'train.py')
        for split in ('train','eval'):shutil.copyfile(derivative/'public'/f'{split}.csv',stage/'data'/f'{split}.csv')
        report['stage']='stream_baseline';predictions=work/'stream-predictions.json'
        env={**os.environ,'FACTORY_PREDICTION_TIME_COLUMN':smoke['time_column'],
             'FACTORY_PREDICTIONS_OUTPUT':str(predictions),'BENCH_IMAGE':image,
             'BENCH_THREADS':str(job['cpus']),'FACTORY_SCORE_TIMEOUT':str(smoke['score_timeout']),
             'FACTORY_WORKER_JOB_ID':job['id']}
        started=time.monotonic()
        result=checked_run([str(python),str(adapter_path),str(derivative/'private/holdout.csv'),
                           smoke['target'],json.dumps(smoke['positive_label'])],smoke['score_timeout']+60,env=env,cwd=stage)
        measured=json.loads(result.strip().splitlines()[-1])
        receipts['stream']={k:measured[k] for k in ('n','seconds','predictions_sha256','protocol')}
        reference=owned_directory(work,'reference');(reference/'data').mkdir()
        for filename in ('train.py','task.json','data/train.csv','data/eval.csv'):shutil.copyfile(stage/filename,reference/filename)
        shutil.copyfile(derivative/'private/holdout.csv',reference/'data/test.csv')
        (reference/'reference.py').write_text(REFERENCE);public_readable(reference)
        report['stage']='reference_baseline'
        name='scout-reference-'+job['id']
        cmd=adapter.docker_command(str(reference),image,name,job['cpus'],job_id=job['id'])
        cmd[-1]='/work/reference.py'
        reference_out=checked_run(cmd,1800,limit=16*1024*1024)
        expected=json.loads(reference_out.strip().splitlines()[-1]);actual=json.loads(predictions.read_text())
        receipts['agreement']=assert_agreement(actual,expected,smoke['tolerance'])
        receipts['baseline_template_sha256']=sha256_file(context/'task_template/train.py')
        receipts['baseline_seconds']=round(time.monotonic()-started,2)
        report['stage']='complete'
    finally:
        receipts['containers_removed_at_close']=cleanup_owned_docker(base,job)
