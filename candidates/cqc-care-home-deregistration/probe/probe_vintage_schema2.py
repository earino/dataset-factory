"""Follow-up probe: WHERE does the Location ID header live in the 2019-2021
January vintages? The value-domain probe showed no header row detected on the
first sheet of those files (0 data rows), so this walks the workbook's sheet
list and dumps the first rows of every sheet (bounded: 8 rows x 12 cells),
plus the cell count of each sheet, to name the exact structural drift vs the
2018 and 2022 files that build.

Output: probe/vintage_schema2_out.json (no row data beyond the first rows'
leading cells; column names and stamps only by construction of the dump).
"""
from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BUILD = REPO / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
WORK = Path("/opt/data/cache/scratch/cqc_vintage_probe")

spec = importlib.util.spec_from_file_location("cqc_build_probe2", str(BUILD))
b = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("no loader for build.py")
spec.loader.exec_module(b)

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

YEARS = [2018, 2019, 2020, 2021, 2022]


def sheet_names_and_paths(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_map = {r.get("Id"): r.get("Target") for r in rels.iter(f"{RELS}Relationship")}
    out = []
    for sheet in wb.find(f"{NS}sheets").findall(f"{NS}sheet"):
        rid = sheet.get(RID)
        target = rid_map.get(rid, "?")
        out.append((sheet.get("name") or "?", "xl/" + str(target).lstrip("/").removeprefix("xl/")))
    return out


def ods_first_rows(path: Path, nrows: int = 8, ncols: int = 12) -> list[list[str]]:
    rows = []
    for kind, cells in b.ods_rows(path):
        if kind in ("stamp", "header"):
            rows.append([str(c) for c in (cells[:ncols])])
        if len(rows) >= nrows:
            break
    return rows


def xlsx_sheet_first_rows(z: zipfile.ZipFile, sheet_path: str,
                          nrows: int = 8, ncols: int = 12) -> list[list[str]]:
    """First nrows rows of the given sheet, first ncols cells, raw reader cells."""
    rows: list[list[str]] = []
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.iter(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    seen = 0
    for _, elem in ET.iterparse(z.open(sheet_path), events=("end",)):
        if elem.tag != f"{NS}row":
            continue
        cells: list[str] = []
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
        rows.append([str(c) for c in cells[:ncols]])
        seen += 1
        elem.clear()
        if seen >= nrows:
            break
    return rows


def main() -> int:
    out: dict = {"probe": "vintage_schema2", "vintages": {}}
    for year in YEARS:
        ext = "xlsx" if year < 2022 else "ods"
        path = WORK / f"active_{year}_01.{ext}"
        if not path.exists():
            # 2022 might be ods per the archive; accept either present file
            alt = WORK / f"active_{year}_01.{'ods' if ext == 'xlsx' else 'xlsx'}"
            if alt.exists():
                path = alt
            else:
                out["vintages"][str(year)] = {"error": "file not on disk"}
                continue
        info: dict = {"file": path.name, "sheets": []}
        if path.suffix.lower() == ".xlsx":
            with zipfile.ZipFile(path) as z:
                for name, spath in sheet_names_and_paths(z):
                    info["sheets"].append({
                        "name": name, "path": spath,
                        "first_rows": xlsx_sheet_first_rows(z, spath)})
        else:
            info["sheets"].append({"name": "<ods single content.xml>",
                                   "first_rows": ods_first_rows(path)})
        out["vintages"][str(year)] = info
        print(f"{year}: {len(info['sheets'])} sheet(s): "
              f"{[s['name'] for s in info['sheets']]}", flush=True)
    dest = HERE / "vintage_schema2_out.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"written: {dest}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
