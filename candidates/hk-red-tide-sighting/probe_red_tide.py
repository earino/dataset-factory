#!/usr/bin/env python3
"""Discovery probe for the AFCD red tide sighting archive (read-only, no construction).

Fetches the live CSV and prints the aggregates quoted in record.json, plus (optionally)
compares against the two Wayback vintages that carry usable row keys.

Usage:
  python3 probe_red_tide.py            # live CSV aggregates only
  python3 probe_red_tide.py --vintages  # also fetch + compare the 2019 and 2025 vintages

Nothing is written to the repository; output goes to stdout. Counts are aggregates over
the publisher's own rows (discovery evidence), not constructed training data.
"""
import argparse
import csv
import io
import urllib.request
import collections
import datetime as dt

LIVE = "https://redtide.afcd.gov.hk/data/RTMS_ob_RTLE.csv"
V2019 = "https://web.archive.org/web/20191102113918id_/http://redtide.afcd.gov.hk/data/RTMS_ob_RTLE.csv"
V2025 = "https://web.archive.org/web/20250402235240id_/https://redtide.afcd.gov.hk/data/RTMS_ob_RTLE.csv"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-discovery/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def load(url):
    raw = fetch(url).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(raw)))


def summarise(rows, label):
    d = [r["Date of Report"] for r in rows]
    print(label, "rows", len(rows),
          "distinct", len(set(r["Red Tide Sighting No."] for r in rows)),
          "min", min(d), "max", max(d))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vintages", action="store_true")
    a = ap.parse_args()

    live = load(LIVE)
    d = summarise(live, "live")
    yr = collections.Counter(x[:4] for x in d)
    print("years", len(yr), "non-zero years 1975-2026:", sum(1 for y in range(1975, 2027) if yr.get(str(y), 0) > 0))
    print("locations", len(set(r["Location"] for r in live)))
    print("group mix", collections.Counter(r["Group"] for r in live).most_common())
    print("rows per sighting number", collections.Counter(
        collections.Counter(r["Red Tide Sighting No."] for r in live).values()).most_common())
    diffs = [(dt.date.fromisoformat(r["Date of Dissipation"]) - dt.date.fromisoformat(r["Date of Report"])).days
             for r in live if r["Date of Dissipation"]]
    diffs.sort()
    print("dissipation lag days: n", len(diffs), "min", diffs[0], "median", diffs[len(diffs)//2], "max", diffs[-1],
          "negative", sum(1 for x in diffs if x < 0))
    for lo, hi in (("1975", "2010"), ("2011", "2018"), ("2019", "2026")):
        s = [r for r in live if lo <= r["Date of Report"][:4] <= hi]
        print("split", lo, hi, len(s), len(set(r["Red Tide Sighting No."] for r in s)), len(set(r["Location"] for r in s)))

    if not a.vintages:
        return

    v19 = load(V2019)
    v25 = load(V2025)
    summarise(v19, "wayback 2019-11-02")
    summarise(v25, "wayback 2025-04-02")
    print("2019 header", list(v19[0].keys()))

    old = [r for r in v19 if r["Date"] <= "2019-05-31"]
    live_keys = {(r["Date of Report"], r["Species"], r["Location"]) for r in live}
    missing = [r for r in old if (r["Date"], r["Species"], r["Location"]) not in live_keys]
    print("2019 rows <=2019-05-31", len(old), "absent from live", len(missing))

    ka = {(r["Red Tide Sighting No."], r["Location"]): r for r in live}
    kb = {(r["Red Tide Sighting No."], r["Location"]): r for r in v25}
    print("live only", len(set(ka) - set(kb)), "vintage only", len(set(kb) - set(ka)), "common", len(set(ka) & set(kb)))
    changed = [k for k in set(ka) & set(kb) if ka[k]["Date of Dissipation"] != kb[k]["Date of Dissipation"]]
    print("common rows with dissipation changed", len(changed))
    print("new rows since 2025 vintage by year", collections.Counter(
        r["Date of Report"][:4] for r in live if (r["Red Tide Sighting No."], r["Location"]) not in kb))


if __name__ == "__main__":
    main()
