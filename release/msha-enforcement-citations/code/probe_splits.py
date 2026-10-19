#!/usr/bin/env python3
"""Split-capacity probe for the MSHA Violations data set (streamed; nothing extracted to disk).

For each proposed window, counts inspections, citations, distinct 30 CFR sections cited and
whether every label on the floor is still present. A window that loses labels is not usable.

Usage: python3 probe_splits.py <Violations.zip>
"""
import collections, csv, io, sys, zipfile

WINDOWS = [("train", "2001", "2020"), ("eval", "2021", "2023"), ("holdout", "2024", "2025")]

def stream(zf):
    name = [n for n in zf.namelist() if n.lower().endswith((".txt", ".csv"))][0]
    with zf.open(name) as fh:
        yield from csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline=""),
                                  delimiter="|")

def main(path):
    zf = zipfile.ZipFile(path)
    year = collections.Counter()          # year -> citations
    year_ev = collections.defaultdict(set)  # year -> event numbers
    label_year = collections.defaultdict(collections.Counter)  # year -> label -> citations
    for row in stream(zf):
        lab = (row.get("PART_SECTION") or "").strip()
        if not lab:
            continue
        d = (row.get("INSPECTION_BEGIN_DT") or "").strip()
        if not d:
            continue
        y = d[-4:]
        e = (row.get("EVENT_NO") or "").strip()
        year[y] += 1
        year_ev[y].add(e)
        label_year[y][lab] += 1
    print("year | citations | inspections | distinct labels")
    for y in sorted(year):
        print(f"{y} | {year[y]:>9,} | {len(year_ev[y]):>7,} | {len(label_year[y]):>5,}")
    # label floor from all years, then presence per window
    tot = collections.Counter()
    for y in year:
        tot.update(label_year[y])
    n_insp_total = len(set().union(*year_ev.values()))
    floor = [lab for lab, v in tot.items() if v >= 0.01 * n_insp_total]
    print(f"\ninspections across all years: {n_insp_total:,}; labels on the 1% floor: {len(floor)}")
    print("\nwindow | years | inspections | citations | labels present | floor labels missing")
    for name, lo, hi in WINDOWS:
        ys = [y for y in year if lo <= y <= hi]
        insp = len(set().union(*[year_ev[y] for y in ys]))
        cit = sum(year[y] for y in ys)
        present = sum(1 for lab in floor if any(label_year[y][lab] for y in ys))
        missing = [lab for lab in floor if not any(label_year[y][lab] for y in ys)]
        print(f"{name} | {lo}-{hi} | {insp:>7,} | {cit:>9,} | {present}/{len(floor)} | {missing[:6]}")

if __name__ == "__main__":
    main(sys.argv[1])
