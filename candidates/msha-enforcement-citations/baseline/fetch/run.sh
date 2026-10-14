#!/bin/sh
# The baseline on the accepted artifact, fetched rather than rebuilt.
#
# The artifact is already built and gated (job msha-002, gate 1.3.0, 32 checks per config), so this
# run fetches config sec_56_12004 from the staging release and measures it through the runner's own
# training and validation contract. What matters is the number obtained on the bytes that will be
# published.
#
# /bin/sh on python:3.13-slim is dash (no pipefail), so each step writes its own log and its exit
# status is captured directly rather than through a tee pipeline.
set -u
OUT=/output
mkdir -p "$OUT"

python3 -m pip install --no-cache-dir "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" > "$OUT/pip-install.log" 2>&1
INSTALL_RC=$?
tail -2 "$OUT/pip-install.log"
python3 -m pip list --format=freeze > "$OUT/dependency-versions.txt" 2>/dev/null

CONFIG=sec_56_12004
WORK=/tmp/task-$CONFIG
rm -rf "$WORK"; mkdir -p "$WORK"
cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
python3 /workspace/materialize.py /data "$WORK" "$CONFIG"
MATERIALIZE_RC=$?

cd "$WORK"
echo "== $CONFIG: python train.py =="
python3 train.py > "$OUT/train-$CONFIG.log" 2>&1
TRAIN_RC=$?
cat "$OUT/train-$CONFIG.log"

echo "== $CONFIG: sh validate.sh =="
sh validate.sh > "$OUT/validate-$CONFIG.log" 2>&1
VALIDATE_RC=$?
cat "$OUT/validate-$CONFIG.log"
cd /

python3 /workspace/report_baseline.py
REPORT_RC=$?

echo "install rc=$INSTALL_RC materialize rc=$MATERIALIZE_RC train rc=$TRAIN_RC validate rc=$VALIDATE_RC report rc=$REPORT_RC"
if [ "$INSTALL_RC" -ne 0 ] || [ "$MATERIALIZE_RC" -ne 0 ] || [ "$TRAIN_RC" -ne 0 ] || [ "$VALIDATE_RC" -ne 0 ]; then
    exit 1
fi
exit "$REPORT_RC"
