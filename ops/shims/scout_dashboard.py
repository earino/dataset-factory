#!/usr/bin/env python3
"""Hourly dashboard refresh: build the snapshot, publish it, verify it anonymously.

Scheduled from cron as a file script (no agent turns). Prints one line; exits non-zero
when the publish or the anonymous read-back fails, so the scheduler records a real
failure instead of a cheerful no-op.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/data/dataset-factory")


def main():
    result = subprocess.run([sys.executable, str(REPO / "scripts/build-dashboard.py"), "--publish"],
                            cwd=REPO, text=True, capture_output=True)
    lines = [line for line in (result.stdout or "").strip().splitlines() if line.strip()]
    payload = {}
    for line in lines:
        try:
            payload.update(json.loads(line))
        except ValueError:
            continue
    verified = payload.get("ok")
    print(f"dashboard: generated {payload.get('generated_at')} live={payload.get('live')} "
          f"published={payload.get('published')} verified={verified}")
    if result.returncode:
        print((result.stderr or "")[-500:], file=sys.stderr)
        return 1
    if payload.get("published") and not verified:
        # Pages can lag a few seconds behind the push; the next hourly run republishes
        # only if content changed, so verify once more before failing the job.
        verify = subprocess.run([sys.executable, "-c",
                                 "import importlib.util,sys;"
                                 "s=importlib.util.spec_from_file_location('bd','scripts/build-dashboard.py');"
                                 "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
                                 "print(m.verify(attempts=4))"], cwd=REPO, text=True, capture_output=True)
        print(verify.stdout.strip())
        if "'ok': True" not in verify.stdout:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
