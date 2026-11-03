#!/usr/bin/env python3
"""Inspect a historical CQC 'HSCA Active Locations' vintage (Jan 2024 ODS).

Measures: columns available at instant T, active care-home count at T,
beds/rating/HSCA-start availability - the per-instant population and features.
"""
import os
import re
import sys
import zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ODS = os.path.join(HERE, "cqc_dl", "active_2024_01.ods")

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}
T_ROW = "{%s}table-row" % NS["table"]
T_CELL = "{%s}table-cell" % NS["table"]
T_REPEATED = "{%s}number-columns-repeated" % NS["table"]
T_ROW_REPEATED = "{%s}number-rows-repeated" % NS["table"]
O_VALUE = "{%s}value" % NS["office"]
O_DATE = "{%s}date-value" % NS["office"]


def cell_text(cell):
    txt = "".join(cell.itertext()).strip()
    if not txt:
        txt = cell.get(O_DATE) or cell.get(O_VALUE) or ""
    return txt


def main():
    z = zipfile.ZipFile(ODS)
    content = [m for m in z.namelist() if m.endswith("content.xml")][0]
    import xml.etree.ElementTree as ET

    header = None
    idx = {}
    n = 0
    ch = 0
    beds = Counter()
    ratings = Counter()
    start_years = Counter()
    status = Counter()
    produced = None

    for event, elem in ET.iterparse(z.open(content), events=("end",)):
        if elem.tag != T_ROW:
            continue
        rep = int(elem.get(T_ROW_REPEATED) or "1")
        if rep > 1000:
            continue
        cells = []
        for cell in elem.findall(T_CELL):
            crep = int(cell.get(T_REPEATED) or "1")
            cells.extend([cell_text(cell)] * crep)
        if header is None:
            if cells and cells[0] == "Location ID":
                header = cells
                print(f"header row: {len(cells)} cols")
                for i, h in enumerate(header):
                    hl = h.lower()
                    if any(k in hl for k in ("location id", "status", "date", "care home", "beds", "rating", "publication", "provider id", "provider name", "type/sector", "service type", "service user", "region", "local authority", "companies house", "charity", "regulated activities", "carried out")):
                        print(f"  [{i:3d}] {h!r}")
                for key, pat in [
                    ("status", "location status"), ("ch", "care home?"), ("beds", "beds"),
                    ("rating", "latest overall rating"), ("pubdate", "publication date"),
                    ("start", "location hsca start date"), ("endid", "location id"),
                    ("provider", "provider id"), ("nursing", "with nursing"),
                    ("residential", "without nursing"),
                ]:
                    for i, h in enumerate(header):
                        if pat in h.lower():
                            idx[key] = i
                            break
                print("index map:", idx)
            elif any("produced" in c.lower() or "source: cqc database" in c.lower() for c in cells if c):
                produced = " | ".join(c for c in cells if c)[:200]
            continue
        n += rep
        get = lambda k: cells[idx[k]] if k in idx and idx[k] < len(cells) else ""
        if "ch" in idx:
            is_ch = get("ch") == "Y"
            if is_ch:
                ch += rep
                beds[get("beds") or "(blank)"] += rep
                ratings[get("rating")] += rep
                m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", get("start"))
                if m:
                    start_years[int(m.group(3))] += rep
        if "status" in idx:
            status[get("status")] += rep

    print(f"produced-note: {produced}")
    print(f"data rows: {n}")
    if "status" in idx:
        print("status mix:", status.most_common(10))
    print(f"care homes (Care home?=Y): {ch}")
    print("\nbeds (top 12):")
    for k, v in beds.most_common(12):
        print(f"  {v:7d}  {k!r}")
    print("\nlatest overall rating at T (care homes):")
    for k, v in ratings.most_common():
        print(f"  {v:7d}  {k!r}")
    ys = sorted(start_years)
    print(f"\nHSCA start-year range of active care homes: {ys[0] if ys else None}..{ys[-1] if ys else None}")
    print("start-year histogram (first 6, last 6):", ys[:6], ys[-6:])

if __name__ == "__main__":
    sys.exit(main())
