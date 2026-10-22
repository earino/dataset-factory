#!/bin/sh
# Script-only scheduler entrypoint; the repository owns admission and the brief.
exec python3 /opt/data/dataset-factory/scripts/scout_worker_followup.py "$@"
