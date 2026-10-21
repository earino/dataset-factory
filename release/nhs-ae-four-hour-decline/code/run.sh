#!/bin/sh
# Worker entrypoint for the nhs-ae-four-hour-decline full build (nhsae-002).
#
# v2026.11 provenance note: the shipped v2026.11 artifact was NOT built by this
# worker entrypoint. The 2026-10-21 rebuild ran the same build.py and the same
# gate on the coordinator, fetching the same 102 publisher CSVs over HTTP
# (composite digest 99cb3339b31ae2045c990c950a40fb44dc93f1dfc4d58f1ae1879fa851666833),
# because the audit fix changes row selection only, not fetching. This file is
# kept as the documented worker path and as the v2026.10 provenance record: a
# worker consumes the staged source tar via --source-dir exactly as below.
# Runs on an expendable worker only. The publisher's CDN (CloudFront) serves
# HTTP 202 with an empty body to this worker's datacenter IP (measured
# 2026-10-21 from worker 171522297; the same URLs serve 200/82 KB to the
# coordinator), so nhsae-001 could not enumerate the year pages. The 102
# monthly CSVs are therefore fetched from the private staging release
# source-nhsae-001 (asset 661561799, sha256 verified on arrival by the
# executor), whose bytes are the publisher fetch measured on the
# coordinator. The build consumes them via --source-dir with the provenance
# recorded in summary.source; the composite digest of the inner files
# (99cb3339b31ae2045c990c950a40fb44dc93f1dfc4d58f1ae1879fa851666833) must
# match the local exercise. The build then writes the runner layout plus
# quality.json and the qualification gate runs over the exact artifact - the
# job fails when the gate fails, and every diagnostic is written under
# /output so it is collected either way.
set -u

OUT=/output/extract
mkdir -p /output
mkdir -p /tmp/ae_csvs
tar -xzf /data/nhsae-source.tar.gz -C /tmp/ae_csvs

echo "== build =="
python3 /workspace/build.py --out "$OUT" --work-dir /tmp/nhsae \
    --source-dir /tmp/ae_csvs \
    --source-provenance "staged fetch from earino/dataset-factory-staging release source-nhsae-001 (asset 661561799, sha256 8d8bc1b1a9e9f8303c8e0125aa2d6b7668fe3ebaf15051cd511bd74f2800d1fb, extracted then verified per-file by build.py); the bytes are the publisher fetch measured on the coordinator 2026-10-21 (102 CSV GETs, 3,115,779 bytes, 1.2 s) - the publisher's CDN serves HTTP 202 with an empty body to this datacenter IP, so the worker cannot fetch the publisher directly (measured on nhsae-001)"
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
    --report /output/qualification-nhs-ae-four-hour-decline.json \
    > /output/qualification-nhs-ae-four-hour-decline.txt 2>&1
qual_status=$?
cat /output/qualification-nhs-ae-four-hour-decline.txt

echo "build_status=$build_status qualification_status=$qual_status"
exit "$qual_status"
