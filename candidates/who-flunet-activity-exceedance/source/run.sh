#!/bin/sh
# Worker entrypoint for the who-flunet-activity-exceedance full build.
#
# Runs on an expendable worker only. Downloads the publisher's single full
# FluNet CSV (one anonymous request, ~30.8 MiB), builds the country-week
# exceedance panel with the systematic-negative-reporting frame, writes the
# runner layout plus quality.json, then runs the qualification gate over the
# exact artifact - the job fails when the gate fails, and every diagnostic
# (summary.json, gate report) is written under /output so it is collected
# either way.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/flunet
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
    --report /output/qualification-who-flunet-activity-exceedance.json \
    > /output/qualification-who-flunet-activity-exceedance.txt 2>&1
qual_status=$?
cat /output/qualification-who-flunet-activity-exceedance.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
