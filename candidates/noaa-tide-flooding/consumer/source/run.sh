#!/bin/sh
# Fresh-consumer verification: follow the published instructions against the published release.
#
# Runs in a container with NO dataset-factory access and NO GitHub credential. It has the published
# repository (mounted at /workspace/repo, byte-checked against MANIFEST.json) and the release assets
# as a consumer receives them, fetched by the worker host - which holds the credential - and mounted
# read-only at /data.
#
# Both levels are checked: each is a contract-complete task instance, so a gate that passes on one
# and fails on the other is a real defect and must not be averaged away.
set -u

OUT=/output
REPO=/workspace/repo
TASK=/tmp/task          # /data is read-only on purpose; work in a writable copy
mkdir -p "$OUT"

echo "== 1. the cloned package matches MANIFEST.json =="
python3 /workspace/verify_package.py "$REPO" || exit 1

echo "== 2. the release assets, as fetched, already carry the layout get_dataset.py restores =="
find /data -type f | sort
mkdir -p "$TASK"
cp -a /data/. "$TASK/"
find "$TASK" -type f | sort

echo "== 3. sha256sum -c SHA256SUMS (the published verification command) =="
cp "$REPO/SHA256SUMS" "$TASK/SHA256SUMS"
( cd "$TASK" && sha256sum -c SHA256SUMS ) || exit 1

echo "== 4. the published dataset passes the published gate, both levels =="
gate_failed=0
for LEVEL in temporal station_disjoint; do
    python3 "$REPO/code/qualify_dataset.py" "$TASK/$LEVEL" > "$OUT/qualification-$LEVEL.txt" 2>&1
    status=$?
    echo "--- $LEVEL ---"
    tail -3 "$OUT/qualification-$LEVEL.txt"
    if [ "$status" -ne 0 ]; then
        echo "the gate rejected the published artifact for $LEVEL" >&2
        gate_failed=1
    fi
done
if [ "$gate_failed" -ne 0 ]; then
    exit 1
fi

echo "== 5. dependencies (the benchmark's declared ranges) =="
# Reported explicitly: this step failed once with nothing in the log to show why, because its
# output went to /output/baseline.log and the container died before that file was uploaded.
python3 -m pip install --no-cache-dir "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" 2>&1 | tail -4
pip_status=$?
python3 - <<'CHECK'
import sys
try:
    import pandas, numpy, xgboost, sklearn
    print("imports OK:", pandas.__version__, numpy.__version__, xgboost.__version__, sklearn.__version__)
except Exception as exc:
    print("IMPORT FAILED:", type(exc).__name__, exc)
    sys.exit(1)
CHECK
if [ $? -ne 0 ] || [ "$pip_status" -ne 0 ]; then
    echo "could not install the benchmark's dependencies; pip status $pip_status" >&2
    exit 1
fi

echo "== 6. the published baseline reproduces, both levels =="
baseline_failed=0
for LEVEL in temporal station_disjoint; do
    echo "--- $LEVEL ---"
    # Tee as well as file: an invisible failure is worse than a slow one.
    sh "$REPO/baseline/reproduce_baseline.sh" "$TASK" "$LEVEL" 2>&1 | tee "$OUT/baseline-$LEVEL.log"
    status=$?
    grep -E "Eval AUC:|CONTRACT OK" "$OUT/baseline-$LEVEL.log"
    if [ "$status" -ne 0 ]; then
        echo "the baseline did not reproduce for $LEVEL (status $status)" >&2
        baseline_failed=1
    fi
done
if [ "$baseline_failed" -ne 0 ]; then
    exit 1
fi

echo "== consumer verification passed =="
{ echo "package: every file matches MANIFEST.json"
  echo "checksums: sha256sum -c OK"
  echo "gate: exit 0 on both levels"
  grep -hE "Eval AUC:|CONTRACT OK" "$OUT"/baseline-*.log
  echo "expected: temporal 0.8638, station_disjoint 0.8688"; } > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
