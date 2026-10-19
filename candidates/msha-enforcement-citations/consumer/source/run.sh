#!/bin/sh
# Fresh-consumer verification for the MSHA release: follow the published instructions against the
# published release bytes.
#
# Runs in a container with NO dataset-factory access and NO GitHub credential. It has the published
# repository (mounted at /workspace/repo, byte-checked against MANIFEST.json) and the release assets
# as a consumer receives them, fetched by the worker host - which holds the credential - and mounted
# read-only at /data in the layout get_dataset.py restores.
#
# All 45 per-section configs are gated: each is a contract-complete binary task instance, so a gate
# that passes on one and fails on another is a real defect and must not be averaged away.
set -u

OUT=/output
REPO=/workspace/repo
TASK=/tmp/task          # /data is read-only on purpose; work in a writable copy
BASELINE_CONFIG=sec_56_12004
mkdir -p "$OUT"

echo "== 1. the cloned package matches MANIFEST.json =="
python3 /workspace/verify_package.py "$REPO" || exit 1

echo "== 2. the release assets, as fetched, carry the layout get_dataset.py restores =="
find /data -type f | wc -l
mkdir -p "$TASK"
cp -a /data/. "$TASK/"

echo "== 3. sha256sum -c SHA256SUMS (the published verification command) =="
cp "$REPO/SHA256SUMS" "$TASK/SHA256SUMS"
( cd "$TASK" && sha256sum -c SHA256SUMS ) || exit 1

echo "== 4. every published config passes the published gate =="
CONFIGS=$(python3 -c "import json;m=json.load(open('$REPO/MANIFEST.json'));print(' '.join(sorted(m['levels'])))")
count=$(echo "$CONFIGS" | wc -w)
echo "configs: $count"
gate_failed=0
for CONFIG in $CONFIGS; do
    python3 "$REPO/code/qualify_dataset.py" "$TASK/$CONFIG" > "$OUT/qualification-$CONFIG.txt" 2>&1
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "the gate rejected the published artifact for $CONFIG" >&2
        tail -5 "$OUT/qualification-$CONFIG.txt" >&2
        gate_failed=1
    fi
done
if [ "$gate_failed" -ne 0 ]; then
    exit 1
fi
grep -h "PASSED\|failed" "$OUT"/qualification-*.txt | sort | uniq -c | head -5

echo "== 5. dependencies (the benchmark's declared ranges) =="
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

echo "== 6. the published baseline reproduces on $BASELINE_CONFIG =="
sh "$REPO/baseline/reproduce_baseline.sh" "$TASK" "$BASELINE_CONFIG" 2>&1 | tee "$OUT/baseline.log"
status=$?
grep -E "Eval AUC:|CONTRACT OK" "$OUT/baseline.log"
if [ "$status" -ne 0 ]; then
    echo "the baseline did not reproduce (status $status)" >&2
    exit 1
fi

echo "== consumer verification passed =="
{ echo "package: every file matches MANIFEST.json"
  echo "checksums: sha256sum -c OK over 226 assets"
  echo "gate: exit 0 on all $count configs"
  grep -hE "Eval AUC:|CONTRACT OK" "$OUT/baseline.log"
  echo "expected: $BASELINE_CONFIG 0.8036, persistence reference 0.5831"; } > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
