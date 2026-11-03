#!/usr/bin/env python3
"""Aggregate CQC Deactivated Locations ODS: the closure-label distribution.

Answers: how many deactivated locations are care homes, their deactivation-year
distribution, status mix, beds at deactivation, and the file's own caveats.
"""
import os
import re
import sys
import zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ODS = os.path.join(HERE, "cqc_dl", "deactivated.ods")

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
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


def parse_date(s):
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s or "")
    if not m:
        return None
    return int(m.group(3)), int(m.group(2)), int(m.group(1))


def main():
    z = zipfile.ZipFile(ODS)
    content = [m for m in z.namelist() if m.endswith("content.xml")][0]
    import xml.etree.ElementTree as ET

    row_idx = 0
    header = None
    caveats = []
    n_data = 0
    status_all = Counter()
    status_ch = Counter()
    ch = 0
    ch_end_year = Counter()
    ch_end_year_2019 = Counter()
    beds = Counter()
    earliest = None
    latest = None
    earliest_ch = None
    rating_at_deact = Counter()
    rate_pub_years = Counter()
    inherited = Counter()

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
            if len(cells) > 50 and cells[0] == "Location ID":
                header = cells
                print(f"header row at {row_idx}, {len(cells)} cols")
            else:
                joined = " ".join(c for c in cells if c)
                if joined and len(joined) > 30:
                    caveats.append(joined)
        else:
            n_data += rep
            get = lambda i: cells[i] if i < len(cells) else ""
            st = get(3)
            status_all[st] += rep
            is_ch = get(6) == "Y"
            d = parse_date(get(5))
            if d:
                if earliest is None or (d[0], d[1], d[2]) < earliest:
                    earliest = (d[0], d[1], d[2])
                if latest is None or (d[0], d[1], d[2]) > latest:
                    latest = (d[0], d[1], d[2])
            if is_ch:
                ch += rep
                status_ch[st] += rep
                if d:
                    ch_end_year[d[0]] += rep
                    ch_end_year_2019[(d[0], st)] += rep
                    if earliest_ch is None or (d[0], d[1], d[2]) < earliest_ch:
                        earliest_ch = (d[0], d[1], d[2])
                b = get(7)
                beds[b if b else "(blank)"] += rep
                rating_at_deact[get(28)] += rep
                inherited[get(30)] += rep
            pd = parse_date(get(29))
            if pd:
                rate_pub_years[pd[0]] += rep
        row_idx += 1
        elem.clear()

    print(f"\ndata rows after header: {n_data}")
    print(f"earliest HSCA end date overall: {earliest}  latest: {latest}")
    print(f"earliest care-home end date: {earliest_ch}")
    print(f"\ncare homes (Care home?=Y): {ch}")
    print("\nstatus mix (all locations):")
    for k, v in status_all.most_common(15):
        print(f"  {v:7d}  {k!r}")
    print("\nstatus mix (care homes):")
    for k, v in status_ch.most_common(15):
        print(f"  {v:7d}  {k!r}")
    print("\ncare-home deactivations by end year:")
    for y in sorted(ch_end_year):
        print(f"  {y}: {ch_end_year[y]}")
    print("\ncare-home end (year, status):")
    for k in sorted(ch_end_year_20119 := ch_end_year_2019)[:0]:  # noop guard
        pass
    for k in sorted(ch_end_year_2019):
        if ch_end_year_2019[k] >= 50:
            print(f"  {k}: {ch_end_year_2019[k]}")
    print("\nbeds at deactivation (care homes, top 12):")
    for k, v in beds.most_common(12):
        print(f"  {v:7d}  {k!r}")
    print("\nlatest overall rating at deactivation (care homes):")
    for k, v in rating_at_deact.most_common():
        print(f"  {v:7d}  {k!r}")
    print("\ninherited rating flag (care homes):")
    for k, v in inherited.most_common():
        print(f"  {v:7d}  {k!r}")
    print(f"\nrating publication years (all rows): {sorted(rate_pub_years.items())[:3]} ... {sorted(rate_pub_years.items())[-3:]}")
    print("\n--- file caveats/notes (joined non-empty cells before header) ---")
    for c in caveats:
        print(" *", c[:400])

if __name__ == "__main__":
    sys.exit(main())
