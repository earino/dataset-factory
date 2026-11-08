"""Small transactional operational store; research/code remain in Git."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time

from .common import FactoryError, identifier

STAGES = ('discover', 'build', 'evaluate', 'publish')
NEXT = dict(zip(STAGES, (*STAGES[1:], 'published')))


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def record_semantic_repair(data, review, attempt_id):
    history = data.setdefault('semantic_repairs', [])
    if not any(item['attempt'] == attempt_id for item in history):
        history.append({'attempt': attempt_id, 'review': review, 'job': data.get('job'),
                        'artifact_version': data.get('evidence', {}).get('MANIFEST.json', {}).get('artifact_version')})
    data['pending_semantic_review'] = review
    data['failure'] = {'stage': 'semantic_review', 'attempt': attempt_id, 'review': review}


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        folder = self.root / '.factory'
        if folder.is_symlink():
            raise FactoryError('Operational directory must not be a symlink')
        folder.mkdir(exist_ok=True)
        self.path = folder / 'pipeline.sqlite3'
        if self.path.is_symlink():
            raise FactoryError('Operational database must not be a symlink')
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY, stage TEXT NOT NULL, data TEXT NOT NULL,
                    created REAL NOT NULL, updated REAL NOT NULL,
                    next_run REAL NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY, candidate TEXT NOT NULL REFERENCES candidates(id),
                    stage TEXT NOT NULL, ordinal INTEGER NOT NULL, status TEXT NOT NULL,
                    started REAL NOT NULL, finished REAL, result TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(candidate, stage, ordinal));
                CREATE UNIQUE INDEX IF NOT EXISTS one_running_attempt
                    ON attempts(candidate) WHERE status = 'running';
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def candidate(row):
        return {**dict(row), 'data': json.loads(row['data'])} if row else None

    def add(self, candidate_id, data):
        identifier(candidate_id)
        stamp = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT * FROM candidates WHERE id=?', (candidate_id,)).fetchone()
            if prior:
                # An add retry cannot overwrite a progressed candidate.
                return self.candidate(prior)
            db.execute('INSERT INTO candidates(id,stage,data,created,updated) VALUES(?,?,?,?,?)',
                       (candidate_id, 'discover', encoded(data), stamp, stamp))
        return self.get(candidate_id)

    def get(self, candidate_id):
        with self.connect() as db:
            return self.candidate(db.execute('SELECT * FROM candidates WHERE id=?', (candidate_id,)).fetchone())

    def listing(self):
        with self.connect() as db:
            return [self.candidate(row) for row in db.execute('SELECT * FROM candidates ORDER BY created,id')]

    def reconcile_misrouted_reviews(self):
        """Correct the old repair->reject routing; preserve the original verdict/history."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute("SELECT * FROM candidates WHERE stage='rejected'").fetchall():
                data = json.loads(row['data']); review = data.get('review', {})
                if review.get('verdict') != 'repair' or not review.get('findings'):
                    continue
                last = db.execute('SELECT * FROM attempts WHERE candidate=? ORDER BY started DESC,id DESC LIMIT 1',
                                  (row['id'],)).fetchone()
                if (not last or last['stage'] != 'evaluate' or last['status'] != 'reject'
                        or json.loads(last['result']).get('reason') != review.get('reason')
                        or row['reason'] != review.get('reason') or data.get('review_routing_corrected')):
                    continue
                record_semantic_repair(data, review, last['id'])
                data['review_routing_corrected'] = {'attempt': last['id'], 'previous_reason': row['reason'],
                                                  'corrected_at': time.time()}
                db.execute("UPDATE candidates SET stage='build',data=?,updated=?,next_run=0,reason=? WHERE id=?",
                           (encoded(data), time.time(), 'Corrected repair verdict routing; fresh construction and review required', row['id']))

    def reconcile_feature_descriptions(self):
        """Recover pre-worker proposals exhausted under the obsolete name rule once."""
        from . import construction
        naming = 'Feature descriptions may only name distinct existing source features'
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute("SELECT * FROM candidates WHERE stage='deferred'").fetchall():
                data = json.loads(row['data'])
                if (data.get('feature_contract_recovery') or
                        any(data.get(k) for k in ('construction', 'job', 'evidence', 'publication_job'))):
                    continue
                attempts = db.execute('SELECT * FROM attempts WHERE candidate=? ORDER BY started,id',
                                      (row['id'],)).fetchall()
                builds = [a for a in attempts if a['stage'] == 'build']
                results = [json.loads(a['result']) for a in builds]
                if (not builds or attempts[-1]['id'] != builds[-1]['id'] or
                        row['reason'] != 'Attempt limit reached: ' + results[-1].get('reason', '') or
                        any(a['status'] != 'retry' or r.get('retry_scope', 'task') != 'task' or
                            not (r.get('reason') == naming or
                                 r.get('reason', '').startswith('Model response is not JSON:'))
                            for a, r in zip(builds, results))):
                    continue
                for attempt, result in reversed(list(zip(builds, results))):
                    if result.get('reason') != naming:
                        continue
                    cached = self.root / '.factory/model-tasks' / identifier(attempt['id']) / 'response.json'
                    if not cached.is_file() or cached.stat().st_size > 256 * 1024:
                        continue
                    try:
                        proposal = json.loads(cached.read_text())
                        construction.validate(proposal)
                        construction.describe_task(data['source'], proposal)
                    except (FactoryError, ValueError, KeyError, TypeError):
                        continue
                    data['construction_draft'] = proposal
                    data['feature_contract_recovery'] = {
                        'from_attempt': attempt['id'], 'previous_reason': row['reason'],
                        'reconciled_at': time.time(), 'used': False}
                    db.execute("UPDATE candidates SET stage='build',data=?,updated=?,next_run=0,reason=? WHERE id=?",
                               (encoded(data), time.time(), 'Saved proposal passes corrected feature contract', row['id']))
                    break

    def reconcile_completed_json(self):
        """Reuse a paid construction deferred solely for its missing final brace."""
        from . import construction
        from .model_tasks import parse_response
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute("SELECT * FROM candidates WHERE stage='deferred'").fetchall():
                data = json.loads(row['data'])
                if data.get('json_closure_recovery'):
                    continue
                last = db.execute('SELECT * FROM attempts WHERE candidate=? ORDER BY started DESC,id DESC LIMIT 1',
                                  (row['id'],)).fetchone()
                result = json.loads(last['result']) if last else {}
                if (not last or last['stage'] != 'build' or last['status'] != 'retry'
                        or result.get('retry_scope', 'task') != 'task'
                        or not result.get('reason', '').startswith('Model response is not JSON:')
                        or row['reason'] != 'Attempt limit reached: ' + result['reason']):
                    continue
                cached = self.root / '.factory/model-tasks' / identifier(last['id']) / 'response.txt'
                if not cached.is_file() or cached.stat().st_size >= 256 * 1024:
                    continue
                raw = cached.read_text().strip()
                try:
                    json.loads(raw)
                    continue  # A valid response is not this parser-recovery class.
                except json.JSONDecodeError as exc:
                    if not (exc.pos == len(raw) and raw.startswith('{') and raw.endswith('}')):
                        continue
                try:
                    proposal = construction.merge_repair(
                        data.get('construction_draft') or data.get('construction'), parse_response(raw))
                    construction.validate(proposal)
                    construction.describe_task(data['source'], proposal)
                except (FactoryError, ValueError, KeyError, TypeError):
                    continue
                data['construction_draft'] = proposal
                data['json_closure_recovery'] = {'from_attempt': last['id'], 'used': False,
                    'previous_reason': row['reason'], 'reconciled_at': time.time(),
                    'reason': 'Recovered missing final object brace; normalized construction envelope'}
                db.execute("UPDATE candidates SET stage='build',data=?,updated=?,next_run=0,reason=? WHERE id=?",
                           (encoded(data), time.time(), 'Saved construction recovered from final-brace failure', row['id']))

    def resume_admitted_tasks(self, admitted):
        """Recheck a pre-call admission wait without changing its attempt or stage."""
        with self.connect() as db:
            waiting = []
            for row in db.execute("""SELECT c.id,a.id AS attempt,a.result FROM candidates c
                    JOIN attempts a ON a.candidate=c.id AND a.stage=c.stage
                    WHERE a.status='running' AND c.next_run>?""", (time.time(),)):
                folder = self.root / '.factory/model-tasks' / identifier(row['attempt'])
                # ModelTasks creates this directory before admission, and writes
                # attempt.json before calling the model. Never replay paid work.
                if (json.loads(row['result']).get('status') == 'waiting' and folder.is_dir()
                        and not any((folder / name).exists() for name in
                                    ('attempt.json', 'prompt.txt', 'response.json', 'response.txt'))):
                    waiting.append(row['id'])
            try:
                ready = bool(waiting) and admitted()
            except (RuntimeError, OSError, ValueError):
                # Unavailable admission cannot wake model work or prevent
                # already-running workers from being reconciled this tick.
                ready = False
            if ready:
                db.executemany('UPDATE candidates SET next_run=0 WHERE id=?', [(key,) for key in waiting])
                return waiting
        return []

    def eligible(self, now=None):
        now = time.time() if now is None else now
        # Resume existing attempts first, then finish releases/reviews before
        # spending on more construction or discovery. Waiting tasks still yield.
        with self.connect() as db:
            rows = db.execute('''SELECT c.* FROM candidates c
                LEFT JOIN attempts a ON a.candidate=c.id AND a.status='running'
                WHERE c.stage IN ('discover','build','evaluate','publish') AND c.next_run<=?
                ORDER BY CASE WHEN a.id IS NULL THEN 1 ELSE 0 END,
                    CASE c.stage WHEN 'publish' THEN 0 WHEN 'evaluate' THEN 1
                         WHEN 'build' THEN 2 ELSE 3 END, c.updated, c.id''', (now,))
            return [self.candidate(row) for row in rows]

    def begin(self, candidate_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            candidate = db.execute('SELECT * FROM candidates WHERE id=?', (candidate_id,)).fetchone()
            if not candidate or candidate['stage'] not in STAGES:
                raise FactoryError('Candidate is not actionable')
            prior = db.execute("SELECT * FROM attempts WHERE candidate=? AND status='running'",
                               (candidate_id,)).fetchone()
            if prior:
                if prior['stage'] != candidate['stage']:
                    raise FactoryError('Attempt and candidate stages disagree')
                return dict(prior)
            ordinal = db.execute('SELECT COUNT(*) FROM attempts WHERE candidate=? AND stage=?',
                                 (candidate_id, candidate['stage'])).fetchone()[0] + 1
            # Job identifiers use this stable attempt identity, including after a restart.
            import hashlib
            prefix = hashlib.sha256(candidate_id.encode()).hexdigest()[:12]
            attempt_id = f'rw-{prefix}-{candidate["stage"]}-{ordinal}'
            db.execute('INSERT INTO attempts(id,candidate,stage,ordinal,status,started) VALUES(?,?,?,?,?,?)',
                       (attempt_id, candidate_id, candidate['stage'], ordinal, 'running', time.time()))
            return dict(db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone())

    def save(self, attempt_id, data):
        """Checkpoint operation identities before any external side effect."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            attempt = db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if not attempt or attempt['status'] != 'running':
                raise FactoryError('Attempt is not running')
            db.execute('UPDATE candidates SET data=?,updated=? WHERE id=?',
                       (encoded(data), time.time(), attempt['candidate']))

    def finish(self, attempt_id, outcome, *, max_attempts=3, now=None):
        stamp = time.time() if now is None else now
        status = outcome['status']
        if status not in ('done', 'waiting', 'retry', 'reject', 'defer', 'repair'):
            raise FactoryError('Unknown operation outcome')
        scope = outcome.get('retry_scope', 'task')
        if scope not in ('task', 'worker'):
            raise FactoryError('Unknown retry scope')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            attempt = db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if not attempt or attempt['status'] != 'running':
                raise FactoryError('Cannot finish an inactive attempt')
            stage = attempt['stage']
            if status == 'repair' and stage != 'evaluate':
                raise FactoryError('Only semantic evaluation can request reconstruction')
            # Model/startup failures and real construction failures have separate
            # bounded allowances. Ordinals remain unique history, not a counter
            # of how many times the builder has actually run.
            failures = 1 + sum(json.loads(row['result']).get('retry_scope', 'task') == scope
                               for row in db.execute(
                                   "SELECT result FROM attempts WHERE candidate=? AND stage=? AND status='retry'",
                                   (attempt['candidate'], stage)))
            if status == 'done':
                stage = NEXT[stage]
            elif status == 'reject':
                stage = 'rejected'
            elif status == 'defer' or (status == 'retry' and failures >= max_attempts):
                stage = 'deferred'
            elif status == 'repair':
                repairs = 1 + db.execute("SELECT COUNT(*) FROM attempts WHERE candidate=? AND stage='evaluate' "
                                        "AND status IN ('repair','reject')", (attempt['candidate'],)).fetchone()[0]
                stage = 'deferred' if repairs >= max_attempts else 'build'
            reason = outcome.get('reason', '')
            if stage == 'deferred' and status == 'retry':
                reason = 'Attempt limit reached: ' + reason
            elif stage == 'deferred' and status == 'repair':
                reason = 'Semantic repair limit reached: ' + reason
            delay = max(0, float(outcome.get('delay', 30 if status == 'waiting' else 60)))
            db.execute('UPDATE candidates SET stage=?,updated=?,next_run=?,reason=? WHERE id=?',
                       (stage, stamp, stamp + delay if status in ('waiting', 'retry') else 0,
                        reason, attempt['candidate']))
            db.execute('UPDATE attempts SET status=?,finished=?,result=? WHERE id=?',
                       ('running' if status == 'waiting' else status,
                        None if status == 'waiting' else stamp, encoded(outcome), attempt_id))
        return self.get(attempt['candidate'])

    def attempts(self, candidate_id=None):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM attempts' + (' WHERE candidate=?' if candidate_id else '')
                              + ' ORDER BY started,id', (candidate_id,) if candidate_id else ())
            return [{**dict(row), 'result': json.loads(row['result'])} for row in rows]
