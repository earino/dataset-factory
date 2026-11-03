#!/usr/bin/env python3
"""Inspect the CQC directory CSV: header, sample rows, and quick aggregates."""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "cqc_dl", "csv", "28_October_2026_CQC_directory.csv")

def find_csv():
    base = os.path.join(HERE, "cqc_dl", "csv")
    if os.path.exists(path):
        return path
    for root, _, files in os.walk(base):
        for f in files:
            if f.lower().endswith(".csv"):
                return os.path.join(root, f)
    return None

def main():
    import zipfile
    base = os.path.join(HERE, "cqc_dl")
    # extract zip if not done
    if not os.path.exists(os.path.join(base, "csv")):
        with zipfile.ZipFile(os.path.join(base, "dir_csv.zip")) as z:
            print("zip members:", z.namelist())
            z.extractall(os.path.join(base, "csv"))
    p = find_csv()
    print("csv path:", p)
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
        r = csv.reader(f)
        header = next(r)
        print(f"columns ({len(header)}):")
        for i, h in enumerate(header):
            print(f"  {i:2d} {h!r}")
        rows = 0
        samples = []
        for row in r:
            rows += 1
            if len(samples) < 3:
                samples.append(row)
        print(f"total data rows: {rows}")
        for s in samples:
            print("  sample:", {header[i]: s[i] for i in range(min(len(s), len(header)))})

if __name__ == "__main__":
    sys.exit(main())
