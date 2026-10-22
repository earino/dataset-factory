#!/bin/sh
# Worker entrypoint for the eutl-installation-net-short full build.
#
# Runs on an expendable worker only. Downloads the Union Registry daily bulk
# extract (one anonymous GET, ~6 MB measured) plus the EEA aggregate zip
# (~10.8 MB measured) for the in-build publisher cross-check, builds the
# (installation, compliance year) panel with settlement-lagged features, writes
# the runner layout plus quality.json, then runs the qualification gate over
# the exact artifact - the job fails when the gate fails, and every diagnostic
# (summary.json, gate report) is written under /output so it is collected
# either way.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/eutl
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
    --report /output/qualification-eutl-installation-net-short.json \
    > /output/qualification-eutl-installation-net-short.txt 2>&1
qual_status=$?
cat /output/qualification-eutl-installation-net-short.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
