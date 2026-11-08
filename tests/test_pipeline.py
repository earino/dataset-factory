import tempfile
from pathlib import Path
import unittest

from factory.pipeline import controller_lock, tick
from factory.state import Store


class PipelineTests(unittest.TestCase):
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

    def test_no_transition_without_explicit_outcome_and_published_is_terminal(self):
        for expected in ('build', 'evaluate', 'publish', 'published'):
            attempt = self.store.begin('example')
            result = self.store.finish(attempt['id'], {'status': 'done'})
            self.assertEqual(expected, result['stage'])
        self.assertEqual([], self.store.eligible())


if __name__ == '__main__': unittest.main()
