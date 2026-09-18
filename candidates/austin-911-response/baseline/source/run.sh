#!/bin/sh
# One baseline through the runner's existing training and validation contract.
#
# Runs on an expendable worker. It rebuilds the accepted artifact, verifies the rebuild is
# byte-identical to the artifact that passed qualification, materializes the runner's task
# directory the way the benchmark's bench/workdir.py does, and runs the contract's two entry
# points: `python train.py` and `validate.sh` (which runs validate.py).
#
# The runner's train.py / validate.py / validate.sh are bundled verbatim and their hashes are
# recorded in the report, so "the existing runner, unmodified" is checkable rather than
# asserted. This is the contract only, not the agent harness loop: no coding agent is run.
#
# The 136 MB extract is rebuilt into /tmp and is NOT uploaded. Only the compact evidence
# (baseline.json, train.log, validate.log) reaches /output and staging.
set -u

EXTRACT=/tmp/extract
WORK=/tmp/workdir
OUT=/output
mkdir -p "$OUT"

echo "== dependencies (ranges from the benchmark's pyproject.toml) =="
python3 -m pip install --no-cache-dir --quiet \
    "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" || {
    echo "dependency install failed" >&2
    exit 1
}

echo "== rebuild the accepted artifact =="
# meta.json embeds built_at_utc, so a rebuild must be told the recorded timestamp or it differs
# from the accepted artifact for that reason alone. Pinning it makes the rebuild byte-identical.
BUILT_AT=$(python3 -c "import json; print(json.load(open('/workspace/expected_artifact.json'))['built_at_utc'])")
python3 /workspace/build.py --out "$EXTRACT" --built-at "$BUILT_AT" || {
    echo "build failed; nothing can be measured" >&2
    exit 1
}

echo "== verify the rebuild is the artifact that passed qualification =="
python3 /workspace/verify_artifact.py "$EXTRACT" /workspace/expected_artifact.json || {
    echo "refusing to measure: the rebuild is not the accepted artifact" >&2
    exit 2
}

echo "== materialize the runner's task directory =="
mkdir -p "$WORK"
cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
python3 /workspace/materialize.py "$EXTRACT" "$WORK" || exit 3

cd "$WORK"

echo "== contract: python train.py =="
python3 train.py > "$OUT/train.log" 2>&1
train_status=$?
cat "$OUT/train.log"

echo "== contract: validate.sh =="
sh validate.sh > "$OUT/validate.log" 2>&1
validate_status=$?
cat "$OUT/validate.log"

echo "== evidence =="
python3 /workspace/report.py "$EXTRACT" "$OUT" "$train_status" "$validate_status" \
    /workspace/runner_files.json

echo "train.py exit=$train_status  validate.sh exit=$validate_status"
if [ "$train_status" -ne 0 ] || [ "$validate_status" -ne 0 ]; then
    echo "the runner's contract did not complete cleanly" >&2
    exit 4
fi
exit 0