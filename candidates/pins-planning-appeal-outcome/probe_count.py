#!/usr/bin/env python3
"""Bounded discovery probe for PINS Casework Database (appeals outcome candidate).

Streams the data worksheet of the two GOV.UK Excel files with stdlib only
(no openpyxl/pandas on the coordinator) and counts:
  data rows (non-empty), decision values, decision years, casework types,
  decision-by-type cross-tab, procedure, distinct refs and LPAs, missing key
  dates, received->valid and valid->decision lag buckets, site-flag presence.

Usage: python3 probe_count.py <file1.xlsx> [file2.xlsx ...]
Prints one JSON object per file.
"""
import json
import re
import sys
import zipfile
from datetime import datetime, timedelta
from xml.etree.ElementTree import iterparse

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}

CELL_RE = re.compile(r"([A-Z]+)(\d+)")
LAG_BUCKETS = [(0, 30), (31, 90), (91, 180), (181, 365), (366, 10**9)]


def load_shared_strings(zf):
    strings = []
    try:
        with zf.open("xl/sharedStrings.xml") as fh:
            for _, el in iterparse(fh, events=("end",)):
                if el.tag.endswith("}si"):
                    strings.append("".join(t.text or "" for t in el.iter()
                                           if t.tag.endswith("}t")))
                    el.clear()
    except KeyError:
        pass
    return strings


def sheet_files(zf):
    rels = {}
    with zf.open("xl/_rels/workbook.xml.rels") as fh:
        for _, el in iterparse(fh, events=("end",)):
            if el.tag.endswith("}Relationship"):
                rels[el.get("Id")] = el.get("Target")
                el.clear()
    out = []
    with zf.open("xl/workbook.xml") as fh:
        for _, el in iterparse(fh, events=("end",)):
            if el.tag.endswith("}sheet"):
                target = rels.get(el.get("{%s}id" % NS["r"]), "")
                path = target.lstrip("/") if target.startswith("/") else "xl/" + target
                out.append((el.get("name"), path))
                el.clear()
    return out


def to_date(raw):
    if raw is None:
        return None
    s = str(raw)
    if s.replace(".", "", 1).isdigit():
        n = float(s)
        if 20000 <= n <= 60000:
            return datetime(1899, 12, 30) + timedelta(days=n)
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def row_cells(row, shared):
    cells = {}
    for c in row.findall("m:c", NS):
        m = CELL_RE.match(c.get("r") or "")
        if not m:
            continue
        t = c.get("t")
        v = c.find("m:v", NS)
        if t == "s" and v is not None and v.text is not None:
            i = int(v.text)
            val = shared[i] if i < len(shared) else None
        elif t == "inlineStr":
            is_el = c.find("m:is", NS)
            val = "".join(x.text or "" for x in is_el.iter()) if is_el is not None else None
        elif v is None:
            val = None
        else:
            val = v.text
        if val is not None and str(val).strip() != "":
            cells[m.group(1)] = val
    return cells


def probe(path):
    zf = zipfile.ZipFile(path)
    sizes = {i.filename: i.file_size for i in zf.infolist()}
    name, target = max(sheet_files(zf), key=lambda sp: sizes.get(sp[1], 0))
    shared = load_shared_strings(zf)
    c = {"file": path.split("/")[-1], "sheet": name, "data_rows": 0,
         "empty_rows": 0, "decision": {}, "decision_year": {},
         "casework_type": {}, "decision_by_type": {}, "procedure": {},
         "distinct_ref": 0, "duplicate_ref": 0, "distinct_lpa": 0,
         "missing_valid": 0, "missing_decision_date": 0,
         "missing_received": 0, "lag_valid_decision": {},
         "lag_received_valid": {}, "flag_presence": {}, "sample_rows": []}
    header, colidx = None, {}
    seen, lpas = set(), set()
    ref_names = ("Case Number", "Older Casework Data Ref No")
    flag_cols = ("Site Green Belt", "Agricultural Holding",
                 "Development Affect Setting Of Listed Building",
                 "In CA Relates To CA", "Is Flooding An Issue",
                 "Is the site within an AONB", "Is site within an SSSI",
                 "Costs Applied for Indicator")
    with zf.open(target) as fh:
        for _, row in iterparse(fh, events=("end",)):
            if not row.tag.endswith("}row"):
                continue
            cells = row_cells(row, shared)
            if header is None:
                if len(cells) >= 10 and "Decision" in [str(v) for v in cells.values()]:
                    header = {k: str(v).strip() for k, v in cells.items()}
                    colidx = {v: k for k, v in header.items()}
                    c["header"] = dict(sorted(header.items()))
                    row.clear()
                    continue
                c["empty_rows"] += 1
                row.clear()
                continue
            if not cells:
                c["empty_rows"] += 1
                row.clear()
                continue
            c["data_rows"] += 1
            if len(c["sample_rows"]) < 2:
                c["sample_rows"].append(dict(cells))
            get = lambda nm: cells.get(colidx.get(nm, "")) if nm in colidx else None
            # uniqueness on whichever reference column exists
            for rn in ref_names:
                if rn in colidx:
                    ref = str(get(rn))
                    if ref in seen:
                        c["duplicate_ref"] += 1
                    seen.add(ref)
                    break
            if "LPA Name" in colidx and get("LPA Name"):
                lpas.add(str(get("LPA Name")))
            typ0 = get("Type of Casework") or get("Type of Appeal")
            dec = get("Decision")
            dec = str(dec) if dec is not None else "<missing>"
            c["decision"][dec] = c["decision"].get(dec, 0) + 1
            typ = get("Type of Casework") or get("Type of Appeal")
            typ = str(typ) if typ is not None else "<missing>"
            c["casework_type"][typ] = c["casework_type"].get(typ, 0) + 1
            key = typ.split(" - ")[0][:40]
            dtab = c["decision_by_type"].setdefault(key, {})
            dtab[dec] = dtab.get(dec, 0) + 1
            proc = get("Procedure")
            if proc is not None:
                c["procedure"][str(proc)] = c["procedure"].get(str(proc), 0) + 1
            for fc in flag_cols:
                if fc in colidx and get(fc) is not None:
                    c["flag_presence"][fc] = c["flag_presence"].get(fc, 0) + 1
            rd, vd, dd = (to_date(get("Received Date")), to_date(get("Valid Date")),
                          to_date(get("Decision Date")))
            if rd is None:
                c["missing_received"] += 1
            if vd is None:
                c["missing_valid"] += 1
            if dd is None:
                c["missing_decision_date"] += 1
            if dd is not None:
                c["decision_year"][str(dd.year)] = c["decision_year"].get(str(dd.year), 0) + 1
            # family x year cross-tab for split-capacity evidence
            fam = None
            if typ0 is not None:
                t0 = str(typ0)
                if t0.startswith("Planning Appeal") or t0.startswith("Householder"):
                    fam = "s78_core"
                elif t0.startswith("Lawful Development") or t0.startswith("Listed Building"):
                    fam = "s174_ext"
            if fam is not None and dd is not None:
                fy = c.setdefault("family_year", {})
                fy.setdefault(fam, {}).setdefault(str(dd.year), {"n": 0, "allowed": 0})
                fy[fam][str(dd.year)]["n"] += 1
                if dec == "Allowed":
                    fy[fam][str(dd.year)]["allowed"] += 1
            for a, b, store in ((vd, dd, "lag_valid_decision"),
                                (rd, vd, "lag_received_valid")):
                if a is not None and b is not None:
                    lag = (b - a).days
                    for lo, hi in LAG_BUCKETS:
                        if lo <= lag <= hi:
                            k = f"{lo}-{hi if hi < 10**9 else 'inf'}"
                            c[store][k] = c[store].get(k, 0) + 1
                            break
            row.clear()
    c["distinct_ref"] = len(seen)
    c["distinct_lpa"] = len(lpas)
    return c


def main():
    out = []
    for p in sys.argv[1:]:
        out.append(probe(p))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
