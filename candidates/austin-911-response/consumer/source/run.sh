#!/bin/sh
# Fresh-consumer verification: follow the published instructions against the published release.
#
# Runs in a container that has NO dataset-factory access and NO GitHub credential. What it does
# have is the published repository (mounted at /workspace/repo, byte-checked against
# MANIFEST.json) and the release assets exactly as a consumer downloads them (fetched to /data by
# the worker host, which holds the credential - the container never does).
#
# Steps mirror REPRODUCE.md: verify the package, lay out the downloaded assets, check the
# checksums, run the qualification gate, and reproduce the baseline.
set -u

OUT=/output
TASK=/data/task
REPO=/workspace/repo
mkdir -p "$OUT"

echo "== 1. the cloned package matches MANIFEST.json =="
python3 /workspace/verify_package.py "$REPO" || exit 1

echo "== 2. lay out the release assets as get_dataset.py would =="
mkdir -p "$TASK/public" "$TASK/private"
cp /data/train.csv "$TASK/public/train.csv"
cp /data/eval.csv "$TASK/public/eval.csv"
cp /data/holdout.csv "$TASK/private/holdout.csv"
cp /data/meta.json /data/quality.json "$TASK/"
ls -l "$TASK" "$TASK/public" "$TASK/private"

echo "== 3. sha256sum -c SHA256SUMS =="
cp "$REPO/SHA256SUMS" "$TASK/SHA256SUMS"
( cd "$TASK" && sha256sum -c SHA256SUMS ) || exit 1

echo "== 4. the published dataset passes the published gate =="
python3 "$REPO/code/qualify_dataset.py" "$TASK" > "$OUT/qualification.txt" 2>&1
gate_status=$?
tail -3 "$OUT/qualification.txt"
if [ "$gate_status" -ne 0 ]; then
    echo "the gate rejected the published artifact" >&2
    exit 1
fi

echo "== 5. the published baseline reproduces =="
if ! python3 -c "import pandas, numpy, xgboost, sklearn" 2>/dev/null; then
    python3 -m pip install --quiet "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
fi
sh "$REPO/baseline/reproduce_baseline.sh" "$TASK" > "$OUT/baseline.log" 2>&1
baseline_status=$?
grep -E "^Eval AUC:|CONTRACT OK|Training time" "$OUT/baseline.log"
if [ "$baseline_status" -ne 0 ]; then
    echo "the baseline did not reproduce" >&2
    exit 1
fi

echo "== consumer verification passed =="
{ echo "gate: exit 0"; tail -3 "$OUT/qualification.txt"; grep -E "^Eval AUC:|CONTRACT OK" "$OUT/baseline.log"; } \
    > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
exit 0