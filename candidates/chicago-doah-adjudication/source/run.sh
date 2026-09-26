#!/bin/sh
# Worker entrypoint for the chicago-doah-adjudication full build.
#
# Runs on an expendable worker only. Reads the City's published Ordinance Violations dataset,
# reduces it to one row per docket_number (a case, not a violation charge), writes the three
# temporal splits, and qualifies the exact artifact. The job fails when the gate fails, so a
# dataset that cannot be scored cannot be collected as if it could.
#
# Diagnostics always travel with the artifacts: the build summary and both gate outputs are
# written under /output, which the worker uploads even when the job exits non-zero.
#
# BUILT_AT is pinned so a rebuild of the same frozen source is byte-identical, which is what lets
# the recorded artifact hash mean anything.
set -u

OUT=/output/extract
BUILT_AT=${BUILT_AT:-2026-09-26T20:00:00+00:00}
mkdir -p /output

echo "== build (built_at=$BUILT_AT) =="
# The builder refuses to finish unless it read every row the source reports, so a partial read is
# a failed job rather than a silently smaller dataset.
python3 /workspace/build.py --out "$OUT" --built-at "$BUILT_AT"
build_status=$?

if [ -f "$OUT/build_summary.json" ]; then
    cp "$OUT/build_summary.json" /output/build_summary.json
fi

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    exit "$build_status"
fi

echo "== qualification =="
python3 /workspace/qualify_dataset.py "$OUT" --json \
    --report /output/qualification.json > /output/qualification.txt 2>&1
qual_status=$?
cat /output/qualification.txt

if [ "$qual_status" -ne 0 ]; then
    echo "qualification FAILED; the artifact must not be scored or accepted" >&2
fi

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
