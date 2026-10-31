#!/bin/sh
# Worker entrypoint for the acnc-charity-ais-deadline-compliance first build.
#
# Order is fixed and each stage stops the next: construct -> qualify ->
# accept exact bytes -> simple references. build.py only constructs files and
# gate diagnostics; no performance number is computed before acceptance, and
# score.py re-checks the accepted report and the artifact digests before its
# first metric. The holdout is never opened by the reference stage.
set -u

NAME=acnc-charity-ais-deadline-compliance
OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 -u /workspace/build.py --out "$OUT" --work-dir /tmp/acnc \
    --built-at 2026-10-31T00:00:00Z --summary-out /output/summary.json
build_status=$?

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    # keep whatever diagnostics the build managed to write for collection
    if [ -f /output/summary.json ]; then
        echo "summary.json exists despite the failure" >&2
    fi
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

echo "== simple references (post-acceptance only; eval rows only) =="
python3 /workspace/score.py --data "$OUT" \
    --accepted-report /output/qualification-$NAME.json \
    --report /output/references-$NAME.json
score_status=$?

echo "build_status=$build_status qualification_status=$qual_status acceptance_status=$accept_status score_status=$score_status"
exit "$score_status"
