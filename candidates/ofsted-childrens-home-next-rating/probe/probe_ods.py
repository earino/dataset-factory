# Probe Ofsted children's social care ODS files: sheets, row counts, date ranges, history depth.
import zipfile, sys, re
import xml.etree.ElementTree as ET

NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}

def cell_value(c):
    p = c.find("text:p", NS)
    if p is None:
        return ""
    return "".join(t.text or "" for t in p.iter() if t.tag == f"{{{NS['text']}}}p".replace("{text}", "")) if False else "".join(
        (t.text or "") for t in p.iter(f"{{{NS['text']}}}p") ) or (p.text or "")

def parse_ods(path, max_rows=None):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("content.xml"))
    sheets = {}
    for tbl in root.iter(f"{{{NS['table']}}}table"):
        name = tbl.get(f"{{{NS['table']}}}name")
        rows = []
        for r in tbl.findall(f"{{{NS['table']}}}table-row"):
            vals = []
            for c in r.findall(f"{{{NS['table']}}}table-cell"):
                rep = int(c.get(f"{{{NS['table']}}}number-columns-repeated", "1"))
                p = c.find(f"{{{NS['text']}}}p")
                v = p.text if p is not None and p.text else ""
                if rep > 100:  # trailing empty repeats
                    rep = 1
                vals.extend([v] * rep)
            if any(v.strip() for v in vals):
                rows.append(vals)
            if max_rows and len(rows) >= max_rows:
                break
        sheets[name] = rows
    return sheets

for path in sys.argv[1:]:
    print("=" * 70)
    print("FILE:", path)
    sheets = parse_ods(path)
    for name, rows in sheets.items():
        print(f"\n  SHEET {name!r}: {len(rows)} non-empty rows")
        if rows:
            print("    HEADER:", rows[0][:20])
            for r in rows[1:3]:
                print("    ROW:  ", r[:20])
