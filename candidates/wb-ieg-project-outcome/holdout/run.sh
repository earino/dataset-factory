#!/bin/sh
# Decisive holdout comparison for wb-ieg-project-outcome (bundle wb-holdout).
#
# Runs on an expendable worker against the FETCHED accepted artifact (the bytes
# that passed the wb-001 gate, fetched from private staging release 421262457),
# never rebuilt. The order is construct -> qualify -> accept -> score -> report:
#
#   1. re-accept the exact fetched bytes through the qualification gate's
#      --accept, against the gate's own collected report bundled from the
#      coordinator, BEFORE any scoring. The source review found scoring inside
#      the build; this stage refuses to repeat that ordering and exits without
#      measuring anything if acceptance fails.
#   2. materialize the runner's public workdir (train+eval only; the private
#      holdout is never copied into a workdir - only score_holdout.py reads it,
#      as the scorer, exactly as bench eval would).
#   3. score_holdout.py runs the benchmark's own train.py verbatim via runpy
#      (the same mechanism the benchmark's validate.py uses), then scores that
#      fitted model and the train-fitted references on identical eval and
#      holdout rows, with a paired cluster bootstrap by country and a
#      per-year breakdown.
#
# /bin/sh on python:3.13-slim is dash, so each step writes its own log and its
# exit status is captured directly rather than through a tee pipeline.
set -u

DATA=/data
WORK=/tmp/workdir
OUT=/output
mkdir -p "$OUT"

echo "== dependencies (ranges from the benchmark's pyproject.toml) =="
python3 -m pip install --no-cache-dir --quiet \
    "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" > "$OUT/pip-install.log" 2>&1
INSTALL_RC=$?
tail -2 "$OUT/pip-install.log"
python3 -m pip list --format=freeze > "$OUT/dependency-versions.txt" 2>/dev/null
if [ "$INSTALL_RC" -ne 0 ]; then
    echo "dependency install failed" >&2
    exit 1
fi

echo "== re-accept the fetched artifact against its qualification report =="
python3 /workspace/qualify_dataset.py --accept /workspace/qualification.json "$DATA/extract" \
    > "$OUT/accept.log" 2>&1
ACCEPT_RC=$?
tail -1 "$OUT/accept.log"
if [ "$ACCEPT_RC" -ne 0 ]; then
    echo "refusing to score: the fetched bytes are not the qualified artifact" >&2
    exit 2
fi

rm -rf "$WORK"
mkdir -p "$WORK"
cp /workspace/train.py "$WORK/"
python3 /workspace/materialize.py "$DATA/extract" "$WORK" > "$OUT/materialize.log" 2>&1
MATERIALIZE_RC=$?
cat "$OUT/materialize.log"
if [ "$MATERIALIZE_RC" -ne 0 ]; then
    echo "materialize failed" >&2
    exit 3
fi

echo "== score: model + train-fitted references on identical eval and holdout rows =="
python3 /workspace/score_holdout.py "$DATA/extract" "$WORK" "$OUT" /workspace/runner_files.json
SCORE_RC=$?
echo "== score exit=$SCORE_RC =="
exit "$SCORE_RC"
