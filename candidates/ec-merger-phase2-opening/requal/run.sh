#!/bin/sh
# Worker entrypoint: re-qualify the audit-corrected descriptor on the exact
# accepted CSV bytes.
#
# The independent pre-flip audit (2026-10-27) returned PUBLISH WITH CONDITIONS.
# The conditions are descriptor/docs-only corrections: the three CSVs are
# byte-identical to the audited artifact (fetched from private staging release
# 425292628, every sha256 verified on arrival), while meta.json and quality.json
# carry the corrections - those two travel in this bundle, hashed in the job
# spec. Nothing is rebuilt from the live register; no performance metric is
# computed here at all. Stages: layout -> qualify (gate two-phase) -> accept.
#
# /bin/sh on python:3.13-slim is dash; each stage writes its own log and its
# exit status is captured directly.
set -u

NAME=ec-merger-phase2-opening
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
    echo "qualification failed: the corrected descriptor is refused on the accepted bytes" >&2
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
