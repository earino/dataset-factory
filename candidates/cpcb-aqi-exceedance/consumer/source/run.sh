#!/bin/sh
# Fresh-consumer verification for the cpcb-aqi-exceedance v2026.11 release:
# every command the published REPRODUCE.md documents, run against the release
# bytes, plus the pre-registered deciding check REPRODUCE.md says recomputation
# must reproduce.
#
# Runs in a container with NO dataset-factory access and NO GitHub credential.
# The published package is mounted read-only at /workspace/repo (byte-checked
# against MANIFEST.json) and the five release assets are fetched by the worker
# host - which holds the read credential outside the container - and mounted
# read-only at /data in the layout get_dataset.py restores.
#
# Order follows the qualification contract: verify bytes, then gate, then
# exact-byte acceptance, and only then any performance figure (baseline,
# references, deciding check). The optional rebuild-from-export step is not
# run: code/build.py refuses any export other than the pinned one and
# REPRODUCE.md documents it as optional (the artifact is reproducible from
# the release assets regardless).
set -u

OUT=/output
REPO=/workspace/repo
TASK=/tmp/task
mkdir -p "$OUT"

echo "== 1. the cloned package matches MANIFEST.json =="
python3 /workspace/verify_package.py "$REPO" || exit 1

echo "== 2. the release assets, as fetched, carry the layout get_dataset.py restores =="
find /data -type f | sort
mkdir -p "$TASK"
cp -a /data/. "$TASK/"

echo "== 3. get_dataset.py verifies the restored tree (files already present; no credential) =="
python3 "$REPO/get_dataset.py" --dest "$TASK" || exit 1

echo "== 4. sha256sum -c SHA256SUMS (the published verification command) =="
cp "$REPO/SHA256SUMS" "$TASK/SHA256SUMS"
( cd "$TASK" && sha256sum -c SHA256SUMS ) || exit 1
rm "$TASK/SHA256SUMS"

echo "== 5. the published gate re-runs on the published bytes =="
python3 "$REPO/code/qualify_dataset.py" "$TASK" > "$OUT/qualification.txt" 2>&1 \
    || { echo "the gate rejected the published artifact" >&2; tail -20 "$OUT/qualification.txt" >&2; exit 1; }
grep -E "PASSED|failed checks" "$OUT/qualification.txt" | tail -3

echo "== 6. exact-byte acceptance against the shipped qualification report =="
python3 "$REPO/code/qualify_dataset.py" --accept "$REPO/qualification.json" "$TASK" > "$OUT/accept.txt" 2>&1 \
    || { echo "exact-byte acceptance failed" >&2; tail -20 "$OUT/accept.txt" >&2; exit 1; }
grep -E "ACCEPTED|artifact" "$OUT/accept.txt" | tail -3

echo "== 7. dependencies (the published ranges) =="
python3 -m pip install --no-cache-dir --quiet "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" \
    || { echo "pip install failed" >&2; exit 1; }
python3 - <<'CHECK' | tee "$OUT/versions.txt"
import platform
import pandas, numpy, xgboost, sklearn
print("imports OK:", platform.python_version(), pandas.__version__, numpy.__version__,
      xgboost.__version__, sklearn.__version__)
CHECK

echo "== 8. the published baseline reproduces =="
( cd "$REPO" && sh baseline/reproduce_baseline.sh "$TASK" ) > "$OUT/baseline.log" 2>&1 \
    || { echo "the baseline did not reproduce" >&2; cat "$OUT/baseline.log" >&2; exit 1; }
cat "$OUT/baseline.log"
grep -c "CONTRACT OK" "$OUT/baseline.log" | grep -qv "^0$" || { echo "CONTRACT OK missing" >&2; exit 1; }
grep -c "the private holdout was NOT copied" "$OUT/baseline.log" | grep -qv "^0$" \
    || { echo "holdout-isolation marker missing" >&2; exit 1; }
python3 - <<'CHECK'
import re, sys
log = open("/output/baseline.log").read()
aucs = re.findall(r"(?:Eval AUC:|eval AUC via predict_proba[^:]*:)\s*([01]\.\d+)", log)
print("auc prints:", aucs)
if len(aucs) < 2 or any(abs(float(a) - 0.9734) > 0.00005 for a in aucs):
    print("BASELINE MISMATCH: expected both AUC prints at 0.9734", file=sys.stderr)
    sys.exit(1)
CHECK

echo "== 9. the published references recompute =="
python3 "$REPO/code/score.py" --data "$TASK" --accepted-report "$REPO/qualification.json" \
    --report "$OUT/references.json" || exit 1
python3 /workspace/check_references.py "$OUT/references.json" "$REPO/measurements.json" || exit 1

echo "== 10. the pre-registered deciding check recomputes on the released bytes =="
DECIDE=/tmp/decide
mkdir -p "$DECIDE"
cp "$REPO/baseline/train.py" "$DECIDE/train.py"
python3 "$REPO/code/materialize.py" "$TASK" "$DECIDE" || exit 1
python3 /workspace/decide_check.py "$REPO" "$TASK" "$DECIDE" "$OUT" "$REPO/measurements.json" || exit 1

echo "== consumer verification passed =="
{ echo "package: every file matches MANIFEST.json"
  echo "download: 5 assets host-fetched and digest-verified, layout restored, get_dataset.py re-verification OK"
  echo "checksums: sha256sum -c SHA256SUMS OK over the restored tree"
  echo "gate: PASSED on the full published artifact"
  echo "accept: ACCEPTED for artifact a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959"
  echo "baseline: CONTRACT OK, both AUC prints 0.9734, holdout never copied into a workdir"
  echo "references: recomputed equal to measurements.json (station_persistence 0.9689, state_season_climatology 0.8617, station_train_rate 0.7616, global_rate degenerate, majority accuracy 0.8434)"
  echo "deciding check: model-minus-persistence [0.0038, 0.0052] and model-minus-climatology [0.1002, 0.1252] reproduced; model AUC CI low above 0.5"
  echo "rebuild: not run (optional per REPRODUCE.md; build.py refuses any changed export)"; } > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
