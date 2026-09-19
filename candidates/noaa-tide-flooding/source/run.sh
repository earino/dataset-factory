#!/bin/sh
# Worker entrypoint for the noaa-tide-flooding full build.
#
# Runs on an expendable worker only. Builds both contract-complete levels from NOAA's verified
# daily maxima and the publisher's own flood-day flags, then qualifies each level's exact artifact
# and fails the job when either gate fails - so a dataset that cannot be scored cannot be collected
# as if it could.
#
# Diagnostics always travel with the artifacts: both gate reports and the built levels are written
# under /output, which the worker uploads even when the job exits non-zero.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --concurrency 4
build_status=$?

if [ -f "$OUT/build_summary.json" ]; then
    cp "$OUT/build_summary.json" /output/build_summary.json
fi

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    exit "$build_status"
fi

# Both levels are contract-complete tasks, so both are gated. The gate is run per level because
# the runner's contract is one task with one eval set.
qual_status=0
for level in temporal station_disjoint; do
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
