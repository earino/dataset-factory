#!/usr/bin/env python3
"""Wait for a worker job to finish, then verify collection.

Polls `worker collect ID` until it stops reporting "running". Collect is idempotent and, on
completion, verifies every uploaded asset against the worker's own manifest - so a successful
exit here means the artifacts are preserved and checked, not merely present.

Usage: python3 scripts/wait-job.py <job-id> [budget-seconds]
Exit 0 = collected, 1 = job failed or collection refused, 3 = still running at the budget.
"""
import json
import subprocess
import sys
import time

JOB = sys.argv[1]
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
POLL = 45


def stamp():
    return time.strftime("%H:%M:%SZ", time.gmtime())


started = time.monotonic()
attempt = 0
while time.monotonic() - started < BUDGET:
    attempt += 1
    done = subprocess.run(["sh", "scripts/scout-factory", "worker", "collect", JOB],
                          capture_output=True, text=True, timeout=180)
    raw = done.stdout.strip()
    try:
        report = json.loads(raw)
    except ValueError:
        print(f"{stamp()} collect exited {done.returncode} with unparseable output")
        print(raw[:2000] or done.stderr[:2000])
        sys.exit(1)
    if report.get("status") == "running":
        elapsed = int(time.monotonic() - started)
        print(f"{stamp()} attempt {attempt}: still running ({elapsed}s); "
              f"expires {report.get('expires')}")
        time.sleep(POLL)
        continue
    print(f"{stamp()} collected after {attempt} attempts, {int(time.monotonic()-started)}s")
    print(json.dumps(report, indent=2)[:4000])
    sys.exit(0 if report.get("uploaded") else 1)

print(f"{stamp()} budget exhausted; job {JOB} still running")
sys.exit(3)