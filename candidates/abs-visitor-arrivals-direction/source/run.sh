#!/bin/sh
# Worker entrypoint for the abs-visitor-arrivals-direction full build.
#
# Runs on an expendable worker only. Downloads the ABS OAD_COUNTRY panel
# (one anonymous SDMX CSV GET, ~3.3 MB measured) plus the dataflow structure
# for the country codelist, builds the (country, target month) visitor-series
# panel with publication-lag-gated features, writes the runner layout plus
# quality.json, then runs the qualification gate over the exact artifact -
# the job fails when the gate fails, and every diagnostic (summary.json, gate
# report) is written under /output so it is collected either way.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/abs
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
    --report /output/qualification-abs-visitor-arrivals-direction.json \
    > /output/qualification-abs-visitor-arrivals-direction.txt 2>&1
qual_status=$?
cat /output/qualification-abs-visitor-arrivals-direction.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
