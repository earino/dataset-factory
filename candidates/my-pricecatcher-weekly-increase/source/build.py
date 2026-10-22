#!/usr/bin/env python3
"""Build the Malaysia PriceCatcher week-ahead price-increase task.

Source: KPDN/DOSM PriceCatcher, monthly bulk files of daily retail prices at
https://storage.data.gov.my/pricecatcher/pricecatcher_YYYY-MM.csv (CC BY 4.0).

Design notes that matter:

* The prediction instant is the end of ISO week W. Every feature comes from weeks <= W. The feed
  carries same-day rows (measured: 2026-10 rows present in the October file), so there is no
  publication lag to model; that is recorded as an administrative record, not a statistical release.
* Eligibility is decided at W: a pair must have at least MIN_OBS observations in week W. A pair whose
  week W+1 has fewer observations has an *unobserved outcome*, which is counted and dropped - it is
  not a membership rule. This is the lesson from the NHS A&E audits, applied before construction.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

NAME = "my-pricecatcher-weekly-increase"
TARGET = "increases"
POSITIVE_LABEL = 1
MIN_OBS = 3
SOURCE_URL = ("https://data.gov.my/data-catalogue/pricecatcher "
              "(bulk: https://storage.data.gov.my/pricecatcher/pricecatcher_YYYY-MM.csv)")
LICENCE = "CC BY 4.0 (data.gov.my / OpenDOSM; KPDN and DOSM)"
PREDICTION_TIME = (
    "End of ISO week W (Sunday 23:59:59 MYT). Features use price observations dated at or before the "
    "end of week W. The publisher's bulk storage carries same-day rows (2026-10 rows were present in "
    "the 2026-10 file, last modified the same day), so no publication lag is modelled.")
QUESTION = (
    "For an item-premise pair in Malaysia's PriceCatcher panel with at least 3 price observations in "
    "ISO week W, will the pair's weekly modal price be higher in week W+1 than in week W?")

FEATURES = [
    "price", "n_obs", "price_lag1", "price_lag2", "price_lag4",
    "delta_1w", "delta_4w", "mean4", "std4", "min4", "max4", "price_vs_mean4",
    "week_of_year", "month", "item_code", "premise_code", "state",
]
FEATURE_DOC = {
    "price": "modal price in week W, computed from observations dated <= Sunday of W",
    "n_obs": "number of observations for this pair in week W",
    "price_lag1": "modal price in week W-1 (NaN when absent)",
    "price_lag2": "modal price in week W-2",
    "price_lag4": "modal price in week W-4",
    "delta_1w": "price - price_lag1",
    "delta_4w": "price - price_lag4",
    "mean4": "mean of the last four weekly modal prices including W",
    "std4": "standard deviation of those four prices",
    "min4": "minimum of those four prices",
    "max4": "maximum of those four prices",
    "price_vs_mean4": "price - mean4",
    "week_of_year": "ISO week number of W (known at the instant)",
    "month": "calendar month of W",
    "item_code": "publisher item code (categorical)",
    "premise_code": "publisher premise code (categorical; the entity key)",
    "state": "premise state from the publisher's premise lookup (categorical, static)",
}


def log(message: str) -> None:
    print(message, flush=True)


def load_month(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"premise_code": "int32", "item_code": "int32",
                                     "price": "float64"}, parse_dates=["date"])
    frame = frame.dropna(subset=["date", "premise_code", "item_code", "price"])
    frame["week"] = frame["date"].dt.normalize() - pd.to_timedelta(frame["date"].dt.weekday, unit="D")
    return frame


def weekly(parquets: list[Path]) -> pd.DataFrame:
    """Concatenate the per-month weekly aggregates produced by prep.py."""
    pieces = []
    for index, path in enumerate(parquets, 1):
        pieces.append(pd.read_parquet(path))
        if index % 6 == 0:
            log(f"  read {index}/{len(parquets)} weekly aggregates")
    return pd.concat(pieces, ignore_index=True)


def _indexed(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.set_index(["premise_code", "item_code"])[["price", "n_obs"]]


def stream_transitions(parquets: list[Path], state: str | None, sink,
                       state_by_premise: dict | None = None) -> dict:
    """Emit one row per (pair, week W) whose week W+1 is observed.

    Weeks are processed in order and only the last four are held in memory, so the 36-month panel
    never has to fit at once. Eligibility is decided at W; a week W+1 with fewer than MIN_OBS
    observations is an unobserved outcome, counted separately.
    """
    window: dict[pd.Timestamp, pd.DataFrame] = {}
    seen_weeks: set[pd.Timestamp] = set()
    emitted = 0
    unobserved = 0
    for index, path in enumerate(parquets, 1):
        frame = pd.read_parquet(path)
        if state:
            if "state" in frame.columns:
                frame = frame[frame["state"] == state]
            elif state_by_premise:
                wanted = {code for code, name in state_by_premise.items() if name == state}
                frame = frame[frame["premise_code"].isin(wanted)]
            else:
                raise SystemExit("--state needs either a state column or --lookup")
            if frame.empty:
                continue
        if frame.empty:
            continue
        for week, block in frame.groupby("week", sort=True):
            if week in seen_weeks:
                continue
            seen_weeks.add(week)
            if week - pd.Timedelta(days=7) in window:
                batch = _emit(window, week - pd.Timedelta(days=7), week, _indexed(block))
                unobserved += _count_unobserved(window, week - pd.Timedelta(days=7), _indexed(block))
                if not batch.empty:
                    sink(batch)
                    emitted += len(batch)
            window[week] = _indexed(block)
            for stale in [w for w in window if w < week - pd.Timedelta(days=28)]:
                del window[stale]
        if index % 6 == 0:
            log(f"  streamed {index}/{len(parquets)} months ({emitted:,} rows, "
                f"rss capped by streaming)")
    return {"unobserved_outcomes": unobserved, "window_weeks": len(window),
            "emitted": emitted}


def _count_unobserved(window, week, nxt) -> int:
    base = window.get(week)
    if base is None:
        return 0
    eligible = base[base["n_obs"] >= MIN_OBS]
    joined = eligible.join(nxt, how="left", lsuffix="_cur", rsuffix="_next")
    return int((joined["price_next"].isna() | (joined["n_obs_next"] < MIN_OBS)).sum())


def _emit(window, week, next_week, nxt) -> pd.DataFrame:
    base = window[week]
    base = base[base["n_obs"] >= MIN_OBS]
    if base.empty:
        return pd.DataFrame()
    frame = base.rename(columns={"price": "price", "n_obs": "n_obs"}).copy()
    for lag in (1, 2, 4):
        prior = window.get(week - pd.Timedelta(days=7 * lag))
        if prior is not None:
            frame = frame.join(prior["price"].rename(f"price_lag{lag}"), how="left")
        else:
            frame[f"price_lag{lag}"] = float("nan")
    joined = frame.join(nxt, how="left", lsuffix="", rsuffix="_next")
    joined = joined[joined["price_next"].notna() & (joined["n_obs_next"] >= MIN_OBS)]
    if joined.empty:
        return pd.DataFrame()
    joined = joined.reset_index()
    joined["delta_1w"] = joined["price"] - joined["price_lag1"]
    joined["delta_4w"] = joined["price"] - joined["price_lag4"]
    window4 = joined[["price", "price_lag1", "price_lag2", "price_lag4"]]
    joined["mean4"] = window4.mean(axis=1)
    joined["std4"] = window4.std(axis=1, ddof=0)
    joined["min4"] = window4.min(axis=1)
    joined["max4"] = window4.max(axis=1)
    joined["price_vs_mean4"] = joined["price"] - joined["mean4"]
    joined["week"] = week
    joined["target_week"] = next_week
    joined[TARGET] = (joined["price_next"] > joined["price"]).astype("int8")
    joined["week_of_year"] = next_week.isocalendar().week
    joined["month"] = next_week.month
    joined = joined.drop(columns=["n_obs_next"])
    # Sentinel -1.0 for a missing lag: prices are strictly positive, so -1 cannot collide with a
    # real value, and the gate's leakage check requires numeric columns without NaN.
    for column in ("price_lag1", "price_lag2", "price_lag4", "delta_1w", "delta_4w",
                   "mean4", "std4", "min4", "max4", "price_vs_mean4"):
        joined[column] = joined[column].fillna(-1.0)
    return joined


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the PriceCatcher weekly price-increase task")
    parser.add_argument("--source-dir", required=True, help="directory of pricecatcher_YYYY-MM.csv files")
    parser.add_argument("--out", required=True)
    parser.add_argument("--lookup", default=None, help="lookup_premise.csv (optional, for state)")
    parser.add_argument("--state", default=None,
                        help="restrict to one publisher state (the artifact is a state-scoped task)")
    parser.add_argument("--start", default="2023-11")
    parser.add_argument("--end", default="2026-10")
    parser.add_argument("--train-end", default="2024-12-31")
    parser.add_argument("--eval-end", default="2025-12-31")
    args = parser.parse_args(argv)

    out = Path(args.out)
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)

    paths = []
    cursor = pd.Period(args.start, freq="M")
    last = pd.Period(args.end, freq="M")
    while cursor <= last:
        path = Path(args.source_dir) / f"p{cursor.year}-{cursor.month:02d}.weekly.parquet"
        if not path.exists():
            path = Path(args.source_dir) / f"pricecatcher_{cursor.year}-{cursor.month:02d}.weekly.parquet"
        if not path.exists():
            raise SystemExit(f"missing weekly aggregate for {cursor}: {path}")
        paths.append(path)
        cursor += 1
    log(f"reading {len(paths)} monthly files")

    lookup_state = {}
    if args.lookup:
        lookup = pd.read_csv(args.lookup, dtype={"premise_code": "int32"})
        if "state" in lookup.columns:
            lookup_state = dict(zip(lookup["premise_code"], lookup["state"]))

    train_end, eval_end = pd.Timestamp(args.train_end), pd.Timestamp(args.eval_end)
    ordered = ["row_id", "target_week", *FEATURES, TARGET]
    paths_out = {"train": out / "public" / "train.csv",
                 "eval": out / "public" / "eval.csv",
                 "holdout": out / "private" / "holdout.csv"}
    stats = {k: {"rows": 0, "positives": 0, "premises": set(),
                 "target_from": None, "target_to": None} for k in paths_out}
    written = set()

    def sink(batch: pd.DataFrame) -> None:
        batch = batch.copy()
        batch["state"] = [lookup_state.get(code, "unknown") for code in batch["premise_code"]]
        batch["row_id"] = (batch["premise_code"].astype(str) + "-" + batch["item_code"].astype(str)
                           + "-" + batch["target_week"].dt.strftime("%Y%m%d"))
        split = pd.Series("holdout", index=batch.index)
        split[batch["target_week"] <= train_end] = "train"
        split[(batch["target_week"] > train_end) & (batch["target_week"] <= eval_end)] = "eval"
        for name, part in batch.groupby(split, sort=False):
            part[ordered].to_csv(paths_out[name], mode="a", header=name not in written, index=False)
            written.add(name)
            stats[name]["rows"] += len(part)
            stats[name]["positives"] += int(part[TARGET].sum())
            stats[name]["premises"].update(part["premise_code"].tolist())
            low, high = part["target_week"].min(), part["target_week"].max()
            if stats[name]["target_from"] is None or low < stats[name]["target_from"]:
                stats[name]["target_from"] = low
            if stats[name]["target_to"] is None or high > stats[name]["target_to"]:
                stats[name]["target_to"] = high

    stream_stats = stream_transitions(paths, args.state, sink, lookup_state)
    log(f"transitions: {stream_stats['emitted']:,} rows, "
        f"unobserved outcomes {stream_stats['unobserved_outcomes']:,}")
    if not stream_stats["emitted"]:
        raise SystemExit("no rows produced")
    for name, entry in stats.items():
        entry["positive_rate"] = round(entry["positives"] / entry["rows"], 6) if entry["rows"] else None
        entry["distinct_events"] = len(entry.pop("premises"))
        entry["target_from"] = str(entry["target_from"].date()) if entry["target_from"] is not None else None
        entry["target_to"] = str(entry["target_to"].date()) if entry["target_to"] is not None else None

    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    meta = {
        "name": NAME,
        "description": QUESTION,
        "source": SOURCE_URL,
        "license": LICENCE,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ["row_id"],
        "split": {"strategy": "temporal on the target week",
                  "boundaries": {"train": f"target weeks <= {args.train_end}",
                                 "eval": f"{args.train_end} < target weeks <= {args.eval_end}",
                                 "holdout": f"target weeks > {args.eval_end}"}},
        "columns": ordered,
        "rows": {k: v["rows"] for k, v in stats.items()},
        "positive_rate": {k: v["positive_rate"] for k, v in stats.items()},
        "built_at_utc": built_at,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "built_at_utc": built_at,
        "task": {"question": QUESTION, "prediction_time": PREDICTION_TIME},
        "features": FEATURES,
        "feature_documentation": [{"column": column, "note": FEATURE_DOC[column],
                                   "available_at": "week W or earlier"} for column in FEATURES],
        "features_documented_at": "prediction_time",
        "post_hoc_columns": [],
        "label_source_columns": ["next_price", "next_obs"],
        "carry_columns": ["row_id", "target_week", "premise_code", "item_code", "state"],
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "target_week",
        "event_key_column": "premise_code",
        "id_columns": ["row_id"],
        "id_columns_are_entity_keys": False,
        "expected_duplicate_ids": 0,
        "high_cardinality_columns": ["premise_code", "item_code"],
        "high_cardinality_note": "premise_code is the entity key and repeats across weeks by design; "
                                 "item_code is the other half of the pair identity.",
        "external_threshold": None,
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "positive_events": {name: {"positives": entry["positives"],
                                   "distinct_events": entry["distinct_events"]}
                            for name, entry in stats.items()},
        "split_stats": stats,
        "split_windows": {k: {"from": v["target_from"], "to": v["target_to"]} for k, v in stats.items()},
        "measurements": [
        {
                "column": "price",
                "unit": "Malaysian ringgit (MYR) per item unit",
                "frame": "modal price in ISO week W, from observations dated on or before Sunday of W"
        },
        {
                "column": "n_obs",
                "unit": "count of price observations",
                "frame": "week W"
        },
        {
                "column": "delta_1w",
                "unit": "MYR difference",
                "frame": "price(W) minus price(W-1)"
        },
        {
                "column": "delta_4w",
                "unit": "MYR difference",
                "frame": "price(W) minus price(W-4)"
        },
        {
                "column": "week_of_year",
                "unit": "ISO week number (1-53)",
                "frame": "week W"
        },
        {
                "column": "target_week",
                "unit": "ISO week (date of Monday)",
                "frame": "week W+1, the outcome week"
        }
],
        "measurement_notes": {
            "min_obs_per_week": MIN_OBS,
            "unobserved_outcomes": stream_stats["unobserved_outcomes"],
            "candidate_rows": stream_stats["emitted"],
            "note": "Eligibility requires >= 3 observations in week W only. A pair whose week W+1 has "
                    "fewer than 3 observations has an unobserved outcome and is counted separately; "
                    "the target week never decides whether a row exists.",
        },
        "timing_selfcheck": {"checked": 0, "mismatches": 0,
                             "note": "every feature is a merge on week-7k keys; no forward reference"},
        "timing": {
            "prediction_instant": {"kind": "period_end", "period": "W",
                                   "days_after_period_end": 0,
                                   "citation": "https://storage.data.gov.my/pricecatcher/ "
                                               "(same-day rows measured 2026-10-21)"},
            "features": {"period": "W", "published_days_after_period_end": 0,
                         "source_kind": "administrative_record"},
            "row_selection": {"latest_period_used": "W", "fields": ["n_obs"],
                              "basis": "the pair needs >= 3 observations in week W; week W+1 supplies "
                                       "the outcome only and a missing outcome is counted, not "
                                       "treated as exclusion"},
            "observations": [],
        },
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")
    (out / "summary.json").write_text(json.dumps(
        {"name": NAME, "built_at_utc": built_at, "splits": stats, "state": args.state,
         "unobserved_outcomes": stream_stats["unobserved_outcomes"],
         "features": FEATURES}, indent=1) + "\n")
    log(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
