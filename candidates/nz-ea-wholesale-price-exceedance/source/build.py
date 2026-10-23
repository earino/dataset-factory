#!/usr/bin/env python3
"""Construction script for the `nz-ea-wholesale-price-exceedance` candidate.

Task: the Electricity Authority (Te Mana Hiko) publishes final wholesale energy
prices per point of connection (POC) and trading period. At the publication
instant of the final prices for trading day D - conservatively bounded at
D + 6 calendar days, which covers the maximum daily-file publication lag
measured on this channel - given the published island daily mean prices for
trading days up to and including D, will the island daily mean final price on
trading day D+7 exceed NZD 100/MWh?

Where this runs
---------------
On a temporary worker. The construction channel is the publisher's anonymous
Azure blob container (documented by the forum thread "New access arrangements
to EMI datasets (retirement of anonymous FTP)"):

  * container listing (one request, all blobs)
  * monthly files  ``.../FinalEnergyPrices/ByMonth/YYYYMM_FinalEnergyPrices.csv``
    (199610..202609, ~8-11 MB each) - own trading dates <= 2025-10-31
  * daily files   ``.../FinalEnergyPrices/YYYYMMDD_FinalEnergyPrices.csv``
    (2025-10-22..now, ~0.33 MB each) - own trading dates  > 2025-10-31
  * ``..._I.csv`` (interim) and ``..._incomplete.csv`` variants are excluded and
    counted: the instant is FINAL price publication, and an incomplete file is
    not the publisher's final statement of the period.
  * NetworkSupplyPointsTable (POC code -> Island NI/SI, with validity dates).

Channel ownership prevents double counting: the ten overlap days
2025-10-22..31 exist in both channels; the monthly aggregate owns them and the
daily aggregate for those days is kept only for a cross-channel consistency
check. Each file is downloaded, stream-parsed, aggregated, and deleted before
the next, so peak disk holds one file at a time.

Frame rules (each measured and reported, never assumed)
------------------------------------------------------
* Grain: one row per (island, anchor trading day D). Row key ``row_id`` =
  ``{island}-{anchor_date}``.
* Prediction instant: publication of day D's final prices. The documented
  instrument (publisher's dispatch-and-pricing page) says interim prices
  "will be declared to be final prices by 2pm the following business day";
  measured on the daily-file channel, Last-Modified minus trade date is 0-5
  calendar days over 365+ files. The instant is therefore placed at
  D + INSTANT_LAG_DAYS (6) calendar days: every feature (final prices for
  trading days <= D) is published by then under the measured maximum, and the
  target day D+7 has not even finished trading at the instant, so its mean
  cannot exist there under any publication scheme.
* Features: island daily mean prices for trading days <= D only (30-day
  trailing window), the cross-island ratio, and the anchor day's calendar
  position. Nothing after day D is read for features.
* Label: island daily mean of DollarsPerMegawattHour over the target day
  D+7 exceeds NZD 100/MWh (threshold frozen from the training-window design;
  the candidate record measured candidate levels 100/150/200/300 on era
  samples; NZD 100 keeps clustered positive weeks measurable in every split
  while remaining roughly twice the long-run median - decision recorded in
  quality.json, never tuned on a held-out score).
* Population: rows are emitted for anchor days where BOTH islands' means are
  available for all of D-29..D (availability only, no label information). A
  missing target-day mean is missing outcome data: counted as
  ``unobserved_target`` per split and excluded, never used to decide another
  row's membership.
* Splits: temporal on the anchor day - train (start..2015-12-31), eval
  (2016-01-01..2022-10-31), holdout (2022-11-01..). The eval->holdout
  boundary coincides with the documented 2022-11-01 real-time pricing regime
  change, so no window straddles the structural break; the holdout is a
  different pricing regime by design and per-year reference reporting is
  mandatory when interpreting it.
* Event clustering: positives arrive in multi-day dry-year/storage episodes.
  ``target_week`` (ISO week of the target day, market-wide, so both islands
  share one key) is the event key; weeks inside one long crisis are not fully
  independent and the count is a capacity floor, not an independence proof.
* Leakage discipline: the target day's prices are the label source and are
  never shipped; every shipped column is derived from trading days <= D or
  the calendar. Absence is asserted in each written header.
* Known-event fixtures (real mode only, asserted from the built panel):
  August 2024 dry-year episode (Authority's Review of winter 2024: "in early
  August the average daily price reached $820/MWh"; record-measured market
  daily means 2024-08-05..08-08 of 815-884) must exceed the threshold;
  2008-07-01 (record-measured market mean 306; "severe hydro shortage during
  the winter" in the Authority's wholesale review) must exceed; January 1997
  (record-measured monthly max 50) must not exceed.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: CC BY 4.0 (EMI LegalInformation and the successor hub's copyright
statement; attribution "www.emi.ea.govt.nz provided by the Electricity
Authority (New Zealand)"). Our derived compilation is dedicated CC0-1.0; this
is a derived research dataset, never the Authority's official product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

NAME = "nz-ea-wholesale-price-exceedance"
TARGET = "target_high_price"
POSITIVE_LABEL = 1
ROW_ID = "row_id"
ANCHOR_DATE = "anchor_date"
TARGET_WEEK = "target_week"
ISLAND = "island"

THRESHOLD_NZD_MWH = 100.0
HORIZON_DAYS = 7
HISTORY_DAYS = 30
INSTANT_LAG_DAYS = 6          # conservative bound over the measured max lag
MONTHLY_LAST_DATE = date(2025, 10, 31)   # monthly channel owns trading dates <= this
DAILY_FIRST_DATE = MONTHLY_LAST_DATE + timedelta(days=1)
OVERLAP_FIRST = date(2025, 10, 22)       # daily channel also covers these, kept for the check

CONTAINER = "https://emidatasets.blob.core.windows.net/publicdata"
LISTING_URL = (CONTAINER + "?restype=container&comp=list"
               "&prefix=Datasets/Wholesale/DispatchAndPricing/FinalEnergyPrices/"
               "&maxresults=5000")
NSP_URL = (CONTAINER + "/Datasets/Wholesale/MappingsAndGeospatial/"
           "NetworkSupplyPointsTable/20261021_NetworkSupplyPointsTable.csv")
UA = "dataset-factory-scout/1.0 (+https://github.com/earino/dataset-factory)"

MONTHLY_RE = re.compile(r"^(\d{6})_FinalEnergyPrices\.csv$")
DAILY_RE = re.compile(r"^(\d{8})_FinalEnergyPrices\.csv$")

# Real split boundaries on the anchor day. The eval->holdout boundary is the
# documented 2022-11-01 real-time pricing regime change.
REAL_BOUNDARIES = {"train": date(2015, 12, 31), "eval": date(2022, 10, 31)}
FIXTURE_BOUNDARIES = {"train": date(2024, 12, 31), "eval": date(2025, 12, 31)}

FEATURES = [
    ISLAND,
    "last_day_mean",
    "mean_7d",
    "mean_30d",
    "max_30d",
    "std_7d",
    "days_above_threshold_30d",
    "cross_island_ratio_7d",
    "anchor_month",
    "anchor_dow",
    "anchor_doy_sin",
    "anchor_doy_cos",
]
CARRY_COLUMNS = [ANCHOR_DATE, TARGET_WEEK]
ID_COLUMNS = [ROW_ID]
HIGH_CARDINALITY = [ANCHOR_DATE]
LABEL_SOURCE_COLUMNS = [
    "target_day_island_mean_price",
    "target_day_DollarsPerMegawattHour_rows",
]
POST_HOC_COLUMNS = []
# One column list, in one place: CARRY_COLUMNS + FEATURES must never overlap.
COLUMNS = [ROW_ID, TARGET] + CARRY_COLUMNS + FEATURES

LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

PREDICTION_QUESTION = (
    "For a New Zealand electricity island, at the publication instant of the "
    "final wholesale energy prices for trading day D (conservatively D + 6 "
    "calendar days, covering the maximum publication lag measured on the "
    "publisher's daily-file channel), given the published island daily mean "
    "final prices for trading days up to and including D, will the island "
    "daily mean final price on trading day D+7 exceed NZD 100/MWh?")

PREDICTION_TIME = (
    "the publication instant of final prices for trading day D. The Authority "
    "documents that interim prices 'will be declared to be final prices by "
    "2pm the following business day'; measured on the daily-file channel, "
    "Last-Modified minus trade date is 0-5 calendar days over 365+ files, so "
    "the instant is placed at D + 6 calendar days. Features are final prices "
    "for trading days <= D; the target trading day D+7 has not finished "
    "trading at the instant, so its price cannot exist there.")


def log(message: str) -> None:
    print(f"[build] {message}", flush=True)


def fetch(url: str, path: Path | None, max_bytes: int | None = None) -> tuple[int, str, str]:
    """Stream a URL (optionally to disk); return (bytes, sha256, last-modified)."""
    digest = hashlib.sha256()
    total = 0
    modified = ""
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=300) as response:
        modified = response.headers.get("Last-Modified") or ""
        sink = path.open("wb") if path else None
        try:
            while True:
                chunk = response.read(4 * 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise SystemExit(f"refusing to buffer more than {max_bytes} bytes from {url}")
                if sink:
                    sink.write(chunk)
        finally:
            if sink:
                sink.close()
    return total, digest.hexdigest(), modified


def http_date(value: str) -> date | None:
    for pattern in ("%a, %d %b %Y %H:%M:%S GMT", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def parse_listing(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    blobs = []
    for blob in root.iter("Blob"):
        name = (blob.findtext("Name") or "").strip()
        properties = blob.find("Properties")
        blobs.append({
            "name": name,
            "bytes": int((properties.findtext("Content-Length") if properties is not None
                           else "0") or "0"),
            "last_modified": ((properties.findtext("Last-Modified") if properties is not None
                               else "") or "").strip(),
        })
    return blobs


def load_island_mapping(rows) -> tuple[dict[str, str], Counter]:
    """POC code -> island from the NSP table (any validity row; island is a
    physical property of a connection point). Conflicts and coverage are counted."""
    mapping: dict[str, Counter] = {}
    stats: Counter = Counter()
    seen_rows = 0
    for row in rows:
        seen_rows += 1
        code = (row.get("POC code") or "").strip()
        island = (row.get("Island") or "").strip().upper()
        if not code or island not in ("NI", "SI"):
            stats["nsp_row_without_island"] += 1
            continue
        mapping.setdefault(code, Counter())[island] += 1
    resolved: dict[str, str] = {}
    for code, counter in mapping.items():
        if len(counter) > 1:
            stats["poc_island_conflicts"] += 1
        resolved[code] = counter.most_common(1)[0][0]
    stats["nsp_rows"] = seen_rows
    stats["nsp_distinct_pocs"] = len(resolved)
    return resolved, stats


def aggregate_price_file(path: Path, island_of: dict[str, str], stats: Counter,
                         island_day: dict, market_day: dict, unmapped_by_year: Counter,
                         own_from: date | None = None,
                         overlap: dict | None = None) -> tuple[int, date | None, date | None]:
    """Stream one price CSV into the accumulators.

    ``own_from`` is the first trading date this file's channel owns; rows for
    earlier dates are skipped for the panel but, when they fall inside the
    measured overlap window, still collected into ``overlap`` so the two
    channels can be compared day by day.
    """
    rows = 0
    first_date = last_date = None
    duplicate_points = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return 0, None, None
        if header[:4] != ["TradingDate", "TradingPeriod", "PointOfConnection",
                          "DollarsPerMegawattHour"]:
            raise SystemExit(f"unexpected header in {path.name}: {header[:6]}")
        for row in reader:
            rows += 1
            if len(row) < 4:
                stats["ragged_rows"] += 1
                continue
            trading_date_text, period, poc, price_text = row[0], row[1], row[2].strip(), row[3]
            try:
                trading_date = date.fromisoformat(trading_date_text)
            except ValueError:
                stats["unparseable_date_rows"] += 1
                continue
            try:
                price = float(price_text)
            except ValueError:
                stats["empty_price_rows"] += 1
                continue
            key = (trading_date_text, period, poc)
            if key in duplicate_points:
                stats["duplicate_points"] += 1
            duplicate_points.add(key)
            if first_date is None or trading_date < first_date:
                first_date = trading_date
            if last_date is None or trading_date > last_date:
                last_date = trading_date
            in_overlap = (overlap is not None
                          and OVERLAP_FIRST <= trading_date <= MONTHLY_LAST_DATE)
            if own_from is not None and trading_date < own_from:
                if in_overlap and overlap is not None:
                    slot = market_day.setdefault(("daily", trading_date), [0.0, 0])
                    slot[0] += price
                    slot[1] += 1
                    island = island_of.get(poc)
                    if island:
                        slot = overlap.setdefault((island, trading_date), [0.0, 0])
                        slot[0] += price
                        slot[1] += 1
                continue
            slot = market_day.setdefault(("monthly", trading_date), [0.0, 0])
            slot[0] += price
            slot[1] += 1
            island = island_of.get(poc)
            if island is None:
                unmapped_by_year[trading_date.year] += 1
                stats["unmapped_poc_rows"] += 1
                continue
            slot = island_day.setdefault((island, trading_date), [0.0, 0])
            slot[0] += price
            slot[1] += 1
    return rows, first_date, last_date


def week_key(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", default="/tmp/nz")
    parser.add_argument("--fixture-dir", default=None,
                        help="read synthetic NSP + price CSVs from a directory instead of the network")
    parser.add_argument("--built-at", default=None)
    args = parser.parse_args()

    fixture = bool(args.fixture_dir)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    stats: Counter = Counter()
    unmapped_by_year: Counter = Counter()
    sources: dict[str, dict] = {}
    island_day: dict[tuple, list] = {}
    market_day: dict[tuple, list] = {}     # keyed ("monthly"|"daily", date)
    daily_overlap: dict[tuple, list] = {}  # (island, date) -> [sum, count]
    monthly_files: list[dict] = []
    daily_files: list[dict] = []
    excluded_blobs: Counter = Counter()
    listing_observed: dict[str, dict] = {}

    if fixture:
        fixture_dir = Path(args.fixture_dir)
        with (fixture_dir / "nsp.csv").open(newline="", encoding="utf-8-sig") as handle:
            island_of, nsp_stats = load_island_mapping(csv.DictReader(handle))
        stats.update(nsp_stats)
        sources["nsp_table"] = {"origin": "fixture",
                                "bytes": (fixture_dir / "nsp.csv").stat().st_size}
        for path in sorted(fixture_dir.glob("*.csv")):
            if path.name == "nsp.csv":
                continue
            if MONTHLY_RE.match(path.name):
                monthly_files.append({"name": path.name, "path": path,
                                      "bytes": path.stat().st_size})
            elif DAILY_RE.match(path.name):
                daily_files.append({"name": path.name, "path": path,
                                    "bytes": path.stat().st_size})
        log(f"fixture: {len(monthly_files)} monthly + {len(daily_files)} daily files "
            f"from {fixture_dir}")
    else:
        log("fetching container listing")
        listing_path = work / "listing.xml"
        listing_bytes, listing_digest, _ = fetch(LISTING_URL, listing_path)
        sources["container_listing"] = {"url": LISTING_URL, "bytes": listing_bytes,
                                        "sha256": listing_digest}
        blobs = parse_listing(listing_path.read_bytes())
        listing_path.unlink()
        log(f"listing: {len(blobs)} blobs")
        for blob in blobs:
            leaf = blob["name"].rsplit("/", 1)[-1]
            listing_observed[leaf] = blob
            if MONTHLY_RE.match(leaf):
                monthly_files.append({"name": leaf, "url": CONTAINER + "/" + blob["name"]})
            elif DAILY_RE.match(leaf):
                daily_files.append({"name": leaf, "url": CONTAINER + "/" + blob["name"]})
            elif "_I" in leaf:
                excluded_blobs["interim_variant"] += 1
            elif "incomplete" in leaf:
                excluded_blobs["incomplete_variant"] += 1
            else:
                excluded_blobs["other_variant"] += 1
        log(f"monthly: {len(monthly_files)}, daily: {len(daily_files)}, "
            f"excluded: {dict(excluded_blobs)}")

        nsp_path = work / "nsp.csv"
        nsp_bytes, nsp_digest, nsp_modified = fetch(NSP_URL, nsp_path)
        sources["nsp_table"] = {"url": NSP_URL, "bytes": nsp_bytes, "sha256": nsp_digest,
                                "last_modified": nsp_modified,
                                "note": "current-vintage mapping file; POCs absent from it "
                                        "are excluded from island aggregation and counted "
                                        "per year"}
        with nsp_path.open(newline="", encoding="utf-8-sig") as handle:
            island_of, nsp_stats = load_island_mapping(csv.DictReader(handle))
        stats.update(nsp_stats)
        nsp_path.unlink()
        log(f"NSP mapping: {stats['nsp_distinct_pocs']} POCs, "
            f"{stats['poc_island_conflicts']} island conflicts")

    # ---- download + aggregate, one file at a time -------------------------
    use_monthly = []
    for entry in monthly_files:
        match = MONTHLY_RE.match(entry["name"])
        if match and match.group(1) <= "202510":   # later months: owned by the daily channel
            use_monthly.append(entry)

    started = time.time()
    processed = 0
    for label, entries, own_from in (
            ("monthly", sorted(use_monthly, key=lambda e: e["name"]), None),
            ("daily", sorted(daily_files, key=lambda e: e["name"]), DAILY_FIRST_DATE)):
        for entry in entries:
            if fixture:
                path, digest, modified, size = entry["path"], "", "", entry["bytes"]
            else:
                path = work / entry["name"]
                size, digest, modified = fetch(entry["url"], path)
                entry["sha256"] = digest
                entry["last_modified"] = modified
                entry["bytes"] = size
            rows, first_date, last_date = aggregate_price_file(
                path, island_of, stats, island_day, market_day, unmapped_by_year,
                own_from=own_from, overlap=daily_overlap)
            if not fixture:
                path.unlink()
            processed += 1
            sources[f"price_file:{entry['name']}"] = {
                "bytes": size, "sha256": digest, "last_modified": modified,
                "rows": rows,
                "first_date": str(first_date) if first_date else None,
                "last_date": str(last_date) if last_date else None,
            }
            if processed % 25 == 0:
                log(f"  processed {processed} files ({time.time() - started:.0f}s)")
    log(f"aggregated {processed} price files in {time.time() - started:.0f}s; "
        f"mapped island-day (POC x period) rows: {sum(v[1] for v in island_day.values()):,}")

    # ---- coverage ---------------------------------------------------------
    all_days = sorted({day for (_island, day) in island_day})
    if not all_days:
        log("FAIL: no island-day data at all")
        return 2
    first_trade, last_trade = all_days[0], all_days[-1]
    expected = (last_trade - first_trade).days + 1
    missing_days = expected - len(all_days)
    coverage = len(all_days) / expected
    log(f"coverage: {len(all_days)}/{expected} days ({coverage:.4f}), "
        f"first {first_trade}, last {last_trade}")
    per_island_days = Counter(island for (island, _day) in island_day)
    boundaries = FIXTURE_BOUNDARIES if fixture else REAL_BOUNDARIES

    first_anchor = first_trade + timedelta(days=HISTORY_DAYS - 1)
    last_anchor = last_trade - timedelta(days=HORIZON_DAYS)
    if last_anchor <= first_anchor:
        log("FAIL: not enough history for any anchor row")
        return 2

    island_mean = {key: total / count for key, (total, count) in island_day.items() if count}
    market_mean = {day: total / count
                   for (channel, day), (total, count) in market_day.items()
                   if channel == "monthly" and count}
    daily_market_mean = {day: total / count
                         for (channel, day), (total, count) in market_day.items()
                         if channel == "daily" and count}

    # monthly-vs-daily channel consistency on the overlap days (real mode)
    channel_consistency = {"days_compared": 0, "max_abs_island_mean_diff": None,
                           "max_abs_market_mean_diff": None}
    if not fixture and daily_overlap:
        max_island_diff = 0.0
        max_market_diff = 0.0
        days_compared = 0
        for (island, day), (total, count) in sorted(daily_overlap.items()):
            monthly_value = island_mean.get((island, day))
            daily_value = total / count
            if monthly_value is None:
                continue
            days_compared += 1
            max_island_diff = max(max_island_diff, abs(monthly_value - daily_value))
        for day in sorted(set(day for (_island, day) in daily_overlap)):
            if day in market_mean and day in daily_market_mean:
                max_market_diff = max(max_market_diff,
                                      abs(market_mean[day] - daily_market_mean[day]))
        channel_consistency = {"days_compared": days_compared,
                               "max_abs_island_mean_diff": round(max_island_diff, 6),
                               "max_abs_market_mean_diff": round(max_market_diff, 6)}
        log(f"channel consistency over {days_compared} island-days: "
            f"max |monthly-daily| island mean diff {max_island_diff:.6f}")
        if days_compared and max_island_diff > 0.01:
            log("FAIL: monthly and daily channels disagree on the overlap days "
                f"(max island mean diff {max_island_diff:.6f} > 0.01)")
            return 2

    # ---- panel construction ------------------------------------------------
    rows_by_split: dict[str, list[dict]] = {key: [] for key in LAYOUT}
    buckets: dict[str, Counter] = {key: Counter() for key in LAYOUT}

    def split_for(anchor: date) -> str:
        if anchor <= boundaries["train"]:
            return "train"
        if anchor <= boundaries["eval"]:
            return "eval"
        return "holdout"

    history_offsets = list(range(HISTORY_DAYS))
    anchor = first_anchor
    while anchor <= last_anchor:
        split = split_for(anchor)
        history = [anchor - timedelta(days=offset) for offset in history_offsets]
        history_ok = all((island, day) in island_mean
                         for island in ("NI", "SI") for day in history)
        if not history_ok:
            buckets[split]["missing_history"] += 2   # both islands' rows dropped
        else:
            means = {island: [island_mean[(island, day)] for day in history]
                     for island in ("NI", "SI")}
            target_day = anchor + timedelta(days=HORIZON_DAYS)
            for island in ("NI", "SI"):
                if (island, target_day) not in island_mean:
                    buckets[split]["unobserved_target"] += 1
                    continue
                own, other = means[island], means["SI" if island == "NI" else "NI"]
                mean_7d_own = statistics.fmean(own[:7])
                mean_7d_other = statistics.fmean(other[:7])
                if abs(mean_7d_other) < 1e-9:
                    stats["zero_other_island_mean"] += 1
                row = {
                    ROW_ID: f"{island}-{anchor.isoformat()}",
                    TARGET: 1 if island_mean[(island, target_day)] > THRESHOLD_NZD_MWH else 0,
                    ISLAND: island,
                    ANCHOR_DATE: anchor.isoformat(),
                    TARGET_WEEK: week_key(target_day),
                    "last_day_mean": round(own[0], 6),
                    "mean_7d": round(mean_7d_own, 6),
                    "mean_30d": round(statistics.fmean(own), 6),
                    "max_30d": round(max(own), 6),
                    "std_7d": round(statistics.pstdev(own[:7]), 6),
                    "days_above_threshold_30d": sum(1 for value in own
                                                    if value > THRESHOLD_NZD_MWH),
                    "cross_island_ratio_7d": round(mean_7d_own / mean_7d_other, 6)
                                             if abs(mean_7d_other) >= 1e-9 else "",
                    "anchor_month": anchor.month,
                    "anchor_dow": anchor.weekday(),
                    "anchor_doy_sin": round(math.sin(2 * math.pi
                                                     * anchor.timetuple().tm_yday / 365.25), 6),
                    "anchor_doy_cos": round(math.cos(2 * math.pi
                                                     * anchor.timetuple().tm_yday / 365.25), 6),
                }
                rows_by_split[split].append(row)
        anchor += timedelta(days=1)

    # ---- known-event fixtures (real source only) ---------------------------
    fixtures = []
    if not fixture:
        def market_on(day: date) -> float:
            if day not in market_mean:
                log(f"FAIL: fixture day {day} missing from the panel")
                return float("nan")
            return market_mean[day]

        checks = []
        for day in (date(2024, 8, 5), date(2024, 8, 6), date(2024, 8, 7), date(2024, 8, 8)):
            checks.append((day, (700.0, 1000.0), "exceeds",
                           "August 2024 dry-year episode (Authority Review of winter 2024: "
                           "'in early August the average daily price reached $820/MWh'; "
                           "record-measured means 815-884)"))
        checks.append((date(2008, 7, 1), (250.0, 360.0), "exceeds",
                       "July 2008 dry winter (record-measured market mean 306; Authority "
                       "wholesale review: '2008, when there was a severe hydro shortage "
                       "during the winter')"))
        fixture_ok = True
        for day, (low, high), verdict, name in checks:
            value = market_on(day)
            ok = low <= value <= high and (
                value > THRESHOLD_NZD_MWH if verdict == "exceeds"
                else value <= THRESHOLD_NZD_MWH)
            fixtures.append({"name": name, "day": day.isoformat(),
                             "market_daily_mean": round(value, 2),
                             "expected_range": [low, high], "expected_verdict": verdict,
                             "ok": bool(ok)})
            if not ok:
                fixture_ok = False
        jan_1997 = [market_mean[day] for day in market_mean
                    if date(1997, 1, 1) <= day <= date(1997, 1, 31)]
        jan_max = max(jan_1997) if jan_1997 else None
        control_ok = jan_max is not None and jan_max <= THRESHOLD_NZD_MWH
        fixtures.append({"name": "January 1997 quiet-era control (record-measured monthly max 50)",
                         "window": "1997-01",
                         "market_daily_mean_max": round(jan_max, 2) if jan_max is not None else None,
                         "expected_verdict": "below", "ok": bool(control_ok)})
        log(f"known-event fixtures: {json.dumps(fixtures)}")
        if not fixture_ok or not control_ok:
            return 2

    # ---- write splits -------------------------------------------------------
    written_stats = {}
    for split, relative in LAYOUT.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = rows_by_split[split]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in COLUMNS})
        positives = [row for row in rows if row[TARGET] == POSITIVE_LABEL]
        positive_weeks = {row[TARGET_WEEK] for row in positives}
        written_stats[split] = {
            "rows": len(rows),
            "positives": len(positives),
            "positive_rate": round(len(positives) / len(rows), 6) if rows else None,
            "distinct_positive_target_weeks": len(positive_weeks),
        }
        log(f"{split}: {written_stats[split]}")

    # publication-lag observations from the daily-file channel
    observations = []
    daily_lag_summary: dict = {}
    if fixture:
        observations = [
            {"period": "2026-06-28", "period_end": "2026-06-28", "published": "2026-06-29",
             "note": "synthetic fixture observation standing in for the measured channel"},
            {"period": "2026-06-29", "period_end": "2026-06-29", "published": "2026-07-02",
             "note": "synthetic fixture observation"},
        ]
    else:
        lags = []
        for name, blob in sorted(listing_observed.items()):
            match = DAILY_RE.match(name)
            if not match:
                continue
            stamp = match.group(1)
            trade = date.fromisoformat(f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}")
            published = http_date(blob["last_modified"])
            if published and published >= trade:
                lags.append((published - trade).days, trade, published, name)
        if lags:
            lag_days = sorted(lag for lag, *_ in lags)
            counter = Counter(lag_days)
            daily_lag_summary = {"files": len(lag_days), "min": min(lag_days),
                                 "max": max(lag_days), "distribution": dict(counter)}
            log(f"daily channel lags over {len(lag_days)} files: min {min(lag_days)}, "
                f"max {max(lag_days)}")
            chosen: dict[str, dict] = {}
            for lag, trade, published, name in sorted(lags, key=lambda item: item[1])[-8:]:
                chosen[name] = {"period": trade.isoformat(), "period_end": trade.isoformat(),
                                "published": published.isoformat(), "source_file": name}
            for lag, trade, published, name in sorted(lags, key=lambda item: -item[0])[:3]:
                chosen.setdefault(name, {"period": trade.isoformat(),
                                         "period_end": trade.isoformat(),
                                         "published": published.isoformat(),
                                         "source_file": name})
            observations = list(chosen.values())
        else:
            log("FAIL: no daily-file publication lags could be measured")
            return 2

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "mode": "fixture" if fixture else "source",
        "threshold_nzd_mwh": THRESHOLD_NZD_MWH,
        "horizon_days": HORIZON_DAYS,
        "history_days": HISTORY_DAYS,
        "instant_lag_days": INSTANT_LAG_DAYS,
        "threshold_decision": (
            "NZD 100/MWh fixed from the training-window design: the candidate record "
            "measured candidate levels on era samples (2020-06: 28/12/5/0 days above "
            "100/150/200/300), and the Authority's own review records 2019 average spot "
            "price $127/MWh and 2020 $105/MWh, so NZD 100 keeps clustered positive weeks "
            "measurable in every split while remaining roughly twice the long-run median; "
            "it was chosen before construction and never tuned on a held-out score"),
        "coverage": {
            "first_trading_day": str(first_trade), "last_trading_day": str(last_trade),
            "calendar_days_expected": expected, "days_present": len(all_days),
            "missing_days": missing_days, "day_coverage_ratio": round(coverage, 6),
            "island_days": dict(per_island_days),
        },
        "unmapped_poc_rows_by_year": dict(sorted(unmapped_by_year.items())),
        "unmapped_poc_rows_total": stats["unmapped_poc_rows"],
        "nsp_stats": {key: stats[key] for key in
                      ("nsp_rows", "nsp_distinct_pocs", "poc_island_conflicts",
                       "nsp_row_without_island", "zero_other_island_mean") if key in stats},
        "row_stats": {key: stats[key] for key in
                      ("ragged_rows", "unparseable_date_rows", "empty_price_rows",
                       "duplicate_points", "unmapped_poc_rows", "zero_other_island_mean")
                      if key in stats},
        "excluded_blob_variants": dict(excluded_blobs),
        "channel_consistency_overlap_2025_10_22_31": channel_consistency,
        "daily_channel_lag_days": daily_lag_summary,
        "splits": written_stats,
        "split_buckets": {split: dict(counter) for split, counter in buckets.items()},
        "known_event_fixtures": fixtures,
        "price_files_processed": processed,
        "sources": sources,
    }

    # capacity assertions (mirror of the gate minimums)
    problems = []
    for split in ("train", "eval", "holdout"):
        if written_stats[split]["rows"] == 0:
            problems.append(f"{split} has no rows")
    for split in ("eval", "holdout"):
        if written_stats[split]["positives"] < 30:
            problems.append(f"{split} has {written_stats[split]['positives']} positives (<30)")
        if written_stats[split]["distinct_positive_target_weeks"] < 20:
            problems.append(f"{split} has "
                            f"{written_stats[split]['distinct_positive_target_weeks']} "
                            f"distinct positive target weeks (<20)")
    if not fixture:
        if coverage < 0.98:
            problems.append(f"day coverage {coverage:.4f} < 0.98")
        unmapped_total = stats["unmapped_poc_rows"]
        mapped_total = sum(v[1] for v in island_day.values())
        if mapped_total and unmapped_total / (unmapped_total + mapped_total) > 0.15:
            problems.append(f"unmapped POC row share "
                            f"{unmapped_total / (unmapped_total + mapped_total):.3f} > 0.15")
        if str(first_trade) != "1996-10-01":
            problems.append(f"first trading day {first_trade} != 1996-10-01")
    if problems:
        summary["capacity_problems"] = problems
        (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        log("FAIL: " + "; ".join(problems))
        return 2

    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    # ---- meta.json + quality.json ------------------------------------------
    windows = {
        "train": {"start": first_anchor.isoformat(),
                  "end": (boundaries["train"] + timedelta(days=1)).isoformat()},
        "eval": {"start": (boundaries["train"] + timedelta(days=1)).isoformat(),
                 "end": (boundaries["eval"] + timedelta(days=1)).isoformat()},
        "holdout": {"start": (boundaries["eval"] + timedelta(days=1)).isoformat(),
                    "end": (last_anchor + timedelta(days=1)).isoformat()},
    }
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": "Electricity Authority (Te Mana Hiko) EMI 'Final energy prices' "
                  "(Real-time dispatch and pricing), Azure blob container",
        "source_urls": [LISTING_URL, NSP_URL],
        "license": "Source: CC BY 4.0 (attribution 'www.emi.ea.govt.nz provided by the "
                   "Electricity Authority (New Zealand)'; EMI LegalInformation and the "
                   "successor hub copyright statement). Our derived compilation is "
                   "dedicated CC0-1.0. Derived research dataset - not the Authority's "
                   "official product.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: written_stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: written_stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal on the anchor trading day; the eval->holdout "
                              "boundary is the documented 2022-11-01 real-time pricing "
                              "regime change",
                  "boundaries": {split: f"{windows[split]['start']} .. {windows[split]['end']}"
                                 for split in LAYOUT}},
        "label_rule": f"island daily mean of DollarsPerMegawattHour over trading day "
                      f"D+{HORIZON_DAYS} exceeds NZD {THRESHOLD_NZD_MWH:g}/MWh "
                      f"(threshold frozen from the training-window design)",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    price_frame = ("island daily mean of the publisher's final DollarsPerMegawattHour "
                   "values, averaged over every (POC x trading period) row of that island "
                   "and trading day, using POCs mapped to the island by the publisher's "
                   "NetworkSupplyPointsTable (POCs absent from that current-vintage table "
                   "are excluded and counted)")
    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": ANCHOR_DATE,
        "event_key_column": TARGET_WEEK,
        "event_key_note": "the gate reads the first ten characters of the event key as its "
                          "independence unit; target_week is the ISO week of the target "
                          "trading day, shared by both islands, so positives inside one "
                          "storage/weather episode cluster together. Weeks within one long "
                          "crisis are not fully independent: the count is a capacity floor "
                          "per the gate's rule, not an independence proof.",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is derived only from final prices published at the "
            "prediction instant and from the calendar: last_day_mean/mean_7d/mean_30d/"
            "max_30d/std_7d/days_above_threshold_30d are statistics of the row's island "
            "daily mean prices over trading days D-29..D (all published by the instant, "
            "which is placed D+6 to cover the maximum measured daily-channel lag of 5 "
            "calendar days); cross_island_ratio_7d divides the row's island 7-day mean by "
            "the other island's (both published in the same files); anchor_month/"
            "anchor_dow/anchor_doy_sin/anchor_doy_cos are calendar fields of the anchor "
            "day D. Field meanings come from the publisher's FinalEnergyPrices dataset "
            "(TradingDate, TradingPeriod, PointOfConnection, DollarsPerMegawattHour) and "
            "the NetworkSupplyPointsTable mapping, both recorded in the candidate record."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": "anchor_date is the anchor trading day (time column); a "
                                 "per-value AUC on it would memorise the calendar, so it is "
                                 "declared here rather than scored as a candidate leak. "
                                 "target_week is the clustered event key, shipped as a "
                                 "carry column.",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "last_day_mean", "unit": "NZD/MWh (nominal)",
             "frame": price_frame + ", for the anchor day D itself"},
            {"column": "mean_7d", "unit": "NZD/MWh (nominal)",
             "frame": price_frame + ", averaged over D-6..D"},
            {"column": "mean_30d", "unit": "NZD/MWh (nominal)",
             "frame": price_frame + ", averaged over D-29..D"},
            {"column": "max_30d", "unit": "NZD/MWh (nominal)",
             "frame": price_frame + ", maximum over D-29..D"},
            {"column": "std_7d", "unit": "NZD/MWh (nominal)",
             "frame": price_frame + ", population standard deviation over D-6..D"},
            {"column": "days_above_threshold_30d", "unit": "count of days (0-30)",
             "frame": "days among D-29..D whose island daily mean exceeds the frozen "
                      "NZD 100/MWh threshold - the same threshold the label uses, applied "
                      "only to published days"},
            {"column": "cross_island_ratio_7d", "unit": "ratio (dimensionless)",
             "frame": "row island mean_7d divided by the other island's mean_7d, both "
                      "from published final prices"},
            {"column": "anchor_month", "unit": "calendar month 1-12",
             "frame": "calendar field of the anchor trading day D"},
            {"column": "anchor_dow", "unit": "day of week 0-6 (Monday=0)",
             "frame": "calendar field of the anchor trading day D"},
            {"column": "anchor_doy_sin", "unit": "dimensionless",
             "frame": "sine of the anchor day's year-day on a 365.25-day cycle"},
            {"column": "anchor_doy_cos", "unit": "dimensionless",
             "frame": "cosine of the anchor day's year-day on a 365.25-day cycle"},
        ],
        "external_threshold": {
            "column": "target day island daily mean price",
            "threshold": THRESHOLD_NZD_MWH,
            "unit": "NZD/MWh (nominal)",
            "frame": price_frame + f", for trading day D+{HORIZON_DAYS}",
            "frozen": "fixed from the training-window design before construction: the "
                      "candidate record measured candidate levels 100/150/200/300 NZD/MWh "
                      "on era samples (2020-06: 28/12/5/0 days above each), and the "
                      "Authority's own wholesale review records the 2019 average spot "
                      "price at $127/MWh and 2020 at $105/MWh - NZD 100 keeps clustered "
                      "positive weeks measurable in every split while remaining roughly "
                      "twice the long-run median; it was not tuned on any held-out score",
        },
        "known_event": {
            "name": "August 2024 New Zealand dry-year wholesale price episode",
            "expected_verdict": "exceeds",
            "source": "Electricity Authority, Review of winter 2024 "
                      "(https://www.ea.govt.nz/documents/7159/Review_of_winter_2024_jnOSQfc.pdf): "
                      "'in early August the average daily price reached $820/MWh'; the "
                      "candidate record independently measured market daily means of "
                      "815-884 NZD/MWh for 2024-08-05..08-08 from the publisher's own "
                      "files. The build asserts all fixture days from the constructed "
                      "panel (see summary.json known_event_fixtures).",
        },
        "known_events_extra": [
            {"name": "July 2008 dry winter", "expected_verdict": "exceeds",
             "source": "Authority wholesale review: '2008, when there was a severe hydro "
                       "shortage during the winter'; record-measured market mean 306 "
                       "NZD/MWh on 2008-07-01"},
            {"name": "January 1997 quiet-era control", "expected_verdict": "below",
             "source": "record-measured monthly maximum market daily mean 50 NZD/MWh"},
        ],
        "timing": {
            "prediction_instant": {
                "kind": "publication",
                "period": "trading day D",
                "days_after_period_end": INSTANT_LAG_DAYS,
                "citation": "Electricity Authority, Real-time dispatch and pricing "
                            "(https://www.ea.govt.nz/data-and-insights/datasets/wholesale/"
                            "dispatch-and-pricing/): interim prices 'will be declared to be "
                            "final prices by 2pm the following business day'. Measured on "
                            "the publisher's daily-file channel, Last-Modified minus trade "
                            "date is 0-5 calendar days over 365+ files (distribution in "
                            "summary.json; observations below), so the instant is placed at "
                            "D+6 calendar days: a conservative bound under which every "
                            "feature (final prices for trading days <= D) is published and "
                            "the target trading day D+7 has not finished trading.",
            },
            "features": {
                "period": "trading days up to and including D",
                "published_days_after_period_end": INSTANT_LAG_DAYS,
                "source_kind": "statistical_release",
            },
            "row_selection": {
                "latest_period_used": "D (the anchor trading day; features read published "
                                      "final prices for trading days <= D only)",
                "fields": ["anchor trading day", "island daily means for D-29..D (both "
                           "islands)", "island daily mean for D+7 (label source, read "
                           "afterwards)"],
                "basis": "membership requires only data published by the instant: both "
                         "islands' daily means for D-29..D must exist. A missing target "
                         "day D+7 is missing outcome data - counted as unobserved_target "
                         "per split and excluded - never used to decide another row's "
                         "membership. No field dated after D is read for selection.",
            },
            "observations": observations,
            "observations_note": "observed Last-Modified dates of the publisher's daily "
                                 "final-price files (period_end = the trade date the file "
                                 "covers, published = the blob's Last-Modified date). The "
                                 "historical monthly files are current-vintage "
                                 "regenerations (the 1996 files' Last-Modified is "
                                 "2022-10-31), so per-day publication lags cannot be "
                                 "observed for 1996-2025; the conservative D+6 instant "
                                 "rests on the documented 2pm-next-business-day timetable "
                                 "plus the measured current-era lags, and is recorded as "
                                 "a supported conservative as-of rule, not a "
                                 "point-in-time reconstruction.",
        },
        "split_windows": windows,
        "split_boundaries": {
            "train": f"anchor days {windows['train']['start']} .. "
                     f"{windows['train']['end']} (ex-post pricing regime)",
            "eval": f"anchor days {windows['eval']['start']} .. {windows['eval']['end']} "
                    f"(ex-post pricing regime)",
            "holdout": f"anchor days {windows['holdout']['start']} .. "
                       f"{windows['holdout']['end']} (real-time pricing regime from the "
                       f"documented 2022-11-01 change; a different market regime by "
                       f"design - per-year reference reporting is mandatory when "
                       f"interpreting it)",
        },
        "positive_events": {
            split: {"positives": written_stats[split]["positives"],
                    "distinct_events": written_stats[split]["distinct_positive_target_weeks"]}
            for split in ("eval", "holdout")},
        "positive_events_note": "distinct_events counts distinct target ISO weeks among "
                                "positive rows (both islands share a week), the clustered "
                                "unit described in event_key_note",
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    # ---- header assertions --------------------------------------------------
    headers_ok = True
    for split, relative in LAYOUT.items():
        with (out / relative).open(encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        leaked = [column for column in header
                  if column in LABEL_SOURCE_COLUMNS or column in POST_HOC_COLUMNS]
        if leaked:
            headers_ok = False
            log(f"FAIL: {split} ships label/post-hoc columns: {leaked}")
        if header != COLUMNS:
            headers_ok = False
            log(f"FAIL: {split} header {header} != declared COLUMNS")
    log("== done ==")
    log(json.dumps({"splits": written_stats,
                    "buckets": {split: dict(counter) for split, counter in buckets.items()}},
                   indent=1))
    return 0 if headers_ok else 2


if __name__ == "__main__":
    sys.exit(main())
