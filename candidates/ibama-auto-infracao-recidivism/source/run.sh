#!/bin/sh
# Worker entrypoint for the ibama-auto-infracao-recidivism construction
# (ibama-build-001).
#
# Order is fixed and each stage stops the next: fixture test -> construct ->
# qualify -> accept exact bytes -> simple references. test_fixture.py proves
# the construction logic (labels, boundaries, normalization, censoring,
# ledger) on a synthetic zip BEFORE the live source is touched. build.py only
# constructs files and gate diagnostics (counts, exclusion buckets, drift vs
# the probe reference, cross-checks - no AUC, no accuracy, no model); the first
# performance number in this job is computed by score.py, which refuses to run
# unless the gate passed over the full artifact AND --accept re-verified the
# exact bytes, and which never opens the private holdout. Everything is
# stdlib-only Python - no pip stage.
set -u

NAME=ibama-auto-infracao-recidivism
OUT=/output/extract
mkdir -p /output

echo "== fixture test (synthetic zip; construction logic proven before the live source) =="
python3 -u /workspace/test_fixture.py --build /workspace/build.py
fixture_status=$?
if [ "$fixture_status" -ne 0 ]; then
    echo "fixture test failed; the construction logic is not fit to touch the source" >&2
    exit "$fixture_status"
fi

echo "== build (construct only; no performance metric) =="
python3 -u /workspace/build.py --out "$OUT" --work-dir /tmp/ibama-build \
    --built-at 2026-11-05T00:00:00Z \
    --summary-out /output/summary.json
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

echo "fixture_status=$fixture_status build_status=$build_status qualification_status=$qual_status acceptance_status=$accept_status score_status=$score_status"
exit "$score_status"
