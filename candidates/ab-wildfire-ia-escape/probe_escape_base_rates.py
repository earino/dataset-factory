#!/usr/bin/env python3
"""Discovery probe: Alberta historical wildfire per-fire record (2006-2025).

Source file: fp-historical-wildfire-data-2006-2025.csv
  URL: https://open.alberta.ca/dataset/a221e7a0-4f46-4be7-9c5a-e29de9a3447e/resource/80480824-0c50-456c-9723-f9d4fc136141/download/fp-historical-wildfire-data-2006-2025.csv
  Licence: Open Government Licence - Alberta (see record license_evidence)
  Downloaded 2026-11-06 through the real browser (open.alberta.ca sits behind a
  Cloudflare managed challenge for plain HTTP clients; curl 403 cf-mitigated:
  challenge measured first, so the fetch below is the documented fallback).
  sha256 of the pinned local copy is asserted at runtime; the pinned copy lives
  at scratch/ab-wildfire/ (coordinator) and is re-downloadable via the browser
  procedure above if lost.

Measurements (all computed from the pinned CSV; no sampling):
  1. row counts per year
  2. prediction-instant ordering: assessment_datetime vs discovered/reported/
     start/dispatch timestamps
  3. feature-field coverage per split window
  4. escape base rates at candidate thresholds, per split window
  5. containment (assessment -> first under control) duration distribution
  6. clustered positive counts (distinct assessment dates of positives)
  7. provenance mix: detection agent type per year (population composition)
  8. uniqueness of (YEAR, FIRE_NUMBER)
  9. label-consistency: SIZE_CLASS vs CURRENT_SIZE thresholds

Usage: python3 probe_escape_base_rates.py <csv-path> <out-json>
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else \
    "/opt/data/cache/scratch/ab-wildfire/fp-historical-wildfire-data-2006-2025.csv"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "probe_escape_base_rates_result.json"
SHA256_EXPECTED = "8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72"

WINDOWS = {"train": range(2006, 2016), "eval": range(2016, 2021), "holdout": range(2021, 2026)}
DT_FORMATS = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]


def parse_dt(v):
    v = (v or "").strip()
    if not v:
        return None
    for fmt in DT_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return "UNPARSED"


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    import hashlib
    h = hashlib.sha256(open(CSV_PATH, "rb").read()).hexdigest()
    assert h == SHA256_EXPECTED, f"pinned CSV hash changed: {h}"

    rows = list(csv.DictReader(open(CSV_PATH, newline="", encoding="utf-8-sig")))
    out = {"sha256_csv": h, "n_rows": len(rows)}

    # 1. per-year counts
    per_year = Counter(int(r["YEAR"]) for r in rows)
    out["per_year_counts"] = dict(sorted(per_year.items()))

    # 2. instant ordering
    keys = ["DISCOVERED_DATE", "REPORTED_DATE", "FIRE_START_DATE", "DISPATCH_DATE",
            "START_FOR_FIRE_DATE"]
    order = {}
    gaps = defaultdict(list)
    unparsed = Counter()
    for k in keys:
        before = after = missing = 0
        for r in rows:
            a = parse_dt(r["ASSESSMENT_DATETIME"])
            b = parse_dt(r.get(k, ""))
            if a == "UNPARSED" or b == "UNPARSED":
                unparsed[k] += 1
                continue
            if a is None or b is None:
                missing += 1
                continue
            if b <= a:
                before += 1
            else:
                after += 1
                if k in ("REPORTED_DATE", "FIRE_START_DATE"):
                    gaps[k].append((a - b).total_seconds())
        n_cmp = before + after
        order[k] = {"at_or_before_assessment": before, "after_assessment": after,
                    "missing": missing, "unparsed": unparsed[k],
                    "frac_at_or_before": round(before / n_cmp, 4) if n_cmp else None}
        if gaps[k]:
            gs = sorted(gaps[k])
            order[k]["median_gap_hours_when_after"] = round(
                gs[len(gs) // 2] / 3600.0, 2)
    out["instant_ordering_vs_assessment"] = order
    out["unparsed_datetime_counts"] = dict(unparsed)

    # 3. feature coverage per window
    feature_cols = ["ASSESSMENT_DATETIME", "ASSESSMENT_HECTARES", "FIRE_SPREAD_RATE",
                    "FIRE_TYPE", "FIRE_POSITION_ON_SLOPE", "WEATHER_CONDITIONS_OVER_FIRE",
                    "TEMPERATURE", "RELATIVE_HUMIDITY", "WIND_DIRECTION", "WIND_SPEED",
                    "FUEL_TYPE", "DETECTION_AGENT_TYPE", "DETECTION_AGENT",
                    "DISCOVERED_DATE", "REPORTED_DATE", "FIRE_START_DATE", "LATITUDE",
                    "LONGITUDE", "FIRE_ORIGIN", "RESPONSIBLE_GROUP", "ACTIVITY_CLASS"]
    cov = {}
    for wname, yrs in WINDOWS.items():
        wrows = [r for r in rows if int(r["YEAR"]) in yrs]
        cov[wname] = {"n": len(wrows)}
        for c in feature_cols:
            filled = sum(1 for r in wrows if (r.get(c) or "").strip() != "")
            cov[wname][c] = round(filled / len(wrows), 4)
    out["feature_coverage_by_window"] = cov

    # 4. escape base rates per window
    thresholds = [4, 10, 40, 100, 200, 1000]
    esc = {}
    for wname, yrs in WINDOWS.items():
        wrows = [r for r in rows if int(r["YEAR"]) in yrs]
        esc[wname] = {"n": len(wrows)}
        for th in thresholds:
            pos = [r for r in wrows if (fnum(r["CURRENT_SIZE"]) or 0) >= th]
            # 6. clustered: distinct (year, date) of positives
            dates = set()
            for r in pos:
                a = parse_dt(r["ASSESSMENT_DATETIME"])
                d = r["ASSESSMENT_DATETIME"][:10] if r.get("ASSESSMENT_DATETIME") else "?"
                dates.add((r["YEAR"], d))
            esc[wname][f"ge_{th}ha"] = {
                "positives": len(pos), "rate": round(len(pos) / len(wrows), 4),
                "distinct_assessment_dates": len(dates)}
    out["escape_base_rates"] = esc

    # 5. containment duration: assessment -> first under control
    dur = []
    for r in rows:
        a = parse_dt(r["ASSESSMENT_DATETIME"])
        u = parse_dt(r["FIRST_UC_DATE"])
        if isinstance(a, datetime) and isinstance(u, datetime) and u >= a:
            dur.append((u - a).total_seconds() / 3600.0)
    dur.sort()
    n = len(dur)
    out["assessment_to_uc_hours"] = {
        "n": n,
        "median": round(dur[n // 2], 2),
        "p90": round(dur[int(n * 0.9)], 2),
        "gt_24h": sum(1 for d in dur if d > 24) / n,
        "gt_48h": sum(1 for d in dur if d > 48) / n,
        "gt_72h": sum(1 for d in dur if d > 72) / n,
        "gt_168h": sum(1 for d in dur if d > 168) / n,
    }
    # per-window containment>72h counts
    cont = {}
    for wname, yrs in WINDOWS.items():
        wrows = [r for r in rows if int(r["YEAR"]) in yrs]
        pos = neg = bad = 0
        for r in wrows:
            a = parse_dt(r["ASSESSMENT_DATETIME"])
            u = parse_dt(r["FIRST_UC_DATE"])
            if isinstance(a, datetime) and isinstance(u, datetime) and u >= a:
                if (u - a).total_seconds() / 3600.0 > 72:
                    pos += 1
                else:
                    neg += 1
            else:
                bad += 1
        cont[wname] = {"n": len(wrows), "pos_gt72h": pos, "neg": neg,
                       "unusable_order": bad}
    out["containment_gt72h_by_window"] = cont

    # 7. provenance mix: detection agent type per year
    mix = defaultdict(dict)
    for y in sorted(per_year):
        yrows = [r for r in rows if int(r["YEAR"]) == y]
        c = Counter(r["DETECTION_AGENT_TYPE"] for r in yrows)
        mix[y] = {k: round(v / len(yrows), 3) for k, v in c.most_common()}
    out["detection_agent_type_share_by_year"] = mix

    # 8. uniqueness
    ids = Counter((r["YEAR"], r["FIRE_NUMBER"]) for r in rows)
    out["dup_year_fire_number"] = sum(1 for v in ids.values() if v > 1)

    # 9. SIZE_CLASS vs CURRENT_SIZE consistency
    bounds = {"A": (0.0, 0.1), "B": (0.1, 4.0), "C": (4.0, 40.0), "D": (40.0, 200.0),
              "E": (200.0, float("inf"))}
    bad = 0
    for r in rows:
        s, sz = r["SIZE_CLASS"], fnum(r["CURRENT_SIZE"])
        if s in bounds and sz is not None:
            lo, hi = bounds[s]
            if not (lo <= sz <= hi if s != "A" else lo <= sz < 0.1 or (abs(sz - 0.1) < 1e-9)):
                bad += 1
    out["size_class_inconsistencies"] = bad

    # extra: zero-size rows and assessment==UC (assessed already under control) share
    out["current_size_zero_rows"] = sum(1 for r in rows if (fnum(r["CURRENT_SIZE"]) or -1) == 0)
    aeq = 0
    for r in rows:
        a, u = parse_dt(r["ASSESSMENT_DATETIME"]), parse_dt(r["FIRST_UC_DATE"])
        if isinstance(a, datetime) and isinstance(u, datetime) and a == u:
            aeq += 1
    out["assessed_already_under_control"] = aeq

    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(json.dumps({k: out[k] for k in ("n_rows", "dup_year_fire_number",
                                          "size_class_inconsistencies")}, indent=1))
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
