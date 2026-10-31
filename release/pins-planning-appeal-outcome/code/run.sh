#!/bin/sh
# Worker entrypoint for the pins-planning-appeal-outcome rebuild (pins-planning-002).
#
# Order is fixed and each stage stops the next: runner-contract probe ->
# construct -> qualify -> accept exact bytes -> simple references. The probe
# (stage 0) is synthetic - no dataset row is read, no metric computed - and
# settles, under the dependency ranges the baseline job itself installs,
# whether the verbatim train.py predict path accepts category dtypes; the
# build's writer needs that verdict before it writes a single byte, because a
# rejection means the nine string-categorical columns must ship as integer
# codes (measured defect class of pins-planning-baseline-001). build.py only
# constructs files and gate diagnostics; no performance number is computed
# before acceptance, and score.py re-checks the accepted report and the
# artifact digests before its first metric. The holdout is never opened by the
# reference stage.
set -u

NAME=pins-planning-appeal-outcome
OUT=/output/extract
mkdir -p /output

echo "== runner-contract probe (synthetic; settles the category-dtype question) =="
python3 -m pip install --no-cache-dir --quiet \
    "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" \
    > /output/probe-pip.log 2>&1
PROBE_DEPS_RC=$?
tail -2 /output/probe-pip.log
if [ "$PROBE_DEPS_RC" -ne 0 ]; then
    echo "probe dependency install failed; the category question cannot be settled" >&2
    exit 5
fi
python3 /workspace/probe_category_predict.py --out /output/category_probe.json
PROBE_RC=$?
if [ "$PROBE_RC" -ne 0 ]; then
    echo "category probe did not run cleanly; refusing to guess the writer mode" >&2
    exit "$PROBE_RC"
fi
cat /output/category_probe.json

echo "== build =="
python3 -u /workspace/build.py --out "$OUT" --work-dir /tmp/pins \
    --built-at 2026-10-31T00:00:00Z --summary-out /output/summary.json \
    --category-probe-result /output/category_probe.json
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

echo "probe_deps_status=$PROBE_DEPS_RC probe_status=$PROBE_RC build_status=$build_status qualification_status=$qual_status acceptance_status=$accept_status score_status=$score_status"
exit "$score_status"
