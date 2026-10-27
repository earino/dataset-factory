#!/usr/bin/env python3
"""Full-file verification probe for ns-bwa-advisory-lift-duration (2026-10-27).

Fetches the complete register CSV once (284 KB, small enough for the
coordinator), pins its sha256, and reproduces every split count, base rate and
hazard count in the candidate record from the file itself - an independent
cross-check of probe_ns_aggregates.py (SoQL, live API).

Usage: python3 probe_ns_csv_verify.py [--reuse ns_bwa_full.csv]
"""
import csv
import hashlib
import io
import json
import sys
import urllib.request
from collections import Counter, defaultdict

URL = ("https://data.novascotia.ca/api/views/7t68-9xmm/rows.csv"
       "?accessType=DOWNLOAD")
UA = {"User-Agent": "scout-discovery/1.0 (dataset-factory research)"}
ISSUE = "Date Advisory Issued"
LIFT = "Date Advisory Removed"
DUR = "Length of Advisory in Days"
SITE = "Site Name"
REASON = "Reason for the Report"
FAC = "Facility Type"


def load():
    if "--reuse" in sys.argv:
        i = sys.argv.index("--reuse")
        with open(sys.argv[i + 1], "rb") as f:
            return f.read()
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=120) as r:
        data = r.read()
        print("Last-Modified header:", r.headers.get("Last-Modified"))
    return data


def year(x):
    v = (x or "").strip()[-4:]
    return v if v.isdigit() and len(v) == 4 else None


def dur(r):
    try:
        return int(r[DUR])
    except (ValueError, KeyError):
        return None


def main():
    data = load()
    sha = hashlib.sha256(data).hexdigest()
    print(f"bytes={len(data)} sha256={sha}")
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8", "replace"))))
    print("rows:", len(rows))
    out = {"bytes": len(data), "sha256": sha, "rows": len(rows)}

    byw = Counter()
    n = Counter()
    l14 = Counter()
    l30 = Counter()
    cens = Counter()
    sites = defaultdict(set)
    neg = []
    zero = 0
    resolved = active = 0
    for r in rows:
        y = year(r[ISSUE])
        d = dur(r)
        if r[LIFT]:
            resolved += 1
        else:
            active += 1
        if d is not None and d < 0:
            neg.append((r[SITE], r[ISSUE], r[LIFT], d))
        if d == 0:
            zero += 1
        if not y:
            continue
        w = ("train" if y <= "2017" else
             "eval" if y <= "2020" else
             "hold" if y <= "2024" else "other")
        byw[w] += 1
        sites[w].add(r[SITE])
        if r[LIFT] and d is not None:
            n[w] += 1
            if d <= 14:
                l14[w] += 1
            if d <= 30:
                l30[w] += 1
        else:
            cens[w] += 1
    for w in ("train", "eval", "hold", "other"):
        out[w] = {"issued": byw[w], "labeled": n[w], "censored": cens[w],
                  "distinct_sites": len(sites[w]),
                  "lift14": round(l14[w] / n[w], 4) if n[w] else None,
                  "lift30": round(l30[w] / n[w], 4) if n[w] else None}
    out["totals"] = {"resolved": resolved, "active_censored": active,
                     "all_distinct_sites": len({r[SITE] for r in rows}),
                     "negative_duration_rows": neg, "zero_duration_rows": zero,
                     "no_issue_year_rows": len(rows) - sum(byw.values()),
                     "missing_reason": sum(1 for r in rows if not r.get(REASON)),
                     "missing_facility_type": sum(1 for r in rows if not r.get(FAC)),
                     "reason_variants": Counter(
                         r.get(REASON) or "MISSING" for r in rows).most_common(8)}
    print(json.dumps(out, indent=1, default=str)[:4500])
    with open("probe_ns_csv_verify_out.json", "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
