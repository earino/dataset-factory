#!/bin/sh
# One baseline through the runner's existing training and validation contract, for both levels.
#
# Runs on an expendable worker. The runner's `train.py`, `validate.py` and `validate.sh` are bundled
# verbatim from the read-only benchmark clone and their hashes are recorded in the report, so
# "the existing runner, unmodified" is checkable rather than asserted. This is the contract only -
# no coding agent is run, and no harness comparison is implied.
#
# The artifact is rebuilt from source here rather than copied from staging: it needs no credential,
# it demonstrates that the dataset can be built and scored from the source in one job, and the
# ~180 MB of CSVs never touch the coordinator. Only compact evidence reaches /output.
set -u

EXTRACT=/tmp/extract
OUT=/output
mkdir -p "$OUT"

echo "== dependencies =="
python3 -m pip install --no-cache-dir --quiet \
    "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" || {
    echo "dependency install failed" >&2
    exit 1
}

echo "== build both levels =="
python3 /workspace/build.py --out "$EXTRACT" --concurrency 3 --max-errors 30 || {
    echo "build failed or coverage was short; nothing can be measured" >&2
    exit 2
}

# The runner reads task.json for target/positive_label/id_columns and drops those from the feature
# matrix. A column the artifact declares as a carry column (description, not a feature) must be
# dropped by the runner too, or a string column reaches the model.
python3 /workspace/materialize.py "$EXTRACT" || exit 3

status=0
for level in temporal station_disjoint; do
    echo "== baseline: $level =="
    WORK="/tmp/work-$level"
    mkdir -p "$WORK"
    cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
    cp "$EXTRACT/$level/task.json" "$WORK/task.json"
    mkdir -p "$WORK/data"
    cp "$EXTRACT/$level/public/train.csv" "$WORK/data/train.csv"
    cp "$EXTRACT/$level/public/eval.csv" "$WORK/data/eval.csv"

    ( cd "$WORK" && python3 train.py ) > "/output/train-$level.log" 2>&1
    train_status=$?
    ( cd "$WORK" && sh validate.sh ) > "/output/validate-$level.log" 2>&1
    validate_status=$?

    echo "  train_status=$train_status validate_status=$validate_status"
    grep -E "Eval AUC|CONTRACT" "/output/train-$level.log" "/output/validate-$level.log" || true

    if [ "$train_status" -ne 0 ] || [ "$validate_status" -ne 0 ]; then
        echo "baseline failed for $level" >&2
        status=1
    fi
done

python3 /workspace/report.py "$EXTRACT" "$OUT" || status=1
echo "baseline_status=$status"
exit "$status"
