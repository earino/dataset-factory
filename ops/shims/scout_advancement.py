#!/usr/bin/env python3
"""Deployed shim for the advancement tick.

Forwards to the versioned runner with `--if-work`, so the tick runs often (every two
hours) but starts no agent when every candidate is parked, published, or waiting on the
operator's flip. The gate still runs first and holds overlapping sessions.
"""
import runpy
import sys

TARGET = "/opt/data/dataset-factory/scripts/scout_research_session.py"

if __name__ == "__main__":
    # Packaging plus a baseline can exceed the old 40-minute ceiling; give it the same
    # envelope as a discovery tick so a tick can actually finish what it starts.
    sys.argv = ([sys.argv[0], "--if-work", "--run-budget", "5400", "--max-turns", "120"]
                + sys.argv[1:])
    runpy.run_path(TARGET, run_name="__main__")
