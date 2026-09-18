#!/bin/sh
# Fresh-consumer verification: follow the published instructions against the published release.
#
# Runs in a container with NO dataset-factory access and NO GitHub credential. It has the
# published repository (mounted at /workspace/repo, byte-checked against MANIFEST.json) and the
# release assets as a consumer receives them, fetched by the worker host - which holds the
# credential - and mounted read-only at /data.
#
# What this exercises is the documented verification, gate and baseline commands. The *network*
# half of `get_dataset.py` is exercised by the worker's fetch, which is the same download with the
# same hash checks; a container cannot run it because it deliberately has no credential.
set -u

OUT=/output
REPO=/workspace/repo
TASK=/tmp/task          # /data is read-only on purpose; work in a writable copy
mkdir -p "$OUT"

echo "== 1. the cloned package matches MANIFEST.json =="
python3 /workspace/verify_package.py "$REPO" || exit 1

echo "== 2. the release assets, as fetched, already carry the runner layout =="
find /data -type f | sort
mkdir -p "$TASK"
cp -a /data/task/. "$TASK/"
find "$TASK" -type f | sort

echo "== 3. sha256sum -c SHA256SUMS (the published verification command) =="
cp "$REPO/SHA256SUMS" "$TASK/SHA256SUMS"
( cd "$TASK" && sha256sum -c SHA256SUMS ) || exit 1

echo "== 4. the published dataset passes the published gate =="
python3 "$REPO/code/qualify_dataset.py" "$TASK" > "$OUT/qualification.txt" 2>&1
gate_status=$?
tail -4 "$OUT/qualification.txt"
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
    tail -20 "$OUT/baseline.log" >&2
    exit 1
fi

echo "== consumer verification passed =="
{ echo "package: every file matches MANIFEST.json"
  echo "checksums: sha256sum -c OK"
  echo "gate: exit 0"
  tail -4 "$OUT/qualification.txt"
  grep -E "^Eval AUC:|CONTRACT OK" "$OUT/baseline.log"; } > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
exit 0