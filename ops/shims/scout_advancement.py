#!/usr/bin/env python3
"""Deployed shim for the advancement tick.

Checks every five minutes, retaining four-hour advancement slots offset from
discovery. Busy slots remain due. `--if-work` avoids model calls when every
candidate is parked, published or awaiting the operator. Admission stays gated.
"""
import runpy
import sys

TARGET = "/opt/data/dataset-factory/scripts/scout_research_schedule.py"

if __name__ == "__main__":
    # Packaging plus a baseline can exceed the old 40-minute ceiling; give it the same
    # envelope as a discovery tick so a tick can actually finish what it starts.
    sys.argv = ([sys.argv[0], "--role", "advancement", "--if-work", "--run-budget", "5400", "--max-turns", "120"]
                + sys.argv[1:])
    runpy.run_path(TARGET, run_name="__main__")
