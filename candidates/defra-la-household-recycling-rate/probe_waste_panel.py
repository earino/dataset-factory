#!/usr/bin/env python3
"""Probe: Defra LA household recycling panel from the cumulative Table_1 (2024-25 ODS).

Extracts (LA, year) household waste totals and recycled tonnages, computes the
household recycling rate, and measures the >=50% label across split windows.
Threshold basis: Waste Framework Directive 2008/98/EC art.11(2)(a) 50% household
recycling by 2020 (a published regulatory target, not an invented cutoff).
"""
import os
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

NS = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
      "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
      "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0"}
T = "{%s}" % NS["table"]
X = "{%s}" % NS["text"]
OFF = "{%s}" % NS["office"]

PATH = "/opt/data/cache/scratch/defra_waste/2024-25.ods"


def cells_of_row(row):
    """Position-preserved cell text list, honouring number-columns-repeated."""
    cells = []
    for c in row.findall("table:table-cell", NS):
        rep = int(c.get(T + "number-columns-repeated", "1"))
        txt = " ".join((p.text or "").strip() for p in c.findall(X + "p", NS)).strip()
        if not txt:
            v = c.get(OFF + "value")
            if v:
                txt = v
        for _ in range(min(rep, 200)):
            cells.append(txt)
    return cells


def sheet_rows(path, sheet_name):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("content.xml"))
    for s in root.findall(".//table:table", NS):
        if s.get(T + "name") == sheet_name:
            return [cells_of_row(r) for r in s.findall("table:table-row", NS)]
    return None


rows = sheet_rows(PATH, "Table_1")
print(f"Table_1 rows read: {len(rows)}")

# find header row (contains 'Financial Year')
hdr_i = None
for i, r in enumerate(rows):
    if r and r[0].strip().lower().startswith("financial year"):
        hdr_i = i
        break
hdr = rows[hdr_i]
print(f"header row at {hdr_i}: {hdr[:9]} ... ({len(hdr)} cols)")

def col(label_prefix):
    for j, h in enumerate(hdr):
        if h.strip().lower().startswith(label_prefix.lower()):
            return j
    return None

c_year, c_code, c_auth, c_type = 0, col("ons code"), col("local authority"), col("authority type")
c_tot, c_rec = col("household - total waste"), col("household - waste sent for recycling")
print(f"cols: code={c_code} auth={c_auth} type={c_type} hhw_total={c_tot} hhw_recycled={c_rec}")


def fnum(s):
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


panel = {}
n_rows = 0
for r in rows[hdr_i + 1:]:
    if len(r) <= max(c_tot, c_rec):
        continue
    year = (r[c_year] or "").strip()
    code = (r[c_code] or "").strip() if c_code is not None else ""
    if not (year[:2] == "20" and "/" in year or year[:2] == "20" and "-" in year):
        continue
    tot, rec = fnum(r[c_tot]), fnum(r[c_rec])
    if tot is None or rec is None or code.startswith("*") or not code.startswith("E"):
        continue
    n_rows += 1
    rate = rec / tot * 100 if tot > 0 else None
    panel[(code, year)] = {
        "auth": (r[c_auth] or "").strip() if c_auth is not None else "",
        "type": (r[c_type] or "").strip() if c_type is not None else "",
        "tot": tot, "rec": rec, "rate": rate,
    }
print(f"data rows with rates: {n_rows}; panel keys: {len(panel)}")

years = sorted({y for (_, y) in panel}, key=lambda s: s[:4])
print("years:", years)
by_year = defaultdict(list)
for (code, year), v in panel.items():
    if v["rate"] is not None:
        by_year[year].append((code, v))
for year in years:
    lst = by_year[year]
    pos50 = [c for c, v in lst if v["rate"] >= 50]
    rates = sorted(v["rate"] for _, v in lst)
    print(f"{year}: n={len(lst):3d} >=50%: {len(pos50):3d} ({len(pos50)/len(lst)*100:.0f}%) "
          f"median={rates[len(rates)//2]:.1f} p90={rates[int(len(rates)*0.9)]:.1f} "
          f"max={rates[-1]:.1f}")

# year-over-year label persistence and split capacity
def year_key(y):
    return y[:4]

ys = years
pairs = [(ys[i], ys[i + 1]) for i in range(len(ys) - 1)]
print("\nyear-over-year >=50% persistence:")
for prev, nxt in pairs:
    stay_pos = stay_neg = flip_pos = flip_neg = 0
    for (code, y), v in panel.items():
        if y != prev or v["rate"] is None:
            continue
        v2 = panel.get((code, nxt))
        if not v2 or v2["rate"] is None:
            continue
        a, b = v["rate"] >= 50, v2["rate"] >= 50
        if a and b:
            stay_pos += 1
        elif a and not b:
            flip_neg += 1
        elif not a and b:
            flip_pos += 1
        else:
            stay_neg += 1
    tot = stay_pos + stay_neg + flip_pos + flip_neg
    if tot:
        acc = (stay_pos + stay_neg) / tot * 100
        print(f"  {prev} -> {nxt}: pos->pos {stay_pos}, pos->neg {flip_neg}, "
              f"neg->pos {flip_pos}, neg->neg {stay_neg}; persistence-acc {acc:.1f}% "
              f"(n={tot})")

# split windows: train <=2020/21, eval 2021/22-2022/23, holdout 2023/24-2024/25
WINDOWS = {"train": ("2014-15", "2020-21"), "eval": ("2021-22", "2022-23"),
           "holdout": ("2023-24", "2024-25")}
print("\nsplit windows (label = rate >= 50% in target year):")
for w, (y0, y1) in WINDOWS.items():
    pos = neg = 0
    pos_auth = set()
    for (code, year), v in panel.items():
        if not (y0[:4] <= year[:4] <= y1[:4]) or v["rate"] is None:
            continue
        # exclude the feature-year ambiguity: target years only
        if w == "train" and year[:4] < "2015":
            continue
        if v["rate"] >= 50:
            pos += 1
            pos_auth.add(code)
        else:
            neg += 1
    print(f"  {w:8s} {y0}..{y1}: rows={pos+neg:5d} pos={pos:4d} neg={neg:4d} "
          f"pos-rate={pos/(pos+neg)*100:5.1f}% distinct-positive-LAs={len(pos_auth)}"
          if pos + neg else f"  {w}: NO ROWS")

# national cross-check: sum over unitary+disposal only (per the file's own note)
print("\nnational household recycling rate (sum over Unitary+Disposal):")
for year in years:
    tot = sum(v["tot"] for (code, y), v in panel.items()
              if y == year and v["type"].lower().startswith(("unitary", "disposal")))
    rec = sum(v["rec"] for (code, y), v in panel.items()
              if y == year and v["type"].lower().startswith(("unitary", "disposal")))
    if tot:
        print(f"  {year}: {rec/tot*100:.1f}%")
