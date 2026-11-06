#!/bin/sh
# Reproduce the recorded runner-contract baseline for cpcb-aqi-exceedance.
# Mirrors worker job cpcb-aqi-baseline-001's run.sh for a local task directory: re-accept
# the bytes against the shipped qualification report BEFORE any score,
# materialize the runner workdir from the PUBLIC splits only (the private
# holdout is never copied into a workdir), then run the benchmark's own
# train.py + validate.sh unmodified. Expected: both print eval AUC 0.9734.
#
# Usage: sh baseline/reproduce_baseline.sh ./task
set -u

TASK=${1:-./task}
WORK=$(mktemp -d)
echo "workdir: $WORK"

echo "== re-accept the artifact against its qualification report =="
python3 code/qualify_dataset.py --accept qualification.json "$TASK" || {
    echo "refusing to score: the bytes are not the qualified artifact" >&2
    exit 2
}

echo "== materialize the runner workdir (public train+eval only) =="
cp baseline/train.py baseline/validate.py baseline/validate.sh "$WORK/"
cp code/score.py "$WORK/score.py"
python3 code/materialize.py "$TASK" "$WORK" || exit 3

echo "== the benchmark's own runner, unmodified =="
( cd "$WORK" && python3 train.py ) || exit 4
( cd "$WORK" && sh validate.sh ) || exit 4

echo "== pre-registered references on the identical eval rows =="
python3 "$WORK/score.py" --data "$TASK" \
    --accepted-report qualification.json \
    --report "$WORK/references.json" || exit 5
echo "expected: station_persistence 0.9689, state_season_climatology 0.8617, model 0.9734"
echo "done - compare the printed AUCs with measurements.json"
