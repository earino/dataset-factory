#!/usr/bin/env python3
"""Construction script for the `eutl-installation-net-short` candidate.

Task: at the close of compliance year t-1's surrender cycle (30 April of year
t - the prediction instant), an ETS installation's verified emissions and free
allocation for t-1 are settled in the Union Registry and its year-t free
allocation is already fixed. Will the installation's verified emissions for
year t exceed the free allocation it holds for year t (a net-short year: the
operator must buy allowances to surrender, or face the excess-emissions
penalty)?

Where this runs
---------------
On a temporary worker: one anonymous GET of the Union Registry daily bulk
extract `operators_yearly_activity_daily.csv.gz` (5,965,780 bytes measured
2026-10-22, snapshot date 2026-10-22) plus the EEA aggregate product zip
(10,794,107 bytes measured) for the publisher cross-check. `--panel-file` /
`--eea-file` accept local copies for a full-assertion dry run on a
coordinator-class machine.

Frame rules (from the candidate record; each measured and reported)
----------------------------------------------------------------------
* Grain: one row per (REGISTRY_CODE, INSTALLATION_IDENTIFIER, PERIOD_YEAR t)
  on the stationary-installation yearly activity extract. The extract is
  rectangular (one row per installation x year 2005-2030), so n/a values - not
  absent rows - mark out-of-frame installation-years.
* In-frame (label rule): both VERIFIED_EMISSIONS(t) and ALLOCATION(t) numeric.
  net_short = 1 iff VERIFIED_EMISSIONS(t) > ALLOCATION(t); an exact tie is 0
  (net-long including balance; 4,224 ties measured on the 2026-10-22
  snapshot, counted). Rows with VE(t) or ALLOCATION(t) = n/a are out of frame:
  counted per year in the frame mix, never silently dropped. Year-2026+ rows
  with allocation but no emissions are the live prediction years (6,449 rows
  measured), scorable when 2026 emissions are reported by 31 March 2027.
* Eligibility: VERIFIED_EMISSIONS(t-1) and ALLOCATION(t-1) both numeric - the
  row needs one settled prior year (16,709 installation-years excluded as
  insufficient_history and counted; this removes every 2005 row, whose t-1
  year predates the extract). EXCLUDED(t)=YES rows are kept (81 in-frame rows,
  0.04%, mix recorded); the flag is a year-t property and cannot condition
  membership at the instant.
* Prediction instant: 30 April of year t, the surrender deadline closing year
  t-1's compliance cycle. Verified emissions for t-1 are reported by 31 March
  (120 days after the t-1 period end at the latest for the surrender side);
  year t's ALLOCATION is fixed in advance by the phase-4 national
  implementation measures and is published in the registry (the extract
  carries allocation rows through 2030, measured). Year t's verified
  emissions are reported by 31 March t+1 and are absent from the registry at
  the instant (measured: no numeric VE for years > 2025).
* Features: last-year levels and derived margins only - ve_l1, alloc_l1,
  alloc_t (announced), alloc_change, margin_l1 (the t-1 net position, the
  persistence analogue), margin_t (last emissions against the announced
  allocation), net_short_l1 (status persistence), age_years, plus registry
  identity and the calendar year. SURR_ALL(t-1) was probed and is missing on
  10,647 of 188,205 eligible rows, so the surrender-history feature is dropped
  rather than shipped partially defined; the decision is recorded.
* Label source columns VERIFIED_EMISSIONS(t) and ALLOCATION(t) are recorded
  in label_source_columns and asserted absent from every written header
  (the shipped alloc_t/ve_l1/margin features are strictly t-1 or pre-announced
  t-allocation quantities; ALLOCATION(t) alone does not determine the label).
* Splits (the record's candidate partition): train 2006-2019, eval 2020-2022,
  holdout 2023-2025. The net-short base rate drifts with the ETS phase
  (train 45.5%, eval 74.0%, holdout 72.2% on eligible rows) - the free
  allocation share fell while the cap declined; a documented phenomenon
  property, not smoothed.
* Event key: installation_key = REGISTRY_CODE@INSTALLATION_IDENTIFIER. An
  installation's net-short status is autocorrelated year to year (measured
  P(short t | short t-1) = 0.857), so the clustered positive count is
  distinct installations, not rows. Installations recur across windows by
  construction of a panel; the composite row id (registry, installation,
  year) is unique per row and the recurring-entity property is declared, not
  treated as split leakage. Shared-regime year effects are documented as the
  per-year prevalence drift instead.
* Known fixtures (recorded in the candidate record, verified in-panel at
  discovery and asserted in-build): (AT, installation 1, 2005) VE 41,399 <
  ALLOC 44,894 -> net-long; (AT, 1, 2007) VE 51,041 > 44,894 -> net-short;
  (AT, 1, 2030) carries advance ALLOCATION 30,485 with VE n/a. The phase-3
  allocation cut mass-flips the panel: the eligible-row 2013 net-short rate
  exceeds the 2012 rate by >= 0.25 (measured gap 0.331).
* Publisher cross-check (in-build, asserted): panel installation sums against
  the EEA's own aggregate product (country x activity x year) for DE 2022 and
  2023, activity codes 10 and 20-99, all entities: VERIFIED_EMISSIONS within
  0.001% (measured: 2022 exact, 2023 diff 4 t = 1.3e-8) and ALLOCATION within
  0.1% (measured 4.3e-4 / 2.7e-4). The sum must use exactly the {10, 20-99}
  activity rows: the EEA sheet also carries per-activity detail rows (20,
  21, ...) whose inclusion double-counts.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: Commission reuse policy - CC BY 4.0 unless otherwise indicated
(class A, recorded in the candidate record's license_evidence with the EEA's
independent confirmation); attribution "European Commission, DG CLIMA - Union
Registry public extracts" carries through to any release. Derived research
dataset - never the Commission's official product.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NAME = "eutl-installation-net-short"
TARGET = "net_short"
POSITIVE_LABEL = 1

PANEL_URL = ("https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic_prod/"
             "extracts/_all_extracts/operators_yearly_activity/"
             "operators_yearly_activity_daily.csv.gz")
EEA_URL = "https://sdi.eea.europa.eu/datashare/s/aZ7Ti5HkRGEbF62/download"

# Split windows in compliance years (end exclusive, as the gate checks).
TRAIN_START, TRAIN_END = 2006, 2019
EVAL_START, EVAL_END = 2020, 2022
HOLDOUT_START, HOLDOUT_END = 2023, 2025
LIVE_YEAR = 2026            # allocation published, emissions not yet reported

MIN_KEYS = 20000            # measured 23,748 keys on the 2026-10-22 snapshot
MIN_REGISTRIES = 30        # measured 32
MIN_LIVE_ROWS = 5000        # measured 6,449 year-2026 alloc-only rows
MIN_SPLIT_POSITIVES = 30    # gate threshold
MIN_SPLIT_EVENTS = 20       # gate threshold
PHASE3_FLIP_MIN_GAP = 0.25  # measured eligible-row gap 0.331
VE_TOLERANCE = 1e-5         # cross-check relative tolerance, verified emissions
ALLOC_TOLERANCE = 1e-3      # cross-check relative tolerance, free allocation
VE_LABEL = "2.1 EU-ETS Verified Emission"
FA_LABEL = "1.1 Freely allocated allowances"
CROSSCHECK_ACTIVITIES = {"10", "20-99"}
CROSSCHECK_CELLS = [
    # (registry, year, field, measured panel sum on the 2026-10-22 snapshot)
    ("DE", 2022, "ve", 361145695.0),
    ("DE", 2023, "ve", 296989213.0),
    ("DE", 2022, "alloc", 129078621.0),
    ("DE", 2023, "alloc", 127923163.0),
]

# Shipped layout: id, features, carry, target.
ID_COLUMNS = ["row_id"]
FEATURES = ["registry_code", "period_year", "ve_l1", "alloc_l1", "alloc_t",
            "alloc_change", "margin_l1", "margin_t", "net_short_l1",
            "age_years"]
CARRY_COLUMNS = ["installation_key"]
HIGH_CARDINALITY = ["row_id", "installation_key"]
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

PREDICTION_TIME = (
    "30 April of compliance year t, the surrender deadline that closes year "
    "t-1's compliance cycle: by then the installation's verified emissions "
    "for t-1 (reported by 31 March) and its surrendered allowances for t-1 "
    "are settled in the Union Registry, and its year-t free allocation is "
    "already fixed and published (the extract carries allocation rows "
    "through 2030, measured). Year t's verified emissions are reported by "
    "31 March t+1 and are absent from the registry at the instant (measured: "
    "no numeric verified emissions for years after 2025 in the daily "
    "extract). The extract refreshes daily, so a monthly refresh of this "
    "task is honest.")
PREDICTION_QUESTION = (
    "At the close of compliance year t-1's surrender cycle (30 April of year "
    "t), will a stationary EU ETS installation's verified emissions for year "
    "t exceed the free allocation it holds for year t (a net-short year), "
    "given its verified-emissions and free-allocation history through t-1, "
    "its already-published year-t allocation, its registry and its "
    "identifier?")


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, dest: Path, attempts: int = 3) -> dict:
    last_error = None
    for attempt in range(attempts):
        try:
            started = time.time()
            request = urllib.request.Request(
                url, headers={"User-Agent": "dataset-factory/eutl-build"})
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
        except Exception as error:           # bounded retry, then fail loudly
            last_error = error
            log(f"fetch attempt {attempt + 1} failed: {error}; retrying")
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"fetch failed after {attempts} attempts: {url}: {last_error}")


def num(text) -> float | None:
    text = (text or "").strip()
    if not text or text.lower() == "n/a":
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value == value else None


def fmt_num(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_panel(path: Path) -> tuple[dict, dict]:
    """Read the daily extract into {(reg, inst): {year: (ve, alloc, excluded)}}
    plus the frame mix (the discovery rule: count the mix of every provenance
    column before deciding what a row means)."""
    data: dict[tuple[str, str], dict[int, tuple]] = defaultdict(dict)
    registries: Counter = Counter()
    excluded_mix: Counter = Counter()
    snapshot_dates: Counter = Counter()
    frame: dict[int, Counter] = defaultdict(Counter)
    rows = 0
    bad_ids = 0
    header: list[str] = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        required = {"REGISTRY_CODE", "INSTALLATION_IDENTIFIER", "PERIOD_YEAR",
                    "VERIFIED_EMISSIONS", "ALLOCATION", "EXCLUDED",
                    "SNAPSHOT_DATE"}
        missing = sorted(required - set(header))
        if missing:
            raise SystemExit(f"extract header missing columns: {missing}")
        for row in reader:
            rows += 1
            reg = (row.get("REGISTRY_CODE") or "").strip()
            inst = (row.get("INSTALLATION_IDENTIFIER") or "").strip()
            year = int((row.get("PERIOD_YEAR") or "0").strip())
            ve = num(row.get("VERIFIED_EMISSIONS"))
            alloc = num(row.get("ALLOCATION"))
            excluded = (row.get("EXCLUDED") or "").strip()
            registries[reg] += 1
            excluded_mix[excluded] += 1
            snapshot_dates[(row.get("SNAPSHOT_DATE") or "").strip()] += 1
            if "@" in reg or "@" in inst:
                bad_ids += 1
            if ve is not None and alloc is not None:
                frame[year]["in_frame"] += 1
            elif ve is None and alloc is not None:
                frame[year]["ve_na_alloc_num"] += 1
            elif ve is not None:
                frame[year]["alloc_na"] += 1
            else:
                frame[year]["both_na"] += 1
            data[(reg, inst)][year] = (ve, alloc, excluded)
    years = sorted({year for per in data.values() for year in per})
    info = {
        "rows": rows,
        "keys": len(data),
        "registries": len(registries),
        "registry_mix": dict(registries),
        "excluded_mix": dict(excluded_mix),
        "snapshot_dates": dict(snapshot_dates),
        "years": {"min": years[0], "max": years[-1], "count": len(years)},
        "frame_mix_by_year": {year: dict(counter) for year, counter
                              in sorted(frame.items())},
        "bad_ids": bad_ids,
        "header": header,
    }
    return dict(data), info


def split_of(year: int) -> str | None:
    if TRAIN_START <= year <= TRAIN_END:
        return "train"
    if EVAL_START <= year <= EVAL_END:
        return "eval"
    if HOLDOUT_START <= year <= HOLDOUT_END:
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
    positive_rank_sum = sum(rank for rank, (_, label) in zip(ranks, pairs)
                             if label == 1)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def fit_rate_table(rows: list[dict], *keys) -> dict[tuple, float]:
    totals: Counter = Counter()
    positives: Counter = Counter()
    for row in rows:
        key = tuple(row[name] for name in keys)
        totals[key] += 1
        positives[key] += row[TARGET]
    return {key: positives[key] / totals[key] for key in totals}


def phase_of(year: int) -> int:
    """ETS trading phase (the record's drift documentation axis)."""
    if year <= 2007:
        return 1
    if year <= 2012:
        return 2
    if year <= 2020:
        return 3
    return 4


def build_rows(data: dict) -> tuple[dict, dict]:
    rows_by_split: dict[str, list[dict]] = {"train": [], "eval": [], "holdout": []}
    accounting: Counter = Counter()
    per_year: dict[str, dict[int, Counter]] = {split: defaultdict(Counter)
                                               for split in rows_by_split}
    transition: Counter = Counter()
    excluded_in_frame: Counter = Counter()
    label_by_excluded: dict[str, Counter] = defaultdict(Counter)
    ties = 0
    live_rows = 0
    for (reg, inst) in sorted(data):
        per = data[(reg, inst)]
        first_active = None
        for year in sorted(per):
            if per[year][0] is not None:
                first_active = year
                break
        for year in sorted(per):
            ve, alloc, excluded = per[year]
            if ve is None or alloc is None:
                if year == LIVE_YEAR and alloc is not None:
                    live_rows += 1
                continue
            label = int(ve > alloc)
            if ve == alloc:
                ties += 1
            excluded_in_frame[excluded] += 1
            label_by_excluded[excluded][label] += 1
            prev = per.get(year - 1)
            if not prev or prev[0] is None or prev[1] is None:
                accounting["insufficient_history"] += 1
                continue
            ve_l1, alloc_l1 = prev[0], prev[1]
            split = split_of(year)
            if split is None:
                accounting["outside_windows"] += 1
                continue
            transition[(int(ve_l1 > alloc_l1), label)] += 1
            row = {
                "row_id": f"{reg}@{inst}@{year}",
                "registry_code": reg,
                "period_year": year,
                "ve_l1": fmt_num(ve_l1),
                "alloc_l1": fmt_num(alloc_l1),
                "alloc_t": fmt_num(alloc),
                "alloc_change": fmt_num(alloc - alloc_l1),
                "margin_l1": fmt_num(ve_l1 - alloc_l1),
                "margin_t": fmt_num(ve_l1 - alloc),
                "net_short_l1": int(ve_l1 > alloc_l1),
                "age_years": (year - 1) - first_active if first_active else 0,
                "installation_key": f"{reg}@{inst}",
                TARGET: label,
                "_margin_l1": ve_l1 - alloc_l1,
                "_excluded": excluded,
            }
            rows_by_split[split].append(row)
            per_year[split][year][label] += 1
    pss = transition[(1, 1)] + transition[(1, 0)]
    psl = transition[(0, 1)] + transition[(0, 0)]
    diagnostics = {
        "accounting": dict(accounting),
        "ties_label_zero": ties,
        "live_year_rows": live_rows,
        "excluded_mix_in_frame": dict(excluded_in_frame),
        "label_by_excluded": {key: dict(counter) for key, counter
                              in label_by_excluded.items()},
        "status_persistence": {
            "p_short_given_short": round(transition[(1, 1)] / pss, 4) if pss else None,
            "p_short_given_long": round(transition[(0, 1)] / psl, 4) if psl else None,
        },
        "per_year_label_counts": {split: {year: dict(counter) for year, counter
                                          in sorted(years.items())}
                                  for split, years in per_year.items()},
    }
    return rows_by_split, diagnostics


def write_splits(out: Path, rows_by_split: dict[str, list[dict]]) -> dict:
    stats = {}
    for split, relative in LAYOUT.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(rows_by_split[split],
                      key=lambda row: (row["period_year"], row["row_id"]))
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        # The gate recomputes events as distinct value[:10] of the event key
        # among positives; declare exactly that, and record the full
        # installation count alongside.
        events = {row["installation_key"][:10] for row in rows if row[TARGET] == POSITIVE_LABEL}
        installations = {row["installation_key"] for row in rows if row[TARGET] == POSITIVE_LABEL}
        stats[split] = {"rows": len(rows), "positives": positives,
                        "positive_rate": round(positives / len(rows), 6) if rows else None,
                        "distinct_events": len(events),
                        "distinct_installations_positive": len(installations)}
    return stats


def crosscheck_eea(eea_path: Path, data: dict) -> dict:
    """Panel installation sums vs the EEA's own aggregate product.

    Streams the ETS_Database xlsx inside the EEA zip and sums, for each
    cross-check cell, the {10, 20-99} activity rows (all entities, all sizes)
    - the subset the discovery session measured to match the panel; including
    the per-activity detail rows would double-count.
    """
    panel: dict[tuple, float] = defaultdict(float)
    for (reg, inst), per in data.items():
        for year, (ve, alloc, _) in per.items():
            if reg == "DE" and year in (2022, 2023):
                if ve is not None:
                    panel[(reg, year, "ve")] += ve
                if alloc is not None:
                    panel[(reg, year, "alloc")] += alloc
    with zipfile.ZipFile(eea_path) as archive:
        members = [name for name in archive.namelist()
                   if name.endswith(".xlsx") and "ETS_Database" in name]
        if len(members) != 1:
            raise SystemExit(f"EEA zip does not carry exactly one ETS_Database "
                             f"xlsx: {members}")
        data_bytes = archive.read(members[0])
    inner = zipfile.ZipFile(io.BytesIO(data_bytes))
    shared: list[str] = []
    with inner.open("xl/sharedStrings.xml") as handle:
        for _, element in ET.iterparse(handle, events=("end",)):
            if element.tag.endswith("}t") or element.tag == "t":
                shared.append(element.text or "")
            element.clear()
    eea: dict[tuple, float] = defaultdict(float)
    with inner.open("xl/worksheets/sheet1.xml") as handle:
        for _, row_element in ET.iterparse(handle, events=("end",)):
            if not row_element.tag.endswith("}row"):
                continue
            cells: dict[str, str] = {}
            for cell in row_element:
                match = re.match(r"([A-Z]+)", cell.get("r") or "")
                if not match:
                    continue
                value_element = cell.find("{*}v")
                if value_element is None or value_element.text is None:
                    continue
                text = value_element.text
                if cell.get("t") == "s":
                    text = shared[int(text)]
                cells[match.group(1)] = text
            row_element.clear()
            # header: version; country_code; main_activity_code; active_installation;
            #         citl_information; year; size; value; unit -> A..I
            if cells.get("B") != "DE" or cells.get("D") != "all entities":
                continue
            if cells.get("C") not in CROSSCHECK_ACTIVITIES:
                continue
            if cells.get("G") != "All sizes":
                continue
            label = cells.get("E", "")
            try:
                year = int(float(cells.get("F", "0")))
            except (TypeError, ValueError):
                continue
            if label not in (VE_LABEL, FA_LABEL) or year not in (2022, 2023):
                continue
            try:
                value = float(cells.get("H"))
            except (TypeError, ValueError):
                continue
            eea[(year, "ve" if label == VE_LABEL else "alloc")] += value
    results = {}
    for reg, year, field, measured_panel in CROSSCHECK_CELLS:
        panel_value = panel.get((reg, year, field), 0.0)
        eea_value = eea.get((year, field), 0.0)
        diff = eea_value - panel_value
        rel = abs(diff) / panel_value if panel_value else None
        results[f"{reg}-{year}-{field}"] = {
            "eea_value": eea_value, "panel_value": panel_value,
            "diff": diff, "rel": rel,
            "tolerance": VE_TOLERANCE if field == "ve" else ALLOC_TOLERANCE,
            "ok": rel is not None and rel <= (VE_TOLERANCE if field == "ve"
                                              else ALLOC_TOLERANCE),
        }
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Build the {NAME} extract")
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--work-dir", default="/tmp/eutl")
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--panel-file", default=None,
                        help="local extract csv.gz (dry run); default fetches live")
    parser.add_argument("--eea-file", default=None,
                        help="local EEA zip (dry run); default fetches live")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log("== download ==")
    if args.panel_file:
        panel_path = Path(args.panel_file)
        sources = {"panel": {"url": "local:" + str(panel_path),
                             "bytes": panel_path.stat().st_size,
                             "last_modified": None, "seconds": 0.0,
                             "sha256": sha256_file(panel_path)}}
    else:
        panel_path = work / "operators_yearly_activity_daily.csv.gz"
        sources = {"panel": fetch(PANEL_URL, panel_path)}
    log(f"panel: {sources['panel']['bytes']} bytes, "
        f"last-modified {sources['panel']['last_modified']}, "
        f"{sources['panel']['seconds']} s")

    log("== parse panel ==")
    data, panel_info = load_panel(panel_path)
    log(json.dumps({key: panel_info[key] for key in
                   ("rows", "keys", "registries", "years", "excluded_mix",
                    "snapshot_dates", "bad_ids")}, indent=1))

    log("== build rows ==")
    rows_by_split, diagnostics = build_rows(data)
    accounting = diagnostics["accounting"]
    for split in rows_by_split:
        log(f"{split}: {len(rows_by_split[split])} rows")
    log(f"accounting: {accounting}; ties {diagnostics['ties_label_zero']}; "
        f"live year {LIVE_YEAR} rows {diagnostics['live_year_rows']}")
    log(f"status persistence: {diagnostics['status_persistence']}")

    stats = write_splits(out, rows_by_split)
    for split, entry in stats.items():
        log(f"{split}: {entry['rows']} rows, {entry['positives']} positives "
            f"(rate {entry['positive_rate']}), {entry['distinct_events']} distinct "
            f"events (gate prefix rule), {entry['distinct_installations_positive']} "
            f"distinct installations")

    log("== publisher cross-check (EEA aggregate product) ==")
    if args.eea_file:
        eea_path = Path(args.eea_file)
        sources["eea_aggregate"] = {"url": "local:" + str(eea_path),
                                    "bytes": eea_path.stat().st_size,
                                    "last_modified": None, "seconds": 0.0,
                                    "sha256": sha256_file(eea_path)}
    else:
        eea_path = work / "eea_ets.zip"
        sources["eea_aggregate"] = fetch(EEA_URL, eea_path)
    log(f"eea aggregate: {sources['eea_aggregate']['bytes']} bytes, "
        f"{sources['eea_aggregate']['seconds']} s")
    crosscheck = crosscheck_eea(eea_path, data)
    for cell, entry in crosscheck.items():
        log(f"cross-check {cell}: EEA {entry['eea_value']:.0f} vs panel "
            f"{entry['panel_value']:.0f} (rel {entry['rel']:.3e}, "
            f"tolerance {entry['tolerance']}) -> "
            f"{'OK' if entry['ok'] else 'FAIL'}")

    # Known-event fixtures on the parsed panel (the record's sample rows).
    at1 = data.get(("AT", "1"), {})
    fixture_2005 = at1.get(2005)
    fixture_2007 = at1.get(2007)
    fixture_2030 = at1.get(2030)
    known_events = {
        "at_installation_1_2005": {
            "expected": "net-long: VE 41,399 < ALLOCATION 44,894",
            "measured": fixture_2005,
            "ok": bool(fixture_2005 and fixture_2005[0] == 41399
                       and fixture_2005[1] == 44894
                       and int(fixture_2005[0] > fixture_2005[1]) == 0)},
        "at_installation_1_2007": {
            "expected": "net-short: VE 51,041 > ALLOCATION 44,894",
            "measured": fixture_2007,
            "ok": bool(fixture_2007 and fixture_2007[0] == 51041
                       and fixture_2007[1] == 44894
                       and int(fixture_2007[0] > fixture_2007[1]) == 1)},
        "at_installation_1_2030": {
            "expected": "advance allocation 30,485 with no verified emissions",
            "measured": fixture_2030,
            "ok": bool(fixture_2030 and fixture_2030[0] is None
                       and fixture_2030[1] == 30485)},
    }
    per_year = diagnostics["per_year_label_counts"]
    rate_2012 = None
    rate_2013 = None
    if 2012 in per_year["train"] and 2013 in per_year["train"]:
        c12, c13 = per_year["train"][2012], per_year["train"][2013]
        rate_2012 = c12.get(1, 0) / max(1, c12.get(0, 0) + c12.get(1, 0))
        rate_2013 = c13.get(1, 0) / max(1, c13.get(0, 0) + c13.get(1, 0))
    flip_gap = (rate_2013 - rate_2012) if (rate_2012 is not None
                                           and rate_2013 is not None) else None
    known_events["phase3_allocation_cut_2013"] = {
        "expected": f"eligible-row net-short rate jumps by at least "
                    f"{PHASE3_FLIP_MIN_GAP} (measured gap 0.331 at discovery)",
        "rate_2012": rate_2012, "rate_2013": rate_2013, "gap": flip_gap,
        "ok": flip_gap is not None and flip_gap >= PHASE3_FLIP_MIN_GAP,
    }
    log("known events: " + json.dumps(known_events))

    # Reference baselines measured at construction on the written rows; rate
    # tables estimated on train rows only. The full-model leg of the triad is
    # the runner-contract baseline job on the accepted artifact.
    train_rows = rows_by_split["train"]
    train_rate = (sum(r[TARGET] for r in train_rows) / len(train_rows)) if train_rows else 0.0
    for row_list in rows_by_split.values():
        for row in row_list:
            row["_phase"] = phase_of(row["period_year"])
    identity_table = fit_rate_table(train_rows, "registry_code")
    calendar_table = fit_rate_table(train_rows, "registry_code", "_phase")
    baselines: dict[str, dict] = {"global_rate_train": round(train_rate, 6)}

    def round_or_none(value: float | None, digits: int = 4) -> float | None:
        return None if value is None else round(value, digits)

    for split in ("eval", "holdout"):
        rows = rows_by_split[split]
        labels = [row[TARGET] for row in rows]
        persistence_scores = [row["_margin_l1"] for row in rows]
        status_scores = [row["net_short_l1"] for row in rows]
        identity_scores = [identity_table.get((row["registry_code"],), train_rate)
                           for row in rows]
        calendar_scores = [calendar_table.get((row["registry_code"], row["_phase"]),
                                               identity_table.get((row["registry_code"],),
                                                                  train_rate))
                           for row in rows]
        baselines[split] = {
            "persistence_margin_l1_auc": round_or_none(auc(labels, persistence_scores)),
            "persistence_status_l1_auc": round_or_none(auc(labels, status_scores)),
            "persistence_status_accuracy": round(
                sum(1 for score, label in zip(status_scores, labels)
                    if score == label) / len(labels), 4),
            "identity_only_registry_auc": round_or_none(auc(labels, identity_scores)),
            "calendar_only_registry_phase_auc": round_or_none(auc(labels, calendar_scores)),
        }
    log("reference baselines: " + json.dumps(baselines))

    # Provenance and snapshot assertions: the panel must be the population the
    # record measured, or the label's meaning has silently changed.
    failures = []
    if panel_info["keys"] < MIN_KEYS:
        failures.append(f"only {panel_info['keys']} installation keys "
                        f"(< {MIN_KEYS})")
    if panel_info["registries"] < MIN_REGISTRIES:
        failures.append(f"only {panel_info['registries']} registries")
    if panel_info["years"]["max"] < 2030 or panel_info["years"]["min"] > 2005:
        failures.append(f"unexpected year coverage {panel_info['years']}")
    if panel_info["bad_ids"]:
        failures.append(f"{panel_info['bad_ids']} rows carry '@' inside identifiers")
    if diagnostics["live_year_rows"] < MIN_LIVE_ROWS:
        failures.append(f"only {diagnostics['live_year_rows']} live {LIVE_YEAR} rows")
    for name, entry in known_events.items():
        if not entry["ok"]:
            failures.append(f"known-event fixture {name} failed: {entry}")
    for cell, entry in crosscheck.items():
        if not entry["ok"]:
            failures.append(f"EEA cross-check {cell} outside tolerance: {entry}")
    for split in ("eval", "holdout"):
        entry = stats[split]
        if entry["positives"] < MIN_SPLIT_POSITIVES:
            failures.append(f"{split} too thin to score: {entry['positives']} positives")
        if entry["distinct_events"] < MIN_SPLIT_EVENTS:
            failures.append(f"{split} has only {entry['distinct_events']} distinct events")
        if entry["positives"] == 0 or entry["positives"] == entry["rows"]:
            failures.append(f"{split} is single-class: {entry}")
    if failures:
        for failure in failures:
            log(f"FAIL: {failure}")
        (out / "summary.json").write_text(json.dumps({
            "name": NAME, "built_at_utc": built_at, "failed": failures,
            "panel": panel_info, "splits": stats, "diagnostics": diagnostics,
        }, indent=1) + "\n")
        return 2

    # The label source columns must be absent from every written header.
    for split, relative in LAYOUT.items():
        with (out / relative).open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        if header != COLUMNS:
            log(f"FAIL: {relative} header differs from the declared columns")
            return 2

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "sources": sources,
        "grain": "one row per (REGISTRY_CODE, INSTALLATION_IDENTIFIER, "
                 "PERIOD_YEAR) on the operators_yearly_activity extract, "
                 "in-frame (label computable) and with a numeric t-1 year",
        "panel": panel_info,
        "splits": stats,
        "eligibility": diagnostics,
        "known_events": known_events,
        "publisher_crosscheck": crosscheck,
        "reference_baselines": {
            "note": "stdlib rank AUC measured at construction on the written "
                    "rows; rate tables estimated on train rows only. "
                    "Persistence (margin_l1 / last-year status) is the rule "
                    "the task must beat; the full-model leg of the triad is "
                    "the runner-contract baseline job on the accepted artifact.",
            **baselines,
        },
        "dropped_feature_note": "SURR_ALL(t-1) was probed as a surrender-"
                                "history feature and dropped: missing on "
                                "10,647 of 188,205 eligible rows (measured "
                                "2026-10-22), and a partially-defined column "
                                "cannot ship. Verified-emissions and "
                                "allocation history carry the signal.",
        "vintage": {
            "snapshot_date": max(panel_info["snapshot_dates"],
                                 key=lambda k: panel_info["snapshot_dates"][k]),
            "last_modified": sources["panel"].get("last_modified"),
            "revision_note": "features are current-snapshot values: the "
                             "registry can correct entries after the fact and "
                             "only the current daily extract is available, so "
                             "the timing claim is a documented assumption "
                             "against the statutory registry calendar",
        },
        "phase_drift_note": "the net-short base rate rises with the ETS phase "
                            "(free-allocation share fell while the cap "
                            "declined); reported per split and per year, not "
                            "smoothed",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": PANEL_URL,
        "license": "Union Registry public extracts: Commission reuse policy "
                   "CC BY 4.0 (source terms preserved; attribution 'European "
                   "Commission, DG CLIMA - Union Registry public extracts'). "
                   "Derived research dataset - not the Commission's official "
                   "product. Our derived compilation: CC0-1.0.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by compliance year (30 April surrender "
                              "deadline of year t)",
                  "boundaries": {"train": f"{TRAIN_START} .. {TRAIN_END}",
                                 "eval": f"{EVAL_START} .. {EVAL_END}",
                                 "holdout": f"{HOLDOUT_START} .. {HOLDOUT_END}"}},
        "label_rule": "net_short = 1 iff VERIFIED_EMISSIONS(t) > ALLOCATION(t); "
                      "exact ties are 0 and counted. Both label source values "
                      "are excluded from every shipped file.",
        "label_source_columns": ["VERIFIED_EMISSIONS(period t)",
                                 "ALLOCATION(period t)"],
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_sha256": sources["panel"]["sha256"],
        "vintage_last_modified": sources["panel"].get("last_modified"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION,
                 "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "period_year",
        "event_key_column": "installation_key",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped quantity is a Union Registry operators_yearly "
            "activity value (column semantics documented on the Union "
            "Registry Public Website data-download page, fetched by this "
            "build): VERIFIED_EMISSIONS and ALLOCATION are in tonnes "
            "CO2-equivalent (1 allowance = 1 tCO2e). ve_l1/alloc_l1 read "
            "year t-1; alloc_t reads the year-t free allocation fixed in "
            "advance by the phase-4 national implementation measures; "
            "margin/difference columns are derived in build.py's module "
            "docstring"),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": ["VERIFIED_EMISSIONS(period t)",
                                 "ALLOCATION(period t)"],
        "post_hoc_columns": ["VERIFIED_EMISSIONS(period t)",
                             "CH_VERIFIED_EMISSIONS(period t)",
                             "SURR_ALL(period t)",
                             "EXCLUDED(period t)",
                             "SNAPSHOT_DATE"],
        "measurements": [
            {"column": "registry_code",
             "unit": "Union Registry country code (EU Member State, EEA-EFTA "
                     "member or XI = Northern Ireland electricity)",
             "frame": "the installation's registry (country) identity; 32 "
                      "registries measured on the 2026-10-22 snapshot"},
            {"column": "period_year",
             "unit": "calendar year (integer)",
             "frame": "compliance year t, the year whose net-short status is "
                      "predicted; the split time column"},
            {"column": "ve_l1",
             "unit": "verified emissions, tonnes CO2-equivalent",
             "frame": "VERIFIED_EMISSIONS of year t-1, reported to the "
                      "registry by 31 March of year t and settled at the "
                      "instant; current-snapshot vintage (the registry can "
                      "correct entries after the fact; only the current daily "
                      "extract is available, so this is stated as "
                      "current-vintage with the cutoff a documented "
                      "assumption)"},
            {"column": "alloc_l1",
             "unit": "free allocation, allowances (1 allowance = 1 tCO2e)",
             "frame": "ALLOCATION of year t-1, as recorded in the registry at "
                      "the instant"},
            {"column": "alloc_t",
             "unit": "free allocation, allowances",
             "frame": "ALLOCATION of year t, fixed in advance by the phase-4 "
                      "national implementation measures and published "
                      "before the instant (measured: the extract carries "
                      "allocation rows through 2030); one side of the label "
                      "comparison but fully known at the instant and does "
                      "not determine the label on its own"},
            {"column": "alloc_change",
             "unit": "allowances (difference)",
             "frame": "alloc_t - alloc_l1, the announced allocation change "
                      "between the last settled year and the target year"},
            {"column": "margin_l1",
             "unit": "allowances (net position)",
             "frame": "ve_l1 - alloc_l1, the installation's net position at "
                      "t-1; the persistence analogue the task must beat"},
            {"column": "margin_t",
             "unit": "allowances (net position)",
             "frame": "ve_l1 - alloc_t, last verified emissions against the "
                      "announced year-t allocation; the natural one-line "
                      "solver rule"},
            {"column": "net_short_l1",
             "unit": "binary indicator",
             "frame": "1 iff ve_l1 > alloc_l1, the status persistence rule "
                      "(measured P(short t | short t-1) = 0.857, "
                      "P(short t | long t-1) = 0.176 on eligible rows)"},
            {"column": "age_years",
             "unit": "years",
             "frame": "(t-1) minus the first year with numeric verified "
                      "emissions in the extract; installations operating "
                      "before 2005 have the age understated by the 2005 left "
                      "edge - a documented left-truncation property"},
            {"column": "installation_key",
             "unit": "composite identifier REGISTRY_CODE@INSTALLATION_IDENTIFIER",
             "frame": "the installation identity across years; the event key "
                      "because an installation's net-short status is "
                      "autocorrelated year to year"},
            {"column": "row_id",
             "unit": "composite identifier registry@installation@year",
             "frame": "unique per row; installations recur across split "
                      "windows by construction of a panel - a declared "
                      "property, not split leakage (the composite id is "
                      "unique across all splits)"},
            {"column": "net_short",
             "unit": "binary indicator",
             "frame": "1 iff VERIFIED_EMISSIONS(t) > ALLOCATION(t); exact "
                      "ties are 0 and counted (4,224 measured); both source "
                      "values are excluded from the shipped columns"},
        ],
        "known_event": {
            "name": "record sample rows and the phase-3 allocation cut",
            "expected": "(AT, installation 1, 2005) is net-long, (2007) is "
                        "net-short, (2030) carries advance allocation with "
                        "no emissions; the eligible-row net-short rate jumps "
                        "from 2012 to 2013 by at least 0.25",
            "source": "Union Registry extract; candidate record "
                      "sample_rows / discovery measurements, verified "
                      "in-panel at discovery 2026-10-20/21",
            "measured": known_events,
        },
        "timing": {
            "prediction_instant": {
                "kind": "publication",
                "period": "Y",
                "days_after_period_end": 120,
                "citation": "Union Registry compliance calendar: verified "
                            "emissions for year t-1 are reported by 31 March "
                            "(Monitoring and Reporting Regulation (EU) "
                            "2018/2066 Art. 7) and allowances surrendered by "
                            "30 April (Directive 2003/87/EC Art. 12(3)) - 120 "
                            "days after the t-1 period end. The instant is "
                            "the close of year t-1's compliance cycle, when "
                            "every shipped t-1 feature is settled in the "
                            "registry and the year-t allocation is in force. "
                            "The extract is an administrative record refreshed "
                            "daily (SNAPSHOT_DATE 2026-10-22 measured; HTTP "
                            "Last-Modified 2026-10-22 measured), so no "
                            "separate statistical-release lag exists to "
                            "observe; the statutory deadlines are the "
                            "publisher's own calendar.",
            },
            "features": {
                "period": "Y",
                "published_days_after_period_end": 120,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "t-1",
                "fields": ["REGISTRY_CODE", "INSTALLATION_IDENTIFIER",
                           "PERIOD_YEAR"],
                "basis": "rows are (installation, year t) pairs whose label "
                         "inputs VERIFIED_EMISSIONS(t) and ALLOCATION(t) are "
                         "both numeric; a row without them is out of frame "
                         "(counted per year in the frame mix, never silently "
                         "dropped) - its own outcome is unobserved, and no "
                         "other year's data affects membership. The latest "
                         "period any feature reads is t-1 (ve_l1, alloc_l1) "
                         "plus the pre-announced year-t allocation.",
            },
            "observations": [],
        },
        "split_windows": {
            "train": {"start": str(TRAIN_START), "end": str(EVAL_START)},
            "eval": {"start": str(EVAL_START), "end": str(HOLDOUT_START)},
            "holdout": {"start": str(HOLDOUT_START), "end": str(HOLDOUT_END + 1)},
        },
        "split_boundaries": {
            "train": f"compliance years {TRAIN_START} .. {TRAIN_END}",
            "eval": f"{EVAL_START} .. {EVAL_END}",
            "holdout": f"{HOLDOUT_START} .. {HOLDOUT_END}",
            "excluded": f"2005 (no t-1 history in the extract: "
                        f"{accounting.get('insufficient_history', 0)} "
                        f"installation-years insufficient_history, counted); "
                        f"{LIVE_YEAR}+ are live prediction years "
                        f"({diagnostics['live_year_rows']} rows measured, "
                        f"scorable when verified emissions are reported)",
        },
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": "row_id is registry@installation@year, unique by "
                           "construction; no identifier repeats inside a "
                           "split or spans two. Installations recur across "
                           "windows (a panel); that is a declared source "
                           "property, and the composite row id keeps the "
                           "identity checks meaningful.",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                    "distinct_events": stats[split]["distinct_events"]}
                            for split in LAYOUT},
        "positive_events_note": "an event is one distinct installation "
                                "carrying at least one net-short year in the "
                                "window (the declared event key; the gate "
                                "counts distinct 10-character prefixes of the "
                                "key among positives, which merges long "
                                "identifiers - both counts are recorded in "
                                "summary.json). Positives also share "
                                "year-level regime effects (the phase drift), "
                                "documented as the per-year prevalence drift "
                                "in the candidate record.",
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats, "accounting": accounting,
                    "known_events": {k: v["ok"] for k, v in known_events.items()},
                    "crosscheck": {k: v["ok"] for k, v in crosscheck.items()},
                    "reference_baselines": baselines}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
