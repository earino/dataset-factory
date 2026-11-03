#!/bin/sh
# Worker entrypoint: re-qualify the audit-corrected descriptor on the exact
# accepted CSV bytes. The 2026-11-03 independent re-audit returned PUBLISH WITH
# CONDITIONS; condition 1 (grain described as appeal-plan ID x plan year, with
# the country-year non-uniqueness recorded) is descriptor-only: the three CSVs
# are byte-identical to the audited v2026.11 artifact (fetched from the private
# GitHub release at audited digests), while quality.json carries the corrected
# id_columns_note. Nothing is rebuilt from the source; no performance metric is
# computed here. Stages: layout -> qualify (gate two-phase) -> accept.
set -u
NAME=ocha-fts-appeal-funding-trajectory
DATA=/data
OUT=/output
EXTRACT="$OUT/extract"
mkdir -p "$OUT" "$EXTRACT/public" "$EXTRACT/private"
echo "== layout (accepted CSV bytes + corrected descriptors) =="
cp "$DATA/extract/public/train.csv"      "$EXTRACT/public/train.csv"
cp "$DATA/extract/public/eval.csv"       "$EXTRACT/public/eval.csv"
cp "$DATA/extract/private/holdout.csv"    "$EXTRACT/private/holdout.csv"
cp /workspace/meta.json                  "$EXTRACT/meta.json"
cp /workspace/quality.json               "$EXTRACT/quality.json"
echo "== qualification (corrected descriptor, accepted bytes) =="
python3 /workspace/qualify_dataset.py "$EXTRACT" --json \
    --report "$OUT/qualification-$NAME.json" \
    > "$OUT/qualification-$NAME.txt" 2>&1
qual_status=$?
cat "$OUT/qualification-$NAME.txt"
if [ "$qual_status" -ne 0 ]; then
    echo "qualification failed" >&2
    exit "$qual_status"
fi
echo "== acceptance (exact bytes) =="
python3 /workspace/qualify_dataset.py --accept \
    "$OUT/qualification-$NAME.json" "$EXTRACT" \
    > "$OUT/acceptance-$NAME.txt" 2>&1
accept_status=$?
cat "$OUT/acceptance-$NAME.txt"
echo "qualification_status=$qual_status acceptance_status=$accept_status"
exit "$accept_status"
