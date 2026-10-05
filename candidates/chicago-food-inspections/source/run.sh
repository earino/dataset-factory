#!/bin/sh
# Worker entrypoint for the chicago-food-inspections full build.
#
# Runs on an expendable worker only. Builds the multi-label suite (one binary
# runner config per floor violation code plus the joint labels.csv), then
# qualifies EVERY config's exact artifact and fails the job when any gate
# fails - so a dataset that cannot be scored cannot be collected as if it
# could.
#
# Diagnostics always travel with the artifacts: every gate report, its text
# rendering and the built configs are written under /output, which the worker
# uploads even when the job exits non-zero.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT"
build_status=$?

for f in summary.json build_summary.json; do
    if [ -f "$OUT/$f" ]; then
        cp "$OUT/$f" "/output/$f"
    fi
done

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    exit "$build_status"
fi

# Every floor code is a contract-complete task, so every one is gated. The
# gate is run per config because the runner's contract is one target per task.
qual_status=0
for level in $(python3 -c 'import json; print(" ".join(json.load(open("/output/summary.json"))["configs"]))'); do
    echo "== qualification: $level =="
    python3 /workspace/qualify_dataset.py "$OUT/$level" --json \
        --report "/output/qualification-$level.json" > "/output/qualification-$level.txt" 2>&1
    level_status=$?
    cat "/output/qualification-$level.txt"
    if [ "$level_status" -ne 0 ]; then
        echo "qualification FAILED for $level; the artifact must not be scored or accepted" >&2
        qual_status="$level_status"
    fi
done

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
