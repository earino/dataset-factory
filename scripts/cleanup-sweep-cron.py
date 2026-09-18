#!/usr/bin/env python3
"""Secondary (on-host, no-agent) expiry sweep for Scout's cron scheduler.

Wraps the same command the primary GitHub Actions sweeper runs, so Scout's own
instance is a backstop when GitHub's schedule is delayed or a queued run is
dropped. Needs no LLM: the scheduler runs this and delivers stdout verbatim.

Quiet on the normal path. An empty sweep (the expected result while
delete-on-collect is working) prints nothing, so no message is sent. Anything
that needs attention - a deleted server, a reclaimed primary IP, an error entry,
or a failed invocation - prints exactly one line.

Exit status is the sweep's own, so a failure is also visible in cron history.
"""

import json
import os
import subprocess
import sys

ROOT = os.environ.get("FACTORY_ROOT", "/opt/data/dataset-factory")
PROJECT = os.environ.get("FACTORY_PROJECT", "earino-dataset-factory")


def main():
    try:
        completed = subprocess.run(
            ["sh", "scripts/scout-factory", "worker", "sweep", "--project", PROJECT],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print("Scout sweep could not run for %s: %s" % (PROJECT, exc))
        return 1

    raw = (completed.stdout or "").strip()
    err = (completed.stderr or "").strip()

    if completed.returncode != 0:
        detail = raw or err or "no output"
        print("Scout sweep FAILED (exit %d) for %s: %s" % (completed.returncode, PROJECT, detail[:800]))
        return completed.returncode

    try:
        data = json.loads(raw)
    except ValueError:
        print("Scout sweep returned unparseable output for %s: %s" % (PROJECT, (raw or err)[:800]))
        return 1

    if data.get("deleted_servers") or data.get("deleted_primary_ips") or data.get("errors"):
        print("Scout sweep for %s: %s" % (PROJECT, json.dumps(data, sort_keys=True)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
