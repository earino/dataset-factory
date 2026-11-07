#!/usr/bin/env python3
"""Probe: parse the OCP mirror's smallest PPIP year-file (2018) to measure what the
licence veto killed. Run from anywhere; writes nothing outside stdout.

Usage: python3 probe_ocds_sample.py [path-to-2018.jsonl.gz]
Downloads the 2018 year-file if no path is given (863,775 bytes, anonymous).
Recorded 2026-11-07; output is transcribed in notes.md / record.measurements.
"""
import collections
import gzip
import io
import json
import sys
import urllib.request

URL = "https://data.open-contracting.org/en/publication/147/download?name=2018.jsonl.gz"


def main():
    if len(sys.argv) > 1:
        data = open(sys.argv[1], "rb").read()
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "research-probe"})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
    print("bytes:", len(data))
    rows = [json.loads(l) for l in gzip.GzipFile(fileobj=io.BytesIO(data))]
    print("records:", len(rows))
    r0 = rows[0]
    print("top keys:", sorted(r0.keys()))
    print("tender keys:", sorted(r0.get("tender", {}).keys()))
    statuses = collections.Counter((x.get("tender") or {}).get("status") for x in rows)
    print("tender.status mix:", dict(statuses))
    n_aw = sum(1 for x in rows if x.get("awards"))
    print("records with >=1 award:", n_aw, f"({n_aw/len(rows):.1%})")
    methods = collections.Counter((x.get("tender") or {}).get("procurementMethod") for x in rows)
    print("procurementMethod:", dict(methods))
    print("sample buyer:", (r0.get("buyer") or {}).get("name"))


if __name__ == "__main__":
    main()
