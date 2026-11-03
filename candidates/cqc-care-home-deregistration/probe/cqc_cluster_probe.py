#!/usr/bin/env python3
"""Provider clustering of care-home deregistrations (independence evidence)."""
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ODS = os.path.join(HERE, "cqc_dl", "deactivated.ods")

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
    by_year = defaultdict(Counter)  # year -> provider -> n
    for event, elem in ET.iterparse(z.open(content), events=("end",)):
        if elem.tag != T_ROW:
            continue
        if int(elem.get(T_ROW_REPEATED) or "1") > 1000:
            continue
        cells = []
        for cell in elem.findall(T_CELL):
            crep = int(cell.get(T_REPEATED) or "1")
            cells.extend([cell_text(cell)] * crep)
        if header is None:
            if cells and cells[0] == "Location ID":
                header = {h: i for i, h in enumerate(cells)}
            continue
        if cells[header["Care home?"]] != "Y":
            continue
        m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", cells[header["Location HSCA End Date"]] or "")
        if not m:
            continue
        year = int(m.group(3))
        prov = cells[header["Provider ID"]]
        by_year[year][prov] += 1
        elem.clear()

    print("year  events  distinct_providers  max_one_provider  top3_share")
    for y in sorted(by_year):
        c = by_year[y]
        total = sum(c.values())
        top3 = sum(v for _, v in c.most_common(3))
        print(f"{y}  {total:5d}  {len(c):6d}  {c.most_common(1)[0][1]:4d}  {top3/total:.3f}")

if __name__ == "__main__":
    sys.exit(main())
