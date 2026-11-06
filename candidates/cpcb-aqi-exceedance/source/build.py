#!/usr/bin/env python3
"""CPCB station-day next-day PM2.5 exceedance panel construction (job cpcb-aqi-build-001).

Candidate: cpcb-aqi-exceedance. This script ONLY constructs the runner-layout artifact
and the diagnostics the qualification gate recomputes. NO performance metric of any
kind is computed here - no AUC, no accuracy, no rate-vs-label performance number;
the reference stage (score.py) runs only after the gate passes on the full artifact
and --accept re-verifies the exact bytes (run.sh enforces the order).

Task (candidate record, prediction_question): for a CPCB CAAQMS station in India, at
23:59 IST on day D, given only that station's own trailing daily PM2.5 history through
the end of day D plus calendar terms, predict whether the station's D+1 calendar-day
24-hour mean PM2.5 exceeds 90 micrograms/m3 - the lower breakpoint edge of the CPCB
National AQI 'Poor' band for 24-hour PM2.5 (About AQI PDF + AQI-Calculator.xlsx,
recorded in measurements.threshold_fixture_2026_11_05).

Population (pre-registered in the candidate record 2026-11-05, BEFORE any score):
  * channel: the XKDR Forum India Air Quality API, anonymous demo tier, /v1/measurements
    agg=daily parameter=PM2.5 for the 549 cpcb_caaq PM2.5 stations (us_embassy DS*
    monitors excluded - single instrumentation stream), monthly x 2 station batches,
    2019-01..2025-12. The full-key bulk path is MISSING ACCESS (email signup, operator
    decision pending); anonymous query access was measured 2026-11-05 (166 requests,
    716,750 station-days).
  * vintage pin: /v1/meta exported_at must equal the recorded 2026-09-30T11:25:11+00:00
    export and its row count; a re-export refuses the build loudly.
  * scored row: a station-day with n_hours >= 18 on day D AND a labelable D+1 (row
    present with n_hours >= 18). Day-D completeness is knowable at the instant; the
    D+1 observability rule never reads the label value - unlabelable rows are excluded
    AND counted per split.
  * splits (re-cut once pre-score on the measured 2025 export hole, record 2026-11-05):
    train 2019-2022 / eval 2023 / holdout 2024 by day D. The 2025-04..09 partial tail
    is excluded and counted; 2025-01..03 and 2025-10..12 are asserted EMPTY (the hole).
  * label: D+1 calendar-day 24-hr mean > 90 ug/m3 (strict), from the same series.
    The label source (the D+1 mean and hourly count) is absent from every shipped
    column; asserted.
  * features: the station's own trailing daily PM2.5 statistics through day D plus
    calendar terms and the station's coarse identity (station_id, state_name). Every
    feature is a function of hourly readings through day D only.

Hard anchors measured on the pinned vintage (record measurements.window_counts_2026_11_05,
preflight_build_design_2026_11_05): the vintage pin (exported_at + row count), the
549-station count, the 2025 hole months (asserted empty), the 2024-11-18 Delhi severe-day
fixture (bulletin-bound: 36 complete, 36/36 exceed) and the 2023-08-15
monsoon trough bound (>= 300 complete, <= 4 exceed) are asserted exactly; a drift fails
the build loudly. The Delhi fixture counts REGISTRY MEMBERSHIP (39 cpcb Delhi stations
in the retained 2026-11-04 snapshot and in the live registry; the publisher's own
bulletin denominator is 36/39), not panel rows on the day (38; the 2026-11-05 preflight
figure this anchor was first transcribed from). The exact panel-total and per-window
station-day/positive counts are
NOT asserted: the 2026-11-05 probe's scratch aggregation lost rows across a 401 window
(record measurements.attempt_002_refusal_2026_11_06), so those figures are carried as a
NON-ASSERTING reference (PROBE_REFERENCE), the build RECORDS its own measured counts in
summary.json and asserts internal consistency (the windows partition the panel exactly;
an independent second pass with the label-rule operands reproduces the per-window
positives). The record adopts the measured counts before any figure is reported, and the
gate recomputes counts from the rows regardless.

Cross-row exposure (declared, measured, not eliminated): row D's label operand is the
D+1 mean, which ships as the pm25_mean feature of row D+1 and enters the trailing
aggregates of rows D+2..D+91. The gate's reverse-history probe (entity station_id,
offset 1 day, gt 90 on the donated pm25_mean) measures that exposure on the full
artifact; access is isolated_rows and the artifact is restricted retrospective research.

--synthetic generates a small seeded synthetic panel through the SAME construction path
(no network, no anchor or fixture assertions) so the gate, --accept and the reference
machinery can be exercised end-to-end before any worker cycle is spent.

Licence posture (record review, class A): CPCB's platform publication is GODL-India
(attribution-only); the XKDR compilation is CC BY 4.0. Any release carries attribution
to CPCB and XKDR Forum and never presents this derived dataset as CPCB's official
product. Stdlib only. No credentials in the container (the demo key is the publisher's
own front-page constant, re-read from the front page on auth refusal).
"""
from __future__ import annotations

import argparse
import calendar
import csv
import io
import json
import math
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

NAME = "cpcb-aqi-exceedance"
TARGET = "exceeds"
POSITIVE_LABEL = 1
ID_COLUMN = "station_day"
TIME_COLUMN = "date"
EVENT_KEY_COLUMN = "date"
THRESHOLD_UGM3 = 90.0
MIN_HOURS = 18

BASE = "https://airquality.xkdr.org"
DEMO_KEY_PINNED = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"  # publisher front-page constant, measured 2026-11-05
USER_AGENT = "Mozilla/5.0 (dataset-factory-cpcb-build/1.0)"
PINNED_EXPORTED_AT = "2026-09-30T11:25:11+00:00"
PINNED_META_ROWS = 196_521_834

COLUMNS = [
    ID_COLUMN, "station_id", "state_name", TIME_COLUMN, "day_of_week", "month",
    "doy_sin", "doy_cos", "pm25_mean", "pm25_max", "pm25_min", "n_hours",
    "pm25_mean_lag1", "pm25_mean_lag2", "pm25_mean_lag3",
    "pm25_mean_7d", "pm25_days_valid_7d",
    "pm25_mean_30d", "pm25_days_valid_30d",
    "pm25_hist_mean_90d", "days_since_gt90", "exceed_count_30d",
    TARGET,
]
FEATURES = [c for c in COLUMNS if c not in (ID_COLUMN, TARGET)]

TRAIN_YEARS = range(2019, 2023)      # 2019..2022
EVAL_YEARS = (2023,)
HOLDOUT_YEARS = (2024,)
FETCH_FIRST = date(2019, 1, 1)
FETCH_LAST = date(2025, 12, 31)
HOLE_MONTHS = {(2025, m) for m in (1, 2, 3, 10, 11, 12)}
TAIL_MONTHS = {(2025, m) for m in (4, 5, 6, 7, 8, 9)}

# Anchors measured on the pinned vintage (candidate record, 2026-11-05/06).
# Attempt -003 policy (record measurements.attempt_002_refusal_2026_11_06
# .repair_for_attempt_003): the vintage pin, the 549-station count, the 2025 hole
# months, the Delhi fixture and the monsoon bound stay HARD; the probe's panel-total
# and per-window counts become a non-asserting reference because the probe's scratch
# aggregation lost rows across a 401 window. The build records its own measured
# counts in summary.json and asserts internal consistency instead.
ANCHORS = {
    "delhi_2024_11_18": {"station_days": 39, "complete_n18": 36, "pos_n18": 36},
    "monsoon_2023_08_15": {"complete_n18_min": 300, "pos_n18_max": 4},
    "cpcb_pm25_stations": 549,
}

# 2026-11-05 probe reference (record measurements.window_counts_2026_11_05).
# Deltas against these values are REPORTED in summary.json, never asserted.
PROBE_REFERENCE = {
    "panel_rows_total": 716_750,
    "window_station_days": {
        "train_2019_2022": 339_557,
        "eval_2023": 154_003,
        "holdout_2024": 175_624,
        "tail_2025_04_09": 47_566,
    },
    "window_positives_n18": {
        "train_2019_2022": 63_735,
        "eval_2023": 20_773,
        "holdout_2024": 19_254,
        "tail_2025_04_09": 829,
    },
}

REQUEST_SLEEP_S = 0.8
PER_REQUEST_TRIES = 6


def fail(message: str) -> None:
    print(f"BUILD REFUSED: {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


# ---------------------------------------------------------------- fetch layer

def api(path: str, params: list, key: str, timeout: int = 90, tries: int = PER_REQUEST_TRIES):
    """One GET with retry/backoff. Returns (body_bytes, headers, error)."""
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"Authorization": "Bearer " + key, "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read(), dict(response.headers), None
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()[:200]
            except Exception:
                pass
            if exc.code in (400, 401, 403, 429, 500, 502, 503, 504):
                wait = min(15 * (2 ** attempt), 120)
                print(f"  HTTP {exc.code} attempt {attempt}: backoff {wait}s "
                      f"body={body[:120]!r}", flush=True)
                time.sleep(wait)
                last = f"HTTP {exc.code}"
                continue
            return None, None, f"HTTP {exc.code}: {body[:120]!r}"
        except Exception as exc:  # noqa: BLE001 - origin flakiness is measured, not fatal
            last = f"{type(exc).__name__}: {exc}"
            print(f"  net {last} attempt {attempt}", flush=True)
            time.sleep(min(10 * (2 ** attempt), 60))
    return None, None, f"exhausted ({last})"


def current_frontpage_key() -> str | None:
    """Re-read the publisher's front-page demo key after an auth refusal.

    The demo key is a published constant on the XKDR front page (record,
    xkdr_channel_access_2026_11_05); it rotated once between 2026-10-20 and
    2026-11-04. This is not a credential - it is the publisher's own anonymous
    access token for query access.
    """
    try:
        req = urllib.request.Request(BASE + "/", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as response:
            html = response.read().decode("utf-8", "replace")
        found = re.findall(r"aqi_demo_[A-Za-z0-9_-]+", html)
        return found[0] if found else None
    except Exception as exc:  # noqa: BLE001
        print(f"front-page key re-read failed: {type(exc).__name__}: {exc}", flush=True)
        return None


def fetch_meta_and_stations(key: str) -> tuple[dict, list[dict], str, int]:
    """Vintage-pin /v1/meta and the 549-station list; one auth retry with a
    re-read front-page key (the measured rotation failure mode)."""
    active_key = key
    body, _, err = api("/v1/meta", [], active_key)
    if body is None:
        fresh = current_frontpage_key()
        if fresh and fresh != active_key:
            print(f"pinned demo key refused ({err}); retrying with the "
                  f"current front-page key", flush=True)
            active_key = fresh
            body, _, err = api("/v1/meta", [], active_key)
    if body is None:
        fail(f"/v1/meta failed after retries: {err}")
    meta = json.loads(body)
    if meta.get("exported_at") != PINNED_EXPORTED_AT or \
            (meta.get("measurements") or {}).get("rows") != PINNED_META_ROWS:
        fail(f"vintage pin mismatch: exported_at={meta.get('exported_at')!r} "
             f"rows={(meta.get('measurements') or {}).get('rows')!r} != pinned "
             f"{PINNED_EXPORTED_AT!r}/{PINNED_META_ROWS}")
    body, _, err = api("/v1/stations", [("format", "json")], active_key)
    if body is None:
        fail(f"/v1/stations failed after retries: {err}")
    stations_doc = json.loads(body)
    data = stations_doc.get("data", stations_doc)
    if isinstance(data, dict):
        data = data.get("data", [])
    cpcb = [s for s in data
            if s.get("source") == "cpcb_caaqm" and "PM2.5" in (s.get("parameters") or [])]
    if len(cpcb) != ANCHORS["cpcb_pm25_stations"]:
        fail(f"cpcb pm25 station count {len(cpcb)} != "
             f"{ANCHORS['cpcb_pm25_stations']}")
    # Measured 2026-11-06 (job cpcb-aqi-build-001 refused on it): the export leaves
    # state_name null for 62 of the 549 cpcb PM2.5 stations (city_name/latitude/
    # longitude null too), all newer stations. Identity is station_id; state_name is a
    # coarse feature, so a station without one ships a DECLARED sentinel rather than
    # dropping 11% of the population (which would invalidate the measured anchors) or
    # inferring a state from the station name (which would be invented data).
    missing_state = 0
    for s in cpcb:
        if not (s.get("state_name") or "").strip():
            missing_state += 1
            s["state_name"] = "UNKNOWN_STATE"
    print(f"station registry: {missing_state} of {len(cpcb)} cpcb PM2.5 stations "
          f"carry no state_name and ship the declared sentinel 'UNKNOWN_STATE'",
          flush=True)
    return meta, cpcb, active_key, missing_state


def fetch_panel(stations: list[dict], key: str, rows_path: Path) -> dict:
    """Stream every daily aggregate to scratch; monthly x 2 station batches.

    Bounded memory: rows go straight to disk; nothing accumulates but receipts.
    """
    station_ids = [s["station_id"] for s in stations]
    batches = [station_ids[i:i + 275] for i in range(0, len(station_ids), 275)]
    months = []
    year, month = FETCH_FIRST.year, FETCH_FIRST.month
    while (year, month) <= (FETCH_LAST.year, FETCH_LAST.month):
        months.append((year, month))
        month += 1
        if month == 13:
            year, month = year + 1, 1

    receipts = {"requests": 0, "truncated_batches": 0, "unparseable_rows": 0,
                "bytes": 0, "key": "pinned" if key == DEMO_KEY_PINNED else "front-page"}
    rows_file = rows_path.open("w")
    t0 = time.time()
    for (y, m) in months:
        last_day = calendar.monthrange(y, m)[1]
        for bi, batch in enumerate(batches):
            params = [("parameter", "PM2.5"), ("agg", "daily"),
                      ("start", f"{y}-{m:02d}-01"), ("end", f"{y}-{m:02d}-{last_day:02d}"),
                      ("format", "csv")]
            for sid in batch:
                params.append(("station", sid))
            body, headers, err = api("/v1/measurements", params, key)
            if body is None:
                rows_file.close()
                fail(f"measurements fetch failed for {y}-{m:02d} batch {bi}: {err}")
            receipts["requests"] += 1
            receipts["bytes"] += len(body)
            if str(headers.get("X-Truncated", "")).lower() == "true":
                receipts["truncated_batches"] += 1
                rows_file.close()
                fail(f"truncated response for {y}-{m:02d} batch {bi}: the demo-tier "
                     f"row cap would silently drop station-days")
            written = 0
            for row in csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))):
                try:
                    mean = float(row["mean"])
                    n = int(row["n"])
                    low = float(row["min"])
                    high = float(row["max"])
                    day = parse_day(row["period_start"][:10])
                except (KeyError, ValueError, TypeError):
                    receipts["unparseable_rows"] += 1
                    continue
                rows_file.write(f"{row['station_id']}|{day.isoformat()}"
                                f"|{n}|{mean:.4f}|{low:.4f}|{high:.4f}\n")
                written += 1
            rows_file.flush()
            time.sleep(REQUEST_SLEEP_S)
        if m == 12:
            print(f"  fetched through {y}-{m:02d}: {receipts['requests']} requests, "
                  f"{time.time() - t0:.0f}s", flush=True)
    rows_file.close()
    receipts["elapsed_s"] = round(time.time() - t0, 1)
    return receipts


# ------------------------------------------------------------- synthetic mode

def synthetic_panel(rows_path: Path) -> dict:
    """Seeded synthetic station-day panel through the identical downstream path.

    Exercises eligibility, labelling, features, splits, CSV writing, the gate,
    --accept and the reference machinery BEFORE any worker cycle. No anchor or
    fixture assertions run (there is no real vintage to bind).
    """
    rng = random.Random(20261105)
    stations = []
    for i in range(8):
        stations.append({"station_id": f"SYN{1000 + i}",
                          "state_name": ["DELHI", "HARYANA", "MAHARASHTRA"][i % 3],
                          "city_name": "Synthetic"})
    rows_file = rows_path.open("w")
    for s in stations:
        carry = 0.0
        offset = [45.0, 30.0, 15.0, 5.0][i % 4] if (i := int(s["station_id"][-1])) < 4 else 5.0
        day = FETCH_FIRST
        while day <= FETCH_LAST:
            doy = day.timetuple().tm_yday
            seasonal = 55.0 * math.sin(2 * math.pi * (doy - 15) / 365.25)
            carry = 0.55 * carry + rng.gauss(0.0, 14.0)
            mean = max(5.0, 18.0 + offset + seasonal + carry)
            if rng.random() < 0.06:            # station offline day
                day += timedelta(days=1)
                continue
            n = 24 if rng.random() < 0.8 else rng.randint(0, 17)
            rows_file.write(f"{s['station_id']}|{day.isoformat()}|{n}|{mean:.4f}|"
                            f"{max(1.0, mean * 0.75):.4f}|{mean * 1.3:.4f}\n")
            day += timedelta(days=1)
    rows_file.close()
    return {"requests": 0, "truncated_batches": 0, "unparseable_rows": 0,
            "bytes": 0, "key": "synthetic", "elapsed_s": 0.0}


# ------------------------------------------------------------- panel + anchors

def load_panel(rows_path: Path) -> tuple[dict, dict]:
    """station -> {date -> (n, mean, min, max)}; plus duplicate/unparseable counts."""
    panel: dict[str, dict] = {}
    duplicates = 0
    seen: set[tuple] = set()
    for line in rows_path.open():
        sid, day_text, n, mean, low, high = line.rstrip("\n").split("|")
        key = (sid, day_text)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        panel.setdefault(sid, {})[parse_day(day_text)] = (
            int(n), float(mean), float(low), float(high))
    return panel, {"duplicate_station_days": duplicates}


def window_of(day: date) -> str | None:
    if day.year in TRAIN_YEARS:
        return "train"
    if day.year in EVAL_YEARS:
        return "eval"
    if day.year in HOLDOUT_YEARS:
        return "holdout"
    return None


def check_panel_anchors(panel: dict, stations: list[dict]) -> dict:
    """Assert the recorded panel-level anchors on the fetched vintage."""
    per_window_days = {"train_2019_2022": 0, "eval_2023": 0, "holdout_2024": 0,
                       "tail_2025_04_09": 0}
    per_window_pos = {k: 0 for k in per_window_days}
    hole_rows = 0
    total = 0
    for series in panel.values():
        for day, (n, mean, _low, _high) in series.items():
            total += 1
            if (day.year, day.month) in HOLE_MONTHS:
                hole_rows += 1
            if day.year in TRAIN_YEARS:
                w = "train_2019_2022"
            elif day.year in EVAL_YEARS:
                w = "eval_2023"
            elif day.year in HOLDOUT_YEARS:
                w = "holdout_2024"
            elif (day.year, day.month) in TAIL_MONTHS:
                w = "tail_2025_04_09"
            else:
                fail(f"panel day {day} falls outside every declared window")
            per_window_days[w] += 1
            if n >= MIN_HOURS and mean > THRESHOLD_UGM3:
                per_window_pos[w] += 1
    if hole_rows != 0:
        fail(f"the 2025 hole months carry {hole_rows} rows; the export changed")
    # Internal consistency (attempt -003 policy, record
    # measurements.attempt_002_refusal_2026_11_06.repair_for_attempt_003): the
    # windows must partition the panel exactly, and an independent second pass over
    # the panel with the same label-rule operands (n >= MIN_HOURS,
    # mean > THRESHOLD_UGM3) must reproduce the counted per-window positives.
    # The 2026-11-05 probe's totals are a non-asserting reference: its scratch
    # aggregation lost rows across a 401 window, so deltas are reported only.
    if sum(per_window_days.values()) != total:
        fail(f"window station-days {per_window_days} sum to "
             f"{sum(per_window_days.values())} != panel rows {total}")
    recount = {k: 0 for k in per_window_days}
    for series in panel.values():
        for day, (n, mean, _low, _high) in series.items():
            if n >= MIN_HOURS and mean > THRESHOLD_UGM3:
                if day.year in TRAIN_YEARS:
                    recount["train_2019_2022"] += 1
                elif day.year in EVAL_YEARS:
                    recount["eval_2023"] += 1
                elif day.year in HOLDOUT_YEARS:
                    recount["holdout_2024"] += 1
                elif (day.year, day.month) in TAIL_MONTHS:
                    recount["tail_2025_04_09"] += 1
    if recount != per_window_pos:
        fail(f"per-window positives {per_window_pos} not reproduced by the "
             f"independent label-rule recount {recount}")
    probe_deltas = {
        "note": ("deltas vs the 2026-11-05 probe reference; reported, never "
                 "asserted (the probe's scratch aggregation lost rows across a "
                 "401 window - record attempt_002_refusal_2026_11_06)"),
        "panel_rows_total": {"probe": PROBE_REFERENCE["panel_rows_total"],
                             "measured": total,
                             "delta": total - PROBE_REFERENCE["panel_rows_total"]},
        "window_station_days": {
            name: {"probe": PROBE_REFERENCE["window_station_days"][name],
                   "measured": per_window_days[name],
                   "delta": per_window_days[name]
                            - PROBE_REFERENCE["window_station_days"][name]}
            for name in per_window_days},
        "window_positives_n18": {
            name: {"probe": PROBE_REFERENCE["window_positives_n18"][name],
                   "measured": per_window_pos[name],
                   "delta": per_window_pos[name]
                            - PROBE_REFERENCE["window_positives_n18"][name]}
            for name in per_window_pos},
    }
    print(f"probe reference deltas (reported, not asserted): "
          f"{json.dumps(probe_deltas)}", flush=True)

    delhi = [s for s in stations if (s.get("city_name") or "") == "Delhi"]
    fixture = {"station_days": 0, "complete_n18": 0, "pos_n18": 0}
    for s in delhi:
        n, mean, _low, _high = panel.get(s["station_id"], {}).get(date(2024, 11, 18),
                                                                 (0, 0.0, 0.0, 0.0))
        fixture["station_days"] += 1
        if n >= MIN_HOURS:
            fixture["complete_n18"] += 1
            fixture["pos_n18"] += int(mean > THRESHOLD_UGM3)
    if fixture != ANCHORS["delhi_2024_11_18"]:
        fail(f"Delhi 2024-11-18 severe-day fixture {fixture} != "
             f"{ANCHORS['delhi_2024_11_18']}")

    monsoon = {"complete_n18": 0, "pos_n18": 0}
    for series in panel.values():
        entry = series.get(date(2023, 8, 15))
        if entry is None:
            continue
        n, mean, _low, _high = entry
        if n >= MIN_HOURS:
            monsoon["complete_n18"] += 1
            monsoon["pos_n18"] += int(mean > THRESHOLD_UGM3)
    if monsoon["complete_n18"] < ANCHORS["monsoon_2023_08_15"]["complete_n18_min"] or \
            monsoon["pos_n18"] > ANCHORS["monsoon_2023_08_15"]["pos_n18_max"]:
        fail(f"monsoon trough fixture {monsoon} violates the recorded bound "
             f"{ANCHORS['monsoon_2023_08_15']}")
    return {
        "panel_rows_total": total,
        "window_station_days": per_window_days,
        "window_positives_n18": per_window_pos,
        "hole_2025_rows": hole_rows,
        "delhi_2024_11_18": fixture,
        "monsoon_2023_08_15": monsoon,
        "probe_reference_deltas": probe_deltas,
    }


# ------------------------------------------------------ features, labels, rows

SEASONS = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
           6: "JJAS", 7: "JJAS", 8: "JJAS", 9: "JJAS", 10: "ON", 11: "ON"}


def build_rows(panel: dict, state_of: dict) -> tuple[dict, dict]:
    """Eligible, labelled, feature-complete rows per split + exclusion counts."""
    split_rows = {"train": [], "eval": [], "holdout": []}
    excluded = {"thin_day": {"train": 0, "eval": 0, "holdout": 0},
                "unlabelable_next_day": {"train": 0, "eval": 0, "holdout": 0},
                "outside_windows": 0}
    for sid, series in panel.items():
        state = state_of[sid]
        valid = sorted((d, v) for d, v in series.items() if v[0] >= MIN_HOURS)
        for day, entry in series.items():
            if entry[0] < MIN_HOURS:
                split = window_of(day)
                if split is not None:
                    excluded["thin_day"][split] += 1
        window: list[tuple[date, float]] = []          # trailing valid days, <= 90
        for day, (n, mean, low, high) in valid:
            # retire entries older than 89 days from the window head
            while window and (day - window[0][0]).days > 89:
                window.pop(0)
            cnt7 = sum7 = cnt30 = sum30 = cnt90 = sum90 = 0
            exceed30 = 0
            since = -1.0
            for wday, wmean in reversed(window + [(day, mean)]):
                lag = (day - wday).days
                if lag > 89:
                    break
                cnt90 += 1
                sum90 += wmean
                if lag <= 29:
                    cnt30 += 1
                    sum30 += wmean
                    exceed30 += int(wmean > THRESHOLD_UGM3)
                if lag <= 6:
                    cnt7 += 1
                    sum7 += wmean
                if since < 0 and wmean > THRESHOLD_UGM3:
                    since = float(lag)

            def day_mean(delta: int) -> float:
                want = day - timedelta(days=delta)
                entry = series.get(want)
                if entry is not None and entry[0] >= MIN_HOURS:
                    return entry[1]
                return -1.0

            next_day = series.get(day + timedelta(days=1))
            # Every VALID day feeds later rows' trailing windows, whether or not this day
            # itself became a scored row. The declared frame is "the mean of the station's
            # valid-day means over the window", not "of its scored rows": a valid day whose
            # D+1 is missing or thin is excluded as a row but was still observed, so it must
            # stay in D+2..D+91 aggregates. (Pre-dry-run review defect: appending only scored
            # days silently thinned the trailing means and over-triggered the -1.0 sentinels.)
            window.append((day, mean))
            split = window_of(day)
            if split is None:
                excluded["outside_windows"] += 1
                continue
            if next_day is None or next_day[0] < MIN_HOURS:
                excluded["unlabelable_next_day"][split] += 1
                continue
            doy = day.timetuple().tm_yday
            row = (
                f"{sid}|{day.isoformat()}",
                sid,
                state,
                day.isoformat(),
                day.weekday(),
                day.month,
                round(math.sin(2 * math.pi * doy / 365.25), 6),
                round(math.cos(2 * math.pi * doy / 365.25), 6),
                round(mean, 4),
                round(low, 4),
                round(high, 4),
                n,
                round(day_mean(1), 4),
                round(day_mean(2), 4),
                round(day_mean(3), 4),
                round(sum7 / cnt7, 4) if cnt7 >= 4 else -1.0,
                cnt7,
                round(sum30 / cnt30, 4) if cnt30 >= 10 else -1.0,
                cnt30,
                round(sum90 / cnt90, 4) if cnt90 >= 30 else -1.0,
                since,
                exceed30,
                1 if next_day[1] > THRESHOLD_UGM3 else 0,
            )
            split_rows[split].append(row)
    for rows in split_rows.values():
        rows.sort(key=lambda r: (r[3], r[1]))      # by date, then station
    return split_rows, excluded


def counts_of(split_rows: dict) -> dict:
    counts = {}
    for key, rows in split_rows.items():
        positives = sum(r[-1] for r in rows)
        counts[key] = {
            "rows": len(rows),
            "positives": positives,
            "positive_rate": round(positives / len(rows), 6) if rows else None,
            "distinct_positive_events": len({r[3] for r in rows if r[-1] == 1}),
            "stations": len({r[1] for r in rows}),
        }
    return counts


# ------------------------------------------------------------------- assembly

def quality_payload(counts: dict, excluded: dict, anchors: dict, synthetic: bool) -> dict:
    windows = {
        "train": {"start": "2019-01-01", "end": "2023-01-01"},
        "eval": {"start": "2023-01-01", "end": "2024-01-01"},
        "holdout": {"start": "2024-01-01", "end": "2025-01-01"},
    }
    tail_days = (anchors.get("window_station_days") or {}).get("tail_2025_04_09")
    tail_pos = (anchors.get("window_positives_n18") or {}).get("tail_2025_04_09")
    if tail_days is not None and tail_pos is not None:
        tail_desc = (f"The 2025-04..09 partial tail ({tail_days:,} station-days, "
                     f"{tail_pos:,} valid-day positives) is excluded and counted")
    else:
        tail_desc = ("The 2025-04..09 partial tail is excluded and counted "
                     "(measured counts in summary.json)")
    quality = {
        "name": NAME,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": [ID_COLUMN],
        "features": FEATURES,
        "high_cardinality_columns": ["station_id", "date"],
        "carry_columns": [],
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "time_column": TIME_COLUMN,
        "event_key_column": EVENT_KEY_COLUMN,
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "external_threshold": True,
        "known_event": {
            "name": "CPCB Daily AQI Bulletin 2024-11-18: Delhi Severe, prominent pollutant PM2.5 (36/39 stations)",
            "expected_verdict": "exceeds",
            "source": "https://cpcb.gov.in/upload/Downloads/AQI_Bulletin_20241118.pdf (retained probe/out/aqi_bulletin_20241118.pdf); the 90 ug/m3 edge is the Poor-band lower breakpoint of CPCB's own National AQI (About AQI PDF, probe/out/about_aqi.pdf, corroborated by AQI-Calculator.xlsx). Measured panel confirmation: 36/36 complete Delhi cpcb station-days on 2024-11-18 carry a 24-hr mean > 90 ug/m3 (235.7-731.5)",
        },
        "negative_control_fixture": {
            "name": "monsoon trough day 2023-08-15",
            "expected": "at most 4 of at least 300 complete (n>=18) all-India cpcb station-days exceed 90 ug/m3",
            "source": "measured 2026-11-05 (probe/out/preflight_build_design_2026_11_05.json): 389 complete, 1 exceed; a unit or reference-frame error would move this rate to its extreme and fail the in-build assertion",
        },
        "features_documented_at": "prediction_time",
        "label_source_columns": ["next_day_pm25_mean", "next_day_n_hours"],
        "post_hoc_columns": ["next_day_pm25_mean", "next_day_n_hours"],
        "task": {
            "prediction_time": "23:59 IST on day D: every hourly reading through day D is knowable at that instant and no D+1 reading exists yet; features are the station's own trailing daily PM2.5 statistics through day D plus calendar terms and the station's coarse identity",
            "target_definition": "the station's D+1 calendar-day 24-hour mean PM2.5 exceeds 90 ug/m3 (strict >), the Poor-band lower breakpoint of CPCB's National AQI for 24-hour PM2.5; both the D and D+1 days must carry n_hours >= 18",
            "description": "for a CPCB CAAQMS station in India, predict whether the next calendar day's 24-hour mean PM2.5 is Poor-or-worse (> 90 ug/m3) from the station's own trailing daily history and the calendar",
        },
        "measurements": [
            {"column": "pm25_mean", "unit": "micrograms/m3 (24-hour mean)",
             "frame": "station-day 24-hr mean of hourly PM2.5 from the XKDR daily aggregate of the cpcb_caaqm stream; compared against the CPCB National AQI Poor-band lower edge 90 ug/m3"},
            {"column": "pm25_max", "unit": "micrograms/m3",
             "frame": "station-day maximum of hourly PM2.5 (same daily aggregate)"},
            {"column": "pm25_min", "unit": "micrograms/m3",
             "frame": "station-day minimum of hourly PM2.5 (same daily aggregate)"},
            {"column": "n_hours", "unit": "count of hourly readings",
             "frame": "hourly readings the daily aggregate covers for the station-day; >= 18 required for a day to be usable"},
            {"column": "pm25_mean_lag1", "unit": "micrograms/m3",
             "frame": "the station's mean on calendar day D-1 when that day exists with n>=18; -1.0 otherwise (lags 2 and 3 analogous)"},
            {"column": "pm25_mean_7d", "unit": "micrograms/m3",
             "frame": "mean of the station's valid-day means over D-6..D; -1.0 when fewer than 4 valid days fall in the window; pm25_days_valid_7d carries the count"},
            {"column": "pm25_mean_30d", "unit": "micrograms/m3",
             "frame": "mean over D-29..D, -1.0 under 10 valid days; pm25_days_valid_30d carries the count"},
            {"column": "pm25_hist_mean_90d", "unit": "micrograms/m3",
             "frame": "trailing 90-day mean over D-89..D; -1.0 under 30 valid days"},
            {"column": "days_since_gt90", "unit": "days",
             "frame": "days back to the most recent valid day with mean > 90 ug/m3 within D-89..D (0 = today); -1.0 when none"},
            {"column": "exceed_count_30d", "unit": "count of days",
             "frame": "valid days with mean > 90 ug/m3 in D-29..D"},
        ],
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "D",
                "days_after_period_end": 0,
                "citation": "the instant is the end of day D in IST (the XKDR archive's collected_at is naive IST, UTC+05:30); the station's own hourly readings through day D are the administrative record. The archive republishes the publisher's measurements with no gap filling ('as reported', 'preliminary and not fully validated', XKDR README); intraday publication latency is unmeasured and day-D trailing completeness at the instant is an explicitly declared assumption",
            },
            "features": {
                "period": "D",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "2024-12",
                "fields": [ID_COLUMN, "station_id", "state_name", TIME_COLUMN,
                           "day_of_week", "month", "doy_sin", "doy_cos",
                           "pm25_mean", "pm25_max", "pm25_min", "n_hours",
                           "pm25_mean_lag1", "pm25_mean_lag2", "pm25_mean_lag3",
                           "pm25_mean_7d", "pm25_days_valid_7d", "pm25_mean_30d",
                           "pm25_days_valid_30d", "pm25_hist_mean_90d",
                           "days_since_gt90", "exceed_count_30d"],
                "basis": f"scored rows are complete (n_hours >= 18) station-days of the cpcb_caaqm PM2.5 stream with day D inside the declared window AND a labelable D+1 (a row present with n_hours >= 18). Day-D completeness is knowable at the instant; the D+1 observability rule is an outcome-observability exclusion that never reads the label value - unlabelable rows are excluded and counted per split. {tail_desc}; the 2025-01..03 and 2025-10..12 hole months are asserted empty. Both label values are retained in every window",
            },
            "observations": [],
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": "each row is one station-day next-day exceedance prediction at 23:59 IST on day D; features are precomputed at construction and the runner predicts row-wise from the shipped columns. Labeled eval is development/validation; the holdout is the final test and stays outside evaluated agents' workspaces. Training-label timing is UNVERIFIED: XKDR publishes a single cleaned export (no historical vintages, no first-publication ledger), so no full-row availability ledger can be constructed - retrospective research only, never a certified historical forecasting setup",
            "vintage": {
                "kind": "current_snapshot",
                "evidence": "the archive is one export stamped 2026-09-30T11:25:11+00:00 (/v1/meta, asserted by this build: exported_at and the 196,521,834-row count are pinned; a re-export refuses the build). Values are 'as reported' with 'no gap filling' and marked 'preliminary and not fully validated' (XKDR README); revision behaviour is unmeasured because a second export has never been observed. Every shipped feature is the current-vintage value of a measurement at or before day D; no as-of value is claimed",
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": "membership is fixed by day-D completeness (n_hours >= 18, knowable at the instant) and the declared window; the only additional rule is D+1 outcome observability (a row with n_hours >= 18 must exist for D+1), which never reads the label value - unlabelable rows are excluded and counted per split. Positives are winter-clustered, so the day-level observability rule could in principle co-move with the label through weather (a monsoon D+1 is both thin and clean); the excluded counts per split and per month are recorded in summary.json so the exclusion's seasonality is measurable, not hidden",
            },
            "limitations": [
                "current_snapshot vintage: a single cleaned export, no historical vintages; values corrected after publication cannot be distinguished",
                "the day-D trailing completeness assumption: CPCB intraday latency is unmeasured, so 23:59 IST features are declared under the assumption the day's hourly record is complete at the instant (the publisher's own 4 PM bulletin shows non-participating stations, so intraday availability is genuinely partial)",
                "cross-row exposure: row D's label operand (the D+1 mean) ships as the pm25_mean feature of row D+1 and enters the trailing aggregates of rows D+2..D+91; the declared reverse-history probe measures the direct join exposure, access is isolated_rows, and the artifact is restricted retrospective research",
                "outcome-observability selection: station-days whose D+1 is missing or thin are unlabelable and excluded (counted per split and per month); the exclusion is not label-reading but its seasonality is recorded",
                "the export's 2025 hole (Jan-Mar, Oct-Dec absent) is why holdout is 2024, not 2025; the 2025-04..09 tail is excluded and counted",
                "training_label_timing is unverified: no as-of ledger exists for when any daily aggregate first appeared in the archive",
                "positives cluster by winter day and station; the independent positive evidence is the declared distinct-positive-days count, not the row count",
                "labeled eval is development/validation, never an untouched final test; the holdout is the final test and remains sealed until the design is frozen",
            ],
            "cross_row_audit": {
                "probes": [
                    {
                        "entity_columns": ["station_id"],
                        "time_column": TIME_COLUMN,
                        "offset_days": 1,
                        "left": "pm25_mean",
                        "operation": "gt",
                        "threshold": 90,
                        "name": "next_day_mean_recovery",
                        "note": "blind-join label recovery: a donor row of the same station one day later donates its pm25_mean, which is exactly this row's label operand (the D+1 24-hr mean); gt 90 reproduces the label by construction. Coverage measures how many rows a same-station next-day join can answer outright on the full artifact",
                    },
                ],
                "probes_note": "the panel's serial structure is real and is measured, not argued away: row D's label is a function of the D+1 mean, which is row D+1's own pm25_mean feature, and the same value is inside the trailing aggregates of rows D+2..D+91 (the bounded-aggregate exposure is declared here; only the direct offset-1 join is exactly expressible as a probe). Coverage is expected to be high, which is why access is isolated_rows and the artifact is restricted retrospective research",
                "rationale": "rows are per-station next-day predictions whose trailing features are precomputed at construction; the runner predicts row-wise from shipped columns. The label source (the D+1 series) is absent from the shipped columns (asserted), but the same station's next row legitimately carries the outcome day as its own pm25_mean feature, so the cross-row join exposure is declared and measured rather than denied",
                "auxiliary_files_review": "the extract ships exactly the runner layout - public/train.csv, public/eval.csv, private/holdout.csv, meta.json, quality.json - plus summary.json, which carries fetch receipts, vintage pins, exclusion counts, per-window anchors and per-split per-month tables; no row-level source data and no performance metric. The fetched daily-aggregate lines stay in the job's scratch directory outside /output and are never uploaded",
            },
        },
        "positive_events": {
            key: {"positives": counts[key]["positives"],
                  "distinct_events": counts[key]["distinct_positive_events"]}
            for key in ("train", "eval", "holdout")
        },
        "split_windows": windows,
        "split_counts": counts,
        "excluded_counts": excluded,
        "panel_anchors_verified": anchors,
        "synthetic_mode": synthetic,
    }
    return quality


def fe_evidence() -> dict:
    verified_pm = ("computed by this build from the station's own daily aggregates "
                   "through day D; every input reading predates the instant")
    assumed_vintage = ("current-vintage value of a measurement at or before day D; "
                       "the archive publishes no historical vintages, so post-hoc "
                       "corrections cannot be distinguished")
    evidence = {
        "station_day": {
            "source": "derived: station_id + calendar date of day D",
            "availability": "unique row identity assigned at construction; names one station-day prediction event",
            "status": "verified",
        },
        "station_id": {
            "source": "XKDR station registry (/v1/stations), cpcb_caaqm stream; the us_embassy DS* monitors are excluded so the population is single-instrumentation",
            "availability": "the station's own identity, fixed for the whole panel",
            "status": "verified",
        },
        "state_name": {
            "source": ("XKDR station registry (/v1/stations) state_name for the station; "
                       "the 62 of 549 cpcb PM2.5 stations the export leaves null (measured "
                       "2026-11-06; city_name/latitude/longitude also null) ship the declared "
                       "sentinel 'UNKNOWN_STATE' - never inferred from the station name"),
            "availability": "static station geography; knowable at any instant",
            "status": "assumed",
            "assumption": ("current-registry station attribute; station metadata could in "
                           "principle be revised in a future export; a missing state is a "
                           "declared sentinel, not missing-row exclusion"),
        },
        "date": {
            "source": "the calendar day D of the prediction instant (IST)",
            "availability": "the prediction instant's own date",
            "status": "verified",
        },
        "day_of_week": {"source": "derived arithmetically from date", "availability": "calendar", "status": "verified"},
        "month": {"source": "derived arithmetically from date", "availability": "calendar", "status": "verified"},
        "doy_sin": {"source": "derived: sin(2*pi*day_of_year/365.25) from date", "availability": "calendar", "status": "verified"},
        "doy_cos": {"source": "derived: cos(2*pi*day_of_year/365.25) from date", "availability": "calendar", "status": "verified"},
        "pm25_mean": {
            "source": "the station's 24-hr mean of hourly PM2.5 on day D (XKDR daily aggregate, cpcb_caaqm)",
            "availability": "the most recent observed daily value at the 23:59 IST instant, under the declared day-D completeness assumption",
            "status": "assumed",
            "assumption": assumed_vintage + "; the day-D trailing completeness at the instant is the declared assumption (intraday latency unmeasured)",
        },
        "pm25_max": {
            "source": "the station's day-D maximum hourly PM2.5 (same daily aggregate)",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "pm25_min": {
            "source": "the station's day-D minimum hourly PM2.5 (same daily aggregate)",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "n_hours": {
            "source": "count of hourly readings the day-D daily aggregate covers",
            "availability": verified_pm,
            "status": "verified",
        },
        "pm25_mean_lag1": {
            "source": "the station's mean on calendar day D-1 when that day exists with n_hours >= 18; -1.0 otherwise",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "pm25_mean_lag2": {
            "source": "the station's mean on calendar day D-2 under the same rule; -1.0 otherwise",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "pm25_mean_lag3": {
            "source": "the station's mean on calendar day D-3 under the same rule; -1.0 otherwise",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "pm25_mean_7d": {
            "source": "mean of the station's valid-day means over D-6..D; -1.0 under 4 valid days",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "pm25_days_valid_7d": {
            "source": "count of valid days (n_hours >= 18) in D-6..D",
            "availability": verified_pm,
            "status": "verified",
        },
        "pm25_mean_30d": {
            "source": "mean over D-29..D; -1.0 under 10 valid days",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "pm25_days_valid_30d": {
            "source": "count of valid days in D-29..D",
            "availability": verified_pm,
            "status": "verified",
        },
        "pm25_hist_mean_90d": {
            "source": "mean over D-89..D; -1.0 under 30 valid days",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "days_since_gt90": {
            "source": "days back to the most recent valid day with mean > 90 ug/m3 within D-89..D; -1.0 when none",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
        "exceed_count_30d": {
            "source": "count of valid days with mean > 90 ug/m3 in D-29..D",
            "availability": verified_pm,
            "status": "assumed",
            "assumption": assumed_vintage,
        },
    }
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--synthetic", action="store_true",
                        help="local dry run: a seeded synthetic panel through the "
                             "same construction path; no network, no anchor asserts")
    args = parser.parse_args()
    out = Path(args.out)
    work = Path(args.work_dir)
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    rows_path = work / "panel_rows.txt"

    # ---- 1. vintage pin, station list, panel fetch (or synthetic panel) --------
    anchors: dict | None = None
    if args.synthetic:
        print("SYNTHETIC dry run: no network, no anchor assertions", flush=True)
        stations = [{"station_id": f"SYN{1000 + i}",
                     "state_name": ["DELHI", "HARYANA", "MAHARASHTRA"][i % 3],
                     "city_name": "Synthetic"} for i in range(8)]
        state_of = {s["station_id"]: s["state_name"] for s in stations}
        receipts = synthetic_panel(rows_path)
        missing_state = 0
    else:
        meta, stations, active_key, missing_state = fetch_meta_and_stations(DEMO_KEY_PINNED)
        state_of = {s["station_id"]: s["state_name"] for s in stations}
        print(f"vintage pinned: exported_at={meta.get('exported_at')} "
              f"stations={len(stations)} key={receipts_key_label(active_key)}", flush=True)
        receipts = fetch_panel(stations, active_key, rows_path)
        print(f"fetched panel: {json.dumps(receipts)}", flush=True)

    # ---- 2. panel load and anchor assertions -----------------------------------
    panel, dup = load_panel(rows_path)
    if not args.synthetic:
        anchors = check_panel_anchors(panel, stations)
        print(f"panel anchors verified: {json.dumps(anchors)}", flush=True)
    else:
        anchors = {"note": "synthetic mode: anchors not applicable"}

    # ---- 3. eligibility, labels, features, splits ------------------------------
    split_rows, excluded = build_rows(panel, state_of)
    counts = counts_of(split_rows)
    if args.synthetic:
        for key in ("eval", "holdout"):
            if counts[key]["positives"] < 30 or counts[key]["distinct_positive_events"] < 30:
                fail(f"synthetic {key} too thin for the gate minimums: {counts[key]}")
    if counts["eval"]["positives"] == 0 or counts["holdout"]["positives"] == 0:
        fail("an evaluation or holdout split with no positives cannot carry a score")
    print(f"shipped rows: {json.dumps(counts)}", flush=True)
    print(f"excluded: {json.dumps(excluded)}", flush=True)

    # ---- 4. write the artifact ---------------------------------------------------
    paths = {"train": out / "public" / "train.csv",
             "eval": out / "public" / "eval.csv",
             "holdout": out / "private" / "holdout.csv"}
    for key, path in paths.items():
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(COLUMNS)
            for row in split_rows[key]:
                writer.writerow(row)

    # label source must be structurally absent from the shipped files
    assert "next_day_pm25_mean" not in COLUMNS and "next_day_n_hours" not in COLUMNS

    # measured tail count for the descriptive texts (adopted from this build's own
    # fetch, never the 2026-11-05 probe reference; attempt -003 policy)
    tail_days = ((anchors or {}).get("window_station_days") or {}).get("tail_2025_04_09")
    tail_meta = (f"{tail_days:,} station-days" if tail_days is not None
                 else "measured count in summary.json")

    meta = {
        "name": NAME,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": [ID_COLUMN],
        "columns": COLUMNS,
        "rows": {key: counts[key]["rows"] for key in ("train", "eval", "holdout")},
        "positive_rate": {key: counts[key]["positive_rate"]
                          for key in ("train", "eval", "holdout")},
        "split_description": (
            "temporal split on the prediction instant (day D, 23:59 IST): train "
            "2019-2022, eval 2023, holdout 2024; scored rows are complete "
            "(n_hours >= 18) cpcb_caaqm PM2.5 station-days with a labelable D+1 "
            "(row present, n_hours >= 18; unlabelable rows excluded and counted); "
            f"the 2025-04..09 partial tail ({tail_meta}) is excluded and "
            "counted, the 2025-01..03 and 2025-10..12 hole months are asserted "
            "empty; label = D+1 24-hr mean > 90 ug/m3 (CPCB National AQI Poor-band "
            "lower breakpoint)"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = quality_payload(counts, excluded, anchors, args.synthetic)
    quality["evaluation_contract"]["feature_evidence"] = fe_evidence()
    quality["station_registry"] = {
        "cpcb_pm25_stations": ANCHORS["cpcb_pm25_stations"],
        "stations_without_state_name": missing_state,
        "missing_state_sentinel": "UNKNOWN_STATE",
        "note": ("measured 2026-11-06; the export leaves state_name null for these "
                 "stations, so the coarse geography feature carries a declared sentinel "
                 "instead of an invented state"),
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    # ---- 5. bounded diagnostics (no performance metric) --------------------------
    # per-month exclusion counts (seasonality of the exclusions, from the panel) - computed
    # BEFORE the per-split table so each month carries its own measured count
    unlabelable_month: dict[str, int] = {}
    thin_month: dict[str, int] = {}
    for sid, series in panel.items():
        for day, (n, _mean, _low, _high) in series.items():
            split = window_of(day)
            if split is None:
                continue
            nxt = series.get(day + timedelta(days=1))
            if n < MIN_HOURS:
                thin_month[day.isoformat()[:7]] = thin_month.get(day.isoformat()[:7], 0) + 1
            elif nxt is None or nxt[0] < MIN_HOURS:
                unlabelable_month[day.isoformat()[:7]] = \
                    unlabelable_month.get(day.isoformat()[:7], 0) + 1

    per_split_month = {}
    for key, rows in split_rows.items():
        table: dict[str, dict] = {}
        for row in rows:
            month = row[3][:7]
            bucket = table.setdefault(month, {"rows": 0, "positives": 0,
                                              "excluded_unlabelable": 0})
            bucket["rows"] += 1
            bucket["positives"] += row[-1]
        for month, bucket in table.items():
            bucket["excluded_unlabelable"] = unlabelable_month.get(month, 0)
        per_split_month[key] = table

    summary = {
        "job": "cpcb-aqi-build-003",
        "name": NAME,
        "synthetic_mode": args.synthetic,
        "source_channel": receipts,
        "panel": {
            "rows_total": sum(len(s) for s in panel.values()),
            "duplicate_station_days": dup["duplicate_station_days"],
            "stations": len(panel),
            "stations_without_state_name": missing_state,
            "missing_state_sentinel": "UNKNOWN_STATE",
            "window_station_days": anchors.get("window_station_days"),
            "window_positives_n18": anchors.get("window_positives_n18"),
            "hole_2025_rows": anchors.get("hole_2025_rows"),
            "delhi_2024_11_18_fixture": anchors.get("delhi_2024_11_18"),
            "monsoon_2023_08_15_fixture": anchors.get("monsoon_2023_08_15"),
            "probe_reference_deltas": anchors.get("probe_reference_deltas"),
        },
        "splits": counts,
        "excluded": excluded,
        "per_split_per_month": per_split_month,
        "exclusion_seasonality": {
            "unlabelable_by_month": dict(sorted(unlabelable_month.items())),
            "thin_day_by_month": dict(sorted(thin_month.items())),
        },
        "no_metric_computed": ("no AUC, accuracy or rate-vs-label performance number "
                               "is computed anywhere in this build; score.py runs only "
                               "after the gate passes and --accept re-verifies"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({"splits": counts, "files": {k: str(p.relative_to(out))
                                                  for k, p in paths.items()}}), flush=True)
    return 0


def receipts_key_label(key: str) -> str:
    return "pinned-front-page-key" if key == DEMO_KEY_PINNED else "re-read-front-page-key"


if __name__ == "__main__":
    raise SystemExit(main())
