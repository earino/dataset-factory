#!/bin/sh
# Bounded diagnostic for ns-bwa-advisory-lift-duration, one accepted artifact.
#
# Order is fixed and each stage stops the next:
#   1. re-accept the FETCHED artifact against the gate's own collected report, so
#      the scored bytes are proved to be the qualified bytes (artifact
#      e8ed2a53eaf0453c...) before any performance number exists;
#   2. materialize the runner task directory the way bench/workdir.py does -
#      public train+eval only, the private holdout is never copied into a workdir;
#   3. re-run the benchmark's own validate.sh (train.py + validate.py, both
#      verbatim) so the contract is re-verified inside this job;
#   4. diag.py: preserve PER-ROW model scores (predict_proba on the eval rows,
#      validate.py's exact call) and compute the model-vs-persistence and
#      model-vs-calendar paired intervals, a site-clustered paired interval for
#      model-vs-persistence, and per-issue-year model AUC/Brier.
#
# No number is computed before step 1 succeeds. No re-tuning happens anywhere:
# the label, threshold and splits are frozen; the model is the runner template's
# own fixed configuration, refit with its own seed.
set -u

DATA=/data
WORK=/tmp/workdir
OUT=/output
mkdir -p "$OUT"

echo "== dependencies (ranges from the benchmark's pyproject.toml) =="
python3 -m pip install --no-cache-dir --quiet \
    "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" > "$OUT/pip-install.log" 2>&1
INSTALL_RC=$?
tail -2 "$OUT/pip-install.log"
python3 -m pip list --format=freeze > "$OUT/dependency-versions.txt" 2>/dev/null
if [ "$INSTALL_RC" -ne 0 ]; then
    echo "dependency install failed" >&2
    exit 1
fi

echo "== re-accept the fetched artifact against its qualification report =="
python3 /workspace/qualify_dataset.py --accept /workspace/qualification.json "$DATA/extract" \
    > "$OUT/accept.log" 2>&1
ACCEPT_RC=$?
tail -1 "$OUT/accept.log"
if [ "$ACCEPT_RC" -ne 0 ]; then
    echo "refusing to score: the fetched bytes are not the qualified artifact" >&2
    exit 2
fi

rm -rf "$WORK"
mkdir -p "$WORK"
cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
python3 /workspace/materialize.py "$DATA/extract" "$WORK" > "$OUT/materialize.log" 2>&1
MATERIALIZE_RC=$?
cat "$OUT/materialize.log"
if [ "$MATERIALIZE_RC" -ne 0 ]; then
    echo "materialize failed" >&2
    exit 3
fi

( cd "$WORK" && sh validate.sh ) > "$OUT/validate.log" 2>&1
VALIDATE_RC=$?
tail -3 "$OUT/validate.log"

echo "== per-row diagnostic =="
python3 /workspace/diag.py "$DATA/extract" "$WORK" "$OUT" /workspace/runner_files.json
DIAG_RC=$?

echo "== validate exit=$VALIDATE_RC diag exit=$DIAG_RC =="
if [ "$VALIDATE_RC" -ne 0 ] || [ "$DIAG_RC" -ne 0 ]; then
    echo "the runner contract or the diagnostic did not complete cleanly" >&2
    exit 4
fi
exit 0
