#!/usr/bin/env python3
"""Construction script for the `abs-visitor-arrivals-direction` candidate.

Task: the ABS Overseas Arrivals and Departures release for reference month M has
just been published (the prediction instant). For a country of residence, will
short-term visitor arrivals to Australia in the first month not yet published,
M+1, fall short of the same calendar month one year earlier?

Where this runs
---------------
On a temporary worker: one anonymous GET of the full OAD_COUNTRY panel
(3,308,454 bytes measured 2026-10-22, SDMX 2.1 CSV) plus the dataflow structure
(~101 KB) for the country codelist. `--panel-file` / `--structure-file` accept
local copies for a full-assertion dry run on the coordinator-class machine.

Frame rules (from the candidate record; each is measured and reported)
----------------------------------------------------------------------
* Grain: one row per (COUNTRY_RESID, target month T) on the CAT_TRAVELLER=06
  "Short-term Visitors arriving" series, TSEST=10 (Original only - the
  structure codelist carries 20/30/40/50 but the dataflow serves only 10, so
  seasonality must be learned, and no seasonally adjusted column can leak the
  label). The 05 "Residents returning" stream ships in the same CSV; it is
  counted in the provenance mix and not used.
* Label: fell_short = 1 iff OBS_VALUE(T) < OBS_VALUE(T-12); an exact tie is 0
  ("did not fall short"), counted separately as flat. Both label source
  columns - the target month's value and the year-earlier value - are excluded
  from the shipped columns (recorded in label_source_columns, asserted absent
  from every written header). Note val(T-12) is the year-earlier level of the
  target month: it is required to exist for the label but never ships.
* Prediction instant: the publication of the OAD release for month M = T-1,
  which the record measured at a maximum observed lag of 43 days after month
  end (Aug 2026 released 2026-10-13; Jul 2026 released 2026-09-11; Apr 2026
  released 2026-06-12). Features use published months <= M only. Only the
  current vintage is downloadable (ABS revises after linked Medicare data
  arrives - the record's revision note), so feature values are stated as
  current-vintage and the cutoff is a documented assumption.
* Features: visitor-arrivals levels at M, M-1, M-2, M-3, M-6 and M-12 (all
  strictly before the target month), four differences among them (the M-vs-
  M-12 difference is the persistence analogue: the YoY sign observed at M),
  country identity and the target calendar (year, month number). Row
  eligibility needs the six feature months present; a row whose label inputs
  (T, T-12) are missing is *missing outcome data*, counted in
  unobserved_target and excluded - never a silent drop.
* Splits (target-month windows, the record's candidate partition):
  train 1992-02..2014-12 (the first month with 13 months of panel history;
  the panel starts 1991-01), eval 2015-01..2019-12, holdout 2022-01..panel
  max. Target months 2020-01..2021-12 are excluded as pandemic extremes -
  the border was closed and the YoY sign is degenerate - and counted with
  their label texture; their *values* remain legitimate feature history for
  2022 rows (published before those rows' prediction instants).
* Event key: target_month. Positives cluster in calendar time (shared
  Australian conditions - shocks, seasons, capacity - move many countries'
  YoY signs together; the record's known events are exactly such months), so
  the conservative independent-event count is the number of distinct target
  months carrying a positive, not the row count.
* Known-event fixtures (recorded in the candidate record, verified in-panel at
  discovery): the March 2020 border closure makes 2020 target months
  overwhelmingly "short" (down share >= 0.75 asserted); the reopening from
  November 2021 makes 2022 overwhelmingly "not short" (up share >= 0.75).

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: ABS website material is CC BY 4.0 International (class A, recorded
in the candidate record's license_evidence); attribution "Source: Australian
Bureau of Statistics" / "Based on ABS data" carries through to any release.
Derived research dataset - never the ABS's official product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NAME = "abs-visitor-arrivals-direction"
TARGET = "fell_short"
POSITIVE_LABEL = 1

PANEL_URL = ("https://data.api.abs.gov.au/rest/data/ABS,OAD_COUNTRY,1.0.0/all"
             "?format=csv&startPeriod=1991-01")
STRUCTURE_URL = "https://data.api.abs.gov.au/rest/dataflow/ABS/OAD_COUNTRY?references=all"

# Traveller category shipped as the task series (06 = short-term visitors
# arriving; 05 = residents returning, counted in the provenance mix only).
VISITOR_CAT = "06"
RESIDENT_CAT = "05"

# Months before the target month T for each shipped level feature.
FEATURE_OFFSETS = {
    "val_m": 1,      # last published month M = T-1
    "val_m1": 2,     # M-1
    "val_m2": 3,     # M-2
    "val_m3": 4,     # M-3
    "val_m6": 7,     # M-6
    "val_m12": 13,   # M-12 (the YoY comparison observed at M)
}
YOY_LAG = 12         # label compares T with T-12

# Shipped layout: id, features, carry, target.
ID_COLUMNS = ["row_id"]
FEATURES = ["country_resid", "target_year", "target_month_num",
            "val_m", "val_m1", "val_m2", "val_m3", "val_m6", "val_m12",
            "diff_mom", "diff_quarter", "diff_half", "diff_yoy_m"]
CARRY_COLUMNS = ["target_month"]
HIGH_CARDINALITY = ["row_id"]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# Split windows in target months. Train starts at the first month carrying the
# required 13 months of panel history (panel begins 1991-01). The pandemic
# window is excluded and counted, never silently dropped.
TRAIN_START, TRAIN_END = "1992-02", "2014-12"
EVAL_START, EVAL_END = "2015-01", "2019-12"
PANDEMIC_START, PANDEMIC_END = "2020-01", "2021-12"
HOLDOUT_START = "2022-01"
MIN_PANEL_MONTH = "2026-08"     # measured vintage coverage at discovery (2026-10-22)

MIN_SPLIT_POSITIVES = 30        # gate threshold: eval/holdout scorable positives
MIN_SPLIT_EVENTS = 20           # gate threshold: distinct positive event months
KNOWN_EVENT_MIN_SHARE = 0.75    # border closure / reopening texture floor

PREDICTION_TIME = (
    "The publication instant of the ABS Overseas Arrivals and Departures (OAD) "
    "release for reference month M, observed at a maximum of 43 days after "
    "month end (Aug 2026 released 2026-10-13, Jul 2026 released 2026-09-11, "
    "Apr 2026 released 2026-06-12; all 11:30am local). At that instant every "
    "month <= M is published and month M+1 - the target month - is the first "
    "unpublished month. Features are published series values for months <= M "
    "only; the target month's value and its year-earlier level never ship.")
PREDICTION_QUESTION = (
    "The OAD release for reference month M has just been published. For a "
    "country of residence, will short-term visitor arrivals to Australia in "
    "the first month not yet published (M+1) fall short of the same calendar "
    "month one year earlier?")


def log(message: str) -> None:
    print(message, flush=True)


def month_index(text: str) -> int:
    year, month = text.split("-")
    return int(year) * 12 + int(month) - 1


def month_from_index(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, dest: Path) -> dict:
    started = time.time()
    request = urllib.request.Request(url, headers={"User-Agent": "dataset-factory/abs-build"})
    with urllib.request.urlopen(request, timeout=300) as response:
        last_modified = response.headers.get("Last-Modified")
        with dest.open("wb") as handle:
            size = 0
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                handle.write(chunk)
                size += len(chunk)
    return {"url": url, "bytes": size, "last_modified": last_modified,
            "seconds": round(time.time() - started, 1),
            "sha256": sha256_file(dest)}


def fmt_num(value: float) -> str:
    """Integral floats print without a decimal tail; others keep 6 decimals."""
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def parse_country_names(structure_path: Path) -> dict[str, str]:
    """Code -> name for CL_OAD_ARRIVALS_COUNTRY from the SDMX structure XML."""
    names: dict[str, str] = {}
    for _, element in ET.iterparse(str(structure_path), events=("end",)):
        if element.tag.endswith("Codelist") and element.get("id") == "CL_OAD_ARRIVALS_COUNTRY":
            for node in element.iter():
                if not node.tag.endswith("Code"):
                    continue
                for child in node.iter():
                    if child.tag.endswith("Name") and (child.text or "").strip():
                        names[node.get("id")] = child.text.strip()
                        break
            element.clear()
    return names


def load_panel(path: Path) -> tuple[dict[str, dict[int, float]], dict]:
    """Read the SDMX CSV into {country: {month_index: value}} plus the
    provenance mix of every categorical column (the discovery skill's rule:
    count the mix before deciding what a row means)."""
    values: dict[str, dict[int, float]] = defaultdict(dict)
    mix: dict[str, Counter] = {key: Counter() for key in
                               ("CAT_TRAVELLER", "TSEST", "FREQ",
                                "OBS_STATUS", "UNIT_MEASURE")}
    countries_all: set[str] = set()
    countries_by_cat: dict[str, set[str]] = {VISITOR_CAT: set(), RESIDENT_CAT: set()}
    rows = 0
    missing_obs = 0
    non_integer = 0
    comment_nonempty = 0
    months_seen: set[int] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"panel CSV has no header: {path}")
        reader.fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
        for row in reader:
            rows += 1
            for key in mix:
                mix[key][(row.get(key) or "").strip()] += 1
            if (row.get("OBS_COMMENT") or "").strip():
                comment_nonempty += 1
            raw = (row.get("OBS_VALUE") or "").strip()
            if not raw:
                missing_obs += 1
                continue
            value = float(raw)
            if value != int(value):
                non_integer += 1
            country = (row.get("COUNTRY_RESID") or "").strip()
            month = (row.get("TIME_PERIOD") or "").strip()
            cat = (row.get("CAT_TRAVELLER") or "").strip()
            countries_all.add(country)
            if cat in countries_by_cat:
                countries_by_cat[cat].add(country)
            if cat != VISITOR_CAT:
                continue
            idx = month_index(month)
            values[country][idx] = value
            months_seen.add(idx)
    diagnostics = {
        "rows_fetched": rows,
        "mix": {key: dict(counts) for key, counts in mix.items()},
        "obs_comment_nonempty": comment_nonempty,
        "missing_obs_value": missing_obs,
        "non_integer_obs_value": non_integer,
        "months": {"min": month_from_index(min(months_seen)),
                   "max": month_from_index(max(months_seen)),
                   "count": len(months_seen)},
        "countries_all_rows": len(countries_all),
        "countries_by_traveller_category": {cat: len(members)
                                             for cat, members in countries_by_cat.items()},
    }
    diagnostics["countries_visitor_series"] = len(values)
    return dict(values), diagnostics


def split_of(target_idx: int, panel_max: int) -> str | None:
    """Split for a target month; None rows are counted by the caller."""
    text = month_from_index(target_idx)
    if TRAIN_START <= text <= TRAIN_END:
        return "train"
    if EVAL_START <= text <= EVAL_END:
        return "eval"
    if PANDEMIC_START <= text <= PANDEMIC_END:
        return "pandemic_excluded"
    if HOLDOUT_START <= text and target_idx <= panel_max:
        return "holdout"
    return None


def auc(labels: list[int], scores: list[float]) -> float | None:
    """Rank-based AUC (Mann-Whitney) with ties averaged, stdlib only."""
    pairs = sorted(zip(scores, labels), key=lambda pair: pair[0])
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    ranks = [0.0] * len(pairs)
    index = 0
    while index < len(pairs):
        stop = index
        while stop < len(pairs) and pairs[stop][0] == pairs[index][0]:
            stop += 1
        average = (index + stop + 1) / 2
        for position in range(index, stop):
            ranks[position] = average
        index = stop
    positive_rank_sum = sum(rank for rank, (_, label) in zip(ranks, pairs) if label == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def fit_rate_table(rows: list[dict], *keys) -> dict[tuple, float]:
    """Positive rate per key tuple estimated on the given rows only."""
    totals: Counter = Counter()
    positives: Counter = Counter()
    for row in rows:
        key = tuple(row[name] for name in keys)
        totals[key] += 1
        positives[key] += row[TARGET]
    return {key: positives[key] / totals[key] for key in totals}


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


def build_rows(values: dict[str, dict[int, float]], panel_max: int) -> tuple[dict, dict]:
    """Emit one row per (country, target month) on the visitor series."""
    rows_by_split: dict[str, list[dict]] = {"train": [], "eval": [], "holdout": []}
    accounting = {"insufficient_history": 0, "unobserved_target": 0,
                  "pandemic_excluded": 0, "outside_windows": 0,
                  "live_month_scorable_rows": 0}
    pandemic_texture: Counter = Counter()
    pandemic_per_year: dict[int, Counter] = defaultdict(Counter)
    per_year: dict[str, dict[int, Counter]] = {"train": defaultdict(Counter),
                                               "eval": defaultdict(Counter),
                                               "holdout": defaultdict(Counter)}
    for country in sorted(values):
        series = values[country]
        first = min(series)
        # A row needs the six feature months (deepest is T-13) and, for the
        # label, months T and T-12. The scan includes one month beyond the
        # panel max: the live prediction month, whose outcome is unobserved.
        for target_idx in range(first + max(FEATURE_OFFSETS.values()), panel_max + 2):
            feature_idx = {name: target_idx - offset
                           for name, offset in FEATURE_OFFSETS.items()}
            if any(idx not in series for idx in feature_idx.values()):
                if split_of(target_idx, panel_max) is not None:
                    accounting["insufficient_history"] += 1
                continue
            if target_idx not in series or (target_idx - YOY_LAG) not in series:
                if split_of(target_idx, panel_max) is not None:
                    accounting["unobserved_target"] += 1
                elif target_idx == panel_max + 1:
                    # the live prediction month: features are published, the
                    # outcome is not - scorable the day the next release lands
                    accounting["live_month_scorable_rows"] += 1
                continue
            v_t = series[target_idx]
            v_year_earlier = series[target_idx - YOY_LAG]
            texture = "flat" if v_t == v_year_earlier else \
                ("down" if v_t < v_year_earlier else "up")
            month_text = month_from_index(target_idx)
            split = split_of(target_idx, panel_max)
            if split == "pandemic_excluded":
                accounting["pandemic_excluded"] += 1
                pandemic_texture[texture] += 1
                pandemic_per_year[int(month_text[:4])][texture] += 1
                continue
            if split is None:
                accounting["outside_windows"] += 1
                continue
            levels = {name: series[idx] for name, idx in feature_idx.items()}
            row = {
                "row_id": f"{country}@{month_text}",
                "country_resid": country,
                "target_year": month_text[:4],
                "target_month_num": int(month_text[5:7]),
                **{name: fmt_num(value) for name, value in levels.items()},
                "diff_mom": fmt_num(levels["val_m"] - levels["val_m1"]),
                "diff_quarter": fmt_num(levels["val_m"] - levels["val_m3"]),
                "diff_half": fmt_num(levels["val_m"] - levels["val_m6"]),
                "diff_yoy_m": fmt_num(levels["val_m"] - levels["val_m12"]),
                "target_month": month_text,
                TARGET: 1 if texture == "down" else 0,
                "_texture": texture,
                "_diff_yoy_m_float": levels["val_m"] - levels["val_m12"],
            }
            rows_by_split[split].append(row)
            per_year[split][int(month_text[:4])][texture] += 1
    return rows_by_split, {"accounting": accounting,
                           "pandemic_texture": dict(pandemic_texture),
                           "pandemic_per_year_texture": {year: dict(counter)
                                                        for year, counter
                                                        in sorted(pandemic_per_year.items())},
                           "per_year_texture": {split: {year: dict(counter)
                                                        for year, counter in sorted(years.items())}
                                                for split, years in per_year.items()}}


def write_splits(out: Path, rows_by_split: dict[str, list[dict]]) -> dict:
    stats = {}
    for split, relative in LAYOUT.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(rows_by_split[split], key=lambda row: (row["target_month"],
                                                             row["country_resid"]))
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        flats = sum(1 for row in rows if row["_texture"] == "flat")
        event_months = {row["target_month"] for row in rows if row[TARGET] == POSITIVE_LABEL}
        stats[split] = {"rows": len(rows), "positives": positives,
                        "flat_label_zero_rows": flats,
                        "positive_rate": round(positives / len(rows), 6) if rows else None,
                        "distinct_event_months": len(event_months)}
    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Build the {NAME} extract")
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--work-dir", default="/tmp/abs")
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--panel-file", default=None,
                        help="local panel CSV (dry run); default fetches the live panel")
    parser.add_argument("--structure-file", default=None,
                        help="local SDMX structure XML (dry run)")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log("== download ==")
    panel_path = Path(args.panel_file) if args.panel_file else None
    structure_path = Path(args.structure_file) if args.structure_file else None
    sources: dict[str, dict] = {}
    if panel_path is None:
        panel_path = work / "oad_country_panel.csv"
        sources["panel"] = fetch(PANEL_URL, panel_path)
        log(f"panel: {sources['panel']['bytes']} bytes, "
            f"last-modified {sources['panel']['last_modified']}, "
            f"{sources['panel']['seconds']} s")
    else:
        sources["panel"] = {"url": "local:" + str(panel_path),
                            "bytes": panel_path.stat().st_size, "last_modified": None,
                            "seconds": 0.0, "sha256": sha256_file(panel_path)}
    if structure_path is None:
        structure_path = work / "oad_country_structure.xml"
        sources["structure"] = fetch(STRUCTURE_URL, structure_path)
        log(f"structure: {sources['structure']['bytes']} bytes, "
            f"{sources['structure']['seconds']} s")
    else:
        sources["structure"] = {"url": "local:" + str(structure_path),
                                "bytes": structure_path.stat().st_size,
                                "last_modified": None, "seconds": 0.0,
                                "sha256": sha256_file(structure_path)}

    log("== parse panel ==")
    values, panel_info = load_panel(panel_path)
    log(json.dumps(panel_info, indent=1))
    panel_max = month_index(panel_info["months"]["max"])

    log("== country codelist ==")
    names = parse_country_names(structure_path)
    unnamed = sorted(set(values) - set(names))
    log(f"CL_OAD_ARRIVALS_COUNTRY: {len(names)} codes parsed; "
        f"in-panel countries: {len(values)}; unnamed in-panel: {len(unnamed)}")
    if not names or unnamed:
        log(f"FAIL: country codelist unusable (parsed {len(names)} names, "
            f"missing {unnamed[:5]})")
        return 2

    rows_by_split, build_info = build_rows(values, panel_max)
    accounting = build_info["accounting"]
    for split in rows_by_split:
        log(f"{split}: {len(rows_by_split[split])} rows")
    log(f"eligibility accounting: {accounting}")
    log(f"pandemic-window texture (excluded, counted): "
        f"{build_info['pandemic_texture']}")

    stats = write_splits(out, rows_by_split)
    for split, entry in stats.items():
        log(f"{split}: {entry['rows']} rows, {entry['positives']} positives "
            f"(rate {entry['positive_rate']}), {entry['flat_label_zero_rows']} flat, "
            f"{entry['distinct_event_months']} distinct positive months")

    # Known-event fixtures on the shipped visitor series. The record measured
    # the border-closure collapse on **2020** target months (2021 is the
    # reopening year and dilutes the collapse), so the fixture reads the
    # pandemic window's 2020 texture, not the combined window.
    texture = build_info["per_year_texture"]
    pandemic_2020 = build_info["pandemic_per_year_texture"].get(2020, {})
    total_2020 = sum(pandemic_2020.values())
    down_share_2020 = pandemic_2020.get("down", 0) / total_2020 if total_2020 else None
    holdout_2022 = texture["holdout"].get(2022, {})
    total_2022 = sum(holdout_2022.values())
    up_share_2022 = holdout_2022.get("up", 0) / total_2022 if total_2022 else None
    known_events = {
        "border_closure_2020": {
            "window": "2020 (excluded pandemic target months)",
            "rows": total_2020,
            "down_share": round_or_none(down_share_2020),
            "threshold": KNOWN_EVENT_MIN_SHARE,
            "source": "ABS OAD; candidate record known_event_fixtures (border "
                      "closed March 2020; measured both-category 2020 YoY "
                      "down 1,492 / up 159 at discovery)"},
        "reopening_2022": {
            "window": "2022 (holdout target months)",
            "rows": total_2022, "up_share": round_or_none(up_share_2022),
            "threshold": KNOWN_EVENT_MIN_SHARE,
            "source": "ABS OAD; candidate record known_event_fixtures (reopening "
                      "from November 2021; measured both-category 2022 YoY "
                      "up 1,645 / down 9 at discovery)"},
    }
    log(f"known events: {json.dumps(known_events)}")

    # Reference baselines, measured before any model spend (the record's
    # step 5): persistence (the YoY sign observed at M, scored by its signed
    # difference), identity-only and calendar-only rates estimated on TRAIN
    # rows only. The full-model leg of the triad is the runner-contract
    # baseline job on the accepted artifact, run separately.
    for row_list in rows_by_split.values():
        for row in row_list:
            row["_country_month"] = (row["country_resid"], row["target_month_num"])
    train_rows = rows_by_split["train"]
    train_rate = (sum(r[TARGET] for r in train_rows) / len(train_rows)) if train_rows else 0.0
    identity_table = fit_rate_table(train_rows, "country_resid")
    calendar_table = fit_rate_table(train_rows, "country_resid", "target_month_num")
    baselines: dict[str, dict] = {"global_rate_train": round(train_rate, 6)}
    for split in ("eval", "holdout"):
        rows = rows_by_split[split]
        labels = [row[TARGET] for row in rows]
        persistence_scores = [row["_diff_yoy_m_float"] for row in rows]
        identity_scores = [identity_table.get((row["country_resid"],), train_rate)
                           for row in rows]
        calendar_scores = [calendar_table.get(row["_country_month"],
                                               identity_table.get((row["country_resid"],),
                                                                  train_rate))
                            for row in rows]
        baselines[split] = {
            "persistence_yoy_sign_auc": round_or_none(auc(labels, persistence_scores)),
            "identity_only_country_auc": round_or_none(auc(labels, identity_scores)),
            "calendar_only_country_month_auc": round_or_none(auc(labels, calendar_scores)),
            "persistence_sign_accuracy": round(
                sum(1 for score, label in zip(persistence_scores, labels)
                    if (score < 0) == (label == 1)) / len(labels), 4) if labels else None,
        }
    log("reference baselines: " + json.dumps(baselines))

    # Provenance assertions: the panel must be exactly the population the
    # record measured, or the label's meaning has silently changed.
    mix = panel_info["mix"]
    failures = []
    if panel_info["months"]["max"] < MIN_PANEL_MONTH:
        failures.append(f"panel covers only to {panel_info['months']['max']}, "
                        f"short of the measured {MIN_PANEL_MONTH}")
    if set(mix["CAT_TRAVELLER"]) != {VISITOR_CAT, RESIDENT_CAT}:
        failures.append(f"CAT_TRAVELLER mix unexpected: {mix['CAT_TRAVELLER']}")
    if set(mix["TSEST"]) != {"10"}:
        failures.append(f"TSEST mix unexpected (seasonally adjusted or trend "
                         f"streams present): {mix['TSEST']}")
    if set(mix["FREQ"]) != {"M"}:
        failures.append(f"FREQ mix unexpected: {mix['FREQ']}")
    if set(mix["UNIT_MEASURE"]) != {"NUM"}:
        failures.append(f"UNIT_MEASURE mix unexpected: {mix['UNIT_MEASURE']}")
    if panel_info["missing_obs_value"]:
        failures.append(f"{panel_info['missing_obs_value']} rows have a missing OBS_VALUE")
    if known_events["border_closure_2020"]["down_share"] is None or \
            known_events["border_closure_2020"]["down_share"] < KNOWN_EVENT_MIN_SHARE:
        failures.append(f"2020 border-closure fixture failed: "
                        f"{known_events['border_closure_2020']}")
    if known_events["reopening_2022"]["up_share"] is None or \
            known_events["reopening_2022"]["up_share"] < KNOWN_EVENT_MIN_SHARE:
        failures.append(f"2022 reopening fixture failed: "
                        f"{known_events['reopening_2022']}")
    for split in ("eval", "holdout"):
        entry = stats[split]
        if entry["positives"] < MIN_SPLIT_POSITIVES:
            failures.append(f"{split} too thin to score: {entry['positives']} positives")
        if entry["distinct_event_months"] < MIN_SPLIT_EVENTS:
            failures.append(f"{split} has only {entry['distinct_event_months']} "
                            f"distinct positive months")
        if entry["positives"] == 0 or entry["positives"] == entry["rows"]:
            failures.append(f"{split} is single-class: {entry}")
    if failures:
        for failure in failures:
            log(f"FAIL: {failure}")
        (out / "summary.json").write_text(json.dumps({
            "name": NAME, "built_at_utc": built_at, "failed": failures,
            "panel": panel_info, "splits": stats,
            "eligibility": build_info,
        }, indent=1) + "\n")
        return 2

    # The label source columns must be absent from every written header.
    for split, relative in LAYOUT.items():
        with (out / relative).open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        if header != COLUMNS:
            log(f"FAIL: {relative} header differs from the declared columns")
            return 2

    data_max = month_from_index(panel_max)
    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "sources": sources,
        "grain": "one row per (COUNTRY_RESID, target month) on the "
                 "CAT_TRAVELLER=06 short-term visitor arrivals series, TSEST=10",
        "panel": panel_info,
        "country_names": {code: names[code] for code in sorted(values)},
        "splits": stats,
        "eligibility": build_info,
        "known_events": known_events,
        "reference_baselines": {
            "note": "stdlib rank AUC measured at construction on the written "
                    "rows; rate tables estimated on train rows only. The "
                    "full-model leg of the triad is the runner-contract "
                    "baseline job on the accepted artifact.",
            **baselines,
        },
        "vintage": {
            "panel_max_month": data_max,
            "last_modified": sources["panel"].get("last_modified"),
            "revision_note": "ABS revises after linked Medicare data arrives "
                             "(record: March 2026 revised in the April 2026 "
                             "issue); only the current vintage is "
                             "downloadable, so features are current-vintage "
                             "and the cutoff is a documented assumption",
        },
        "pandemic_window": {
            "target_months": f"{PANDEMIC_START}..{PANDEMIC_END}",
            "rows_excluded_and_counted": accounting["pandemic_excluded"],
            "label_texture": build_info["pandemic_texture"],
            "per_year_label_texture": build_info["pandemic_per_year_texture"],
            "note": "border closed: the YoY sign is degenerate; values remain "
                    "legitimate feature history for 2022 rows (published "
                    "before those rows' prediction instants)",
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    holdout_end_exclusive = month_from_index(panel_max + 1)
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": PANEL_URL,
        "license": "ABS website material CC BY 4.0 International (source terms "
                   "preserved; attribution 'Source: Australian Bureau of "
                   "Statistics' required). Derived research dataset - not an "
                   "ABS official product. Our derived compilation: CC0-1.0.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by target month (OAD publication instant)",
                  "boundaries": {"train": f"{TRAIN_START} .. {TRAIN_END}",
                                 "eval": f"{EVAL_START} .. {EVAL_END}",
                                 "holdout": f"{HOLDOUT_START} .. {data_max}",
                                 "excluded": f"{PANDEMIC_START} .. {PANDEMIC_END} "
                                             "(pandemic extremes, counted)"}},
        "label_rule": "fell_short = 1 iff visitor arrivals OBS_VALUE(T) < "
                      "OBS_VALUE(T-12); exact ties are 0 and counted flat. "
                      "Both label source columns are excluded from every "
                      "shipped file.",
        "label_source_columns": ["OBS_VALUE(target month M+1)",
                                 "OBS_VALUE(year-earlier month M-11)"],
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_sha256": sources["panel"]["sha256"],
        "vintage_last_modified": sources["panel"].get("last_modified"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "target_month",
        "event_key_column": "target_month",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped level feature is an OBS_VALUE of the publisher's "
            "OAD_COUNTRY dataflow (SDMX 2.1, CSV column semantics documented "
            "in the ABS Data API user guide and the dataflow structure, "
            "fetched by this build): CAT_TRAVELLER=06 short-term visitors "
            "arriving, TSEST=10 Original, UNIT_MEASURE=NUM persons, "
            "TIME_PERIOD monthly. country_resid is a CL_OAD_ARRIVALS_COUNTRY "
            "codelist code (names recorded in summary.json and the release "
            "data dictionary). target_year/target_month_num are the target "
            "month's calendar. diff_* columns are differences of the shipped "
            "levels, documented in build.py's module docstring"),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": ["OBS_VALUE(target month M+1)",
                                 "OBS_VALUE(year-earlier month M-11)"],
        "post_hoc_columns": ["OBS_VALUE(target month M+1)",
                             "OBS_VALUE(year-earlier month M-11)",
                             "OBS_STATUS", "OBS_COMMENT"],
        "measurements": [
            {"column": "val_m",
             "unit": "short-term visitor arrivals (persons), Original series",
             "frame": "OBS_VALUE of the CAT_TRAVELLER=06 series at month M = "
                      "target month T minus one, the last month published at "
                      "the prediction instant; current vintage (ABS revises "
                      "post-release, so this is stated as current-vintage "
                      "with the cutoff a documented assumption)"},
            {"column": "val_m1", "unit": "persons (Original series)",
             "frame": "OBS_VALUE at M-1 (two months before the target month)"},
            {"column": "val_m2", "unit": "persons (Original series)",
             "frame": "OBS_VALUE at M-2 (three months before the target month)"},
            {"column": "val_m3", "unit": "persons (Original series)",
             "frame": "OBS_VALUE at M-3 (four months before the target month)"},
            {"column": "val_m6", "unit": "persons (Original series)",
             "frame": "OBS_VALUE at M-6 (seven months before the target month)"},
            {"column": "val_m12", "unit": "persons (Original series)",
             "frame": "OBS_VALUE at M-12 (thirteen months before the target "
                      "month); diff_yoy_m = val_m - val_m12 is the YoY "
                      "difference observed at M, the persistence analogue - "
                      "the sign the task must beat"},
            {"column": "diff_mom", "unit": "persons (difference)",
             "frame": "val_m - val_m1, the month-over-month change at the "
                      "prediction instant"},
            {"column": "diff_quarter", "unit": "persons (difference)",
             "frame": "val_m - val_m3"},
            {"column": "diff_half", "unit": "persons (difference)",
             "frame": "val_m - val_m6"},
            {"column": "diff_yoy_m", "unit": "persons (difference)",
             "frame": "val_m - val_m12, the year-on-year difference at the "
                      "prediction instant"},
            {"column": "country_resid",
             "unit": "CL_OAD_ARRIVALS_COUNTRY codelist code",
             "frame": "country (or area) of residence; 78 codes in the "
                      "codelist, the in-panel visitor series carries "
                      f"{len(values)}; names recorded in summary.json"},
            {"column": "target_month", "unit": "calendar month (YYYY-MM)",
             "frame": "the target month T = M+1, the first month unpublished "
                      "at the prediction instant; the time column and the "
                      "conservative event key (positives cluster in calendar "
                      "time through shared Australian conditions)"},
            {"column": "fell_short",
             "unit": "binary indicator",
             "frame": "1 iff OBS_VALUE(T) < OBS_VALUE(T-12); exact ties are 0 "
                      "and counted flat; both source values are excluded "
                      "from the shipped columns"},
        ],
        "known_event": {
            "event": "Australia's international border closure (March 2020) "
                     "and reopening (from November 2021)",
            "expected": "2020 target months overwhelmingly fall short "
                        "(down share >= 0.75); 2022 target months "
                        "overwhelmingly do not (up share >= 0.75)",
            "source": "ABS OAD panel; candidate record known_event_fixtures, "
                      "measured in-panel at discovery 2026-10-22",
            "measured": known_events,
        },
        "timing": {
            "prediction_instant": {
                "kind": "publication",
                "period": "M",
                "days_after_period_end": 43,
                "citation": "ABS OAD release calendar, observed 2026-10-22: "
                            "Aug 2026 released 2026-10-13 (43 days), Jul 2026 "
                            "released 2026-09-11 (42 days), Apr 2026 released "
                            "2026-06-12 (43 days); next-release schedule Oct "
                            "2026 due 2026-12-15, Nov 2026 due 2027-01-19",
            },
            "features": {
                "period": "M",
                "published_days_after_period_end": 43,
                "source_kind": "statistical_release",
            },
            "row_selection": {
                "latest_period_used": "M",
                "fields": ["COUNTRY_RESID", "target_month"],
                "basis": "rows are (country, target month M+1) pairs on the "
                         "visitor series; eligibility needs the six feature "
                         "months <= M and the label inputs (M+1, M-11) - a "
                         "missing outcome is counted in unobserved_target, "
                         "never a membership decision on future data; the "
                         "latest period any feature reads is M",
            },
            "observations": [
                {"period": "2026-08", "period_end": "2026-08-31",
                 "published": "2026-10-13"},
                {"period": "2026-07", "period_end": "2026-07-31",
                 "published": "2026-09-11"},
                {"period": "2026-04", "period_end": "2026-04-30",
                 "published": "2026-06-12"},
            ],
        },
        "split_windows": {
            "train": {"start": TRAIN_START, "end": EVAL_START},
            "eval": {"start": EVAL_START, "end": PANDEMIC_START},
            "holdout": {"start": HOLDOUT_START, "end": holdout_end_exclusive},
        },
        "split_boundaries": {
            "train": f"target months {TRAIN_START} .. {TRAIN_END}",
            "eval": f"{EVAL_START} .. {EVAL_END}",
            "holdout": f"{HOLDOUT_START} .. {data_max}",
            "excluded": f"{PANDEMIC_START} .. {PANDEMIC_END} (pandemic "
                        f"extremes, counted with label texture)",
        },
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": "row_id is country@target_month, unique by "
                           "construction; no identifier repeats inside a "
                           "split or spans two",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                    "distinct_events": stats[split]["distinct_event_months"]}
                            for split in LAYOUT},
        "positive_events_note": "an event is one distinct target month "
                                "carrying at least one positive: positives "
                                "cluster in calendar time (shared Australian "
                                "conditions move many countries together; the "
                                "2020 and 2022 fixtures are such months), so "
                                "the month is the conservative cluster; "
                                "per-country persistence is a second axis "
                                "recorded as a property in the candidate "
                                "record",
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats, "accounting": accounting,
                    "known_events": known_events,
                    "reference_baselines": baselines}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
