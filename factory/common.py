from __future__ import annotations

import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone


class FactoryError(Exception):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", value):
        raise FactoryError("IDs must be 1–48 lowercase letters, digits, or hyphens")
    return value


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise FactoryError(f"Cannot read JSON: {path}: {exc}") from exc


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def locked(root):
    folder = Path(root) / ".factory"
    folder.mkdir(exist_ok=True)
    with (folder / "worker.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield
