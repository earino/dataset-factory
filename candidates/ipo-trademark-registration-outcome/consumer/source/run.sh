#!/bin/sh
# Fresh-consumer verification for the ipo-trademark-registration-outcome v2026.10 release:
# every command the published REPRODUCE.md documents, run against the release bytes.
#
# Runs in a container with NO dataset-factory access and NO GitHub credential. The published
# package is mounted read-only at /workspace/repo (byte-checked against MANIFEST.json) and the
# five release assets are fetched by the worker host - which holds the read credential outside
# the container - and mounted read-only at /data in the layout get_dataset.py restores.
#
# Order follows the qualification contract: verify bytes, then gate, then exact-byte
# acceptance, and only then any performance figure (baseline, references). The optional
# rebuild from source runs last and must be byte-identical to the release.
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

echo "== 5. the published gate re-runs on the published bytes =="
python3 "$REPO/code/qualify_dataset.py" "$TASK" > "$OUT/qualification.txt" 2>&1 \
    || { echo "the gate rejected the published artifact" >&2; tail -20 "$OUT/qualification.txt" >&2; exit 1; }
grep -E "PASSED|failed checks" "$OUT/qualification.txt" | tail -3

echo "== 6. exact-byte acceptance against the shipped qualification report =="
python3 "$REPO/code/qualify_dataset.py" --accept "$REPO/qualification.json" "$TASK" > "$OUT/accept.txt" 2>&1 \
    || { echo "exact-byte acceptance failed" >&2; tail -20 "$OUT/accept.txt" >&2; exit 1; }
grep -E "ACCEPTED|artifact" "$OUT/accept.txt" | tail -3

echo "== 7. dependencies (the benchmark's declared ranges) =="
python3 -m pip install --no-cache-dir --quiet "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5" \
    || { echo "pip install failed" >&2; exit 1; }
python3 - <<'CHECK'
import pandas, numpy, xgboost, sklearn
print("imports OK:", pandas.__version__, numpy.__version__, xgboost.__version__, sklearn.__version__)
CHECK

echo "== 8. the published baseline reproduces =="
( cd "$REPO" && WORK=/tmp/baseline-workdir sh baseline/reproduce_baseline.sh "$TASK" ) > "$OUT/baseline.log" 2>&1 \
    || { echo "the baseline did not reproduce" >&2; cat "$OUT/baseline.log" >&2; exit 1; }
cat "$OUT/baseline.log"
grep -c "CONTRACT OK" "$OUT/baseline.log" | grep -qv "^0$" || { echo "CONTRACT OK missing" >&2; exit 1; }
python3 - <<'CHECK'
import re, sys
log = open("/output/baseline.log").read()
aucs = re.findall(r"(?:Eval AUC:|eval AUC via predict_proba[^:]*:)\s*([01]\.\d+)", log)
print("auc prints:", aucs)
if len(aucs) < 2 or any(abs(float(a) - 0.6224) > 0.00005 for a in aucs):
    print("BASELINE MISMATCH: expected both AUC prints at 0.6224", file=sys.stderr)
    sys.exit(1)
CHECK

echo "== 9. the published references recompute =="
python3 "$REPO/code/score.py" --data "$TASK" --accepted-report "$REPO/qualification.json" \
    --report "$OUT/references.json" || exit 1
python3 - "$OUT/references.json" "$REPO/measurements.json" <<'CHECK' || exit 1
import json, sys
report = json.load(open(sys.argv[1]))
recorded = json.load(open(sys.argv[2]))["references"]
expected = dict(recorded["aucs"])
expected["majority_class"] = recorded.get("majority_class_accuracy_this_split")

def value_of(entry):
    # majority_class carries auc_eval: null by design (a constant has no ranking
    # information) and its accuracy in accuracy_eval - a plain .get with default
    # returns the existing null, which is exactly the first version's defect.
    if not isinstance(entry, dict):
        return None
    auc = entry.get("auc_eval")
    return auc if auc is not None else entry.get("accuracy_eval")

checked, bad = 0, []
for name, want in sorted(expected.items()):
    got = value_of(report["references"].get(name))
    if want is None or got is None:
        bad.append(f"{name}: missing value (recomputed {got}, recorded {want})")
        continue
    checked += 1
    if abs(got - want) > 1e-9:
        bad.append(f"{name}: recomputed {got} != recorded {want}")
print(f"  {checked} references recomputed and equal to the recorded figures")
if bad:
    print("REFERENCE MISMATCH:", *bad, sep="\n  ", file=sys.stderr)
    sys.exit(1)
CHECK

echo "== 10. rebuild from source reproduces byte-identical files =="
python3 "$REPO/code/build.py" --out /tmp/rebuild --work-dir /tmp/ipotm-work \
    --built-at 2026-10-30T00:00:00Z > "$OUT/rebuild.log" 2>&1 \
    || { echo "the rebuild failed" >&2; tail -20 "$OUT/rebuild.log" >&2; exit 1; }
tail -5 "$OUT/rebuild.log"
cp "$REPO/SHA256SUMS" /tmp/rebuild/SHA256SUMS
( cd /tmp/rebuild && sha256sum -c SHA256SUMS ) || { echo "rebuild is NOT byte-identical" >&2; exit 1; }
echo "rebuild byte-identical to the release: all five digests match"

echo "== consumer verification passed =="
{ echo "package: every file matches MANIFEST.json"
  echo "download: 5 assets host-fetched and digest-verified, layout restored, get_dataset.py re-verification OK"
  echo "checksums: sha256sum -c SHA256SUMS OK over the restored tree"
  echo "gate: PASSED on the full published artifact"
  echo "accept: ACCEPTED for artifact 2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d"
  echo "baseline: CONTRACT OK, both AUC prints 0.6224"
  echo "references: recomputed equal to the recorded figures (mark_type 0.5650, nice_class 0.5421, ...)"
  echo "rebuild: byte-identical to the release (--built-at 2026-10-30T00:00:00Z)"; } > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
