#!/usr/bin/env python3
"""Probe 2/2 for za-cct-substation-evening-peak-exceedance (retained recipe).

Label, split, cluster and fixture computation from probe_fullscan.py's
reduced aggregates: evening-peak (16:00-22:00 SAST) trailing-90-evening p95
exceedance labels by year, clustered distinct-day counts, monthly
seasonality, per-station winter/summer ratios, and the dated worked example.
Run: python3 probe_cluster.py [loadprofile_reduce.json]"""

import collections
import datetime
import json
import statistics
import sys

R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "loadprofile_reduce.json"))
series = collections.defaultdict(list)
for k, v in R["eve_peak"].items():
    d, c = k.split("|")
    series[c].append((d, v))

pos_by_year = collections.defaultdict(lambda: [0, 0])
pos_days = collections.defaultdict(set)
all_days = collections.defaultdict(set)
per_station_year = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for c, vals in series.items():
    vals.sort()
    for i, (d, v) in enumerate(vals):
        hist = [vv for _, vv in vals[max(0, i - 90):i]]
        if len(hist) < 30:
            continue  # eligibility: >= 30 prior evenings
        h = sorted(hist)
        p95 = h[int(0.95 * (len(h) - 1))]
        yr = d[:4]
        all_days[yr].add(d)
        pos_by_year[yr][1] += 1
        per_station_year[c][yr][1] += 1
        if v > p95:
            pos_by_year[yr][0] += 1
            pos_days[yr].add(d)
            per_station_year[c][yr][0] += 1

print("labels by year (pos/total):")
for yr in sorted(pos_by_year):
    p, t = pos_by_year[yr]
    print(f"  {yr}: {p}/{t} ({100 * p / t:.2f}%), distinct exceedance days {len(pos_days[yr])}")
good = sum(1 for c in series if all(per_station_year[c].get(y, [0, 0])[0] > 0
                                    for y in ("2022", "2023", "2024")))
print(f"stations with >=1 positive in every year: {good}/{len(series)}")

monthly = collections.defaultdict(list)
for k, v in R["eve_peak"].items():
    monthly[k[:7]].append(v)
print("monthly mean evening peak (MVA):",
      {m: round(statistics.mean(v), 2) for m, v in sorted(monthly.items())})
for c in ("Grassy_Park_66kV", "Atlantis_Industrial_132kV", "Foreshore_132kV"):
    w = statistics.mean([v for d, v in series[c] if d[5:7] in ("05", "06", "07", "08")])
    s = statistics.mean([v for d, v in series[c] if d[5:7] in ("11", "12", "01", "02")])
    print(f"{c}: winter {w:.1f} summer {s:.1f} ratio {w / s:.2f}")

# dated worked example
c, d = "Grassy_Park_66kV", "2024-07-15"
vals = series[c]
i = [j for j, (dd, _) in enumerate(vals) if dd == d][0]
hist = [vv for _, vv in vals[max(0, i - 90):i]]
h = sorted(hist)
p95 = h[int(0.95 * (len(h) - 1))]
print(f"example {c} {d}: evening peak {vals[i][1]:.2f} vs trailing-90-evening "
      f"p95 {p95:.2f} -> exceed {vals[i][1] > p95}")
