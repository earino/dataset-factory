#!/usr/bin/env python3
"""Cheap five-minute checks; four-hour research slots survive busy/held ticks.

Receipts consume a slot before launching, never on a refused admission. Missed
slots coalesce. A crash after admission is not retried until the next normal slot.
"""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time

# runpy shims run outside the checkout and do not add this directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scout_research_session as session

PERIOD = 4 * 3600
CHECK = 5 * 60
OFFSETS = {"discovery": 0, "advancement": 2 * 3600}


def slot_for(role, stamp):
    offset = OFFSETS[role]
    return (int(stamp) - offset) // PERIOD * PERIOD + offset


def state_path(role):
    return session.FACTORY_DIR / f"research-schedule-{role}.json"


def read_state(role):
    path = state_path(role)
    if path.is_symlink():
        raise session.AdmissionError("schedule receipt must not be a symlink")
    if not path.exists():
        return dict(version=1, slot=None, work=[], extra_used=False,
                    followup_allowed=False, event="new", reason="no receipt")
    try:
        if not path.is_file() or path.stat().st_size > 65536:
            raise ValueError()
        value = json.loads(path.read_text(), object_pairs_hook=session._unique_json)
        if (not isinstance(value, dict)
                or not {"version", "slot", "work", "extra_used", "followup_allowed", "event", "reason"} <= value.keys()
                or type(value.get("version")) is not int or value["version"] != 1
                or (value.get("slot") is not None and
                    (type(value["slot"]) is not int or
                     slot_for(role, value["slot"]) != value["slot"]))
                or not isinstance(value.get("work"), list)
                or any(not isinstance(pair, list) or len(pair) != 2 or
                       any(not isinstance(s, str) for s in pair) for pair in value["work"])
                or any(type(value.get(k)) is not bool for k in ("extra_used", "followup_allowed"))
                or any(not isinstance(value.get(k), str) for k in ("event", "reason"))):
            raise ValueError()
        return value
    except (ValueError, TypeError, KeyError):
        raise session.AdmissionError("invalid schedule receipt; inspect before recovery") from None


def save_state(role, state):
    path = state_path(role)
    if path.is_symlink():
        raise session.AdmissionError("schedule receipt must not be a symlink")
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".research-schedule-")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(name).unlink(missing_ok=True)


@contextlib.contextmanager
def role_lock(role):
    """Serialize receipt writers, including duplicate manual/scheduled invocations."""
    folder = session.FACTORY_DIR
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink():
        raise session.AdmissionError("session state directory must not be a symlink")
    fd = os.open(folder / f"research-schedule-{role}.mutex",
                 os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise session.AdmissionError("schedule mutex must be a single-link regular file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise session.SessionBusy("same scheduled role is already checking/running") from None
        yield
    finally:
        os.close(fd)


def due(role, state, work, stamp):
    slot = slot_for(role, stamp)
    if state["slot"] is None or state["slot"] < slot:
        return "cadence"
    # Notes/next-action rewrites and removal of a candidate are not new eligibility.
    # At most one extra admission per slot, and never after a failed/crashed run.
    if (role == "advancement" and state["slot"] == slot
            and state["followup_allowed"] and not state["extra_used"]
            and set(map(tuple, work)) - set(map(tuple, state["work"]))):
        return "new eligible step"
    return None


def tick(role, args, stamp=None):
    stamp = time.time() if stamp is None else stamp
    with role_lock(role):
        state = read_state(role)
        work = [list(pair) for pair in session.actionable_work(session.REPO)] if role == "advancement" else []
        why = due(role, state, work, stamp)
        if not why:
            return 0

        def record(event, reason):
            changed = (state["event"], state["reason"]) != (event, reason)
            state.update(event=event, reason=reason, checked_at=int(time.time()),
                         next_check=int(time.time()) // CHECK * CHECK + CHECK)
            if event in ("admitted", "idle"):
                state.update(slot=slot_for(role, stamp), work=work,
                             extra_used=why != "cadence", followup_allowed=event == "idle")
            save_state(role, state)
            if changed and event in ("held", "busy"):
                print(f"Scout {role} deferred: {reason}; next scheduled check within 5 minutes.")

        try:
            with session.admission_lock() as lock_fd:
                code = session.run_session(args, lock_fd, observe=record)
                if state["event"] == "admitted":
                    state["followup_allowed"] = code == 0
                    record("completed" if code == 0 else "failed", f"session exit {code}")
                return code
        except session.SessionBusy as exc:
            record("busy", str(exc))
            return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=OFFSETS, required=True)
    parser.add_argument("--status", action="store_true", help="read receipt/due state; no gate or model")
    options, rest = parser.parse_known_args(argv)
    try:
        if options.status:
            state = read_state(options.role)
            work = [list(pair) for pair in session.actionable_work(session.REPO)]
            stamp = time.time()
            print(json.dumps(dict(role=options.role, receipt=state,
                                  due=due(options.role, state, work, stamp),
                                  next_cadence=slot_for(options.role, stamp) + PERIOD,
                                  next_scheduled_check=int(stamp) // CHECK * CHECK + CHECK)))
            return 0
        args = session.parse_args(rest)
        # Read-only diagnostics retain the original runner and never consume a slot.
        if args.dry_run:
            return session.main(rest)
        if args.source_tag != session.SOURCE_TAG or args.late_minutes is not None:
            parser.error("scheduled recovery uses ordinary research accounting and fresh admission")
        if options.role == "advancement" and not args.if_work:
            parser.error("advancement requires --if-work")
        session.SOURCE_TAG_ACTIVE = session.SOURCE_TAG
        return tick(options.role, args)
    except session.SessionBusy:
        return 0
    except (session.AdmissionError, OSError) as exc:
        reason = str(exc) if isinstance(exc, session.AdmissionError) else type(exc).__name__
        print(f"Scout schedule refused: {reason}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
