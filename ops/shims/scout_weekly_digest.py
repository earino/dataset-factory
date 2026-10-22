#!/usr/bin/env python3
"""Weekly Scout research digest, delivered to Telegram.

Runs as a `no_agent` cron job: the script's stdout is delivered verbatim, so the digest costs
no model calls and keeps working when the research allowance is spent or unconfigured. It is
monitoring, and monitoring is deliberately independent of the research quota.

The figures come from the repository's `scripts/research-budget.py --digest`, which reads
Hermes's own usage records.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/data/dataset-factory")
BUDGET = REPO / "scripts" / "research-budget.py"


def main():
    if not BUDGET.is_file():
        print("Scout digest unavailable: research-budget.py not found at "
              f"{BUDGET}. The dataset-factory checkout may be missing or moved.")
        return 1
    result = subprocess.run(
        [sys.executable, str(BUDGET), "--digest"],
        capture_output=True, text=True, cwd=str(REPO), timeout=120,
    )
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.returncode != 0:
        print(f"(research-budget.py exited {result.returncode})")
    if result.stderr.strip():
        print("stderr: " + result.stderr.strip()[:500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
