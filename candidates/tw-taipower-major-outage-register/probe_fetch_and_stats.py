#!/usr/bin/env python3
"""Probe: fetch the Taipower major-outage register (live + archived vintages) and
print the measured aggregates recorded in this candidate's record.json / notes.md.

Anonymous; 3 requests total (~28 KB). Run from anywhere:
    python3 probe_fetch_and_stats.py
"""
import csv
import io
import subprocess
import sys
from collections import Counter
from datetime import datetime

MIRROR = ("https://quality.data.gov.tw/dq_download_csv.php"
          "?nid=122741&md5_url=8f7d7b0af4d16c3074393c7afba36244")
WAYBACK = "http://web.archive.org/web/{}if_/https://service.taipower.com.tw/data/opendata/apply/file/d077011/001.csv"
CDX = ("http://web.archive.org/cdx/search/cdx"
       "?url=service.taipower.com.tw/data/opendata/apply/file/d077011*&output=json")


def fetch(url):
    # curl is the proven path: quality.data.gov.tw's chain fails this Python's
    # strict SSL verification (Missing Subject Key Identifier) but verifies under
    # the system curl. Do not "fix" this by disabling certificate checks.
    out = subprocess.run(["curl", "-sSL", "-m", "60", "--fail", url],
                         capture_output=True, check=True)
    return out.stdout


def parse_dt(s):
    s = s.strip().lstrip("\ufeff")
    for fmt in ("%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y%m%dT%H%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def stats(label, data):
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8", "replace"))))
    occ = [parse_dt(r.get("發生時間", "")) for r in rows]
    res = [parse_dt(r.get("復電時間", "")) for r in rows]
    good = [(o, x) for o, x in zip(occ, res) if o and x]
    durs = sorted((x - o).total_seconds() / 60.0 for o, x in good)
    negs = [d for d in durs if d < 0]
    years = Counter(o.year for o in occ if o)
    print("%s: rows=%d occ_missing=%d res_missing=%d" % (label, len(rows),
          sum(1 for o in occ if not o), sum(1 for x in res if not x)))
    print("  years:", dict(sorted(years.items())))
    print("  duration min: n=%d min=%s p25=%s median=%s p75=%s max=%s neg=%d" % (
        len(durs), durs[0], durs[len(durs) // 4], durs[len(durs) // 2],
        durs[3 * len(durs) // 4], durs[-1], len(negs)))
    for th in (30, 60, 120, 240):
        over = sum(1 for d in durs if d > th)
        print("  > %d min: %d/%d (%.1f%%)" % (th, over, len(durs), 100.0 * over / len(durs)))
    months = Counter(o.month for o in occ if o)
    print("  by month:", dict(sorted(months.items())))


def main():
    print("== CDX ==")
    try:
        import json
        caps = json.loads(fetch(CDX).decode())
        for row in caps[1:]:
            print(" ", row[1], row[3], row[4])
    except Exception as e:
        print("  CDX fetch failed:", e)
    print("== live register (quality mirror) ==")
    live = fetch(MIRROR)
    print("  %d bytes" % len(live))
    stats("live", live)
    for ts in ("20241004143131", "20260929233634"):
        print("== wayback vintage %s ==" % ts)
        try:
            data = fetch(WAYBACK.format(ts))
            print("  %d bytes" % len(data))
            stats(ts, data)
        except Exception as e:
            print("  fetch failed:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
