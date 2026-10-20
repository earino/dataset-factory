#!/bin/sh
# Fresh-consumer verification for the chicago-food-inspections release: follow the published
# instructions against the release bytes in the private dataset repository.
#
# Runs in a container with NO dataset-factory access and NO GitHub credential. It has the
# published repository (mounted at /workspace/repo, byte-checked against MANIFEST.json) and the
# release assets as a consumer receives them: fetched by the worker host - which holds the
# credential - and mounted read-only at /data in the layout get_dataset.py restores.
#
# All 40 per-code configs are checked: each is a contract-complete binary task instance, so an
# --accept that passes on one and fails on another is a real defect and must not be averaged away.
set -u

OUT=/output
REPO=/workspace/repo
TASK=/tmp/task          # /data is read-only on purpose; work in a writable copy
BASELINE_CONFIG=code_38
EXPECTED_AUC=0.6326
mkdir -p "$OUT"

echo "== 1. the cloned package matches MANIFEST.json =="
python3 /workspace/verify_package.py "$REPO" || exit 1

echo "== 2. the release assets, as fetched, carry the layout get_dataset.py restores =="
find /data -type f | wc -l
mkdir -p "$TASK"
cp -a /data/. "$TASK/"

echo "== 3. sha256sum -c SHA256SUMS (the published verification command) =="
cp "$REPO/SHA256SUMS" "$TASK/SHA256SUMS"
( cd "$TASK" && sha256sum -c SHA256SUMS ) || exit 1

echo "== 4. every published config re-accepts through the qualification gate =="
CONFIGS=$(python3 -c "import json;m=json.load(open('$REPO/MANIFEST.json'));print(' '.join(sorted(m['levels'])))")
count=$(echo "$CONFIGS" | wc -w)
echo "configs: $count"
accept_failed=0
for CONFIG in $CONFIGS; do
    python3 "$REPO/code/qualify_dataset.py" --accept \
        "/workspace/qual-reports/qualification-$CONFIG.json" "$TASK/$CONFIG" \
        > "$OUT/accept-$CONFIG.txt" 2>&1
    status=$?
    if [ "$status" -ne 0 ]; then
        echo "gate --accept rejected the published bytes for $CONFIG" >&2
        tail -5 "$OUT/accept-$CONFIG.txt" >&2
        accept_failed=1
    fi
done
if [ "$accept_failed" -ne 0 ]; then
    exit 1
fi
echo "gate --accept: exit 0 on all $count configs"

echo "== 5. the published baseline reproduces on $BASELINE_CONFIG =="
sh "$REPO/baseline/reproduce_baseline.sh" "$TASK" "$BASELINE_CONFIG" > "$OUT/baseline.log" 2>&1
status=$?
grep -E "eval AUC|CONTRACT" "$OUT/baseline.log" || true
if [ "$status" -ne 0 ]; then
    echo "the baseline contract failed (status $status)" >&2
    tail -20 "$OUT/baseline.log" >&2
    exit 1
fi
python3 - "$OUT/baseline.log" <<'CHECK'
import re, sys
text = open(sys.argv[1]).read()
match = re.search(r"\[validate\] eval AUC[^:]*:\s*([0-9.]+)", text)
if not match:
    print("no [validate] eval AUC line in the baseline log")
    sys.exit(1)
value = float(match.group(1))
if abs(value - 0.6326) > 0.001:
    print(f"baseline AUC {value:.4f} does not reproduce the recorded 0.6326")
    sys.exit(1)
print(f"baseline AUC reproduces: {value:.4f} (recorded 0.6326, tolerance 0.001)")
CHECK
if [ $? -ne 0 ]; then
    echo "the baseline did not reproduce" >&2
    exit 1
fi

echo "== consumer verification passed =="
{ echo "package: every file matches MANIFEST.json"
  echo "checksums: sha256sum -c OK over 201 assets"
  echo "gate: --accept exit 0 on all $count configs (bytes identical to the qualified artifact version)"
  grep -E "eval AUC" "$OUT/baseline.log" | tail -2
  echo "expected: $BASELINE_CONFIG 0.6326 (food-baseline-002/003), tolerance 0.001"; } > "$OUT/consumer.txt"
cat "$OUT/consumer.txt"
