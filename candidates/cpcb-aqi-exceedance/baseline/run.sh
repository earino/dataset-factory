#!/bin/sh
# Runner-contract baseline for cpcb-aqi-exceedance, one artifact, plus the
# pre-registered model-vs-triad deciding check.
#
# Order is fixed and each stage stops the next:
#   1. re-accept the FETCHED artifact against the gate's own collected report,
#      so the scored bytes are proved to be the qualified bytes before any
#      performance number exists;
#   2. materialize the runner task directory the way bench/workdir.py does -
#      public train+eval only; the private holdout is fetched so --accept can
#      run over the full artifact but is never copied into a workdir;
#   3. run the benchmark's own train.py and validate.sh, bundled verbatim from
#      the read-only clone, and record both eval AUCs;
#   4. report.py computes the pre-registered deciding check: the full model's
#      per-row eval scores (same code path as validate.py) against every triad
#      member on identical eval rows, station-clustered paired bootstrap,
#      cluster = station_id.
# No number here is computed before step 1 succeeds.
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

echo "== pre-registered reference triad (post-acceptance, eval rows only) =="
python3 /workspace/score.py --data "$DATA/extract" \
    --accepted-report /workspace/qualification.json \
    --report "$OUT/references-cpcb-aqi-exceedance.json" \
    > "$OUT/references.log" 2>&1
SCORE_RC=$?
tail -6 "$OUT/references.log"
if [ "$SCORE_RC" -ne 0 ]; then
    echo "the reference triad failed; the deciding check is not meaningful" >&2
    exit 5
fi

rm -rf "$WORK"
mkdir -p "$WORK"
cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
cp /workspace/score.py "$WORK/score.py"
python3 /workspace/materialize.py "$DATA/extract" "$WORK" > "$OUT/materialize.log" 2>&1
MATERIALIZE_RC=$?
cat "$OUT/materialize.log"
if [ "$MATERIALIZE_RC" -ne 0 ]; then
    echo "materialize failed" >&2
    exit 3
fi

( cd "$WORK" && python3 train.py ) > "$OUT/train.log" 2>&1
TRAIN_RC=$?
tail -3 "$OUT/train.log"

( cd "$WORK" && sh validate.sh ) > "$OUT/validate.log" 2>&1
VALIDATE_RC=$?
tail -3 "$OUT/validate.log"
echo "== train exit=$TRAIN_RC validate exit=$VALIDATE_RC =="

echo "== evidence + pre-registered deciding check =="
python3 /workspace/report.py "$DATA/extract" "$OUT" /workspace/runner_files.json
REPORT_RC=$?

if [ "$TRAIN_RC" -ne 0 ] || [ "$VALIDATE_RC" -ne 0 ]; then
    echo "the runner's contract did not complete cleanly" >&2
    exit 4
fi
exit "$REPORT_RC"