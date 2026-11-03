#!/usr/bin/env python3
"""Streaming ODS inspector, pass 2: dump first rows' non-empty cells to locate the header."""
import os
import sys
import zipfile

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


def main():
    z = zipfile.ZipFile(ODS)
    content = [m for m in z.namelist() if m.endswith("content.xml")][0]
    import xml.etree.ElementTree as ET
    max_rows = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    row_idx = 0
    for event, elem in ET.iterparse(z.open(content), events=("end",)):
        if elem.tag != T_ROW:
            continue
        rep = int(elem.get(T_ROW_REPEATED) or "1")
        if rep > 1000:
            continue
        cells = []
        for cell in elem.findall(T_CELL):
            crep = int(cell.get(T_REPEATED) or "1")
            t = cell_text(cell)
            cells.extend([t] * crep)
        nonempty = [(i, t) for i, t in enumerate(cells) if t]
        print(f"row {row_idx} (rep {rep}): {len(nonempty)} non-empty cells")
        if nonempty:
            for i, t in nonempty[:45]:
                print(f"   [{i:3d}] {t[:70]!r}")
        row_idx += 1
        if row_idx >= max_rows:
            break
        elem.clear()

if __name__ == "__main__":
    sys.exit(main())
