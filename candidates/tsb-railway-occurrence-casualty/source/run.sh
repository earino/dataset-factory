#!/bin/sh
# Worker entrypoint for the tsb-railway-occurrence-casualty full build.
#
# Runs on an expendable worker only. Downloads the five RODSdb public CSVs
# (~157 MB, browser-like headers; a plain User-Agent gets HTTP 403), builds the
# occurrence-level casualty panel, writes the runner layout plus quality.json,
# then runs the qualification gate over the exact artifact - the job fails
# when the gate fails, and every diagnostic (summary.json, gate report) is
# written under /output so it is collected either way.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/tsb
build_status=$?

if [ -f "$OUT/summary.json" ]; then
    cp "$OUT/summary.json" /output/summary.json
fi

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    exit "$build_status"
fi

echo "== qualification =="
python3 /workspace/qualify_dataset.py "$OUT" --json \
    --report /output/qualification-tsb-railway-occurrence-casualty.json \
    > /output/qualification-tsb-railway-occurrence-casualty.txt 2>&1
qual_status=$?
cat /output/qualification-tsb-railway-occurrence-casualty.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
