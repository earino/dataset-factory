#!/usr/bin/env python3
"""Measure the CBSA monthly land BWT service-standard file (2026-11-05).

Reproduces the numbers in record.json measurements.monthly_cross_check_panel_2026_11_05.

Input (fetch first, see notes.md section 5):
  land-bwt-opengov-en.csv - resource 2b5853e4 of open.canada.ca dataset
  000fe5aa-1d77-42d1-bfe7-458c51dacfef ("Historical Border Wait Times -
  2019-04-01 to 2025-10-31"), 80,693 B.

Usage: python3 measure_monthly.py <input-dir>
"""
import csv, collections, sys

BASE = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/") + "/"
path = BASE + "land-bwt-opengov-en.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
print("total rows:", len(rows))
print("columns:", list(rows[0].keys()))

ports = collections.Counter(r["Port of Entry"] for r in rows)
months = collections.Counter(r["Month"] for r in rows)
fy = collections.Counter(r["Fiscal Year"] for r in rows)
print("distinct ports:", len(ports))
print("distinct months:", len(months), sorted(months.keys()))
print("fiscal years:", sorted(fy.keys()))

def pct(v):
    try:
        return float(v.replace("%", "").strip())
    except Exception:
        return None

vals = [pct(r["Percentage Met Service Standard"]) for r in rows]
bad = [v for v in vals if v is None]
print("unparseable percentage cells:", len(bad))
ok = [v for v in vals if v is not None]
print("pct range:", min(ok), max(ok))
print("pct==100 count:", sum(1 for v in ok if v == 100.0))
for thr in (90, 95, 97, 99):
    below = sum(1 for v in ok if v < thr)
    print(f"pct<{thr}: {below} ({below/len(ok):.1%})")

pm = collections.Counter((r["Port of Entry"], r["Month"], r["Fiscal Year"]) for r in rows)
print("duplicate port-month cells:", sum(1 for c in pm.values() if c > 1))
print("min/max rows per port:", min(ports.values()), max(ports.values()))
