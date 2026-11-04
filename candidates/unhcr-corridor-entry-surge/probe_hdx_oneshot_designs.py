#!/usr/bin/env python3
"""Design-sensitivity probe (unhcr-corridor-entry-surge), 2026-11-04.

The capacity probe measured the one-shot redesign at the recorded eligibility
(>=500) with the house 2x next-year label and found eval/holdout positives just
under the qualification gate's minimum (30 positives, 20 distinct events, both
enforced on eval and holdout). This probe measures, on the same pinned CSV and
the same one-shot population definition, how the operator's two recorded reopen
shapes and the eligibility threshold change that capacity:

  label families (all decided at prediction instant, before any score):
    next1_2x   total(T0+1) >= 2.0 x total(T0)     [house family]
    next1_15x  total(T0+1) >= 1.5 x total(T0)
    next1_g25  total(T0+1) >= 1.25 x total(T0)
    next1_3x   total(T0+1) >= 3.0 x total(T0)
    cum2_2x    total(T0+1) + total(T0+2) >= 2.0 x total(T0)  [aggregate outcome]

  eligibility thresholds: 500 (recorded), 400, 300, 250, 200

For every combination it reports, per window (entry-year windows mirroring the
panel task's label-year windows shifted by one), the row count, positives,
prevalence and the conservative independent-event count (distinct origin|entry-
year among POSITIVE rows - the gate's event metric). No labels shipped, no
model, counts only.

Usage: python3 candidates/unhcr-corridor-entry-surge/probe_hdx_oneshot_designs.py \
          [--csv PATH] [--json PATH]
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

WINDOWS_NEXT1 = {  # entry years; label year = T0+1
    "train": (2000, 2015),
    "eval": (2016, 2020),
    "holdout": (2021, 2024),
}
WINDOWS_CUM2 = {  # entry years; outcome years = T0+1..T0+2 (max published 2025)
    "train": (2000, 2014),
    "eval": (2015, 2020),
    "holdout": (2021, 2023),
}

LABELS = {
    "next1_2x": lambda t0v, t1v, t2v: t1v >= 2.0 * t0v,
    "next1_15x": lambda t0v, t1v, t2v: t1v >= 1.5 * t0v,
    "next1_g25": lambda t0v, t1v, t2v: t1v >= 1.25 * t0v,
    "next1_3x": lambda t0v, t1v, t2v: t1v >= 3.0 * t0v,
    "cum2_2x": lambda t0v, t1v, t2v: (t1v + t2v) >= 2.0 * t0v,
}


def load_gp_totals(path):
    corridor = defaultdict(lambda: defaultdict(int))
    host_years = defaultdict(set)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if (row.get("Procedure Type") or "").strip() != "G":
                continue
            if (row.get("Application Data Type") or "").strip() != "P":
                continue
            try:
                n = int(row["Number of Applications"])
            except (TypeError, ValueError):
                continue
            year = int(row["Year"])
            key = ((row["Country of Origin Code"] or "").strip(),
                   (row["Country of Asylum Code"] or "").strip())
            corridor[key][year] += n
            host_years[key[1]].add(year)
    return corridor, host_years


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=SCRATCH_DEFAULT)
    ap.add_argument("--json")
    args = ap.parse_args(argv)

    corridor, host_years = load_gp_totals(args.csv)

    def corridor_year_total(key, year):
        """Observed total; 0 when the host reports that year but the corridor
        has no row (the record's observed-zero rule)."""
        o, h = key
        if year in host_years[h]:
            return corridor[key].get(year, 0)
        return None  # host silent => unobserved

    out: dict = {"designs": {}}

    for threshold in (500, 400, 300, 250, 200):
        # entries at this threshold
        entries = {}
        for key, series in corridor.items():
            for y in sorted(series):
                if series[y] >= threshold:
                    entries[key] = y
                    break
        for label_name, label_fn in LABELS.items():
            windows = WINDOWS_CUM2 if label_name == "cum2_2x" else WINDOWS_NEXT1
            design = {"threshold": threshold, "label": label_name,
                      "windows": {k: list(v) for k, v in windows.items()},
                      "splits": {}, "excluded": {
                          "entry_at_or_after_last_outcome_year": 0,
                          "host_silent_outcome_year": 0}}
            rows = []
            for key, t0 in entries.items():
                o, h = key
                max_outcome_year = 2025 if label_name != "cum2_2x" else 2024
                # cum2 needs T0+2 <= 2025 => T0 <= 2023; next1 needs T0 <= 2024
                last_outcome_year = t0 + (2 if label_name == "cum2_2x" else 1)
                if last_outcome_year > 2025:
                    design["excluded"]["entry_at_or_after_last_outcome_year"] += 1
                    continue
                vals = []
                unobserved = False
                for yy in range(t0 + 1, last_outcome_year + 1):
                    v = corridor_year_total(key, yy)
                    if v is None:
                        unobserved = True
                        break
                    vals.append(v)
                if unobserved:
                    design["excluded"]["host_silent_outcome_year"] += 1
                    continue
                t0v = corridor[key][t0]
                t1v = vals[0] if vals else 0
                t2v = vals[1] if len(vals) > 1 else 0
                rows.append({"origin": o, "host": h, "t0": t0, "pos": label_fn(t0v, t1v, t2v)})
            for wname, (lo, hi) in windows.items():
                wrows = [r for r in rows if lo <= r["t0"] <= hi]
                pos_rows = [r for r in wrows if r["pos"]]
                events = len({f"{r['origin']}|{r['t0']}" for r in pos_rows})
                design["splits"][wname] = {
                    "rows": len(wrows),
                    "positives": len(pos_rows),
                    "prevalence": round(len(pos_rows) / len(wrows), 4) if wrows else None,
                    "distinct_events_among_positives": events,
                    "gate_ok_30_20": len(pos_rows) >= 30 and events >= 20,
                }
            out["designs"][f"elig{threshold}_{label_name}"] = design

    # ---- momentum association for every label family at elig 500 -----------
    # The operator's reopen condition requires the redesign to KEEP corridor
    # momentum; this measures, source-side and without any model, whether the
    # pre-entry momentum signal still separates each candidate label, as it did
    # for the dropped panel task's next-year label (capacity probe).
    entries500 = {}
    for key, series in corridor.items():
        for y in sorted(series):
            if series[y] >= 500:
                entries500[key] = y
                break
    base_rows = []
    for key, t0 in entries500.items():
        o, h = key
        t0v = corridor[key][t0]
        t1 = corridor_year_total(key, t0 + 1)
        t2 = corridor_year_total(key, t0 + 2)
        base_rows.append({"origin": o, "t0": t0, "tot_t0": t0v,
                          "prior": corridor[key].get(t0 - 1),
                          "t1": t1, "t2": t2})
    assoc = {}
    for label_name, label_fn in LABELS.items():
        need_t2 = label_name == "cum2_2x"
        mom_rows = []
        for r in base_rows:
            if r["t0"] + (2 if need_t2 else 1) > 2025:
                continue
            t1, t2 = r["t1"], r["t2"]
            if t1 is None or (need_t2 and t2 is None):
                continue  # host silent in an outcome year: unobserved
            mom_rows.append({**r, "pos": label_fn(r["tot_t0"], t1 or 0, t2 or 0)})
        buckets = {"growth_into_entry_gt_3x": [], "growth_into_entry_1.5x_to_3x": [],
                   "growth_into_entry_lt_1.5x": [], "no_published_prior_year": []}
        for r in mom_rows:
            if not r["prior"]:
                buckets["no_published_prior_year"].append(r)
            else:
                growth = r["tot_t0"] / r["prior"]
                if growth > 3:
                    buckets["growth_into_entry_gt_3x"].append(r)
                elif growth >= 1.5:
                    buckets["growth_into_entry_1.5x_to_3x"].append(r)
                else:
                    buckets["growth_into_entry_lt_1.5x"].append(r)
        assoc[label_name] = {
            k: {"n": len(v), "positives": sum(1 for x in v if x["pos"]),
                "prevalence": round(sum(1 for x in v if x["pos"]) / len(v), 4) if v else None}
            for k, v in buckets.items()}
    out["momentum_association_by_label"] = assoc
    out["momentum_association_note"] = (
        "positive rate by growth INTO the entry year (T0-1 -> T0) among corridors "
        "with a published T0-1 value, per label family, eligibility 500; "
        "no_published_prior_year is the left-censored/first-observed set. A "
        "MONOTONE-INCREASING profile keeps the panel task's momentum-continuation "
        "phenomenon; a flat or inverted profile means the label is dominated by "
        "mean reversion instead.")

    # per-entry-year positives for the two leading designs (both-classes check)
    per_year: dict = defaultdict(lambda: defaultdict(lambda: {"rows": 0, "pos": 0}))
    for label_name in ("next1_2x", "next1_15x", "next1_g25", "cum2_2x"):
        need_t2 = label_name == "cum2_2x"
        for r in base_rows:
            if r["t0"] + (2 if need_t2 else 1) > 2025:
                continue
            t1, t2 = r["t1"], r["t2"]
            if t1 is None or (need_t2 and t2 is None):
                continue
            y = str(r["t0"])
            per_year[label_name][y]["rows"] += 1
            per_year[label_name][y]["pos"] += int(
                LABELS[label_name](r["tot_t0"], t1 or 0, t2 or 0))
    out["per_entry_year_by_label"] = {k: {y: v for y, v in sorted(d.items())}
                                      for k, d in per_year.items()}

    # ---- capacity under the parent's momentum-feature eligibility -----------
    # The dropped panel task's construction required a published year-D-1
    # corridor value (the momentum feature family needs it). If the one-shot
    # build repeats that rule, the population shrinks by the rows without a
    # published T0-1 value (left-censored T0=2000 entrants plus corridors first
    # observed at their crossing year). Measure gate capacity for the viable
    # label families under that restriction.
    with_prior: dict = {}
    for label_name in ("next1_15x", "next1_g25", "cum2_2x"):
        need_t2 = label_name == "cum2_2x"
        windows = WINDOWS_CUM2 if need_t2 else WINDOWS_NEXT1
        splits = {}
        for wname, (lo, hi) in windows.items():
            n_rows = n_pos = 0
            events = set()
            for r in base_rows:
                if not r["prior"]:
                    continue
                if r["t0"] + (2 if need_t2 else 1) > 2025:
                    continue
                t1, t2 = r["t1"], r["t2"]
                if t1 is None or (need_t2 and t2 is None):
                    continue
                if not (lo <= r["t0"] <= hi):
                    continue
                pos = LABELS[label_name](r["tot_t0"], t1 or 0, t2 or 0)
                n_rows += 1
                if pos:
                    n_pos += 1
                    events.add(f"{r['origin']}|{r['t0']}")
            splits[wname] = {"rows": n_rows, "positives": n_pos,
                             "distinct_events_among_positives": len(events),
                             "gate_ok_30_20": n_pos >= 30 and len(events) >= 20}
        with_prior[label_name] = splits
    out["capacity_with_published_t0m1"] = with_prior

    # print a compact decision table

    hdr = f"{'design':24s} {'eval rows/pos/ev':>18s} {'holdout rows/pos/ev':>20s} gate"
    print(hdr)
    for name, d in out["designs"].items():
        e, h = d["splits"].get("eval", {}), d["splits"].get("holdout", {})
        ok = e.get("gate_ok_30_20") and h.get("gate_ok_30_20")
        print(f"{name:24s} {e.get('rows','-'):>6}/{e.get('positives','-'):>3}/{e.get('distinct_events_among_positives','-'):>3}"
              f" {h.get('rows','-'):>8}/{h.get('positives','-'):>3}/{h.get('distinct_events_among_positives','-'):>3}"
              f" {'PASS' if ok else 'fail'}")
    payload = json.dumps(out, indent=1, sort_keys=True)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(payload)
    print("\nfull JSON written" if args.json else payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
