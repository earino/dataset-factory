#!/bin/sh
# Worker entrypoint for the ibama-auto-infracao-recidivism discovery aggregate probe.
# Measurement only: no dataset files are constructed, no gate runs, nothing is scored.
# All bulk bytes (zip, extracted CSVs, sqlite scratch DB) stay in /tmp/probe inside the
# container; only bounded JSON/CSV reports are written to /output for upload.
set -u

mkdir -p /output

python3 -u /workspace/probe_aggregate.py --out /output --work-dir /tmp/probe
status=$?

echo "probe_status=$status"
exit "$status"
