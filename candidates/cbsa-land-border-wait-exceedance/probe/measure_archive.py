#!/usr/bin/env python3
"""Discovery measurements on the CBSA hourly snapshot archive samples (2026-11-05).

Reproduces the numbers in record.json measurements.grain_and_coverage_2026_11_05,
duplicate_conflicts_2026_11_05, base_rates_2019q3_2026_11_05 and
known_event_fixture_2026_11_05.

Inputs (fetch first, see notes.md section 2):
  q2019q3.csv          - bwt-taf-2019-07-01--2019-09-30-en.csv   (full file)
  q2020q1_fr.csv      - bwt-taf-2020-01-01--2020-03-31-fr.csv   (full file, cp1252)
  bwt-2010-2014-head.csv, era2010_mid.csv, era2010_end.csv - 60 KB range slices

Usage: python3 measure_archive.py <input-dir>
"""
import csv, collections, re, sys

BASE = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/") + "/"

def parse_minutes(v):
    """Return (kind, number|None) for a flow cell; kind is one of
    no_delay/closed/not_applicable/missed_entry/minutes*/empty/other."""
    s = (v or "").strip()
    if not s:
        return ("empty", None)
    low = s.lower()
    if low.startswith("no delay"):
        return ("no_delay", None)
    if "closed" in low or "temporarily" in low:
        return ("closed", None)
    if low.startswith("not applicable"):
        return ("not_applicable", None)
    if "missed" in low:
        return ("missed_entry", None)
    m = re.match(r"^(\d+)\s*(min|minutes)?$", low)
    if m:
        return ("minutes", int(m.group(1)))
    m2 = re.match(r"^(\d+)\s*(min|minutes)?\b.*", low)
    if m2:
        return ("minutes_with_text", int(m2.group(1)))
    return ("other", None)

# ---------- full quarter 2019 Q3 ----------
with open(BASE + "q2019q3.csv", encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f)
    hdr = next(rd)
    print("2019Q3 header:", hdr)
    rows = list(rd)
print("2019Q3 data rows:", len(rows))

offices = collections.Counter()
tmin, tmax = None, None
tzs = collections.Counter()
keys = collections.Counter()
vocab_trav = collections.Counter()
vocab_comm = collections.Counter()
trav_minutes = []
per_office_rows = collections.Counter()
for r in rows:
    office, loc, updated, comm, trav = (r + [""] * 5)[:5]
    offices[office] += 1
    per_office_rows[office] += 1
    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+(\w+)", updated)
    if m:
        tzs[m.group(2)] += 1
        dt = m.group(1)
        if tmin is None or dt < tmin: tmin = dt
        if tmax is None or dt > tmax: tmax = dt
    keys[(office, updated)] += 1
    k1 = parse_minutes(comm); k2 = parse_minutes(trav)
    vocab_comm[k1[0]] += 1
    vocab_trav[k2[0]] += 1
    if k2[0].startswith("minutes"):
        trav_minutes.append(k2[1])

print("2019Q3 offices:", len(offices))
print("2019Q3 distinct (office,timestamp) keys:", len(keys),
      "dups:", sum(1 for c in keys.values() if c > 1),
      "max-dup:", max(keys.values()))
print("2019Q3 time range:", tmin, "->", tmax)
print("2019Q3 tz abbrevs:", dict(tzs))
print("2019Q3 traveller vocab:", dict(vocab_trav))
print("2019Q3 commercial vocab:", dict(vocab_comm))
print("2019Q3 rows/office min/median/max:",
      min(per_office_rows.values()),
      sorted(per_office_rows.values())[len(per_office_rows)//2],
      max(per_office_rows.values()))

# duplicates with conflicting values?
conflict = collections.Counter()
bykey = {}
for r in rows:
    office, loc, updated, comm, trav = (r + [""] * 5)[:5]
    k = (office, updated)
    if k in bykey and (bykey[k][0] != comm or bykey[k][1] != trav):
        conflict[office] += 1
    bykey.setdefault(k, (comm, trav))
print("2019Q3 dup keys with CONFLICTING values:", sum(conflict.values()), dict(conflict))

valid = [m for m in trav_minutes if m is not None]
import statistics
if valid:
    print("2019Q3 traveller minutes rows:", len(valid),
          "mean:", round(statistics.mean(valid), 2),
          "max:", max(valid))
    for thr in (5, 10, 15, 30, 60):
        n = sum(1 for m in valid if m > thr)
        print(f"  traveller wait > {thr} min: {n} ({n/len(valid):.1%})")

per_office_pos = collections.Counter()
per_office_valid = collections.Counter()
for r in rows:
    office, loc, updated, comm, trav = (r + [""] * 5)[:5]
    k2 = parse_minutes(trav)
    if k2[0].startswith("minutes") and k2[1] is not None:
        per_office_valid[office] += 1
        if k2[1] > 30:
            per_office_pos[office] += 1
print("2019Q3 per-office traveller>30 (top 12):")
for o, p in per_office_pos.most_common(12):
    print(f"   {o}: {p}/{per_office_valid[o]} ({p/max(per_office_valid[o],1):.1%})")
print("offices with zero >30 traveller snapshots:",
      sum(1 for o in per_office_valid if per_office_pos[o] == 0), "/", len(per_office_valid))

# ---------- 2010-2014 era slices ----------
for name in ("bwt-2010-2014-head.csv", "era2010_mid.csv", "era2010_end.csv"):
    txt = open(BASE + name, encoding="utf-8-sig", errors="replace").read()
    lines = txt.splitlines()
    print(f"\n{name}: {len(lines)} lines (bounded slice)")
    hdr0 = lines[0]
    vt = collections.Counter(); vc = collections.Counter(); tz = collections.Counter()
    dates = []
    for line in lines[1:]:
        parts = next(csv.reader([line])) if '"' in line else line.split(",")
        if len(parts) < 5:
            parts = (parts + [""] * 5)[:5]
        vc[parse_minutes(parts[3])[0]] += 1
        vt[parse_minutes(parts[4])[0]] += 1
        m = re.search(r"(\d{4}-\d{2}-\d{2})", parts[2])
        if m: dates.append(m.group(1))
        m2 = re.search(r"\d{2}:\d{2} (\w+)", parts[2])
        if m2: tz[m2.group(1)] += 1
    print("  header:", hdr0[:80])
    print("  date span in slice:", (min(dates), max(dates)) if dates else "n/a")
    print("  tz:", dict(tz), "| trav vocab:", dict(vt), "| comm vocab:", dict(vc))
