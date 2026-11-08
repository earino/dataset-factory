"""One-time deployment correction for the observed startup/worker retry mix-up.

Run from the live checkout after deploying the retry-scope fix. No model, worker,
or publication is invoked; the existing coordinator performs the remaining work.
"""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from factory.common import FactoryError, read_json, write_json
from factory.pipeline import controller_lock
from factory.state import Store, encoded


def recover(root):
    root = Path(root)
    candidate_id = 'source-000001'
    attempt_id = 'rw-4fa4bc1fda01-build-3'
    receipt_path = root / '.factory' / 'initial-build-retry-correction.json'
    with controller_lock(root) as acquired:
        if not acquired:
            raise FactoryError('Controller busy; retry after the current tick')
        store = Store(root)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if row and json.loads(row['result']).get('retry_scope') == 'worker':
                return {'status': 'already-corrected'}
            candidate = store.get(candidate_id)
            job = read_json(root / 'jobs' / (attempt_id + '.json'))
            if (not row or row['status'] != 'retry' or row['stage'] != 'build'
                    or row['candidate'] != candidate_id or candidate['stage'] != 'deferred'
                    or job.get('status') != 'deleted' or job.get('result', {}).get('exit_code') != 1
                    or candidate['data'].get('construction_attempt') != attempt_id):
                raise FactoryError('Observed deployment failure no longer matches; no changes made')
            for ordinal in (1, 2):
                failure = read_json(root / '.factory/model-tasks' /
                                    f'rw-4fa4bc1fda01-build-{ordinal}' / 'failure.json')
                if (failure.get('exit_code') != 1 or '0 new sessions' not in encoded(failure)
                        or (root / 'jobs' / f'rw-4fa4bc1fda01-build-{ordinal}.json').exists()):
                    raise FactoryError('Earlier attempts are not the observed zero-session failures')
            before = {**dict(row), 'result': json.loads(row['result'])}
            receipt = {'candidate_before': candidate, 'attempt_before': before,
                       'reason': 'Separate zero-session startup failures from real worker repair attempts',
                       'corrected_at': time.time()}
            # Preserve the original state before committing the correction.
            if not receipt_path.exists():
                write_json(receipt_path, receipt)
            result = {**before['result'], 'retry_scope': 'worker'}
            db.execute('UPDATE attempts SET result=? WHERE id=?', (encoded(result), attempt_id))
            db.execute("UPDATE candidates SET stage='build',next_run=0,updated=?,reason=? WHERE id=?",
                       (time.time(), receipt['reason'], candidate_id))
        return {'status': 'corrected', 'candidate': candidate_id, 'receipt': str(receipt_path)}


if __name__ == '__main__':
    print(json.dumps(recover(ROOT), indent=2))
