#!/usr/bin/env python3
"""Probe 2: label feasibility on the HDX UNHCR asylum-applications panel.

Questions answered (stream = Government/Persons only, the dominant stream):
  1. What are the 5,346 duplicate dimension keys - identical rows or conflicting counts?
  2. Host-year reporting continuity (censoring check): in which years does each
     asylum country appear at all? Missing corridor rows vs non-reporting hosts.
  3. Eligible corridors (>= MIN apps in year D) and label base rates for:
       direction (D+1 < D), growth>25%, growth>50%, >=2x, >=3x
     with missing D+1 corridor rows counted as 0 applications, split by whether
     the host reported anything in D+1 (observed zero vs censored).
  4. Candidate temporal splits with both classes present and clustered counts
     (distinct surging origins per year).

Data source: see probe_hdx_asylum.py header (sha256 d5808616...).
Usage: python3 probe_hdx_asylum_labels.py [--csv path] [--min 500]
"""
import argparse
import csv
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = "/opt/data/cache/scratch/hdx/asylum_applications_residing_world.csv"


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--min", type=int, default=500)
    args = ap.parse_args()
    MIN = args.min

    rows = load(args.csv)

    # 1. duplicate dimension keys
    keycols = ["Year", "Country of Origin Code", "Country of Asylum Code",
               "Procedure Type", "Application Type Code", "Application Data Type"]
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[c] for c in keycols)].append(r)
    conflicts = 0
    identical = 0
    examples = []
    for k, g in groups.items():
        if len(g) > 1:
            counts = {x["Number of Applications"] for x in g}
            if len(counts) > 1:
                conflicts += 1
                if len(examples) < 5:
                    examples.append((k, sorted(counts)))
            else:
                identical += 1
    print(f"dup keys: groups={sum(1 for g in groups.values() if len(g)>1)} "
          f"conflicting-count={conflicts} identical-count={identical}")
    for k, c in examples:
        print("  conflict example:", k, "counts:", c)

    # stream G/P only, Application Type in {N, V} kept separate; sum across types
    # per (year, origin, asylum): applications are additive across application types.
    gp = [r for r in rows if r["Procedure Type"] == "G" and r["Application Data Type"] == "P"]
    panel = defaultdict(int)
    for r in gp:
        panel[(int(r["Year"]), r["Country of Origin Code"], r["Country of Asylum Code"])] += int(float(r["Number of Applications"]))
    print(f"G/P panel cells (year,origin,asylum): {len(panel)}; rows folded: {len(gp)}")

    years = sorted({k[0] for k in panel})
    origins = sorted({k[1] for k in panel})
    hosts = sorted({k[2] for k in panel})
    print(f"years {years[0]}..{years[-1]}, origins {len(origins)}, hosts {len(hosts)}")

    # 2. host-year reporting continuity
    host_years = defaultdict(set)
    for (y, o, a), v in panel.items():
        host_years[a].add(y)
    active_hosts = {y: sum(1 for a, ys in host_years.items() if y in ys) for y in years}
    print("hosts reporting per year:", {y: active_hosts[y] for y in years})

    # 3. eligibility and labels
    by_corridor_year = panel
    target_years = [y for y in years if y + 1 <= years[-1]]
    stats = defaultdict(Counter)
    n_elig = Counter()
    for y in target_years:
        corridors = {(o, a): v for (yy, o, a), v in by_corridor_year.items() if yy == y and v >= MIN}
        for (o, a), v in corridors.items():
            nxt = by_corridor_year.get((y + 1, o, a), 0)
            host_active = (y + 1) in host_years[a]
            n_elig[y] += 1
            bucket = "host_active" if host_active else "host_silent"
            stats[bucket]["n"] += 1
            stats[bucket]["decline"] += nxt < v
            stats[bucket]["grow25"] += nxt > 1.25 * v
            stats[bucket]["grow50"] += nxt > 1.5 * v
            stats[bucket]["x2"] += nxt >= 2 * v
            stats[bucket]["x3"] += nxt >= 3 * v
    print(f"\neligible corridors per year (>= {MIN} apps, G/P):", dict(sorted(n_elig.items())))
    for bucket, c in stats.items():
        n = c["n"]
        if n == 0:
            continue
        print(f"{bucket}: n={n} decline={c['decline']/n:.3f} grow25={c['grow25']/n:.3f} "
              f"grow50={c['grow50']/n:.3f} x2={c['x2']/n:.3f} x3={c['x3']/n:.3f}")

    # 4. candidate splits: eval-label years 2017-2021, holdout 2022-2025, train rest
    splits = {
        "train": [y for y in target_years if y + 1 <= 2016],
        "eval": [y for y in target_years if 2017 <= y + 1 <= 2021],
        "holdout": [y for y in target_years if y + 1 >= 2022],
    }
    for name, ys in splits.items():
        per_year_counts = {}
        for y in ys:
            corridors = {(o, a): v for (yy, o, a), v in by_corridor_year.items() if yy == y and v >= MIN}
            pos = 0
            pos_origins = set()
            n = 0
            for (o, a), v in corridors.items():
                if (y + 1) not in host_years[a]:
                    continue
                n += 1
                nxt = by_corridor_year.get((y + 1, o, a), 0)
                if nxt >= 2 * v:
                    pos += 1
                    pos_origins.add(o)
            per_year_counts[y] = (n, pos, len(pos_origins))
        tot_n = sum(x[0] for x in per_year_counts.values())
        tot_p = sum(x[1] for x in per_year_counts.values())
        tot_o = len(set().union(*[set() if False else set() for _ in []])) if False else None
        print(f"\nsplit {name}: label-years {ys}")
        for y, (n, p, po) in per_year_counts.items():
            print(f"  {y}->{y+1}: n={n} x2_pos={p} distinct_pos_origins={po}")
        print(f"  TOTAL n={tot_n} pos={tot_p}")

    # origin overlap across splits (independence flavour): top surge origins per split
    print("\ntop-10 surge origins by positive corridors, x2 label, host_active only:")
    for name, ys in splits.items():
        cnt = Counter()
        for y in ys:
            corridors = {(o, a): v for (yy, o, a), v in by_corridor_year.items() if yy == y and v >= MIN}
            for (o, a), v in corridors.items():
                if (y + 1) not in host_years[a]:
                    continue
                if by_corridor_year.get((y + 1, o, a), 0) >= 2 * v:
                    cnt[o] += 1
        print(f"  {name}: {cnt.most_common(10)}")


if __name__ == "__main__":
    main()
