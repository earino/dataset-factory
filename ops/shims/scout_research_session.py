#!/usr/bin/env python3
"""Deployed shim. The source of truth is versioned in the repository, so the routine's code
lives in Git rather than only on this host. Cron requires the job's script to sit under the
scheduler's scripts directory, hence the forward."""
import runpy
import sys

TARGET = "/opt/data/dataset-factory/scripts/scout_research_session.py"

if __name__ == "__main__":
    sys.argv[0] = TARGET
    runpy.run_path(TARGET, run_name="__main__")
