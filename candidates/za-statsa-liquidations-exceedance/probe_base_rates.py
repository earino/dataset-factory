#!/usr/bin/env python3
"""Label base rates and split capacity for the StatsSA P0043.1 liquidations panel.

Task frame: at the publication instant of the reference-month-M release (published
~4 weeks after M), predict month M+2's aggregate (which begins after the instant
and ends after the next publication). Month M+1 is ongoing at the instant: it can
be neither feature nor target.
"""
import statistics as st

SCRATCH = "/opt/data/cache/scratch/statsa-liq"
N = 321  # months 2000-01..2026-09

# load ASCII panel
blocks = []
cur = {"values": []}
import re
for line in open(f"{SCRATCH}/ASCII_Liquidations.txt", encoding="utf-8", errors="replace"):
    line = line.rstrip("\n").lstrip()
    m = re.match(r"(H\d+):\s*(.*)", line)
    if line.startswith("H01:"):
        if cur.get("values"):
            blocks.append(cur)
        cur = {"values": []}
    if m:
        cur[m.group(1)] = m.group(2).strip()
    elif re.match(r"^\d+$", line):
        cur["values"].append(int(line))
if cur.get("values"):
    blocks.append(cur)

def mi(seq):
    y, m = divmod(seq, 12)
    return f"{2000 + y:04d}-{m + 1:02d}"

# candidate population: industry-level series (exclude Totals and Unclassified)
units = [b for b in blocks if b["H07"] and b["H07"] != "Unclassified" and not b["H07"] == ""]
print(f"industry-level units: {len(units)} (entity x procedure x 9 industries)")

def label_median(b, i):
    """Target month is i (= M+2 in release-of-M frame). Features use months <= i-2."""
    feat_last = i - 2                      # reference month M = target_month - 2
    if feat_last < 11:
        return None
    window = b["values"][feat_last - 11: feat_last + 1]
    med = st.median(window)
    if med <= 0:
        return None                        # all-zero trailing window: uninformative
    return 1 if b["values"][i] > med else 0

def label_yoy(b, i):
    feat_last = i - 2
    prior_year = i - 12                    # same calendar month one year earlier
    if prior_year < 0 or feat_last < 11:
        return None
    if b["values"][prior_year] == 0 and b["values"][i] == 0:
        return None
    return 1 if b["values"][i] > b["values"][prior_year] else 0

def windows(year_from, year_to):
    return [i for i in range(N) if year_from <= 2000 + i // 12 <= year_to]

splits = [("train", 2002, 2016), ("eval", 2017, 2020), ("holdout", 2021, 2026)]

for name, fn in [("median-exceedance", label_median), ("yoy-direction", label_yoy)]:
    print(f"\n== {name} ==")
    tot_pos = tot = 0
    for sname, y0, y1 in splits:
        pos = n = 0
        series_with_pos = set()
        for b in units:
            for i in windows(y0, y1):
                lab = fn(b, i)
                if lab is None:
                    continue
                n += 1
                pos += lab
                if lab:
                    series_with_pos.add(b["H03"])
        print(f"  {sname} {y0}-{y1}: rows {n}, positives {pos} ({pos / n:.1%}), series w/ positives {len(series_with_pos)}/{len(units)}")
        tot_pos += pos; tot += n
    print(f"  total: rows {tot}, positives {tot_pos} ({tot_pos / tot:.1%})")

# totals-series check: how often does the national total exceed its trailing median?
tb = blocks[0]
pos = n = 0
for i in range(12, N - 2):
    lab = label_median(tb, i)
    if lab is None: continue
    n += 1; pos += lab
print(f"\nnational total series median-exceedance: {pos}/{n} = {pos / n:.1%}")

# clustered positives: count distinct positive MONTHS (across all units) per year, train/eval/holdout
for name, fn in [("median-exceedance", label_median)]:
    print(f"\npositive months per year ({name}):")
    by_year = {}
    for b in units:
        for i in range(12, N):
            if fn(b, i) == 1:
                by_year.setdefault(2000 + i // 12, set()).add(i)
    for y in sorted(by_year):
        print(f"  {y}: {len(by_year[y])} distinct positive months, max unit-months in a month = {max(1 for _ in [0]) if y else ''}"[:0] or f"  {y}: {len(by_year[y])} distinct positive months")
