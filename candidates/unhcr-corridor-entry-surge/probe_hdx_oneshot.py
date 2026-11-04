#!/usr/bin/env python3
"""One-shot per-corridor redesign probe (unhcr-corridor-entry-surge), 2026-11-04.

Measures, from the HDX global package asylum-applications CSV (G/P rows only,
sum-all rule per corridor-year, both validated in unhcr-refugee-data-finder),
whether the operator's recorded reopen shape - one example per corridor, taken
at the corridor's FIRST year >= 500 government-procedure applications - can
carry disjoint train/eval/holdout windows with both classes:

  - corridor entry years and their distribution over time
  - the doubling label on the entry year (total T0+1 >= 2 x total T0)
  - split capacity by entry-year window (one row per corridor)
  - pre-entry history depth / momentum-feature coverage (published T0-1 value)
  - host-silent censoring, live-edge 2025 entries, known-event fixtures
  - base rates for the alternative thresholds on the same one-shot population

No labels are shipped, no model is fit, no panel is constructed: counts only.

Usage: python3 candidates/unhcr-corridor-entry-surge/probe_hdx_oneshot.py \
          [--csv PATH] [--json PATH]
Default CSV path is the scratch download; re-fetch with the curl command in
notes.md (sha256 pinned there) to reproduce.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

SCRATCH_DEFAULT = os.path.expanduser(
    "/opt/data/cache/scratch/unhcr-oneshot-2026-11-04/asylum_applications_residing_world.csv"
)

# Entry-year windows: entry year T0 has label year T0+1, so these mirror the
# panel task's label-year windows (train 2001-2016 / eval 2017-2021 /
# holdout 2022-2025) shifted by one. Construction may re-draw boundaries
# BEFORE any score is seen; this probe measures capacity at these boundaries.
WINDOWS = {
    "train": (2000, 2015),
    "eval": (2016, 2020),
    "holdout": (2021, 2024),
}


def load_gp_totals(path):
    """Return (corridor -> {year: total}, host -> set(years active)) for G/P rows."""
    corridor = defaultdict(lambda: defaultdict(int))
    host_years = defaultdict(set)
    n_rows = n_kept = n_zero = 0
    years = set()
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            n_rows += 1
            if (row.get("Procedure Type") or "").strip() != "G":
                continue
            if (row.get("Application Data Type") or "").strip() != "P":
                continue
            n_kept += 1
            year = int(row["Year"])
            o = (row["Country of Origin Code"] or "").strip()
            h = (row["Country of Asylum Code"] or "").strip()
            try:
                n = int(row["Number of Applications"])
            except (TypeError, ValueError):
                continue
            if n == 0:
                n_zero += 1
            corridor[(o, h)][year] += n
            host_years[h].add(year)
            years.add(year)
    return corridor, host_years, dict(n_rows=n_rows, n_kept=n_kept,
                                      n_zero=n_zero, year_min=min(years),
                                      year_max=max(years))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=SCRATCH_DEFAULT)
    ap.add_argument("--json", help="write measurements JSON here")
    args = ap.parse_args(argv)

    corridor, host_years, shape = load_gp_totals(args.csv)
    out: dict = {"shape": shape}

    # ---- entry years ------------------------------------------------------
    entries = {}  # corridor -> (T0, total_T0)
    for key, series in corridor.items():
        for y in sorted(series):
            if series[y] >= 500:
                entries[key] = (y, series[y])
                break
    out["corridors_gp_any"] = len(corridor)
    out["corridors_ever_ge500"] = len(entries)

    by_entry_year = defaultdict(list)
    for key, (t0, tot) in entries.items():
        by_entry_year[t0].append(key)
    out["entries_by_year"] = {y: len(v) for y, v in sorted(by_entry_year.items())}

    # ---- labeled one-shot population -------------------------------------
    # Eligible: T0 <= 2024 (label year T0+1 <= 2025 is published in this vintage)
    # and host active in T0+1 (the panel task's censoring rule: host silent in
    # the label year => unobserved target, excluded).
    rows = []
    excluded = {"entry_2025_live_edge": 0, "host_silent_t0_plus_1": 0}
    for key, (t0, tot_t0) in entries.items():
        if t0 >= 2025:
            excluded["entry_2025_live_edge"] += 1
            continue
        o, h = key
        if (t0 + 1) not in host_years[h]:
            excluded["host_silent_t0_plus_1"] += 1
            continue
        series = corridor[key]
        tot_t1 = series.get(t0 + 1, 0)  # host active => observed zero
        # pre-entry history
        prior_years = [y for y in series if y < t0]
        first_seen = min(series) if series else t0
        rows.append({
            "origin": o, "host": h, "t0": t0, "tot_t0": tot_t0, "tot_t1": tot_t1,
            "label_2x": tot_t1 >= 2 * tot_t0,
            "label_15x": tot_t1 >= 1.5 * tot_t0,
            "label_3x": tot_t1 >= 3 * tot_t0,
            "decline": tot_t1 < tot_t0,
            "n_prior_years": len(prior_years),
            "has_prior_value": bool(prior_years),
            "prior_t0m1": series.get(t0 - 1),
            "corridor_age_at_entry": t0 - first_seen,
        })
    out["excluded"] = excluded
    out["labeled_one_shot_rows"] = len(rows)

    # ---- momentum-feature coverage (published T0-1 corridor value) --------
    with_prior = [r for r in rows if r["has_prior_value"]]
    out["momentum_coverage"] = {
        "with_any_prior_year": len(with_prior),
        "with_t0m1_published": sum(1 for r in rows if r["prior_t0m1"] is not None),
        "with_2plus_prior_years": sum(1 for r in rows if r["n_prior_years"] >= 2),
        "left_censored_t0_2000": sum(1 for r in rows if r["t0"] == 2000),
    }

    # ---- base rates on the one-shot population -----------------------------
    n = len(rows)
    def rate(key):
        return round(sum(1 for r in rows if r[key]) / n, 4) if n else None
    out["base_rates_one_shot"] = {
        "n": n, "decline": rate("decline"), "grow_25": None, "label_15x": rate("label_15x"),
        "label_2x": rate("label_2x"), "label_3x": rate("label_3x"),
    }

    # ---- split capacity -----------------------------------------------------
    def window_of(t0):
        for name, (lo, hi) in WINDOWS.items():
            if lo <= t0 <= hi:
                return name
        return None

    splits = {}
    for wname, (lo, hi) in WINDOWS.items():
        wrows = [r for r in rows if lo <= r["t0"] <= hi]
        wrows_m = [r for r in wrows if r["prior_t0m1"] is not None]
        pos = sum(1 for r in wrows if r["label_2x"])
        pos_m = sum(1 for r in wrows_m if r["label_2x"])
        origins = {r["origin"] for r in wrows}
        origin_years = {(r["origin"], r["t0"]) for r in wrows}
        both_classes_by_year = all(
            (any(r["label_2x"] for r in wrows if r["t0"] == y) and
             any(not r["label_2x"] for r in wrows if r["t0"] == y))
            for y in range(lo, min(hi, 2024) + 1) if any(r["t0"] == y for r in wrows)
        )
        splits[wname] = {
            "entry_years": [lo, hi],
            "rows": len(wrows), "positives_2x": pos,
            "prevalence": round(pos / len(wrows), 4) if wrows else None,
            "rows_with_t0m1": len(wrows_m), "positives_2x_with_t0m1": pos_m,
            "distinct_origins": len(origins),
            "origin_entryyear_clusters": len(origin_years),
            "positives_per_entry_year": {
                str(y): sum(1 for r in wrows if r["t0"] == y and r["label_2x"])
                for y in range(lo, hi + 1)
            },
            "both_classes_every_entry_year": both_classes_by_year,
        }
    out["split_capacity_2x"] = splits

    # ---- momentum association (source-side, no model) -----------------------
    # Positive rate by growth INTO entry (T0-1 -> T0), among rows with T0-1.
    mom = [r for r in rows if r["prior_t0m1"]]
    buckets = {"lt_1.5x": [], "1.5x_to_3x": [], "gt_3x": [], "new_530": []}
    for r in mom:
        growth = r["tot_t0"] / r["prior_t0m1"]
        if growth > 3:
            buckets["gt_3x"].append(r)
        elif growth >= 1.5:
            buckets["1.5x_to_3x"].append(r)
        else:
            buckets["lt_1.5x"].append(r)
    # entrants with NO prior published year at all
    noprior = [r for r in rows if not r["has_prior_value"]]
    buckets["new_530"] = noprior
    out["momentum_association"] = {
        k: {"n": len(v),
            "pos_2x": sum(1 for r in v if r["label_2x"]),
            "prevalence": round(sum(1 for r in v if r["label_2x"]) / len(v), 4) if v else None}
        for k, v in buckets.items()
    }

    # ---- fixtures ------------------------------------------------------------
    def fixture(o, h):
        key = (o, h)
        if key not in entries:
            return {"corridor": f"{o}->{h}", "never_crossed_500": True}
        t0, tot = entries[key]
        r = next((x for x in rows if x["origin"] == o and x["host"] == h), None)
        if r is None:
            return {"corridor": f"{o}->{h}", "t0": t0, "tot_t0": tot, "excluded_or_live": True}
        return {"corridor": f"{o}->{h}", "t0": t0, "tot_t0": r["tot_t0"],
                "tot_t1": r["tot_t1"], "label_2x": r["label_2x"],
                "prior_t0m1": r["prior_t0m1"]}
    out["fixtures"] = [fixture("SYR", "DEU"), fixture("AFG", "USA"),
                       fixture("AFG", "DEU"), fixture("VEN", "COL"),
                       fixture("UKR", "POL"), fixture("TUR", "ITA")]

    # ---- live edge (entries 2025: label year 2026 unpublished) ----------------
    live = [(key, entries[key]) for key in entries if entries[key][0] == 2025]
    out["live_edge_2025_entries"] = {
        "n": len(live),
        "top_by_t0_total": [
            {"corridor": f"{o}->{h}", "tot_2025": tot}
            for (o, h), (t0, tot) in sorted(live, key=lambda kv: -kv[1][1])[:10]
        ],
    }

    payload = json.dumps(out, indent=1, sort_keys=True)
    print(payload)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
