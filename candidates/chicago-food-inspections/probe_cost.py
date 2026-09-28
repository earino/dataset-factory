#!/usr/bin/env python3
"""Extraction-cost probe for chicago-food-inspections (4ijn-s7e5), run on the coordinator.

The discovery skill requires measured - not estimated - extraction cost before a candidate
can be called `ready`. This probe downloads a bounded sample of full rows (the `violations`
blob dominates size) in the exact paged pattern construction will use: a total order with a
tiebreaker, fixed page size, sequential offsets. It counts requests, bytes and wall-clock,
then scales nothing: it reports the measured sample cost and the measured total row count,
and states the full-pull extrapolation as an estimate (labelled, with its arithmetic).

Anonymous, no key. The coordinator is small, so the sample is bounded and streamed - no
bulk data is stored here.

Usage: python3 .factory/probe_cost_chicago_food.py [--rows 20000] [--page-size 5000]
"""
import argparse
import io
import json
import time
import urllib.parse
import urllib.request

BASE = "https://data.cityofchicago.org"
DATASET = "4ijn-s7e5"
UA = {"User-Agent": "scout-verify/1.0 (dataset-factory extraction-cost probe)"}
ORDER = "inspection_id"          # unique per row (316,205 distinct ids in 316,205 rows), so the
                                 # order key is its own tiebreaker and offset paging is stable.


def get_bytes(url):
    request = urllib.request.Request(url, headers=UA)
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    return body, time.perf_counter() - start


def get_json(url):
    body, _ = get_bytes(url)
    return json.loads(body.decode("utf-8"))


def resource_url(params):
    return f"{BASE}/resource/{DATASET}.json?" + urllib.parse.urlencode(params)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--page-size", type=int, default=5000)
    args = parser.parse_args()

    requests = 0
    bytes_total = 0
    wall_start = time.perf_counter()

    # total row count, re-measured now (was 316,205 on 2026-09-27)
    count = get_json(resource_url({"$select": "count(*) AS n"}))
    requests += 1
    total_rows = int(count[0]["n"])
    print(f"total rows (count query): {total_rows:,}")

    # full-select list, the columns construction will pull; blob column dominates size
    columns = [
        "inspection_id", "inspection_date", "results", "violations", "license_",
        "facility_type", "risk", "city", "state", "zip", "latitude", "longitude",
        "inspection_type", "aka_name", "dba_name",
    ]
    select = ",".join(columns)

    offset = 0
    fetched = 0
    pages = 0
    per_page = []
    while fetched < args.rows:
        want = min(args.page_size, args.rows - fetched)
        params = {"$select": select, "$order": ORDER, "$limit": str(want),
                  "$offset": str(offset)}
        body, _ = get_bytes(resource_url(params))
        rows = json.loads(body.decode("utf-8"))
        requests += 1
        pages += 1
        bytes_total += len(body)
        if not rows:
            break
        per_page.append((pages, len(rows), len(body)))
        fetched += len(rows)
        offset += len(rows)
    wall = time.perf_counter() - wall_start

    print(f"\nmeasured sample: {fetched:,} rows in {pages} pages")
    print(f"requests: {requests} (1 count + {pages} pages)")
    print(f"bytes downloaded: {bytes_total:,}")
    print(f"wall clock: {wall:.1f}s (includes the count query)")
    print(f"mean bytes per row: {bytes_total / max(fetched, 1):,.0f}")
    for page, n, size in per_page:
        print(f"  page {page}: {n} rows, {size:,} bytes")
    if fetched and total_rows:
        est_pages = -(-total_rows // args.page_size)  # ceil
        est_bytes = bytes_total / fetched * total_rows
        est_seconds = wall / fetched * total_rows
        print(f"\nestimate (labelled, arithmetic shown) for a full {total_rows:,}-row pull")
        print(f"  at page size {args.page_size}: ~{est_pages} pages + 1 count query")
        print(f"  ~{est_bytes:,.0f} bytes ({est_bytes / 1e6:.0f} MB) at the measured mean row size")
        print(f"  ~{est_seconds:.0f}s at the measured per-row rate")
        print("  the full pull runs on the worker; these figures are an estimate, not a measurement")


if __name__ == "__main__":
    main()
