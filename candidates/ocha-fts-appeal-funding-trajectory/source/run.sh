#!/bin/sh
# Worker entrypoint for the ocha-fts-appeal-funding-trajectory construction
# (fts-appeal-003, the P0-recovery rebuild: the prior-outcome history features
# country_prior_appeals / country_prior_covered_rate / country_last_prior_covered
# no longer ship; see the job record and the 2026-11-01 queue audit).
#
# Order is fixed and each stage stops the next: construct -> qualify -> accept
# exact bytes -> simple references. build.py only constructs files and gate
# diagnostics (row/positive counts, dated fixture asserts, exclusion buckets -
# no AUC, no accuracy, no model); the first performance number in this job is
# computed by score.py, which refuses to run unless the gate passed over the
# full artifact AND --accept re-verified the exact bytes, and which never opens
# the private holdout. Everything is stdlib-only Python - no pip stage.
set -u

NAME=ocha-fts-appeal-funding-trajectory
OUT=/output/extract
mkdir -p /output

echo "== build (construct only; no performance metric) =="
python3 -u /workspace/build.py --out "$OUT" --work-dir /tmp/fts \
    --built-at 2026-11-02T00:00:00Z --summary-out /output/summary.json
build_status=$?

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    # keep whatever diagnostics the build managed to write for collection
    exit "$build_status"
fi

echo "== qualification (full artifact, current gate) =="
python3 /workspace/qualify_dataset.py "$OUT" --json \
    --report /output/qualification-$NAME.json \
    > /output/qualification-$NAME.txt 2>&1
qual_status=$?
cat /output/qualification-$NAME.txt

if [ "$qual_status" -ne 0 ]; then
    echo "qualification failed; nothing is scored" >&2
    exit "$qual_status"
fi

echo "== acceptance (exact bytes) =="
python3 /workspace/qualify_dataset.py --accept \
    /output/qualification-$NAME.json "$OUT" \
    > /output/acceptance-$NAME.txt 2>&1
accept_status=$?
cat /output/acceptance-$NAME.txt

if [ "$accept_status" -ne 0 ]; then
    echo "acceptance failed; nothing is scored" >&2
    exit "$accept_status"
fi

echo "== simple references (post-acceptance only; eval rows only; holdout sealed) =="
python3 /workspace/score.py --data "$OUT" \
    --accepted-report /output/qualification-$NAME.json \
    --report /output/references-$NAME.json
score_status=$?

echo "build_status=$build_status qualification_status=$qual_status acceptance_status=$accept_status score_status=$score_status"
exit "$score_status"
