#!/usr/bin/env python3
"""Build the dated worked example for the CQC deregistration task.

Joins (a) the January 2024 'HSCA Active Locations' vintage (population at T)
with (b) the current 'Deactivated Locations' file (event dates) by Location ID.
Prints named homes at T with: HSCA start date, beds, latest rating + publication
date at T, and - where the location later deregistered - its HSCA end date.
"""
import os
import re
import sys
import zipfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DEACT = os.path.join(HERE, "cqc_dl", "deactivated.ods")
VINT = os.path.join(HERE, "cqc_dl", "active_2024_01.ods")

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


def rows(ods_path):
    z = zipfile.ZipFile(ods_path)
    content = [m for m in z.namelist() if m.endswith("content.xml")][0]
    import xml.etree.ElementTree as ET
    header = None
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
                yield ("__header__", header)
            continue
        yield ("row", cells)
        elem.clear()


def dparse(s):
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s or "")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def main():
    # pass 1: deactivated care homes
    deact = {}
    for kind, cells in rows(DEACT):
        if kind == "__header__":
            hdr = {h: i for i, h in enumerate(cells)}
            continue
        if cells[hdr["Care home?"]] != "Y":
            continue
        lid = cells[hdr["Location ID"]]
        deact[lid] = {
            "name": cells[hdr["Location Name"]],
            "end": cells[hdr["Location HSCA End Date"]],
            "status": cells[hdr["Location Status"]],
            "la": cells[hdr["Location Local Authority"]],
        }
    print(f"deactivated care homes indexed: {len(deact)}")

    # pass 2: Jan-2024 vintage care homes; find join examples
    T = date(2024, 1, 5)
    joined = []
    not_joined = []
    n_ch = 0
    pub_after_T = 0
    for kind, cells in rows(VINT):
        if kind == "__header__":
            hdr = {h: i for i, h in enumerate(cells)}
            continue
        if cells[hdr["Care home?"]] != "Y":
            continue
        n_ch += 1
        lid = cells[hdr["Location ID"]]
        if (pd := dparse(cells[hdr["Publication Date"]])) and pd > T:
            pub_after_T += 1
        rec = {
            "id": lid,
            "name": cells[hdr["Location Name"]],
            "start": cells[hdr["Location HSCA start date"]],
            "beds": cells[hdr["Care homes beds"]],
            "rating": cells[hdr["Location Latest Overall Rating"]],
            "rating_pub": cells[hdr["Publication Date"]],
            "la": cells[hdr["Location Local Authority"]],
            "region": cells[hdr["Location Region"]],
        }
        if lid in deact:
            rec.update(deact[lid])
            joined.append(rec)
        else:
            not_joined.append(rec)
    print(f"vintage care homes: {n_ch}; later deactivated (label 1 known): {len(joined)}; "
          f"not deactivated as of 2026-11-02: {len(not_joined)}")
    print(f"as-of check: vintage rows with rating Publication Date after T=2024-01-05: {pub_after_T}")

    # worked example: T = 2024-01-05 (vintage production date); window = (T, T+365d]
    win_end = date(2025, 1, 5)
    pos = [r for r in joined if (e := dparse(r["end"])) and T < e <= win_end]
    pos.sort(key=lambda r: r["end"])
    print(f"\npositives at T=2024-01-05 (end date in (T, T+365d]): {len(pos)}")
    for r in pos[:3]:
        print(f"  POS {r['name']!r} id={r['id']} LA={r['la']} beds={r['beds']} "
              f"start={r['start']} rating={r['rating']!r} rating_pub={r['rating_pub']} end={r['end']} status={r['status']}")
    neg = [r for r in joined if (e := dparse(r["end"])) and e > win_end][:2]
    for r in neg:
        print(f"  NEG(late) {r['name']!r} id={r['id']} LA={r['la']} beds={r['beds']} "
              f"start={r['start']} rating={r['rating']!r} rating_pub={r['rating_pub']} end={r['end']} (outside window)")
    # a censored-free negative: still active today
    for r in not_joined[:2]:
        print(f"  NEG(active) {r['name']!r} id={r['id']} LA={r['la']} beds={r['beds']} "
              f"start={r['start']} rating={r['rating']!r} rating_pub={r['rating_pub']}")

if __name__ == "__main__":
    sys.exit(main())
