#!/bin/sh
# One baseline through the runner's existing training and validation contract, on ONE
# per-code config of the chicago-food-inspections multi-label suite: code_38, the
# mid-prevalence code named in the candidate's next_action as the sanity check.
#
# Runs on an expendable worker. The artifact is FETCHED from private staging (the bytes
# that passed the food-001 gate and the bytes that will be released), not rebuilt; the
# fetch verifies every asset's sha256 on arrival. The job then:
#   1. re-accepts the exact artifact through the qualification gate's --accept, against
#      the per-config report bundled from the coordinator - so the scored bytes are
#      proved to be the qualified bytes before anything is measured;
#   2. materializes the runner's task directory the way the benchmark's bench/workdir.py
#      does (public train+eval only; the private holdout is never copied);
#   3. runs the contract's two entry points: `python train.py` and `validate.sh`;
#   4. writes compact evidence to /output (baseline.json, train.log, validate.log).
#
# The runner's train.py / validate.py / validate.sh are bundled verbatim out of the
# read-only benchmark clone and their hashes are recorded in the report, so "the
# existing runner, unmodified" is checkable rather than asserted. This is the contract
# only, not the agent harness loop: no coding agent is run.
set -u

DATA=/data/code_38
WORK=/tmp/workdir
OUT=/output
mkdir -p "$OUT"

echo "== dependencies (ranges from the benchmark's pyproject.toml) =="
python3 -m pip install --no-cache-dir --quiet \
    "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" || {
    echo "dependency install failed" >&2
    exit 1
}

echo "== re-accept the fetched artifact against its qualification report =="
python3 /workspace/qualify_dataset.py --accept /workspace/qualification-code_38.json \
    "$DATA" > "$OUT/accept.log" 2>&1
accept_status=$?
cat "$OUT/accept.log"
if [ "$accept_status" -ne 0 ]; then
    echo "refusing to score: the fetched bytes are not the qualified artifact" >&2
    exit 2
fi

echo "== materialize the runner's task directory =="
mkdir -p "$WORK"
cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
python3 /workspace/materialize.py "$DATA" "$WORK" || exit 3

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
python3 /workspace/report.py "$DATA" "$OUT" "$train_status" "$validate_status" \
    /workspace/runner_files.json

echo "train.py exit=$train_status  validate.sh exit=$validate_status"
if [ "$train_status" -ne 0 ] || [ "$validate_status" -ne 0 ]; then
    echo "the runner's contract did not complete cleanly" >&2
    exit 4
fi
exit 0
