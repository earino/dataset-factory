#!/bin/sh
# Worker entrypoint for the austin-911-response full-data build.
#
# Runs on an expendable worker only. Builds the extract, then qualifies the exact artifact it
# just wrote, and fails the job when qualification fails - so a dataset that cannot be scored
# cannot be collected as if it could.
#
# Diagnostics always travel with the artifacts: the gate report, its human-readable rendering
# and the extract itself are all written under /output, which the worker uploads even when the
# job exits non-zero. A failed qualification therefore preserves evidence; the coordinator
# collects it and then deletes the worker as usual.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT"
build_status=$?

# A compact report for the coordinator; the bulk artifacts stay in the release.
if [ -f "$OUT/summary.json" ]; then
    cp "$OUT/summary.json" /output/summary.json
fi

echo "== qualification =="
python3 /workspace/qualify_dataset.py "$OUT" --json --report /output/qualification.json \
    > /output/qualification.txt 2>&1
qual_status=$?
cat /output/qualification.txt

echo "build_status=$build_status qualification_status=$qual_status"

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    exit "$build_status"
fi

if [ "$qual_status" -ne 0 ]; then
    echo "qualification FAILED; the artifact must not be scored or accepted" >&2
fi

exit "$qual_status"
