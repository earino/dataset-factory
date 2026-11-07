#!/bin/sh
# Worker entrypoint for the dvsa-mot-next-test-outcome full build
# (dvsa-mot-build-002; identical stage order to build-001).
#
# Order is fixed and each stage stops the next: construct -> qualify ->
# accept exact bytes -> pre-registered reference triad. build.py only
# constructs files and gate diagnostics; no performance number is computed
# before acceptance. The deciding model-vs-triad comparison runs in the
# baseline job, never here.
set -u

NAME=dvsa-mot-next-test-outcome
OUT=/output/extract
mkdir -p /output /tmp/dvsa

echo "== build =="
python3 -u /workspace/build.py --out "$OUT" --work-dir /tmp/dvsa
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
    --report /output/qualification-$NAME.json \
    > /output/qualification-$NAME.txt 2>&1
qual_status=$?
tail -5 /output/qualification-$NAME.txt

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

echo "== pre-registered reference triad (post-acceptance only) =="
python3 /workspace/score.py --data "$OUT" \
    --accepted-report /output/qualification-$NAME.json \
    --report /output/references-$NAME.json
score_status=$?

echo "build_status=$build_status qualification_status=$qual_status acceptance_status=$accept_status score_status=$score_status"
exit "$score_status"
