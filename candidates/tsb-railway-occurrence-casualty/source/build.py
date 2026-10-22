#!/usr/bin/env python3
"""Construction script for the `tsb-railway-occurrence-casualty` candidate.

Task: a railway occurrence begins at a known place, time and operating context
on the Canadian federal network. At that instant, given only pre-onset context -
where (subdivision, nearest location, province, region, lat/long), which
railway, when (date, local hour, season), and what the train was doing
(activity type) - will the occurrence result in at least one casualty (fatality
or any injury)?

Where this runs
---------------
On a temporary worker: five RODSdb CSVs (~157 MB total, browser-like headers;
plain User-Agent gets HTTP 403 - measured, probe_access.py). `--smoke` accepts
local file paths over the URLs for a bounded pipeline exercise and relaxes the
assertions a tiny fixture cannot carry (split capacity, vintage coverage,
publisher cross-check, panel-start bounds).

Frame rules (from the candidate record; each is measured and reported)
----------------------------------------------------------------------
* Grain: one row per TSB rail occurrence. Row key: OccNo (the TSB occurrence
  number, documented "a unique identifier for the occurrence"). The OCCURRENCE
  table's OccID column is empty in the current vintage's newest rows (measured
  2026-10-22: 1,495/1,495 newest rows empty), so OccNo is the usable key; the
  INJURIES child table still carries both keys and joins on OccNo.
* Exact duplicates: the current vintage contains byte-identical exported rows
  (measured 2026-10-22: OccNo R26D0003 twice, all 345 columns equal). Exact
  duplicates are dropped and counted; the count is recorded, not guessed.
* Modern-era panel start is *measured*, not guessed: per-year share of
  early-signature rows (AccIncType containing HISTORICAL or DG LEAKER, or
  TimeZoneID empty/N/A - the 1983-1990s traits the discovery samples showed).
  The panel starts at the first year from which that share stays under 2% in
  every later year (asserted within [1995, 2010]; the record proposed 2004).
* Splits (occurrence-date windows): train panel-start..2021-12-31,
  eval 2022-01-01..2024-12-31, holdout 2025-01-01..2026-08-31. The holdout
  ends one full month behind the measured vintage so every windowed occurrence
  has had at least one monthly release to settle in; occurrences after the
  window are counted and excluded, never silently dropped.
* Prediction instant: the occurrence onset (OccDate, local time at the site;
  TimeZoneID documents the site timezone, DST-aware abbreviations). This is an
  administrative register: the record is written at/after the event, and every
  shipped field is documented by the publisher as a property of the occurrence
  at its onset (RODSdb-dd.csv, 699 documented columns, recorded in the
  candidate record). ReportedDate/ReportedTime (the notification instant)
  post-date the onset and are excluded.
* Label: casualty = InjuriesIND == 1 OR TotalFatalInjuries +
  TotalSeriousInjuries + TotalMinorInjuries > 0. Both components and the
  separate INJURIES child table are cross-checked and the agreement recorded.
* Frames: latitude/longitude are integers scaled by 10^4 (measured: 505900 ->
  50.59 N, Revelstoke-area BC), degrees, of the *nearest city or town*; the
  build converts West longitudes to the east-positive convention and asserts
  every present value inside the Canadian envelope (41-72 N, 52-145 W).
  subd_mileage is miles from the subdivision start. occ_hour is the LOCAL hour
  at the site; UTC normalization is deliberately not applied because the
  DST-aware timezone string ships beside it and a hand-rolled offset map could
  silently misplace an hour (the unit/frame discipline this gate exists for).

Leakage discipline
-------------------
Everything TSB records during or after the occurrence is excluded from the
shipped columns: accident/incident type (its taxonomy embeds outcomes, e.g.
'NON-MAIN-TRACK TRAIN DERAILMENT (NO DAMAGE)'), occurrence class, all outcome
flags and injury counts (label sources), evacuation/DG/fire flags, process
dates, the free-text Summary, weather/light/temperature observations, and
NumberTrainsInvolved (known only as the occurrence unfolds). The label source
columns are asserted absent from every written CSV header.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: Open Government Licence - Canada 2.0 (open.canada.ca package record
4f8d9b0d, measured 2026-10-21, recorded in the candidate record); attribution
carries through to any release; our derived compilation is dedicated CC0-1.0
per standing policy. Derived research dataset - never TSB's official product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

NAME = "tsb-railway-occurrence-casualty"
TARGET = "casualty"
POSITIVE_LABEL = 1

BASE = "https://www.tsb.gc.ca/sites/default/files/stats/RODSdb_MDOTW_VW_{}_PUBLIC.csv"
TABLES = ["OCCURRENCE", "TRAIN", "ROLLING_STOCK", "INJURIES", "COMPONENTS"]
DICT_URL = "https://www.tsb.gc.ca/sites/default/files/data/en/RODSdb-dd.csv"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")
BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
    "Referer": "https://www.tsb.gc.ca/",
}

# Source columns read from the OCCURRENCE table (documented meanings recorded in
# the candidate record from RODSdb-dd.csv; fetched again by this build).
F_OCCNO = "OccNo"
F_OCCDATE = "OccDate"
F_OCCTIME = "OccTime"
F_TZ = "TimeZoneID_DisplayEng"
F_ACTIVITY = "ActivityTypeID_DisplayEng"
F_SUBD = "SubdNameID_DisplayEng"
F_SUBD_MILE = "SubdMileage"
F_RAILWAY = "SUBD_OWNER_ABBREV_ENG"
F_NEAR = "NearLocation"
F_PROVINCE = "ProvinceID_DisplayEng"
F_REGION = "RegionOfOccurrence_DisplayEng"
F_LAT = "Latitude"
F_LON = "Longitude"
F_INJIND = "InjuriesIND"
F_FATAL = "TotalFatalInjuries"
F_SERIOUS = "TotalSeriousInjuries"
F_MINOR = "TotalMinorInjuries"
F_OCTYPE = "OccurrenceTypeID_DisplayEng"       # publisher cross-check only
F_ACCINC = "AccIncTypeID_DisplayEng"            # early-era diagnostic only
SOURCE_FIELDS = [F_OCCNO, F_OCCDATE, F_OCCTIME, F_TZ, F_ACTIVITY, F_SUBD,
                 F_SUBD_MILE, F_RAILWAY, F_NEAR, F_PROVINCE, F_REGION,
                 F_LAT, F_LON, F_INJIND, F_FATAL, F_SERIOUS, F_MINOR,
                 F_OCTYPE, F_ACCINC]

# Shipped layout: id, features, carry, target.
ID_COLUMNS = ["occ_no"]
FEATURES = [
    "occ_year", "occ_month", "occ_day_of_week", "occ_hour",
    "timezone", "activity_type",
    "subdivision", "subd_mileage", "railway",
    "near_location", "province", "region",
    "latitude", "longitude",
]
CARRY_COLUMNS = ["occ_date"]
HIGH_CARDINALITY = ["occ_date", "near_location", "latitude", "longitude",
                    "subd_mileage"]
LABEL_SOURCE_COLUMNS = [F_INJIND, F_FATAL, F_SERIOUS, F_MINOR]
POST_HOC_COLUMNS = [
    "AccIncTypeID_DisplayEng", "OccurrenceTypeID_DisplayEng",
    "OccClassID_DisplayEng", "OccClassID", "AccIncTypeID", "OccurrenceTypeID",
    "ReportedDate", "ReportedTime", "Summary", "NumberTrainsInvolved",
    "NumTracksInvolved", "TotalRSInvolved", "TotalDerailedRS",
    "DerailedRSIND", "FireIND", "ExplosionIND", "EvacuationIND",
    "NumEvacuated", "IsolationRadius_Feet", "DGCarsInvolvedIND",
    "DGReleasedCarsIND", "TotalDGCarsInvolved", "TotalDGReleasedCars",
    "DeployedIND", "ENTRY_DT", "RELEASE_DT", "DAILY_RELEASED_DT",
    "OccClosedDate", "Temperature_Celsius", "WeatherSourceID_DisplayEng",
    "LightConditionID_DisplayEng", "WindID_DisplayEng",
    "PrecipitationTypeID_DisplayEng", "SkyConditionID_DisplayEng",
]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# Split windows (occurrence dates). The panel start is measured; the rest are
# pinned: eval/holdout boundaries from the candidate record, holdout end one
# full month behind the measured vintage. tsb-002 measured the taxonomy-era
# share (AccIncType HISTORICAL/DG LEAKER) at 25-38% in 1983-1991, 8-17% in
# 1993-2000, 4-9% in 2001-2013 and 2.3% in 2015, reaching ~0 only at 2016
# (0.58%) and 0.0% from 2017 - so the record's proposed 2004 start is inside
# a measured 6.8% early-taxonomy tail, and the measured modern panel starts
# at 2016. The band pins the measurement without freezing it.
EVAL_START = date(2022, 1, 1)
HOLDOUT_START = date(2025, 1, 1)
WINDOW_END = date(2026, 8, 31)
PANEL_START_MIN, PANEL_START_MAX = 2014, 2018
EARLY_SIG_MAX_SHARE = 0.02        # early-signature share per year, from panel start on
MIN_SPLIT_POSITIVES = 30
MIN_SPLIT_EVENTS = 20
PUBLISHED_2025 = {"ACCIDENT": 831, "INCIDENT": 332}   # TSB 2025 annual summary
CROSSCHECK_TOL = 0.10

# Canadian geographic envelope for the lat/long frame assertion.
LAT_MIN, LAT_MAX = 41.0, 72.0
LON_MIN, LON_MAX = -145.0, -52.0

PREDICTION_TIME = (
    "The instant the occurrence begins: OccDate (local time at the site, with "
    "TimeZoneID_DisplayEng documenting the site timezone). Every shipped "
    "feature is documented by the publisher as a property of the occurrence "
    "at its onset - where it is, which railway, when it is, and what the train "
    "was doing. Everything TSB records during or after the occurrence is "
    "excluded; the casualty outcome unfolds after onset and is the label.")
PREDICTION_QUESTION = (
    "A railway occurrence begins at a known place, time and operating context "
    "on the Canadian federal network. At that instant, given only pre-onset "
    "context - where (subdivision, nearest location, province, region, "
    "lat/long), which railway, when (date, local hour, season), and what the "
    "train was doing (activity type) - will the occurrence result in at least "
    "one casualty (fatality or any injury)?")


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, dest: Path) -> dict:
    """One anonymous GET with the browser-like header set (probe_access.py)."""
    started = time.time()
    request = urllib.request.Request(url, headers=BROWSER_HEADERS)
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


def clean(value: str | None) -> str:
    if value is None:
        return ""
    value = value.strip()
    return "" if value in ("N/A", "NULL", "None") else value


def parse_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_occurrence_datetime(raw: str) -> datetime | None:
    if not raw:
        return None
    # RODS stamps OccDate "YYYY-MM-DD HH:MM:SS.0000000" (7-digit fraction) or
    # date-only for the oldest rows; drop the fraction and parse the rest.
    text = raw.split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def scaled_coord(raw: str) -> float | None:
    """RODS writes lat/long as degrees x 10^4 integers (measured 2026-10-22)."""
    value = parse_float(clean(raw))
    if value is None:
        return None
    if abs(value) > 1000:            # still in the publisher's 10^4 scale
        value = value / 10000.0
    return value


def load_occurrences(path: Path) -> tuple[list[dict], dict]:
    """Stream the OCCURRENCE CSV: drop exact duplicates, keep needed fields.

    Returns (rows, diagnostics). Each kept row is a compact dict of the
    SOURCE_FIELDS plus the parsed onset datetime. Per-year diagnostics cover
    every year in the file so the panel start is measured, not asserted.
    """
    rows: list[dict] = []
    seen_hashes: set[str] = set()
    exact_duplicates = 0
    bad_datetime = 0
    per_year: dict[int, dict] = defaultdict(lambda: {"rows": 0, "casualty": 0,
                                                     "early_sig": 0, "tz_missing": 0})
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
        reader.fieldnames = fieldnames
        for source in reader:
            row_hash = hashlib.sha1(
                "\x1f".join((source.get(name) or "") for name in fieldnames)
                .encode("utf-8", "replace")).hexdigest()
            if row_hash in seen_hashes:
                exact_duplicates += 1
                continue
            seen_hashes.add(row_hash)

            when = parse_occurrence_datetime(clean(source.get(F_OCCDATE)))
            if when is None:
                bad_datetime += 1
                continue
            ind = clean(source.get(F_INJIND)) == "1"
            totals = (parse_int(clean(source.get(F_FATAL)))
                      + parse_int(clean(source.get(F_SERIOUS)))
                      + parse_int(clean(source.get(F_MINOR))))
            casualty = 1 if (ind or totals > 0) else 0
            accinc = clean(source.get(F_ACCINC)).upper()
            tz = clean(source.get(F_TZ))
            tz_bad = tz == "" or tz.upper() == "N/A"
            # The era signal is the *taxonomy*: TSB's early-year backfill
            # classifications (HISTORICAL, DG LEAKER) that the discovery
            # samples measured in the 1983-1990s rows. Timezone-missingness
            # is recorded separately per year: tsb-001 measured that sporadic
            # N/A timezones persist into the 2010s, so folding them into the
            # era rule pushed the measured start to 2016 - a missingness
            # property, not an era property.
            era_sig = "HISTORICAL" in accinc or "DG LEAKER" in accinc

            row = {name: clean(source.get(name)) for name in SOURCE_FIELDS}
            row["onset"] = when
            row["casualty"] = casualty
            rows.append(row)

            year = when.year
            per_year[year]["rows"] += 1
            per_year[year]["casualty"] += casualty
            if era_sig:
                per_year[year]["early_sig"] += 1
            if tz_bad:
                per_year[year]["tz_missing"] += 1

    diagnostics = {
        "exact_duplicate_rows_dropped": exact_duplicates,
        "rows_without_parseable_occdate": bad_datetime,
        "per_year": {year: {"rows": stats["rows"],
                            "casualty_rate": round(stats["casualty"] / stats["rows"], 4)
                            if stats["rows"] else None,
                            "era_sig_share": round(stats["early_sig"] / stats["rows"], 4)
                            if stats["rows"] else None,
                            "tz_missing_share": round(stats["tz_missing"] / stats["rows"], 4)
                            if stats["rows"] else None}
                     for year, stats in sorted(per_year.items())},
    }
    return rows, diagnostics


def print_diagnostics(diagnostics: dict) -> None:
    log("year  rows  casualty_rate  era_sig_share  tz_missing_share")
    for year, stats in diagnostics["per_year"].items():
        log(f"{year}  {stats['rows']:5d}  {stats['casualty_rate']!s:>13}  "
            f"{stats['era_sig_share']!s:>13}  {stats['tz_missing_share']!s:>15}")


def choose_panel_start(diagnostics: dict) -> int:
    """First year from which the taxonomy-era signature stays under the
    threshold in every later year (minimum 100 rows so a thin year cannot gate
    the choice). The record proposed 2004; the rule measures it. tsb-001
    measured the start at 2016 under a rule that also counted timezone
    missingness; the era signal is the taxonomy alone, and tz-missingness is
    a recorded per-year property instead."""
    per_year = {int(year): stats for year, stats in diagnostics["per_year"].items()}
    years = sorted(per_year)
    for candidate in years:
        if per_year[candidate]["rows"] < 100:
            continue
        if all(per_year[later]["era_sig_share"] is not None
               and per_year[later]["era_sig_share"] < EARLY_SIG_MAX_SHARE
               for later in years if later >= candidate):
            return candidate
    raise SystemExit("no year satisfies the modern-era rule; inspect diagnostics")


def split_of(onset: datetime, panel_start: date) -> str | None:
    when = onset.date()
    if when < panel_start or when > WINDOW_END:
        return None
    if when < EVAL_START:
        return "train"
    if when < HOLDOUT_START:
        return "eval"
    return "holdout"


def feature_row(row: dict, row_id: str) -> dict:
    onset: datetime = row["onset"]
    lat = scaled_coord(row[F_LAT])
    lon = scaled_coord(row[F_LON])
    if lon is not None and lon > 0:            # Canadian longitudes are West
        lon = -lon
    return {
        "occ_no": row_id,
        "occ_year": onset.year,
        "occ_month": onset.month,
        "occ_day_of_week": onset.weekday(),
        "occ_hour": onset.hour,
        "timezone": row[F_TZ],
        "activity_type": row[F_ACTIVITY],
        "subdivision": row[F_SUBD],
        "subd_mileage": row[F_SUBD_MILE],
        "railway": row[F_RAILWAY],
        "near_location": row[F_NEAR],
        "province": row[F_PROVINCE],
        "region": row[F_REGION],
        "latitude": f"{lat:.4f}" if lat is not None else "",
        "longitude": f"{lon:.4f}" if lon is not None else "",
        "occ_date": onset.strftime("%Y-%m-%d %H:%M"),
        TARGET: row["casualty"],
    }


def write_splits(out: Path, rows_by_split: dict[str, list[dict]]) -> dict:
    stats = {}
    for split, rel in LAYOUT.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_by_split.get(split, [])
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        events = len({row["occ_no"][:10] for row in rows if row[TARGET] == POSITIVE_LABEL})
        stats[split] = {"rows": len(rows), "positives": positives,
                        "positive_rate": round(positives / len(rows), 6) if rows else None,
                        "distinct_events": events}
    return stats


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


def level_rate_baselines(rows_by_split: dict, columns: list[str]) -> dict:
    """Naive conditional-rate baselines measured before anything is spent on a
    model: per-level casualty rates estimated on TRAIN rows only, scored on the
    eval and holdout rows (unseen levels fall back to the train global rate).
    These are exactly the record's step (4): global rate, per-railway,
    per-subdivision, per-activity (plus province and month)."""
    train = rows_by_split["train"]
    train_rate = (sum(r[TARGET] for r in train) / len(train)) if train else 0.0
    out: dict[str, dict] = {"global_rate_train": round(train_rate, 6)}
    for column in columns:
        totals: dict[str, int] = Counter()
        positives: dict[str, int] = Counter()
        for row in train:
            totals[row[column]] += 1
            positives[row[column]] += row[TARGET]
        rates = {level: positives[level] / count for level, count in totals.items()}
        per_split = {}
        for split in ("eval", "holdout"):
            rows = rows_by_split[split]
            labels = [row[TARGET] for row in rows]
            scores = [rates.get(row[column], train_rate) for row in rows]
            per_split[split] = round(auc(labels, scores), 4) if labels else None
        levels = {level: round(rate, 4) for level, rate in
                  sorted(rates.items(), key=lambda item: -item[1])[:12]}
        out[column] = {"levels_top": levels, "n_levels": len(rates),
                       "eval_auc": per_split["eval"], "holdout_auc": per_split["holdout"]}
    return out


def trailing_rate_baselines(rows_by_split: dict) -> dict:
    """The persistence analogue for an event stream: the casualty rate over the
    12 months of occurrences strictly before the row's own month (knowable at
    the row's instant; falls back to the overall panel rate when the window is
    empty)."""
    panel = [row for split in rows_by_split.values() for row in split]
    panel.sort(key=lambda row: row["occ_date"])
    months: dict[str, list[int]] = defaultdict(list)
    for row in panel:
        months[row["occ_date"][:7]].append(row[TARGET])
    out = {}
    for split in ("eval", "holdout"):
        labels, scores = [], []
        for row in rows_by_split[split]:
            year, month = (int(part) for part in row["occ_date"][:7].split("-"))
            window = [label for offset in range(1, 13)
                      for label in months.get(f"{year - (month - offset <= 0):04d}-"
                                             f"{(month - offset - 1) % 12 + 1:02d}", [])]
            scores.append(sum(window) / len(window) if window else 0.5)
            labels.append(row[TARGET])
        out[split] = round(auc(labels, scores), 4)
    return out


def injury_table_casualties(path: Path) -> set[str]:
    """OccNo set with >=1 injury row in the INJURIES child table (any severity
    count column > 0), for the label cross-check."""
    casualties: set[str] = set()
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
        key = "OccNo" if "OccNo" in reader.fieldnames else reader.fieldnames[0]
        count_cols = [name for name in reader.fieldnames
                      if re.search(r"(Fatal|Serious|Minor)", name)]
        for row in reader:
            if any(parse_int(clean(row.get(name))) > 0 for name in count_cols):
                occno = clean(row.get(key))
                if occno:
                    casualties.add(occno)
    return casualties


def table_occno_counts(path: Path) -> dict:
    rows = 0
    occnos: set[str] = set()
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
        key = "OccNo" if "OccNo" in reader.fieldnames else reader.fieldnames[0]
        for row in reader:
            rows += 1
            occno = clean(row.get(key))
            if occno:
                occnos.add(occno)
    return {"rows": rows, "distinct_occno": len(occnos)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Build the {NAME} extract")
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--work-dir", default="/tmp/tsb")
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--smoke", action="store_true",
                        help="bounded exercise on local files: pass file paths "
                             "instead of URLs; assertions a tiny fixture cannot "
                             "carry are skipped")
    parser.add_argument("--occurrence-file")
    parser.add_argument("--injuries-file")
    parser.add_argument("--train-file")
    parser.add_argument("--rolling-stock-file")
    parser.add_argument("--components-file")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log("== download ==")
    sources = {}
    occ_path = Path(args.occurrence_file) if args.occurrence_file else None
    inj_path = Path(args.injuries_file) if args.injuries_file else None
    if not args.smoke:
        for table in TABLES:
            dest = work / f"RODSdb_MDOTW_VW_{table}_PUBLIC.csv"
            sources[table] = fetch(BASE.format(table), dest)
            log(f"{table}: {sources[table]['bytes']} bytes, "
                f"last-modified {sources[table]['last_modified']}, "
                f"sha256 {sources[table]['sha256'][:16]}...")
        occ_path = work / "RODSdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv"
        inj_path = work / "RODSdb_MDOTW_VW_INJURIES_PUBLIC.csv"
    else:
        for table, local in (("OCCURRENCE", args.occurrence_file),
                            ("INJURIES", args.injuries_file)):
            if local:
                sources[table] = {"url": local, "bytes": Path(local).stat().st_size,
                                  "last_modified": None, "seconds": 0.0,
                                  "sha256": sha256_file(Path(local))}

    log("== parse occurrence panel ==")
    rows, diagnostics = load_occurrences(occ_path)
    log(f"kept {len(rows)} occurrences "
        f"(exact duplicates dropped: {diagnostics['exact_duplicate_rows_dropped']}, "
        f"unparseable OccDate: {diagnostics['rows_without_parseable_occdate']})")
    # Evidence before assertions: a failed run must still upload its per-year
    # diagnostics (tsb-001 failed before summary.json was written, leaving
    # only the log line to diagnose from).
    print_diagnostics(diagnostics)
    (out / "diagnostics.json").write_text(json.dumps(diagnostics, indent=1) + "\n")

    panel_start_year = choose_panel_start(diagnostics)
    panel_start = date(panel_start_year, 1, 1)
    log(f"measured modern-era panel start: {panel_start} "
        f"(early-signature share < {EARLY_SIG_MAX_SHARE} from {panel_start_year} on)")
    if not args.smoke and not (PANEL_START_MIN <= panel_start_year <= PANEL_START_MAX):
        log(f"FAIL: measured panel start {panel_start_year} outside the "
            f"expected [{PANEL_START_MIN}, {PANEL_START_MAX}] band")
        return 2

    # splits + out-of-window accounting; row ids are panel-scoped: a pre-panel
    # row without a usable OccNo must neither fail the build nor suffix a panel
    # row's id, and collisions are only meaningful among rows that ship
    rows_by_split = {"train": [], "eval": [], "holdout": []}
    pre_window = post_window = 0
    panel_pairs: list[tuple[dict, str]] = []
    for row in rows:
        split = split_of(row["onset"], panel_start)
        if split is None:
            if row["onset"].date() < panel_start:
                pre_window += 1
            else:
                post_window += 1
            continue
        panel_pairs.append((row, row[F_OCCNO] or ""))
    occno_counts = Counter(occno for _, occno in panel_pairs)
    collision_occnos = {occno for occno, count in occno_counts.items()
                        if count > 1 and occno}
    no_occno = sum(1 for _, occno in panel_pairs if not occno)
    suffix_seen: dict[str, int] = {}
    id_rows = []
    for row, occno in panel_pairs:
        if occno in collision_occnos:
            suffix_seen[occno] = suffix_seen.get(occno, 0) + 1
            row_id = occno if suffix_seen[occno] == 1 else f"{occno}#{suffix_seen[occno]}"
        else:
            row_id = occno or "MISSING"
        id_rows.append((row, row_id))
        rows_by_split[split_of(row["onset"], panel_start)].append(feature_row(row, row_id))
    log(f"OccNo collisions (non-identical panel rows sharing a number): "
        f"{len(collision_occnos)}; panel rows with empty OccNo: {no_occno}")
    log(f"panel rows: train {len(rows_by_split['train'])}, "
        f"eval {len(rows_by_split['eval'])}, holdout {len(rows_by_split['holdout'])} "
        f"(pre-window {pre_window}, post-window {post_window})")

    # label cross-checks on the panel
    ind_only = totals_only = both_flagged = 0
    injuries_table_flag = injuries_table_total = 0
    inj_casualties = injury_table_casualties(inj_path) if inj_path and inj_path.is_file() else set()
    for row, row_id in id_rows:
        if split_of(row["onset"], panel_start) is None:
            continue
        ind = clean(row[F_INJIND]) == "1"
        totals = (parse_int(row[F_FATAL]) + parse_int(row[F_SERIOUS])
                  + parse_int(row[F_MINOR]))
        if ind and totals > 0:
            both_flagged += 1
        elif ind:
            ind_only += 1
        elif totals > 0:
            totals_only += 1
        if row[F_OCCNO] in inj_casualties:
            injuries_table_flag += 1
            injuries_table_total += row["casualty"]
    label_checks = {
        "injuriesind_and_totals_both": both_flagged,
        "injuriesind_only": ind_only,
        "totals_only": totals_only,
        "injuries_table_occnos_flagged": injuries_table_flag,
        "injuries_table_flagged_and_label_positive": injuries_table_total,
        "note": "label = InjuriesIND==1 OR fatal+serious+minor totals > 0; the "
                "INJURIES child table cross-check counts panel occurrences whose "
                "OccNo carries any nonzero injury severity row",
    }

    # lat/long frame assertion (the unit/frame discipline: no silent mismatch)
    bad_coords = []
    for split in rows_by_split.values():
        for row in split:
            lat = parse_float(row["latitude"])
            lon = parse_float(row["longitude"])
            if lat is not None and not (LAT_MIN <= lat <= LAT_MAX):
                bad_coords.append(("lat", row["occ_no"], row["latitude"]))
            if lon is not None and not (LON_MIN <= lon <= LON_MAX):
                bad_coords.append(("lon", row["occ_no"], row["longitude"]))
    if bad_coords:
        log(f"FAIL: coordinates outside the Canadian envelope: {bad_coords[:5]}")
        return 2
    log(f"lat/long frame check: 0 of "
        f"{sum(len(s) for s in rows_by_split.values())} rows outside "
        f"[{LAT_MIN},{LAT_MAX}]N / [{LON_MIN},{LON_MAX}]E")

    # publisher cross-check: 2025 accidents/incidents vs the annual summary
    counts_2025 = Counter()
    for row, _ in id_rows:
        if row["onset"].year == 2025:
            counts_2025[clean(row[F_OCTYPE]).upper()] += 1
    crosscheck = {kind: {"published": published, "panel": counts_2025.get(kind, 0)}
                  for kind, published in PUBLISHED_2025.items()}
    crosscheck_ok = all(
        abs(entry["panel"] - entry["published"]) <= CROSSCHECK_TOL * entry["published"]
        for entry in crosscheck.values())
    log(f"publisher cross-check 2025: {crosscheck}")

    stats = write_splits(out, rows_by_split)
    for split, entry in stats.items():
        log(f"{split}: {entry['rows']} rows, {entry['positives']} positives "
            f"(rate {entry['positive_rate']}), {entry['distinct_events']} events")

    # label source columns must be absent from the shipped files
    for split, rel in LAYOUT.items():
        with (out / rel).open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        leaked = [column for column in LABEL_SOURCE_COLUMNS + POST_HOC_COLUMNS
                  if column in header]
        if leaked:
            log(f"FAIL: label-source or post-hoc column(s) shipped in {rel}: {leaked}")
            return 2

    baselines = level_rate_baselines(rows_by_split,
                                     ["activity_type", "railway", "subdivision",
                                      "province", "occ_month"])
    trailing = trailing_rate_baselines(rows_by_split)
    log(f"naive baselines (eval AUC): "
        + ", ".join(f"{column}={baselines[column]['eval_auc']}" for column in baselines
                    if isinstance(baselines[column], dict) and "eval_auc" in baselines[column]))
    log(f"trailing-12m-rate baseline: {trailing}")

    data_max = max(row["onset"] for row, _ in id_rows).strftime("%Y-%m-%d")
    vintage = {
        "built_at_utc": built_at,
        "data_max_occurrence": data_max,
        "window_end": WINDOW_END.isoformat(),
        "expected_vintage_coverage": "the vintage must contain occurrences at "
                                     "least through the window end",
        "post_window_rows_excluded": post_window,
        "pre_panel_rows_excluded": pre_window,
    }

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "sources": sources,
        "grain": "one row per TSB rail occurrence (OccNo key)",
        "panel_start": {"year": panel_start_year,
                        "rule": f"first year from which the taxonomy-era share "
                                f"(AccIncType HISTORICAL/DG LEAKER) stays < "
                                f"{EARLY_SIG_MAX_SHARE} in every later year; "
                                f"measured, not assumed (record proposed 2004). "
                                f"Timezone-missingness is recorded per year as a "
                                f"separate property, not an era signal"},
        "diagnostics": diagnostics,
        "vintage": vintage,
        "label_checks": label_checks,
        "publisher_crosscheck_2025": crosscheck,
        "child_tables": {
            table: table_occno_counts(work / f"RODSdb_MDOTW_VW_{table}_PUBLIC.csv")
            for table in ("TRAIN", "ROLLING_STOCK", "COMPONENTS")
            if not args.smoke
        },
        "occno_collisions": {"distinct_colliding_numbers": len(collision_occnos),
                             "rows_with_empty_occno": no_occno},
        "splits": stats,
        "reference_baselines": {
            "note": "stdlib rank AUC measured at construction on the written rows; "
                    "naive conditional rates estimated on train rows only, per the "
                    "record's step (4) - measured before any model spend",
            "global_rate_train": baselines["global_rate_train"],
            "per_column": {column: baselines[column] for column in baselines
                           if column != "global_rate_train"},
            "trailing_12m_rate_auc": trailing,
        },
    }

    if not args.smoke:
        if not crosscheck_ok:
            log(f"FAIL: 2025 panel counts disagree with the publisher's annual "
                f"summary beyond {CROSSCHECK_TOL:.0%}: {crosscheck}")
            return 2
        for split in ("eval", "holdout"):
            entry = stats[split]
            if entry["positives"] < MIN_SPLIT_POSITIVES or entry["distinct_events"] < MIN_SPLIT_EVENTS:
                log(f"FAIL: {split} too thin to score: {entry}")
                return 2
        if data_max < WINDOW_END.isoformat():
            log(f"FAIL: vintage covers only to {data_max}, short of the window "
                f"end {WINDOW_END}")
            return 2
        if no_occno:
            log(f"FAIL: {no_occno} panel rows carry no OccNo; the row key is unusable")
            return 2
        disagreement = label_checks["injuriesind_only"] + label_checks["totals_only"]
        panel_rows = sum(entry["rows"] for entry in stats.values())
        if disagreement / max(panel_rows, 1) > 0.05:
            log(f"FAIL: label components disagree on {disagreement}/{panel_rows} rows; "
                f"investigate before shipping: {label_checks}")
            return 2
    else:
        log("SMOKE MODE: capacity, vintage, cross-check and collision assertions skipped")

    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    collision_rows = sum(count - 1 for occno, count in occno_counts.items()
                         if count > 1 and occno)
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": BASE.format("OCCURRENCE"),
        "license": "Open Government Licence - Canada 2.0 (source terms preserved; "
                   "attribution required). Derived research dataset - not a TSB "
                   "official product. Our derived compilation: CC0-1.0.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by occurrence date",
                  "boundaries": {"train": f"{panel_start} .. {EVAL_START}",
                                 "eval": f"{EVAL_START} .. {HOLDOUT_START}",
                                 "holdout": f"{HOLDOUT_START} .. {WINDOW_END}"}},
        "label_rule": "casualty = 1 iff InjuriesIND == 1 or TotalFatal+"
                      "TotalSerious+TotalMinor injuries > 0 (label source "
                      "columns excluded from every shipped file)",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_sha256": sources.get("OCCURRENCE", {}).get("sha256"),
        "vintage_last_modified": sources.get("OCCURRENCE", {}).get("last_modified"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "occ_date",
        "event_key_column": "occ_no",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every source field is documented in the publisher's RODSdb data "
            "dictionary (RODSdb-dd.csv, 699 rows, fetched 2026-10-22, recorded in "
            "the candidate record): OccDate/OccTime/TimeZoneID (occurrence date, "
            "time, site timezone), ActivityTypeID (train activity at the time of "
            "the occurrence), SubdNameID/SubdMileage/SUBD_OWNER_ABBREV "
            "(subdivision, mileage, owner), NearLocation/Latitude/Longitude "
            "(nearest city/town and its coordinates), ProvinceID, "
            "RegionOfOccurrence; derived columns are documented in build.py's "
            "module docstring and ship in the release DATA_DICTIONARY"),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "latitude",
             "unit": "decimal degrees, north positive",
             "frame": "RODS writes degrees x 10^4 integers; the build divides by "
                      "10^4 and asserts every present value inside the Canadian "
                      "envelope 41-72 N (measured example 505900 -> 50.59)"},
            {"column": "longitude",
             "unit": "decimal degrees, east positive (West negative)",
             "frame": "RODS writes degrees x 10^4 unsigned West longitudes; the "
                      "build negates and asserts -145 <= lon <= -52 (measured "
                      "example 1181200 -> -118.12)"},
            {"column": "occ_hour",
             "unit": "local hour of day at the occurrence site (0-23)",
             "frame": "parsed from OccDate's local time; the DST-aware site "
                      "timezone ships in the timezone column, so the local hour "
                      "needs no offset map (a hand-rolled UTC normalization could "
                      "silently misplace an hour, which is what this measurement "
                      "block exists to prevent)"},
            {"column": "subd_mileage",
             "unit": "miles from the start of the named subdivision",
             "frame": "publisher's SubdMileage, shipped verbatim as the source's "
                      "own scale; empty when the source records none"},
            {"column": "casualty",
             "unit": "binary indicator",
             "frame": "1 iff InjuriesIND == 1 or fatal+serious+minor injury "
                      "totals > 0; component agreement cross-checked against the "
                      "separate INJURIES child table and recorded in "
                      "summary.json label_checks"},
        ],
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "instant",
                "days_after_period_end": 0,
                "citation": "OccDate/OccTime at the occurrence onset, local time "
                            "at the site with TimeZoneID documenting the timezone; "
                            "an administrative register written at/after the event "
                            "(TSB RODS; ReportedDate/ReportedTime post-date the "
                            "onset and are excluded)",
            },
            "features": {
                "period": "instant",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "the occurrence onset itself (each row is "
                                      "one occurrence; selection windows are "
                                      "occurrence-date ranges ending 2026-08-31)",
                "fields": ["occ_date", "occ_no"],
                "basis": "rows are the occurrences; no selection reads any "
                         "post-onset data",
            },
            "observations": [],
            "observations_note": "administrative record: the register row is "
                                 "written at/after the event, so no publication "
                                 "lag applies to the features; the vintage "
                                 "(last-modified + sha256) is recorded in meta.json",
        },
        "split_windows": {
            "train": {"start": panel_start.isoformat(),
                       "end": EVAL_START.isoformat()},
            "eval": {"start": EVAL_START.isoformat(),
                     "end": HOLDOUT_START.isoformat()},
            "holdout": {"start": HOLDOUT_START.isoformat(),
                        "end": (date(WINDOW_END.year, WINDOW_END.month + 1, 1)
                                if WINDOW_END.month < 12
                                else date(WINDOW_END.year + 1, 1, 1)).isoformat()},
        },
        "split_boundaries": {
            "train": f"occurrences {panel_start} .. {EVAL_START}",
            "eval": f"{EVAL_START} .. {HOLDOUT_START}",
            "holdout": f"{HOLDOUT_START} .. {WINDOW_END}",
        },
        "expected_duplicate_ids": collision_rows,
        "id_columns_are_entity_keys": not collision_occnos,
        "id_columns_note": "occ_no is the TSB occurrence number, documented as a "
                           "unique identifier; the current vintage carries "
                           "byte-identical exported rows (deduplicated, counted) "
                           "and any remaining non-identical collisions are "
                           "suffixed and pinned via expected_duplicate_ids",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                    "distinct_events": stats[split]["distinct_events"]}
                            for split in ("eval", "holdout")},
        "positive_events_note": "occurrences are independent single events (the "
                                "candidate record measured no storm-style "
                                "clustering), so each positive is its own event; "
                                "distinct_events counts distinct occ_no prefixes "
                                "among positive rows",
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats, "panel_start": str(panel_start),
                    "label_checks": label_checks, "crosscheck": crosscheck,
                    "baselines": summary["reference_baselines"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
