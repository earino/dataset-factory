#!/usr/bin/env python3
"""Split-capacity probe for chicago-food-inspections (4ijn-s7e5). Run on the coordinator.

Aggregate-first, per the discovery skill: window pool counts come from one grouped count
query per window; distinct licences (the cluster unit - one establishment contributes
several inspections) from a grouped licence list; floor codes from a bounded recent scan
of the modelling pool (the same 15,000-row probe the density profile used); and per-window
presence of every floor code from server-side string matches against the `violations` blob
(`starts_with` for a leading code, `like '%| C. %'` for a mid-blob entry, matching the
publisher's `|`-separated blob format; separator format is verified on live rows first).

Blob matching is an approximate screen for *presence*, not exact parsing: construction
parses codes exactly. Any count here can over-count only rows where the same code both
leads the blob and repeats mid-blob, which cannot hide a label from a window.

Anonymous, no key, nothing stored. Usage: python3 probe_splits.py [--json]
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

BASE = "https://data.cityofchicago.org"
DATASET = "4ijn-s7e5"
UA = {"User-Agent": "scout-verify/1.0 (dataset-factory split-capacity probe)"}
ORDER = "inspection_id"
POOL = "results in ('Pass','Fail','Pass w/ Conditions') AND violations IS NOT NULL"
WINDOWS = {
    "train": ("2010-01-01", "2020-12-31"),
    "eval": ("2021-01-01", "2023-12-31"),
    "holdout": ("2024-01-01", "2026-09-30"),
}
CODE_RE = re.compile(r"(?:^|\|)\s*(\d{1,3})\.")


def get_json(params):
    url = f"{BASE}/resource/{DATASET}.json?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8")), len(response.read())


def pool_where(window=None):
    where = POOL
    if window:
        lo, hi = WINDOWS[window]
        where += f" AND inspection_date >= '{lo}' AND inspection_date <= '{hi}'"
    return where


def count(where):
    rows, _ = get_json({"$select": "count(*) AS n", "$where": where})
    return int(rows[0]["n"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    started = time.time()
    requests = 0
    report = {}

    # 0. blob separator format, verified on live rows before any pattern is trusted
    rows, _ = get_json({"$select": "inspection_id,violations",
                        "$where": POOL, "$order": ORDER, "$limit": "5"})
    requests += 1
    print("blob separator check (first 5 pool rows):")
    for row in rows:
        blob = row["violations"]
        head = blob[:60].replace("\n", "\\n")
        seps = sorted({m.group(0)[:4] for m in re.finditer(r"\|[^\S\n]*\d{1,3}\.", blob)})
        print(f"  id={row['inspection_id']} head={head!r} separators={seps}")

    # 1. per-window pool counts (grouped census by year, one query)
    rows, _ = get_json({"$select": "date_extract_y(inspection_date) AS y, count(*) AS n",
                        "$where": POOL, "$group": "y", "$order": "y"})
    requests += 1
    census = {int(r["y"]): int(r["n"]) for r in rows}
    print(f"\npool census by year ({sum(census.values()):,} pool rows):")
    for y in sorted(census):
        print(f"  {y}: {census[y]:,}")
    report["pool_census_by_year"] = {str(k): v for k, v in sorted(census.items())}

    # 2. per-window pool rows and distinct licences (the cluster unit)
    print("\nwindow | pool rows | distinct licences | inspections/licence")
    report["windows"] = {}
    for name, (lo, hi) in WINDOWS.items():
        where = pool_where(name)
        n = count(where)
        requests += 1
        # grouped licence list, paged explicitly: Socrata caps a grouped query at 1000
        # rows by default, which would silently undercount distinct licences
        licences, offset = [], 0
        while True:
            page, _ = get_json({"$select": "license_", "$where": where,
                                "$group": "license_", "$order": "license_",
                                "$limit": "50000", "$offset": str(offset)})
            requests += 1
            licences.extend(page)
            if len(page) < 50000:
                break
            offset += len(page)
        lic = len(licences)
        report["windows"][name] = {
            "window": [lo, hi], "pool_rows": n, "distinct_licences": lic,
            "inspections_per_licence": round(n / lic, 2) if lic else None,
        }
        print(f"  {name} {lo}..{hi}: {n:,} rows, {lic:,} licences, "
              f"{n / lic:.2f} inspections/licence" if lic else f"  {name}: EMPTY")

    # 3. floor codes re-derived from a bounded recent scan of the pool (15k rows)
    scan_rows, scan_bytes = 0, 0
    code_rows = {}  # code -> rows containing it (for the floor)
    offset = 0
    while scan_rows < 15000:
        limit = min(5000, 15000 - scan_rows)
        params = {"$select": "inspection_id,violations", "$where": POOL,
                  "$order": f"{ORDER} DESC", "$limit": str(limit), "$offset": str(offset)}
        body_url = f"{BASE}/resource/{DATASET}.json?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(body_url, headers=UA)
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
        requests += 1
        scan_bytes += len(body)
        page = json.loads(body.decode("utf-8"))
        if not page:
            break
        for row in page:
            codes = {c for c in CODE_RE.findall(row["violations"] or "")}
            for c in codes:
                code_rows[c] = code_rows.get(c, 0) + 1
        scan_rows += len(page)
        offset += len(page)
    scanned = scan_rows
    floor = sorted([c for c, v in code_rows.items() if v >= 0.01 * scanned],
                   key=lambda c: -code_rows[c])
    print(f"\nfloor from a fresh {scanned:,}-row recent pool scan "
          f"({scan_bytes:,} bytes, {requests} requests so far): "
          f"{len(code_rows)} distinct codes, {len(floor)} at >=1% of scanned rows")
    print(f"  floor codes: {floor}")
    report["floor"] = {
        "scan_rows": scanned, "scan_bytes": scan_bytes,
        "distinct_codes": len(code_rows), "codes_ge_1pct": floor,
        "code_row_counts": {c: code_rows[c] for c in floor},
    }

    # 4. per-window presence of every floor code (server-side screen on the blob)
    presence = {}
    print("\nwindow | floor codes present | missing")
    for name in WINDOWS:
        missing = []
        for code in floor:
            lo, hi = WINDOWS[name]
            where = (pool_where(name) +
                    f" AND (violations LIKE '%| {code}. %' OR violations LIKE '%|{code}. %'"
                    f" OR starts_with(violations, '{code}. '))")
            try:
                n = count(where)
            except Exception as exc:  # noqa: BLE001 - report, do not guess
                print(f"  presence query failed for {name}/{code}: {exc}")
                missing.append(f"{code}(error)")
                continue
            requests += 1
            if n == 0:
                missing.append(code)
            presence.setdefault(name, {})[code] = n
        present = len(floor) - len(missing)
        print(f"  {name}: {present}/{len(floor)} floor codes present, "
              f"missing: {missing or 'none'}")
    report["floor_code_rows_per_window"] = presence
    report["requests"] = requests
    report["probe_seconds"] = round(time.time() - started, 1)
    print(f"\nrequests: {requests}, wall clock: {report['probe_seconds']}s")

    if args.json:
        print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
