#!/usr/bin/env python3
"""Watch worker jobs and report the moment one finishes - without the operator having to ask.

The gap this closes: a remote job outlives the turn that launched it, so nothing comes back by
itself. `notify` on the launching command fires when the *launch* exits, not when the job does, and
`worker status` reports the *server*, which idles until its lifetime expires. The only cheap signal
is `worker collect`, which returns `status: running` until the job has a result.

Output is deliberately deterministic: one line per watched job, with elapsed time omitted while a
job is still running. That is what lets the scheduler use this as a change detector - identical
output skips the agent entirely, so watching costs nothing until there is something to say.

    python3 scout_job_watch.py            # used by the scheduler
    python3 scout_job_watch.py --status   # same output, for a human
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / ".factory/watchlist.json"
COLLECT_TIMEOUT = 240


def watchlist():
    if not WATCHLIST.is_file():
        return []
    try:
        entries = json.loads(WATCHLIST.read_text())
    except json.JSONDecodeError:
        return []
    return [str(entry) for entry in entries] if isinstance(entries, list) else []


def state_of(job_id):
    """One job's state, cheaply.

    The locally collected result wins: once a job has been collected its worker may already be
    destroyed, and a dead worker's `collect` cannot read the remote result - which would otherwise
    look identical to a job that is still running.
    """
    local = ROOT / ".factory" / job_id / "result.json"
    if local.is_file():
        try:
            payload = json.loads(local.read_text())
            return {"job": job_id, "state": payload.get("status") or "unknown",
                    "exit_code": payload.get("exit_code"),
                    "elapsed_minutes": round((payload.get("elapsed_seconds") or 0) / 60),
                    "assets": len(payload.get("assets") or []),
                    "release_id": payload.get("release_id"),
                    "uploaded": payload.get("uploaded")}
        except json.JSONDecodeError:
            pass
    try:
        result = subprocess.run(["sh", "scripts/scout-factory", "worker", "collect", job_id],
                                cwd=ROOT, capture_output=True, text=True,
                                timeout=COLLECT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"job": job_id, "state": "unknown", "detail": "collect timed out"}
    payload = None
    for chunk in (result.stdout, result.stderr):
        for line in reversed((chunk or "").splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    payload = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        if payload:
            break
    if not payload:
        # Only an explicit `{"status": "running"}` means running. Anything else - including the
        # cleanup sweep having destroyed the worker before the result was collected - is a terminal
        # state, because a watchdog that reports a swept job as "running" waits forever.
        message = ((result.stderr or result.stdout or "").strip().splitlines() or ["no result"])[-1]
        return {"job": job_id, "state": "gone", "detail": message[:140]}
    if payload.get("status") == "running":
        return {"job": job_id, "state": "running"}
    return {"job": job_id, "state": payload.get("status") or "unknown",
            "exit_code": payload.get("exit_code"),
            "elapsed_minutes": round((payload.get("elapsed_seconds") or 0) / 60),
            "assets": len(payload.get("assets") or []),
            "release_id": payload.get("release_id"),
            "uploaded": payload.get("uploaded")}


def render(state):
    """Deterministic one-liner. Nothing time-varying while a job is still running."""
    if state["state"] == "running":
        return f'{state["job"]}: running'
    if state["state"] in ("unknown", "gone"):
        return f'{state["job"]}: {state["state"]} ({state.get("detail", "no result")})'
    return (f'{state["job"]}: {state["state"]} exit={state.get("exit_code")} '
            f'elapsed_min={state.get("elapsed_minutes")} assets={state.get("assets")} '
            f'release={state.get("release_id")} uploaded={state.get("uploaded")}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="same output, for a human")
    args = parser.parse_args()
    jobs = watchlist()
    if not jobs:
        # Nothing watched: silent, which the scheduler reads as no change.
        return 0
    for job_id in jobs:
        print(render(state_of(job_id)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())