#!/bin/sh
# The runner-contract baseline on EVERY shipped per-code config of the
# chicago-food-inspections multi-label suite (40 configs), in one uniform run.
#
# Runs on an expendable worker. The artifact is FETCHED from private staging
# (the bytes that passed the food-001 gate and the bytes that will be released),
# not rebuilt; the fetch verifies every asset's sha256 on arrival. For each
# config the job:
#   1. re-accepts the exact fetched bytes through the qualification gate's
#      --accept, against the gate's own collected report bundled from the
#      coordinator - so the scored bytes are proved to be the qualified bytes
#      before anything is measured;
#   2. materializes the runner's task directory the way the benchmark's
#      bench/workdir.py does (public train+eval only; the private holdout is
#      never copied into a workdir);
#   3. runs the contract's two entry points: `python train.py` and `validate.sh`.
# A config that fails is recorded and the run continues, so one bad config
# cannot cost the other 39; the job exits non-zero if any config failed.
#
# The runner's train.py / validate.py / validate.sh are bundled verbatim out of
# the read-only benchmark clone and their hashes are recorded in the report, so
# "the existing runner, unmodified" is checkable rather than asserted. This is
# the contract only, not the agent harness loop: no coding agent is run.
#
# /bin/sh on python:3.13-slim is dash, so each step writes its own log and its
# exit status is captured directly rather than through a tee pipeline.
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

CONFIGS=$(ls -1 "$DATA" | sort)
N_CONFIGS=$(echo "$CONFIGS" | wc -l | tr -d ' ')
echo "== configs fetched: $N_CONFIGS =="
if [ "$N_CONFIGS" -ne 40 ]; then
    echo "expected 40 fetched configs, found $N_CONFIGS" >&2
    exit 2
fi

FAILED=""
for CONFIG in $CONFIGS; do
    echo "== $CONFIG: re-accept the fetched artifact against its qualification report =="
    python3 /workspace/qualify_dataset.py --accept \
        "/workspace/qualification-reports/qualification-$CONFIG.json" \
        "$DATA/$CONFIG" > "$OUT/accept-$CONFIG.log" 2>&1
    ACCEPT_RC=$?
    tail -1 "$OUT/accept-$CONFIG.log"
    if [ "$ACCEPT_RC" -ne 0 ]; then
        echo "refusing to score $CONFIG: the fetched bytes are not the qualified artifact" >&2
        FAILED="$FAILED $CONFIG"
        continue
    fi

    rm -rf "$WORK"
    mkdir -p "$WORK"
    cp /workspace/train.py /workspace/validate.py /workspace/validate.sh "$WORK/"
    python3 /workspace/materialize.py "$DATA/$CONFIG" "$WORK" > "$OUT/materialize-$CONFIG.log" 2>&1
    MATERIALIZE_RC=$?
    cat "$OUT/materialize-$CONFIG.log"
    if [ "$MATERIALIZE_RC" -ne 0 ]; then
        echo "$CONFIG: materialize failed" >&2
        FAILED="$FAILED $CONFIG"
        continue
    fi

    ( cd "$WORK" && python3 train.py ) > "$OUT/train-$CONFIG.log" 2>&1
    TRAIN_RC=$?
    tail -1 "$OUT/train-$CONFIG.log"

    ( cd "$WORK" && sh validate.sh ) > "$OUT/validate-$CONFIG.log" 2>&1
    VALIDATE_RC=$?
    tail -1 "$OUT/validate-$CONFIG.log"
    echo "== $CONFIG: train exit=$TRAIN_RC validate exit=$VALIDATE_RC =="

    if [ "$TRAIN_RC" -ne 0 ] || [ "$VALIDATE_RC" -ne 0 ]; then
        FAILED="$FAILED $CONFIG"
    fi
done

echo "== evidence =="
python3 /workspace/report_all.py "$DATA" "$OUT" /workspace/runner_files.json
REPORT_RC=$?

echo "failed configs:${FAILED:- none}"
if [ -n "$FAILED" ]; then
    echo "the runner's contract did not complete cleanly for:$FAILED" >&2
    exit 4
fi
exit "$REPORT_RC"
