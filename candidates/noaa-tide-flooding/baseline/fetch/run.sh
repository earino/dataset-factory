#!/bin/sh
# The baseline on the accepted artifact, fetched rather than rebuilt.
#
# The artifact is already built and gated, so this run fetches it from staging and measures it. The
# rebuild-and-measure variant belongs with the build job; what matters here is the number obtained on
# the bytes that will be published.
set -u
OUT=/output
mkdir -p "$OUT"

python3 -m pip install --no-cache-dir "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" 2>&1 | tail -2

for LEVEL in temporal station_disjoint; do
    WORK=/tmp/task-$LEVEL
    rm -rf "$WORK"; mkdir -p "$WORK"
    cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
    python3 /workspace/materialize.py /data "$WORK" "$LEVEL"
    cd "$WORK"
    echo "== $LEVEL: python train.py =="
    python3 train.py 2>&1 | tee "$OUT/train-$LEVEL.log"
    echo "== $LEVEL: sh validate.sh =="
    sh validate.sh 2>&1 | tee "$OUT/validate-$LEVEL.log"
    cd /
done

python3 /workspace/report_baseline.py
