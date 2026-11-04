#!/bin/sh
# Worker entrypoint for the ipa-tm-registration-outcome DISCOVERY measurement job.
#
# This is not a construction job: it produces no dataset and no scored artifact.
# It measures the aggregates the candidate record needs before a ready verdict:
# filing counts by year, outcome (standing-registration vs pre-grant-terminal vs
# censored) distribution by year, pending share for the eligibility cutoff,
# feature-table coverage, the classification-record lag (filing-time availability
# of Nice classes), and three dated example applications. The single input is
# the 1.35 GB IPRAPID.zip (CC BY 4.0, IP Australia via data.gov.au), downloaded
# once and streamed member-by-member; nothing is extracted to disk and nothing
# leaves the worker except the compact JSON report.
set -u

OUT=/output/extract
mkdir -p /output "$OUT"

echo "== ipa-tm-001 discovery aggregate =="
python3 /workspace/build.py --out "$OUT" --zip /tmp/iprapid.zip
status=$?

if [ -f "$OUT/report.json" ]; then
    cp "$OUT/report.json" /output/ipa-tm-001-report.json
fi

echo "build_status=$status"
exit "$status"
