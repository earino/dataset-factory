"""Drop-in scorer for an OWNED execution copy of the existing harness.

Original train.py/predict_proba contract and sklearn metrics; prediction inputs are delivered
chronologically, one row per committed response, into a networkless Docker container. No
holdout file or label ledger is mounted. This does not verify historical feature availability.
"""
from __future__ import annotations
import json
import csv
import hashlib
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

CHILD = r'''
import contextlib, io, json, runpy, sys
import numpy as np
import pandas as pd
with contextlib.redirect_stdout(sys.stderr):
    ns = runpy.run_path("train.py", run_name="__train__")
fn = ns.get("predict_proba")
if not callable(fn):
    raise RuntimeError("no predict_proba")
print("FACTORY_READY", flush=True)
for line in sys.stdin:
    df = pd.read_json(io.StringIO(line), orient="table")
    if len(df) != 1:
        raise RuntimeError("exactly one prediction row required")
    with contextlib.redirect_stdout(sys.stderr):
        p = np.asarray(fn(df), dtype=float).ravel()
    if len(p) != 1 or not np.isfinite(p[0]) or not 0 <= p[0] <= 1:
        raise RuntimeError("invalid probability")
    print(json.dumps(float(p[0])), flush=True)
'''


def docker_command(folder, image, name, threads, job_id=None):
    if not image or image.startswith('-') or any(c.isspace() for c in image):
        raise ValueError('explicit trusted BENCH_IMAGE required')
    labels = []
    if job_id is not None:
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,80}', job_id):
            raise ValueError('invalid worker job identity')
        labels = ['--label', 'factory.smoke.job=' + job_id]
    return ['docker', 'run', *labels, '--rm', '-i', '--init', '--name', name,
            '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '128',
            '--cpus', str(threads), '--memory', '4g', '--user', '1000:1000',
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=512m', '--tmpfs', '/app/data:ro,size=1m',
            '--mount', f'type=bind,src={folder},dst=/work,readonly', '-w', '/work',
            '-e', f'BENCH_THREADS={threads}', '-e', f'OMP_NUM_THREADS={threads}',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '--entrypoint', '/app/.venv/bin/python',
            image, '-u', '/work/factory_child.py']


def receive(proc, deadline):
    pending = getattr(proc, '_factory_pending', b'')
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ)
        while b'\n' not in pending:
            if len(pending) > 65536:
                raise ValueError('oversized prediction response')
            if not selector.select(max(0, deadline - time.monotonic())):
                raise TimeoutError('prediction protocol deadline exceeded')
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError('predictor exited before returning a committed prediction')
            pending += chunk
    line, pending = pending.split(b'\n', 1)
    proc._factory_pending = pending
    if len(line) > 65536:
        raise ValueError('oversized prediction response')
    return line.decode().strip()


def assert_scoring_separate(scored, development, id_columns):
    """Reject accidental test exposure, even when a file was renamed or reordered."""
    if not id_columns:
        raise ValueError('reviewed task.id_columns required for split separation')
    def keys(path):
        with Path(path).open(newline='') as stream:
            reader = csv.DictReader(stream)
            if not set(id_columns) <= set(reader.fieldnames or []):
                raise ValueError('split separation ID columns missing')
            for row in reader:
                yield tuple(row[col] for col in id_columns)
    scored_keys = set(keys(scored))
    if not scored_keys:
        raise ValueError('empty scoring split')
    for path in development:
        if Path(path).resolve() == Path(scored).resolve() or any(key in scored_keys for key in keys(path)):
            raise ValueError('scoring rows overlap mounted development inputs')


def main():
    import pandas as pd
    from sklearn.metrics import average_precision_score, roc_auc_score
    started = time.monotonic()
    csv_path, target, positive = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    time_col = os.environ.get('FACTORY_PREDICTION_TIME_COLUMN')
    if not time_col:
        raise ValueError('FACTORY_PREDICTION_TIME_COLUMN must name the reviewed ordering column')
    frame = pd.read_csv(csv_path)
    dev_eval = Path(os.environ.get('FACTORY_DEV_EVAL', 'data/eval.csv'))
    task = json.loads(Path('task.json').read_text())
    assert_scoring_separate(csv_path, [Path('data/train.csv'), dev_eval], task.get('id_columns'))
    if time_col not in frame or frame[time_col].isna().any():
        raise ValueError('prediction ordering column missing or incomplete')
    times = pd.to_datetime(frame[time_col], utc=True, errors='raise')
    order = times.sort_values(kind='stable').index
    # This parent owns all labels/features. The container has only whitelisted development inputs.
    y = (frame[target] == positive).astype(int).to_numpy()
    features = frame.drop(columns=[target]); predictions = [None] * len(frame)
    deadline = time.monotonic() + int(os.environ.get('FACTORY_SCORE_TIMEOUT', '3600'))
    threads = int(os.environ.get('BENCH_THREADS', '4'))
    if not 1 <= threads <= 64:
        raise ValueError('invalid thread allowance')
    name = 'factory-predict-' + uuid.uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix='factory-prediction-') as tmp:
        folder = Path(tmp); folder.chmod(0o755); (folder/'data').mkdir()
        for rel in ('train.py', 'task.json', 'data/train.csv', 'data/eval.csv'):
            source = dev_eval if rel == 'data/eval.csv' else Path(rel)
            if source.is_symlink() or not source.is_file():
                raise ValueError(f'non-regular development input: {rel}')
            shutil.copyfile(source, folder/rel); (folder/rel).chmod(0o444)
        (folder/'factory_child.py').write_text(CHILD)
        (folder/'factory_child.py').chmod(0o444)
        # Only worker-host execution is supported; nested host-path mappings are deliberately refused.
        if os.environ.get('BENCH_IN_DOCKER'):
            raise ValueError('run scorer on worker host with its execution-copy venv, not nested Docker')
        command = docker_command(folder, os.environ.get('BENCH_IMAGE'), name, threads,
                                 job_id=os.environ.get('FACTORY_WORKER_JOB_ID'))
        # Candidate stderr is untrusted and must not fill worker disk.
        with open(os.devnull, 'w') as logs:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=logs, text=True, bufsize=1)
            try:
                if receive(proc, deadline) != 'FACTORY_READY':
                    raise RuntimeError('predictor initialization failed')
                for index in order:
                    proc.stdin.write(features.iloc[[index]].to_json(orient='table', index=False) + '\n')
                    proc.stdin.flush()
                    value = json.loads(receive(proc, deadline))
                    if type(value) not in (int, float) or not 0 <= value <= 1:
                        raise ValueError('invalid prediction response')
                    predictions[index] = value  # irrevocable before the next row is sent
                proc.stdin.close()
                proc.wait(timeout=max(1, deadline-time.monotonic()))
                if proc.returncode:
                    raise RuntimeError('predictor failed at closeout')
            finally:
                if proc.poll() is None:
                    proc.kill(); proc.wait()
                subprocess.run(['docker','rm','-f',name], capture_output=True, timeout=30)
    prediction_bytes = (json.dumps(predictions, separators=(',', ':')) + '\n').encode()
    if os.environ.get('FACTORY_PREDICTIONS_OUTPUT'):
        # Trusted parent output, written only after all predictions are committed; never mounted.
        with open(os.environ['FACTORY_PREDICTIONS_OUTPUT'], 'xb') as output:
            output.write(prediction_bytes)
    print(json.dumps({'auc':float(roc_auc_score(y,predictions)),
                      'ap':float(average_precision_score(y,predictions)), 'n':len(y),
                      'positives':int(y.sum()), 'protocol':'chronological-row-stream-v1',
                      'seconds':round(time.monotonic()-started,1),
                      'predictions_sha256':hashlib.sha256(prediction_bytes).hexdigest(),
                      'prediction_time_column':time_col}))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error':str(exc)}))
        sys.exit(1)
