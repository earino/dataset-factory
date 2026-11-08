"""One deterministic scheduler tick. No model decides transitions or closeout."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path

from .common import FactoryError
from .state import Store


@contextmanager
def controller_lock(root):
    folder = Path(root) / '.factory'
    if folder.is_symlink():
        raise FactoryError('Operational directory must not be a symlink')
    folder.mkdir(exist_ok=True)
    fd = os.open(folder / 'pipeline.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def tick(root, driver, *, max_attempts=3):
    with controller_lock(root) as acquired:
        if not acquired:
            return {'status': 'busy'}
        store = Store(root)
        candidates = store.eligible()
        if not candidates:
            return {'status': 'idle'}
        candidate = candidates[0]
        attempt = store.begin(candidate['id'])
        # Drivers checkpoint stable operation identities through save before calls.
        # An unhandled crash leaves this attempt running; the next tick resumes it.
        outcome = driver.execute(candidate, attempt, lambda data: store.save(attempt['id'], data))
        current = store.finish(attempt['id'], outcome, max_attempts=max_attempts)
        return {'status': outcome['status'], 'candidate': current['id'],
                'stage': current['stage'], 'attempt': attempt['id'], 'reason': current['reason']}
