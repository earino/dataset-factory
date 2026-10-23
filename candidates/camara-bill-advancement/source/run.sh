#!/bin/sh
# Worker entrypoint for the camara-bill-advancement full build.
#
# Runs on an expendable worker only. Downloads the publisher's bulk year
# files (proposicoes + proposicoesAutores, 1991-2025, 70 files, ~1.2 GB
# measured 2026-10-23), builds the presentation-instant panel with the
# terminal-outcome label, writes the runner layout plus quality.json, then
# runs the qualification gate over the exact artifact - the job fails when
# the gate fails, and every diagnostic (summary.json, gate report) is
# written under /output so it is collected either way.
set -u

OUT=/output/extract
mkdir -p /output

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/camara
build_status=$?

if [ -f "$OUT/summary.json" ]; then
    cp "$OUT/summary.json" /output/summary.json
fi

if [ "$build_status" -ne 0 ]; then
    echo "build failed; the extract is incomplete and qualification is not meaningful" >&2
    exit "$build_status"
fi

echo "== qualification =="
python3 /workspace/qualify_dataset.py "$OUT" --json \
    --report /output/qualification-camara-bill-advancement.json \
    > /output/qualification-camara-bill-advancement.txt 2>&1
qual_status=$?
cat /output/qualification-camara-bill-advancement.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
