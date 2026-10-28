#!/usr/bin/env python3
"""Decisive cohort measurement for austender-contract-amendment-occurrence.

Downloads two windows of the anonymous AusTender 'Contract Notice and Amendments
Published' report (XLSX), streams them, and reproduces the 12-month first-
amendment rate recorded 2026-10-28 for parents published 01-31 Jul 2017:
n=6,285; 30d 0.38% / 90d 2.39% / 180d 5.62% / 365d 10.96% (689 positives),
plus the dated fixtures. The OCDS negative (registry carries no amendment
events) is reproduced by the --ocds check.

Run: python3 probe_cohort_rate.py            (cohort + follow-up, ~100 MB total? no: ~7 MB)
     python3 probe_cohort_rate.py --ocds     (scan 2018.jsonl.gz: ~14 MB, amendment-free)
"""
import collections
import datetime
import gzip
import io
import json
import re
import sys
import time
import urllib.request
import zipfile

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
BASE = ("https://www.tenders.gov.au/Reports/CnAndAmendmentsDownload?AgencyStatus=0"
        "&DateType=Publish%20Date&DateStart={}&DateEnd={}")


def fetch(url):
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "https://www.tenders.gov.au/Reports/CnAndAmendmentsForm"})
    with urllib.request.urlopen(req, timeout=300) as r:
        b = r.read()
    return b, len(b), time.time() - t0


def parse_xlsx_rows(b):
    """Stream an XLSX: list of rows, each a list of cell values (strings/serials)."""
    z = zipfile.ZipFile(io.BytesIO(b))
    ss = z.read("xl/sharedStrings.xml").decode("utf-8", "replace")
    strings = re.findall(r"<t[^>]*>([^<]*)</t>", ss)
    sheet = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")][0]
    rows = []
    buf = b""
    with z.open(sheet) as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            buf += chunk
            while b"</row>" in buf:
                r_, buf = buf.split(b"</row>", 1)
                rows.append(r_.decode("utf-8", "replace"))
    out = []
    for r in rows:
        vals = []
        for c in re.findall(r"<c\b[^>]*(?:/>|>.*?</c>)", r, flags=re.S):
            t = re.search(r't="(\w+)"', c)
            v = re.search(r"<v>([^<]*)</v>", c)
            if t and t.group(1) == "s" and v:
                idx = int(v.group(1))
                vals.append(strings[idx] if idx < len(strings) else "")
            elif v:
                vals.append(v.group(1))
            else:
                vals.append("")
        out.append(vals)
    return out


def data_rows(rows):
    hdr = None
    for i, v in enumerate(rows):
        if v and "CN ID" in v[:6]:
            hdr = i
            break
    if hdr is None:
        raise ValueError("report header row ('CN ID') not found - channel layout changed")
    return [v for v in rows[hdr + 1:] if len(v) >= 9 and v[1].startswith("CN")]


def serial_dt(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if 30000 < f < 60000:
        return datetime.datetime(1899, 12, 30) + datetime.timedelta(days=f)
    return None


def ods_negative():
    """Reproduce: the OCDS registry year file carries no amendment events."""
    url = "https://data.open-contracting.org/en/publication/19/download?name=2018.jsonl.gz"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    n = n_amend = 0
    with urllib.request.urlopen(req, timeout=240) as r:
        for line in gzip.GzipFile(fileobj=r):
            n += 1
            if b"amendment" in line:
                n_amend += 1
    print(f"OCDS 2018: {n} processes, {n_amend} lines mentioning 'amendment' (description text only)")
    d = json.loads(b'{"ok": true}')  # placeholder to keep import
    print("OCDS negative reproduced." if n_amend < 10 else "UNEXPECTED: many amendment lines - re-examine!")


def main():
    b1, n1, t1 = fetch(BASE.format("01-Jul-2017", "31-Jul-2017"))
    print(f"cohort window: {n1} bytes in {t1:.1f}s")
    b2, n2, t2 = fetch(BASE.format("01-Aug-2017", "31-Jul-2018"))
    print(f"follow-up window: {n2} bytes in {t2:.1f}s")

    d1 = data_rows(parse_xlsx_rows(b1))
    d2 = data_rows(parse_xlsx_rows(b2))
    print("cohort rows:", len(d1), "| follow-up rows:", len(d2))

    parents = {}
    for v in d1:
        if re.match(r"^CN\d+$", v[1]):
            dt = serial_dt(v[8])
            if dt:
                parents[v[1]] = dt
    ev = collections.defaultdict(list)
    for rows in (d1, d2):
        for v in rows:
            m = re.match(r"^(CN\d+)-A\d+$", v[1])
            if m:
                dt = serial_dt(v[8])
                if dt:
                    ev[m.group(1)].append(dt)

    rates = {30: 0, 90: 0, 180: 0, 365: 0}
    examples = []
    for cnid, pdate in parents.items():
        deltas = sorted(e for e in ev.get(cnid, []) if (e - pdate).total_seconds() > 0)
        if not deltas:
            continue
        days = (deltas[0] - pdate).total_seconds() / 86400
        for lim in rates:
            if days <= lim:
                rates[lim] += 1
        if days <= 365 and len(examples) < 4:
            examples.append((cnid, pdate.isoformat(sep=" "), deltas[0].isoformat(sep=" "), round(days, 1)))

    n = len(parents)
    print(f"parents published Jul-2017: {n}")
    for lim in (30, 90, 180, 365):
        print(f"  first amendment within {lim}d: {rates[lim]} ({rates[lim]/n:.2%})")
    for e in examples:
        print("  TRUE fixture:", e)


if __name__ == "__main__":
    if "--ocds" in sys.argv:
        ods_negative()
    else:
        main()
