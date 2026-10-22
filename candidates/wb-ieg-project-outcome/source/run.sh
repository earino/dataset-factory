#!/bin/sh
# Worker entrypoint for the wb-ieg-project-outcome full build.
#
# Runs on an expendable worker only. Downloads the IEG World Bank Project
# Performance Ratings CSV (one anonymous GET, 3,340,648 bytes measured
# 2026-10-22) plus the paged World Bank projects search API (offset paging,
# 1,000 records per page, ~23 requests), builds the project-level
# approval-instant panel with strictly-prior country rating history, writes
# the runner layout plus quality.json, then runs the qualification gate over
# the exact artifact - the job fails when the gate fails, and every
# diagnostic (summary.json, gate report) is written under /output so it is
# collected either way.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/wb
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
    --report /output/qualification-wb-ieg-project-outcome.json \
    > /output/qualification-wb-ieg-project-outcome.txt 2>&1
qual_status=$?
cat /output/qualification-wb-ieg-project-outcome.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
