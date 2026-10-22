#!/usr/bin/env python3
"""Deployed shim for the release notifier; the logic is versioned in the repository."""
import runpy
import sys

TARGET = "/opt/data/dataset-factory/scripts/notify-release.py"

if __name__ == "__main__":
    sys.argv[0] = TARGET
    runpy.run_path(TARGET, run_name="__main__")
