#!/usr/bin/env python3
"""Cron shim: run Scout's secondary no-agent expiry sweep.

The sweep itself lives in the dataset-factory repo (tracked, testable):
/opt/data/dataset-factory/scripts/cleanup-sweep-cron.py

Hermes requires cron scripts to live in ~/.hermes/scripts/, so this shim exists
only to bridge that requirement. It forwards stdout, stderr and exit status.
"""

import os
import subprocess
import sys

TARGET = "/opt/data/dataset-factory/scripts/cleanup-sweep-cron.py"


def main():
    if not os.path.exists(TARGET):
        print("Scout sweep shim: target missing: %s" % TARGET)
        return 1
    completed = subprocess.run([sys.executable, TARGET])
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
