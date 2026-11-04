"""Inspect probe2 output: sheet structure + first rows, and print the data
sheets' headers compactly. Then (probe3) compute the care-home-identifying
column's full value domain on the DATA sheet of each 2019-2021 vintage (the
sheet whose header row starts with Location ID), to confirm the Y/N domain
did not also drift."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/data/cache/scratch/cqc_vintage_probe")
BUILD = HERE.parents[2] / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
spec = importlib.util.spec_from_file_location("cqc_build_probe3", str(BUILD))
b = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("no loader")
spec.loader.exec_module(b)

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
CARE_RE = re.compile(r"care\s*home", re.I)

d2 = json.loads((HERE / "vintage_schema2_out.json").read_text())
for year in ("2018", "2019", "2020", "2021"):
    info = d2["vintages"][year]
    print(f"== {year} ==")
    for s in info["sheets"]:
        first = s["first_rows"]
        print(f"  sheet {s['name']!r}: {len(first)} first rows")
        for r in first[:3]:
            print(f"    {[c[:38] for c in r[:6]]}")

# probe3: value domains on the DATA sheet
def data_sheet_path(z: zipfile.ZipFile) -> tuple[str, str]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_map = {r.get("Id"): r.get("Target") for r in rels.iter(f"{RELS}Relationship")}
    for sheet in wb.find(f"{NS}sheets").findall(f"{NS}sheet"):
        target = "xl/" + str(rid_map.get(sheet.get(RID), "")).lstrip("/").removeprefix("xl/")
        # peek: does any of the first 8 rows start with Location ID?
        rows = probe3_first_rows(z, target, nrows=8, ncols=3)
        if any(r and r[0].strip() == "Location ID" for r in rows if r):
            return sheet.get("name") or "?", target
    return "", ""


def probe3_first_rows(z: zipfile.ZipFile, sheet_path: str, nrows: int, ncols: int):
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.iter(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    rows, seen = [], 0
    for _, elem in ET.iterparse(z.open(sheet_path), events=("end",)):
        if elem.tag != f"{NS}row":
            continue
        cells = []
        for cell in elem.findall(f"{NS}c"):
            ref = cell.get("r") or ""
            idx = b._col_index(ref) if ref else len(cells)
            while len(cells) < idx:
                cells.append("")
            v = cell.find(f"{NS}v")
            inline = cell.find(f"{NS}is")
            ctype = cell.get("t")
            if ctype == "inlineStr" and inline is not None:
                val = "".join(t.text or "" for t in inline.iter(f"{NS}t"))
            elif v is None:
                val = ""
            elif ctype == "s":
                val = shared[int(v.text)] if (v.text or "").isdigit() else ""
            else:
                val = v.text or ""
            cells.append(val.strip())
        rows.append(cells[:ncols])
        seen += 1
        elem.clear()
        if seen >= nrows:
            break
    return rows


out = {"probe": "vintage_schema3_data_sheet", "vintages": {}}
for year in (2018, 2019, 2020, 2021):
    path = WORK / f"active_{year}_01.xlsx"
    with zipfile.ZipFile(path) as z:
        name, spath = data_sheet_path(z)
        if not spath:
            out["vintages"][str(year)] = {"error": "no sheet with Location ID header"}
            print(f"{year}: NO data sheet found")
            continue
        # full pass over the data sheet: header + care-home-ish domains
        header = None
        care_cols: dict[int, tuple[str, Counter]] = {}
        rows = passing = 0
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.iter(f"{NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
        for _, elem in ET.iterparse(z.open(spath), events=("end",)):
            if elem.tag != f"{NS}row":
                continue
            cells = []
            for cell in elem.findall(f"{NS}c"):
                ref = cell.get("r") or ""
                idx = b._col_index(ref) if ref else len(cells)
                while len(cells) < idx:
                    cells.append("")
                v = cell.find(f"{NS}v")
                inline = cell.find(f"{NS}is")
                ctype = cell.get("t")
                if ctype == "inlineStr" and inline is not None:
                    val = "".join(t.text or "" for t in inline.iter(f"{NS}t"))
                elif v is None:
                    val = ""
                elif ctype == "s":
                    val = shared[int(v.text)] if (v.text or "").isdigit() else ""
                else:
                    val = v.text or ""
                cells.append(val.strip())
            if header is None:
                if cells and cells[0].strip() == "Location ID":
                    header = cells
                    care_cols = {i: (h, Counter()) for i, h in enumerate(header)
                                 if CARE_RE.search(h)}
                    for i, (t_, c_) in care_cols.items():
                        c_["__header__"] = 1  # placeholder, removed below
                continue
            rows += 1
            for i, (_, counter) in care_cols.items():
                counter[(cells[i] if i < len(cells) else "") or ""] += 1
                counter.pop("__header__", None)
            m = b.resolve_header(header)["idx"].get("care_home")
            if m is not None and m < len(cells) and (cells[m] or "").strip() == "Y":
                passing += 1
            elem.clear()
        res = b.resolve_header(header)
        domains = {f"col[{i}] {t_!r}": dict(counter.most_common(12))
                   for i, (t_, counter) in sorted(care_cols.items())}
        out["vintages"][str(year)] = {
            "data_sheet": name, "data_rows": rows,
            "missing_required": [f for f, pat in b.REQUIRED_FIELDS.items()
                                 if f not in res["idx"]],
            "resolved_required": res["idx"],
            "care_home_columns_domains": domains,
            "rows_passing_eqY_filter": passing,
        }
        print(f"{year}: data sheet {name!r}: rows={rows} passing_eqY={passing} "
              f"missing={out['vintages'][str(year)]['missing_required']}")

dest = HERE / "vintage_schema3_out.json"
dest.write_text(json.dumps(out, indent=1))
print(f"written: {dest}")
