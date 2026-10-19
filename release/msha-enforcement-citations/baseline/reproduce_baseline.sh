#!/bin/sh
# Reproduce the recorded baseline: the benchmark's own train.py and validate.py, unmodified,
# against one config of this dataset.
#
#   sh baseline/reproduce_baseline.sh [dataset-dir] [config]     (default: ./task sec_56_12004)
#
# <dataset-dir> is what get_dataset.py produces: 45 per-section config directories, each holding
# public/, private/, meta.json, quality.json. The private holdout is deliberately not copied into
# the working directory - the contract scores train and eval only.
set -eu

DATASET=$(cd "${1:-task}" && pwd)
CONFIG="${2:-sec_56_12004}"
HERE=$(cd "$(dirname "$0")" && pwd)

if [ ! -f "$DATASET/$CONFIG/meta.json" ]; then
    echo "no $CONFIG/meta.json in $DATASET - run get_dataset.py --config $CONFIG first" >&2
    exit 1
fi

if ! python3 -c "import pandas, numpy, xgboost, sklearn" 2>/dev/null; then
    echo "installing the benchmark's declared dependency ranges ..."
    python3 -m pip install --quiet "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
fi

WORK="${WORK:-/tmp/msha-baseline-$CONFIG}"
rm -rf "$WORK"
mkdir -p "$WORK"
cp "$HERE/train.py" "$HERE/validate.py" "$HERE/validate.sh" "$WORK/"
python3 "$HERE/../code/materialize.py" "$DATASET" "$WORK" "$CONFIG"

cd "$WORK"
echo "== $CONFIG: contract: python train.py =="
python3 train.py
echo "== $CONFIG: contract: sh validate.sh =="
sh validate.sh
cd - >/dev/null

echo
echo "Compare against the recorded values in MANIFEST.json: sec_56_12004 eval AUC 0.8036"
echo "(train AUC 0.8036 on the same run). Only sec_56_12004 has a recorded baseline;"
echo "per-config persistence references for all 45 are in MANIFEST.json measurements.levels."
