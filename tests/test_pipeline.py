import tempfile
from pathlib import Path
import unittest

from factory.pipeline import controller_lock, tick
from factory.state import Store


class PipelineTests(unittest.TestCase):
    def test_admission_change_resumes_unstarted_task_without_advancing_or_replaying(self):
        from unittest.mock import Mock
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        root = Path(tmp.name); store = Store(root)
        for name in ('blocked', 'paid', 'blocked-access', 'paid-access'):
            store.add(name, {})
            attempt = store.begin(name)
            folder = root / '.factory/model-tasks' / (attempt['id'] + ('-access' if name.endswith('-access') else ''))
            folder.mkdir(parents=True)
            if name.startswith('paid'): (folder / 'attempt.json').write_text('{}')
            store.finish(attempt['id'], {'status':'waiting','reason':'Admission held','delay':3600})
        history = store.attempts()
        denied = Mock(return_value=False)
        self.assertEqual([], store.resume_admitted_tasks(denied)); denied.assert_called_once()
        self.assertEqual([], store.eligible())
        unavailable = Mock(side_effect=RuntimeError('Accounting unavailable'))
        self.assertEqual([], store.resume_admitted_tasks(unavailable))
        self.assertEqual([], store.eligible())
        allowed = Mock(return_value=True)
        self.assertEqual({'blocked','blocked-access'}, set(store.resume_admitted_tasks(allowed)))
        allowed.assert_called_once()
        self.assertEqual(['blocked','blocked-access'], [c['id'] for c in store.eligible()])
        self.assertEqual(history, store.attempts())
        self.assertEqual(history[0]['id'], store.begin('blocked')['id'])
        self.assertEqual('discover', store.get('blocked')['stage'])
        allowed.reset_mock()
        self.assertEqual([], store.resume_admitted_tasks(allowed)); allowed.assert_not_called()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); self.store = Store(self.root)
        self.store.add('example', {'source': 'unit fixture'})

    def test_crash_resumes_same_attempt_and_pre_side_effect_checkpoint(self):
        seen = []
        class Driver:
            def execute(_, candidate, attempt, save):
                seen.append(attempt['id'])
                if len(seen) == 1:
                    save({**candidate['data'], 'job_id': attempt['id']})
                    raise RuntimeError('lost reply after checkpoint')
                self.assertEqual(attempt['id'], candidate['data']['job_id'])
                return {'status': 'done'}
        driver = Driver()
        with self.assertRaises(RuntimeError): tick(self.root, driver)
        self.assertEqual('build', tick(self.root, driver)['stage'])
        self.assertEqual(seen[0], seen[1]); self.assertEqual(1, len(self.store.attempts()))

    def test_waiting_candidate_does_not_starve_another(self):
        class Driver:
            def execute(_, candidate, attempt, save):
                return {'status': 'waiting', 'delay': 600} if candidate['id'] == 'example' else {'status': 'done'}
        tick(self.root, Driver()); self.store.add('another', {})
        self.assertEqual('another', tick(self.root, Driver())['candidate'])
        self.assertEqual('discover', self.store.get('example')['stage'])

    def test_finish_ready_work_before_more_discovery_without_interrupting_attempts(self):
        for name, stages in [('release', 3), ('review', 2), ('construction', 1)]:
            self.store.add(name, {})
            for _ in range(stages):
                self.store.finish(self.store.begin(name)['id'], {'status': 'done'})
        self.assertEqual(['release', 'review', 'construction', 'example'],
                         [c['id'] for c in self.store.eligible()])
        active = self.store.begin('construction')
        self.assertEqual('construction', self.store.eligible()[0]['id'])
        self.store.finish(active['id'], {'status': 'waiting', 'delay': 600})
        class Driver:
            def execute(_, candidate, attempt, save):
                self.assertEqual('publish', candidate['stage'])
                return {'status': 'done'}
        self.assertEqual('published', tick(self.root, Driver())['stage'])
        self.assertEqual('review', self.store.eligible()[0]['id'])
        self.assertEqual('discover', self.store.get('example')['stage'])

    def test_retry_is_bounded_and_does_not_approve_artifact(self):
        for number in range(1, 4):
            attempt = self.store.begin('example')
            self.assertEqual(number, attempt['ordinal'])
            result = self.store.finish(attempt['id'], {'status': 'retry', 'reason': 'HTTP 504', 'delay': 0})
        self.assertEqual('deferred', result['stage']); self.assertEqual([], self.store.eligible())

    def test_duplicate_tick_is_busy_and_duplicate_add_cannot_reset_progress(self):
        class Driver:
            def execute(_, candidate, attempt, save): return {'status': 'done'}
        with controller_lock(self.root): self.assertEqual({'status': 'busy'}, tick(self.root, Driver()))
        tick(self.root, Driver()); self.store.add('example', {'replacement': True})
        self.assertEqual('build', self.store.get('example')['stage'])
        self.assertNotIn('replacement', self.store.get('example')['data'])

    def test_startup_failures_do_not_exhaust_worker_repair_allowance(self):
        self.store.finish(self.store.begin('example')['id'], {'status': 'done'})
        for _ in range(2):
            result = self.store.finish(self.store.begin('example')['id'], {'status': 'retry'})
        for number in range(3):
            attempt = self.store.begin('example')
            result = self.store.finish(attempt['id'], {'status': 'retry', 'retry_scope': 'worker'})
            self.assertEqual('deferred' if number == 2 else 'build', result['stage'])
        self.assertEqual(5, attempt['ordinal'])
        self.assertEqual(6, len(self.store.attempts()))  # includes discovery

    def test_initial_deployment_correction_preserves_evidence_and_only_runs_once(self):
        import runpy
        from factory.common import write_json
        recover = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                     'audits/rewrite/recover_initial_build.py'))['recover']
        self.store.add('source-000001', {})
        self.store.finish(self.store.begin('source-000001')['id'], {'status': 'done'})
        for ordinal in range(1, 4):
            attempt = self.store.begin('source-000001')
            if ordinal < 3:
                write_json(self.root / '.factory/model-tasks' / attempt['id'] / 'failure.json',
                           {'exit_code': 1, 'accounting': 'Expected one model session; observed 0 new sessions'})
            else:
                self.store.save(attempt['id'], {'construction_attempt': attempt['id']})
                write_json(self.root / 'jobs' / (attempt['id'] + '.json'),
                           {'status': 'deleted', 'result': {'exit_code': 1}})
            self.store.finish(attempt['id'], {'status': 'retry'})
        self.assertEqual('deferred', self.store.get('source-000001')['stage'])
        self.assertEqual('corrected', recover(self.root)['status'])
        self.assertEqual('already-corrected', recover(self.root)['status'])
        self.assertEqual('build', self.store.get('source-000001')['stage'])
        receipt = self.root / '.factory/initial-build-retry-correction.json'
        self.assertIn('deferred', receipt.read_text())
        self.assertEqual(4, len(self.store.attempts('source-000001')))

    def test_no_transition_without_explicit_outcome_and_published_is_terminal(self):
        for expected in ('build', 'evaluate', 'publish', 'published'):
            attempt = self.store.begin('example')
            result = self.store.finish(attempt['id'], {'status': 'done'})
            self.assertEqual(expected, result['stage'])
        self.assertEqual([], self.store.eligible())

    def test_semantic_repairs_require_reconstruction_and_are_bounded(self):
        self.store.finish(self.store.begin('example')['id'], {'status': 'done'})
        for number in range(3):
            self.store.finish(self.store.begin('example')['id'], {'status': 'done'})
            self.assertEqual('evaluate', self.store.get('example')['stage'])
            result = self.store.finish(self.store.begin('example')['id'],
                                       {'status': 'repair', 'reason': 'Incorrect source pivot'})
            self.assertEqual('deferred' if number == 2 else 'build', result['stage'])
        self.assertIn('Semantic repair limit', result['reason'])
        self.assertFalse(any(a['stage'] == 'publish' for a in self.store.attempts()))

    def test_misrouted_repair_correction_preserves_history_and_true_rejections(self):
        for name, verdict in [('example', 'repair'), ('true-reject', 'reject'), ('changed-reason', 'repair')]:
            self.store.add(name, {})
            for _ in range(2):
                self.store.finish(self.store.begin(name)['id'], {'status': 'done'})
            attempt = self.store.begin(name)
            review = {'verdict': verdict, 'reason': 'Source issue', 'findings': [{'issue': 'Wrong pivot'}]}
            self.store.save(attempt['id'], {'review': review, 'job': {'id': 'finished-build'},
                'evidence': {'MANIFEST.json': {'artifact_version': 'old-artifact'}}})
            self.store.finish(attempt['id'], {'status': 'reject', 'reason': 'Source issue'})
        with self.store.connect() as db:
            db.execute("UPDATE candidates SET reason='Later independent rejection' WHERE id='changed-reason'")
        history = self.store.attempts()
        self.store.reconcile_misrouted_reviews()
        self.store.reconcile_misrouted_reviews()
        repaired = self.store.get('example')
        self.assertEqual('build', repaired['stage'])
        self.assertEqual(history, self.store.attempts())
        self.assertEqual(1, len(repaired['data']['semantic_repairs']))
        self.assertEqual('old-artifact', repaired['data']['semantic_repairs'][0]['artifact_version'])
        self.assertEqual('repair', repaired['data']['pending_semantic_review']['verdict'])
        self.assertEqual('rejected', self.store.get('true-reject')['stage'])
        self.assertEqual('rejected', self.store.get('changed-reason')['stage'])
        # The misrouted failed review still counts toward the repair bound.
        self.store.finish(self.store.begin('example')['id'], {'status': 'done'})
        result = self.store.finish(self.store.begin('example')['id'], {'status': 'repair'}, max_attempts=2)
        self.assertEqual('deferred', result['stage'])


if __name__ == '__main__': unittest.main()
