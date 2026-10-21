#!/bin/sh
# Reproduce the runner-contract baseline on a downloaded copy of this dataset.
#
# Usage: sh baseline/reproduce_baseline.sh <dataset-dir>
#
# Runs the benchmark's own train.py and validate.sh, unmodified, on the public
# splits; the private holdout is never copied into the workdir. Needs the
# dependency ranges in the benchmark's pyproject.toml (pandas, numpy, xgboost,
# scikit-learn) - install them first if they are missing.
#
# The measured result of this exact procedure is recorded in VERIFICATION.md and
# in MANIFEST.json's baseline block.
set -u

DATA=${1:-./task}
WORK=${WORK:-./baseline-workdir}

if [ ! -f "$DATA/meta.json" ]; then
    echo "no meta.json under $DATA - run get_dataset.py first" >&2
    exit 2
fi

rm -rf "$WORK"
mkdir -p "$WORK/data"
cp baseline/train.py baseline/validate.py baseline/validate.sh "$WORK/"

python3 - "$DATA" "$WORK" <<'PY'
import json, shutil, sys
from pathlib import Path
data, work = Path(sys.argv[1]), Path(sys.argv[2])
meta = json.loads((data / "meta.json").read_text())
keys = ("name", "description", "target", "positive_label", "id_columns", "split", "columns", "rows")
(work / "task.json").write_text(json.dumps({k: meta[k] for k in keys}, indent=2) + "\n")
for name in ("train.csv", "eval.csv"):
    shutil.copyfile(data / "public" / name, work / "data" / name)
print("task.json + data/ prepared from the public splits (holdout NOT copied)")
PY

( cd "$WORK" && python3 train.py ) || exit 3
( cd "$WORK" && sh validate.sh ) || exit 4
echo "baseline reproduced: see the Eval AUC printed by train.py and validate.py above"