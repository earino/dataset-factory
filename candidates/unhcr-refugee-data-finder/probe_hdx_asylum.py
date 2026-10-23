#!/usr/bin/env python3
"""Probe: HDX global UNHCR asylum-applications CSV (annual corridor grain).

Reproducibility: run from the repo root or the candidate dir; the CSV path
defaults to the scratch download. Data source (downloaded 2026-10-23):
  https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8/resource/295cd9e4-8464-43ee-ad17-47196991a1f7/download/asylum_applications_residing_world.csv
  sha256 d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950
Usage: python3 probe_hdx_asylum.py [--csv path] [--limit N]
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = "/opt/data/cache/scratch/hdx/asylum_applications_residing_world.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--limit", type=int, default=None, help="only read first N data rows")
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        if header is None:
            raise SystemExit("empty CSV")
        print("HEADER:", header)
        rows = list(reader)
        if args.limit:
            rows = rows[: args.limit]

    print("data rows:", len(rows))

    # distinct value mixes of every categorical column
    for col in header:
        vals = Counter(r.get(col, "") for r in rows)
        if len(vals) <= 25:
            print(f"{col}: {dict(vals.most_common())}")

    # numeric sanity
    bad = 0
    zero_persons = 0
    years = set()
    for r in rows:
        years.add(int(r["Year"]))
        try:
            n = float(r["Number of Applications"])
        except ValueError:
            bad += 1
            continue
        if r["Application Data Type"] == "P" and n == 0:
            zero_persons += 1
    print("years:", min(years), "..", max(years), "count:", len(years))
    print("non-numeric Number of Applications:", bad)
    print("persons-rows with 0:", zero_persons)

    # duplicates on the full dimension key?
    keycols = [c for c in header if c != "Number of Applications"]
    keys = Counter(tuple(r[c] for c in keycols) for r in rows)
    dup = sum(v - 1 for v in keys.values() if v > 1)
    print("duplicate dimension keys (extra rows):", dup)

    # corridor counts per stream
    stream = Counter((r["Procedure Type"], r["Application Data Type"]) for r in rows)
    print("stream mix (Procedure, DataType):", dict(stream))

    for (proc, dt) in sorted(stream):
        sub = [r for r in rows if r["Procedure Type"] == proc and r["Application Data Type"] == dt]
        corridors = set((r["Country of Origin Code"], r["Country of Asylum Code"]) for r in sub)
        org = set(r["Country of Origin Code"] for r in sub)
        asy = set(r["Country of Asylum Code"] for r in sub)
        total = sum(int(float(r["Number of Applications"])) for r in sub)
        print(
            f"stream {proc}/{dt}: rows={len(sub)} corridors={len(corridors)} "
            f"origins={len(org)} asylums={len(asy)} total_apps={total}"
        )

    # aggregate the whole file ignoring stream, per year (rough check of coverage growth)
    per_year = defaultdict(int)
    for r in rows:
        per_year[int(r["Year"])] += int(float(r["Number of Applications"]))
    ys = sorted(per_year)
    print("per-year sum (all streams mixed):")
    for y in ys:
        print(f"  {y}: {per_year[y]:,}")


if __name__ == "__main__":
    main()
