#!/usr/bin/env python3
"""Construction script for the `wb-ieg-project-outcome` candidate.

Task: at the moment a World Bank (IBRD/IDA) lending project reaches Board
approval, will the Independent Evaluation Group's final evaluation of that
project rate its outcome Moderately Satisfactory or better (MS+) on the
six-point IEG outcome scale?

Where this runs
---------------
On a temporary worker: one anonymous GET of the IEG World Bank Project
Performance Ratings CSV (3,340,648 bytes measured 2026-10-22, 12,629 rows)
plus the World Bank projects search API paged by `os` offset (1,000 records
per page, 23 requests for the full 22,729-project index, ~1.19 MB per lean
page measured) with bounded supplementary id-lookups for any IEG project the
paged pull misses. `--ieg-file` / `--projects-file` accept local copies for a
full-assertion dry run on a coordinator-class machine.

Frame rules (from the candidate record; each measured and reported)
----------------------------------------------------------------------
* Grain: one row per project_id, deduped to the latest evaluation_fy
  (P122764 is the one duplicated id, measured at discovery). The population
  is IEG's rated-project universe restricted to approval FY <= 2019; label
  = 1 iff the six-point outcome rating is MS+.
* Prediction instant: the project's own Board approval (event_time). Every
  shipped feature is approval-time. The evaluation-vintage columns the record
  measured as anachronistic (country_fcs_status, country_fcs_lending_group,
  country_lending_group) and every IEG evaluation-time column (outcome,
  bank_performance, quality_at_entry, quality_of_supervision, me_quality,
  evaluation_fy, evaluation_type, final_closing_fy, as_of_date) never ships.
* History features (prior_msplus_share, prior_evals_count) use only other
  rows' ratings whose latest evaluation_fy <= this row's approval_fy - 1:
  an evaluation in FY(k-1) or earlier is complete before FYk starts on 1
  July, so the history is strictly knowable at the approval instant. Because
  only the current vintage is downloadable (a later PPAR re-rating hides the
  earlier rating and removes that project from earlier histories), the
  feature is a conservative lower bound on the knowable track record - a
  documented current-vintage assumption.
* Splits by approval_fy: train 1956-2009, eval 2010-2014, holdout 2015-2019
  (the record's pinned windows). Approval FY 2020+ rows are outside the
  windows and counted; 'Not Rated' rows are unobserved targets, counted;
  projects in the API index approved <= FY2019 with no IEG row are
  not-yet-evaluated, counted per window.
* Event key: country. Positives cluster by borrower (the record measured
  4,695 (country, approval_fy) cells), so the conservative independent-event
  count is distinct positive borrower clusters; the gate recomputes it as
  distinct country[:10] among positive rows and the build counts the same way.
* Provenance: evaluation_type is a seven-stream mixture (ICRR 54.7%, PPAR
  29.4%, PCR 11.7%, EVM 3.9% + 38 others, measured); the label is the latest
  IEG outcome rating regardless of stream, the mixture is declared in
  quality.json and the per-stream MS+ rates are recorded in summary.json.
* Prevalence drift across splits (train 0.707 -> eval 0.789 -> holdout 0.807,
  measured at discovery) is a property of the phenomenon (later cohorts rate
  better), documented, not "fixed".
* Cross-check: IEG RAP 2024 Figure O.3 publishes the MS+ share by fiscal year
  of project closing (71% in FY13 rising to 91% in FY23). The build recomputes
  the panel's closing-FY shares and asserts the published trend (FY13 share
  at least 10 points below FY23 share); the absolute gap under every cohort
  restriction is recorded in summary.json.
* Reference baselines measured before any model spend: global train rate
  (the majority-class rule - no persistence leg exists at project grain,
  each project is evaluated once), identity-only (country), calendar-only
  (country x approval_fy), plus per-agreement_type and per-practice rules.
  The full-model leg of the triad is the runner-contract baseline job on the
  accepted artifact, run separately.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: CC BY 4.0 International (class A, recorded in the candidate record's
license_evidence from the Data Catalog dataset page and metadata API).
Attribution "Source: World Bank Group - Independent Evaluation Group" carries
through to any release. Derived research dataset - never the World Bank's
official product.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

NAME = "wb-ieg-project-outcome"
TARGET = "msplus"
POSITIVE_LABEL = 1

IEG_URL = ("https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
           "?datasetId=DS00053&resourceId=RS00055&top=20000&type=csv")
PROJECTS_URL = "https://search.worldbank.org/api/v2/projects?format=json&rows=10000"
# NOTE (measured this session): the paged query IGNORES `fl` for field
# selection - with `fl` it serves a search-result record (id, project_name,
# url, project_abstract only). Without `fl` it serves the full structured
# approval record (approvalfy, board_approval_month, boardapprovaldate,
# amounts, lendinginstr, prodline, sector1-3 dicts, mjsector/mjtheme lists)
# WITHOUT the fat abstract. The id-lookup path (&id=P...;P...) serves full
# records either way. So: page without fl; supplement with id-lookups.
PAGE_SIZE = 1000
LOOKUP_BATCH = 20
LOOKUP_REQUEST_CAP = 30

MS_PLUS = {"Highly Satisfactory", "Satisfactory", "Moderately Satisfactory"}
MS_MINUS = {"Highly Unsatisfactory", "Unsatisfactory", "Moderately Unsatisfactory"}
NOT_RATED = "Not Rated"
OUTCOME_VOCAB = MS_PLUS | MS_MINUS | {NOT_RATED}

MONTHS = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5,
          "June": 6, "July": 7, "August": 8, "September": 9, "October": 10,
          "November": 11, "December": 12}

# Shipped layout: id, features, target.
ID_COLUMNS = ["project_id"]
FEATURES = [
    "approval_fy", "approval_month_num", "country", "wb_region",
    "agreement_type", "lending_instrument_type", "global_practice",
    "practice_group", "lending_instrument", "prodline",
    "sector1", "sector2", "sector3", "sector1_pct", "sector2_pct",
    "sector3_pct", "mjsector1", "mjsector_count", "mjtheme1", "mjtheme_count",
    "ibrd_commit_musd", "ida_commit_musd", "grant_commit_musd",
    "project_cost_musd", "amounts_missing",
    "prior_evals_count", "prior_msplus_share",
]
CARRY_COLUMNS = []
HIGH_CARDINALITY = []
COLUMNS = ID_COLUMNS + FEATURES + CARRY_COLUMNS + [TARGET]
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# Split windows in approval fiscal years (end values are exclusive, matching
# the qualification gate's rows_within_declared_windows comparison).
TRAIN_END = 2009        # train: 1956..2009
EVAL_START, EVAL_END = 2010, 2015   # eval: 2010..2014
HOLDOUT_START, HOLDOUT_END = 2015, 2020   # holdout: 2015..2019

# Discovery-measured anchors (record.json, measured 2026-10-22 on the
# data_as_of 2026-10-20 vintage). Tolerances absorb a quarterly refresh.
EXPECTED = {
    "rows_total": (12500, 12800),
    "train_rows": (9500, 10000), "train_positives": (6700, 7080),
    "eval_rows": (1450, 1530), "eval_positives": (1140, 1210),
    "holdout_rows": (1060, 1135), "holdout_positives": (860, 910),
    "msplus_share_overall": (0.72, 0.75),
    "approval_fy_min": 1956, "approval_fy_max": (2015, 2030),
    "not_rated_rows": (100, 220),
}
RAP_TREND_MIN_GAP = 10.0   # FY13 -> FY23 closing-year MS+ share gap, points
# IEG RAP 2024, Figure O.3 (MS+ % by fiscal year of project closing),
# https://documents1.worldbank.org/curated/en/099845103072525633/pdf/
# SECBOS-e45e1b2e-4fff-4e52-8d27-c33709508fe8.pdf - pinned at this session.
RAP_FIG_O3 = {2013: 71.0, 2014: 71.5, 2015: 76.5, 2016: 72.5, 2017: 84.5,
              2018: 86.5, 2019: 86.0, 2020: 86.5, 2021: 89.5, 2022: 88.5,
              2023: 91.0}

LABEL_SOURCE_COLUMNS = [
    "outcome", "bank_performance", "quality_at_entry", "quality_of_supervision",
    "me_quality", "evaluation_fy", "evaluation_type", "final_closing_fy",
    "as_of_date", "country_fcs_status", "country_fcs_lending_group",
    "country_lending_group",
]
POST_HOC_COLUMNS = LABEL_SOURCE_COLUMNS + [
    "closingdate", "status", "projectstatusdisplay", "teamleadname",
    "curr_ibrd_commitment", "curr_ida_commitment", "curr_total_commitment",
    "p2a_updated_date", "supplementprojectflg", "impagency", "borrower",
]

PREDICTION_TIME = (
    "The moment the project reaches World Bank Board approval (the "
    "boardapprovaldate of the project's own approval record). Every shipped "
    "feature is approval-time: the approval fiscal year and month, the "
    "project's agreement type, lending instrument and product line, its "
    "country and region, its sectors with percentages and major themes, its "
    "Board-committed amounts and total project cost estimate, and the "
    "borrower country's IEG rating track record from evaluations that "
    "completed strictly before the approval fiscal year began. IEG evaluates "
    "years later (approval-to-evaluation lag measured: min 1, median 8, max "
    "31 years); no evaluation-time field ships.")
PREDICTION_QUESTION = (
    "At the moment a World Bank (IBRD/IDA) lending project reaches Board "
    "approval, will the Independent Evaluation Group's final evaluation of "
    "the project rate its outcome Moderately Satisfactory or better (MS+) on "
    "the six-point IEG outcome scale?")


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
        if attempt:
            time.sleep(2 ** attempt)
        started = time.time()
        request = urllib.request.Request(url, headers={"User-Agent": "dataset-factory/wb-build"})
        try:
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
        except Exception as error:  # bounded retry, reported on final failure
            last_error = error
            log(f"fetch attempt {attempt + 1} failed for {url[:90]}: {error}")
    raise SystemExit(f"fetch failed after {attempts} attempts: {url} ({last_error})")


def fetch_json(url: str, attempts: int = 3):
    last_error = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 ** attempt)
        request = urllib.request.Request(url, headers={"User-Agent": "dataset-factory/wb-build"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read())
        except Exception as error:
            last_error = error
            log(f"json fetch attempt {attempt + 1} failed: {error}")
    raise SystemExit(f"json fetch failed after {attempts} attempts: {url} ({last_error})")


def parse_amount(text) -> float | None:
    """Comma-grouped currency string -> float USD, or None."""
    if text is None:
        return None
    cleaned = str(text).strip().replace(",", "").replace("$", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def first_name(coded_list, prefix: str) -> tuple[str, int]:
    """First (name or code) plus distinct-code count from a *_namecode list."""
    if not isinstance(coded_list, list) or not coded_list:
        return "", 0
    codes = []
    for entry in coded_list:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("code") or "").strip()
        if code and code not in codes:
            codes.append(code)
    first = coded_list[0] if isinstance(coded_list[0], dict) else {}
    name = str(first.get("name") or "").strip()
    if not name:
        code = str(first.get("code") or "").strip()
        name = f"{prefix}{code}" if code else ""
    return name, len(codes)


def sector_fields(record: dict, number: int) -> tuple[str, float]:
    entry = record.get(f"sector{number}")
    if not isinstance(entry, dict):
        return "", 0.0
    name = str(entry.get("Name") or "").strip()
    percent = entry.get("Percent")
    try:
        pct = float(percent)
    except (TypeError, ValueError):
        pct = 0.0
    return name, pct


def musd(value: float | None) -> float:
    return round(value / 1_000_000.0, 4) if value is not None else 0.0


def load_ieg(path: Path) -> tuple[list[dict], dict]:
    """Read the IEG ratings CSV, dedupe to the latest evaluation_fy per
    project_id, and report the provenance mix."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"IEG CSV has no header: {path}")
        reader.fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
        rows = [{k.strip(): (v or "").strip() for k, v in row.items()} for row in reader]

    by_id: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_id[row["project_id"]].append(row)
    deduped, duplicates = [], []
    for project_id, group in sorted(by_id.items()):
        if len(group) > 1:
            duplicates.append({
                "project_id": project_id,
                "evaluation_fys": sorted(g["evaluation_fy"] for g in group),
                "outcomes": sorted({g["outcome"] for g in group}),
            })
        group.sort(key=lambda r: (int(float(r["evaluation_fy"])), r["as_of_date"]))
        deduped.append(group[-1])

    outcome_mix = Counter(r["outcome"] for r in rows)
    unexpected = sorted(set(outcome_mix) - OUTCOME_VOCAB)
    eval_mix = Counter(r["evaluation_type"] for r in rows)
    info = {
        "rows_fetched": len(rows),
        "distinct_project_ids": len(by_id),
        "duplicate_ids_deduped_to_latest_evaluation_fy": duplicates,
        "outcome_mix": dict(outcome_mix),
        "outcome_vocabulary_unexpected": unexpected,
        "evaluation_type_mix": dict(eval_mix),
        "as_of_date_values": sorted({r["as_of_date"] for r in rows}),
        "approval_fy_missing": sum(1 for r in rows if not r["approval_fy"]),
    }
    return deduped, info


def pull_projects(work: Path, missing_ids: list[str] | None = None) -> tuple[dict[str, dict], dict]:
    """Page the projects search API by offset (full records; `fl` is ignored
    on the paged path - see the note above), then supplement with bounded
    id-lookups for any id the paged pull missed."""
    projects: dict[str, dict] = {}
    pages, requests, total_bytes = 0, 0, 0
    started = time.time()
    offset = 0
    total = None
    while True:
        url = f"{PROJECTS_URL}&os={offset}"
        data = fetch_json(url)
        requests += 1
        pages += 1
        page_projects = data.get("projects") or {}
        for pid, record in page_projects.items():
            if isinstance(record, dict):
                projects.setdefault(str(pid), record)
        total_bytes += len(json.dumps(page_projects))
        if total is None:
            total = data.get("total")
        if len(page_projects) < PAGE_SIZE or (total and len(projects) >= int(total)):
            break
        offset += PAGE_SIZE
        if offset > 40000:
            break
    paging = {"pages": pages, "paged_requests": requests,
              "records": len(projects), "total_reported": total}

    lookups = {"batches": 0, "requests": 0, "records_added": 0}
    if missing_ids:
        wanted = [pid for pid in missing_ids if pid not in projects]
        for start in range(0, len(wanted), LOOKUP_BATCH):
            if lookups["requests"] >= LOOKUP_REQUEST_CAP:
                log(f"id-lookup cap reached; {len(wanted) - start} ids unlooked")
                break
            batch = wanted[start:start + LOOKUP_BATCH]
            data = fetch_json(f"{PROJECTS_URL}&id=" + ";".join(batch))
            lookups["requests"] += 1
            lookups["batches"] += 1
            for pid, record in (data.get("projects") or {}).items():
                if isinstance(record, dict):
                    before = len(projects)
                    projects.setdefault(str(pid), record)
                    if len(projects) > before:
                        lookups["records_added"] += 1
    paging["supplementary_lookups"] = lookups
    paging["seconds"] = round(time.time() - started, 1)
    return projects, paging


def load_projects(path: Path) -> tuple[dict[str, dict], dict]:
    """Local merged {id: record} JSON (dry run) or the live pull."""
    with path.open(encoding="utf-8") as handle:
        merged = json.load(handle)
    projects = {str(pid): rec for pid, rec in merged.items() if isinstance(rec, dict)}
    return projects, {"source": "local:" + str(path), "records": len(projects)}


def approval_month(record: dict) -> int:
    return MONTHS.get(str(record.get("board_approval_month") or "").strip(), 0)


def build_rows(ieg_rows: list[dict], projects: dict[str, dict]) -> tuple[dict, dict]:
    """Emit one row per rated in-window project; count everything else."""
    rows_by_split: dict[str, list[dict]] = {"train": [], "eval": [], "holdout": []}
    accounting = Counter()
    outside_windows_by_fy: Counter = Counter()
    not_rated_by_type: Counter = Counter()
    api_missing = []
    fy_mismatches = []
    unobserved_by_window: Counter = Counter()

    # The history pool is the full rated universe (all approval years), keyed
    # by country; a rating joins a row's history iff eval_fy <= approval_fy-1.
    history: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in ieg_rows:
        outcome = row["outcome"]
        if outcome in (MS_PLUS | MS_MINUS):
            history[row["country"]].append((int(float(row["evaluation_fy"])),
                                            1 if outcome in MS_PLUS else 0))
    for country in history:
        history[country].sort()

    def split_of(approval_fy: int) -> str | None:
        if approval_fy <= TRAIN_END:
            return "train"
        if EVAL_START <= approval_fy < EVAL_END:
            return "eval"
        if HOLDOUT_START <= approval_fy < HOLDOUT_END:
            return "holdout"
        return None

    # Not-yet-evaluated: API projects approved <= FY2019 with no IEG row.
    ieg_ids = {row["project_id"] for row in ieg_rows}
    api_unmatched = 0
    for pid, record in projects.items():
        if pid in ieg_ids:
            continue
        api_unmatched += 1
        fy_text = str(record.get("approvalfy") or "").strip()
        try:
            approval_fy = int(float(fy_text))
        except ValueError:
            accounting["api_records_unknown_approval_fy"] += 1
            continue
        if approval_fy < 1956:
            continue
        split = split_of(approval_fy)
        if split is None:
            if approval_fy >= HOLDOUT_END:
                accounting["api_not_yet_evaluated_fy2020plus"] += 1
            continue
        unobserved_by_window[split] += 1
    accounting["api_records_total"] = len(projects)
    accounting["api_records_not_in_ieg"] = api_unmatched

    for row in ieg_rows:
        project_id = row["project_id"]
        outcome = row["outcome"]
        if outcome not in (MS_PLUS | MS_MINUS):
            accounting["unobserved_target_not_rated"] += 1
            not_rated_by_type[row["evaluation_type"]] += 1
            continue
        approval_fy = int(float(row["approval_fy"]))
        split = split_of(approval_fy)
        if split is None:
            accounting["outside_windows"] += 1
            outside_windows_by_fy[approval_fy] += 1
            continue

        record = projects.get(project_id)
        if record is None:
            accounting["api_join_missing"] += 1
            api_missing.append(project_id)

        # ---- approval-time features -------------------------------------
        month = approval_month(record) if record else 0
        api_fy_text = str((record or {}).get("approvalfy") or "").strip()
        try:
            api_fy = int(float(api_fy_text))
        except ValueError:
            api_fy = None
        if api_fy is not None and api_fy != approval_fy:
            fy_mismatches.append({"project_id": project_id,
                                  "ieg_approval_fy": approval_fy,
                                  "api_approvalfy": api_fy})

        sector1, sector1_pct = sector_fields(record, 1) if record else ("", 0.0)
        sector2, sector2_pct = sector_fields(record, 2) if record else ("", 0.0)
        sector3, sector3_pct = sector_fields(record, 3) if record else ("", 0.0)
        mjsector1, mjsector_count = (first_name(record.get("mjsector_namecode"), "MJCODE:")
                                     if record else ("", 0))
        mjtheme1, mjtheme_count = (first_name(record.get("mjtheme_namecode"), "MJTHEME:")
                                   if record else ("", 0))

        amounts = {name: parse_amount((record or {}).get(name))
                   for name in ("ibrdcommamt", "idacommamt", "grantamt", "lendprojectcost")}
        amounts_missing = int(all(value is None for value in amounts.values()))
        if amounts_missing:
            accounting["rows_with_no_amounts"] += 1

        # ---- history features (strictly pre-approval evaluations) --------
        evals = history.get(row["country"], [])
        keys = [eval_fy for eval_fy, _ in evals]
        cut = bisect.bisect_right(keys, approval_fy - 1)
        prior_evals = evals[:cut]
        prior_count = len(prior_evals)
        prior_share = (round(sum(label for _, label in prior_evals) / prior_count, 4)
                       if prior_count else 0.0)

        rows_by_split[split].append({
            "project_id": project_id,
            "approval_fy": approval_fy,
            "approval_month_num": month,
            "country": row["country"],
            "wb_region": row["wb_region"],
            "agreement_type": row["agreement_type"],
            "lending_instrument_type": row["lending_instrument_type"],
            "global_practice": row["global_practice"],
            "practice_group": row["practice_group"],
            "lending_instrument": str((record or {}).get("lendinginstr") or "").strip(),
            "prodline": str((record or {}).get("prodline") or "").strip(),
            "sector1": sector1,
            "sector2": sector2,
            "sector3": sector3,
            "sector1_pct": sector1_pct,
            "sector2_pct": sector2_pct,
            "sector3_pct": sector3_pct,
            "mjsector1": mjsector1,
            "mjsector_count": mjsector_count,
            "mjtheme1": mjtheme1,
            "mjtheme_count": mjtheme_count,
            "ibrd_commit_musd": musd(amounts["ibrdcommamt"]),
            "ida_commit_musd": musd(amounts["idacommamt"]),
            "grant_commit_musd": musd(amounts["grantamt"]),
            "project_cost_musd": musd(amounts["lendprojectcost"]),
            "amounts_missing": amounts_missing,
            "prior_evals_count": prior_count,
            "prior_msplus_share": prior_share,
            TARGET: 1 if outcome in MS_PLUS else 0,
        })

    diagnostics = {
        "accounting": dict(accounting),
        "unobserved_not_yet_evaluated_by_window": dict(unobserved_by_window),
        "outside_windows_by_approval_fy": dict(sorted(outside_windows_by_fy.items())),
        "not_rated_by_evaluation_type": dict(not_rated_by_type),
        "api_join_missing_ids": api_missing,
        "approval_fy_mismatches": fy_mismatches[:20],
        "approval_fy_mismatch_count": len(fy_mismatches),
    }
    return rows_by_split, diagnostics


def write_splits(out: Path, rows_by_split: dict[str, list[dict]]) -> dict:
    stats = {}
    for split, relative in LAYOUT.items():
        path = out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = sorted(rows_by_split[split], key=lambda row: row["project_id"])
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        positives = sum(row[TARGET] for row in rows)
        # The gate recomputes clustered events as distinct event_key[:10]
        # among positive rows; the build counts the same way, and also
        # records the untruncated count (the IEG country names are long
        # official forms, so [:10] merges all 'Republic of ...' borrowers).
        event_keys = {row["country"][:10] for row in rows if row[TARGET] == POSITIVE_LABEL}
        full_keys = {row["country"] for row in rows if row[TARGET] == POSITIVE_LABEL}
        stats[split] = {"rows": len(rows), "positives": positives,
                        "positive_rate": round(positives / len(rows), 6) if rows else None,
                        "distinct_positive_countries": len(event_keys),
                        "distinct_positive_countries_untruncated": len(full_keys)}
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


def fit_rate_table(rows: list[dict], *keys) -> dict[tuple, float]:
    totals: Counter = Counter()
    positives: Counter = Counter()
    for row in rows:
        key = tuple(row[name] for name in keys)
        totals[key] += 1
        positives[key] += row[TARGET]
    return {key: positives[key] / totals[key] for key in totals}


def rate_table_scores(table, rows, *keys, fallback):
    scores = []
    for row in rows:
        key = tuple(row[name] for name in keys)
        scores.append(table.get(key, fallback(row)))
    return scores


def closing_year_shares(ieg_rows: list[dict]) -> dict[str, float]:
    """MS+ share by final_closing_fy (all instruments, rated rows) for the
    RAP Figure O.3 cross-check; the published chart is the anchor."""
    by_year: dict[int, list[int]] = defaultdict(list)
    for row in ieg_rows:
        if row["outcome"] not in (MS_PLUS | MS_MINUS):
            continue
        try:
            closing_fy = int(float(row["final_closing_fy"]))
        except (TypeError, ValueError):
            continue
        by_year[closing_fy].append(1 if row["outcome"] in MS_PLUS else 0)
    shares = {}
    for year, labels in sorted(by_year.items()):
        shares[str(year)] = round(sum(labels) / len(labels), 4)
    return shares


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Build the {NAME} extract")
    parser.add_argument("--out", default="/output/extract")
    parser.add_argument("--work-dir", default="/tmp/wb")
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--ieg-file", default=None,
                        help="local IEG ratings CSV (dry run); default fetches live")
    parser.add_argument("--projects-file", default=None,
                        help="local merged {id: record} JSON (dry run); "
                             "default pulls the live projects API")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    log("== download ==")
    sources: dict[str, dict] = {}
    ieg_path = Path(args.ieg_file) if args.ieg_file else None
    projects_path = Path(args.projects_file) if args.projects_file else None
    if ieg_path is None:
        ieg_path = work / "ieg_ratings.csv"
        sources["ieg_ratings_csv"] = fetch(IEG_URL, ieg_path)
    else:
        sources["ieg_ratings_csv"] = {"url": "local:" + str(ieg_path),
                                      "bytes": ieg_path.stat().st_size,
                                      "last_modified": None, "seconds": 0.0,
                                      "sha256": sha256_file(ieg_path)}
    log(f"IEG CSV: {sources['ieg_ratings_csv']['bytes']} bytes, "
        f"{sources['ieg_ratings_csv']['seconds']} s")

    log("== parse IEG ratings ==")
    ieg_rows, ieg_info = load_ieg(ieg_path)
    log(json.dumps({k: v for k, v in ieg_info.items()
                    if k != "duplicate_ids_deduped_to_latest_evaluation_fy"}, indent=1))
    log(f"duplicate ids deduped: {ieg_info['duplicate_ids_deduped_to_latest_evaluation_fy']}")

    # Ids the join needs: every rated, in-window project (these ship; history
    # rows need no API record).
    wanted_ids = sorted({row["project_id"] for row in ieg_rows
                          if row["outcome"] in (MS_PLUS | MS_MINUS)
                          and 1956 <= int(float(row["approval_fy"])) < HOLDOUT_END})

    if projects_path is None:
        projects, paging = pull_projects(work, missing_ids=wanted_ids)
        merged_path = work / "projects_merged.json"
        merged_path.write_text(json.dumps(projects))
        sources["projects_api"] = {
            "url": PROJECTS_URL + "&os=<offset> (full records; fl ignored on "
                                  "the paged path, measured this session)",
            "requests": paging["paged_requests"] + paging["supplementary_lookups"]["requests"],
            "bytes": merged_path.stat().st_size,
            "last_modified": None,
            "seconds": paging["seconds"],
            "sha256": sha256_file(merged_path),
            "paging": {k: v for k, v in paging.items() if k != "seconds"},
        }
    else:
        projects, local_info = load_projects(projects_path)
        sources["projects_api"] = {"url": "local:" + str(projects_path),
                                   "bytes": projects_path.stat().st_size,
                                   "last_modified": None, "seconds": 0.0,
                                   "sha256": sha256_file(projects_path),
                                   "paging": {"source": "local", "records": len(projects)}}
    log(f"projects index: {len(projects)} records")

    log("== build rows ==")
    rows_by_split, diagnostics = build_rows(ieg_rows, projects)
    accounting = diagnostics["accounting"]
    for split in rows_by_split:
        log(f"{split}: {len(rows_by_split[split])} rows")
    log("eligibility accounting: " + json.dumps(
        {k: v for k, v in diagnostics.items() if k != "api_join_missing_ids"}, indent=1))
    log(f"api join missing ids: {diagnostics['api_join_missing_ids'][:10]} "
        f"(total {len(diagnostics['api_join_missing_ids'])})")

    stats = write_splits(out, rows_by_split)
    for split, entry in stats.items():
        log(f"{split}: {entry['rows']} rows, {entry['positives']} positives "
            f"(rate {entry['positive_rate']}), "
            f"{entry['distinct_positive_countries']} distinct positive countries")

    # ---- reference baselines (measured before any model spend) -----------
    train_rows = rows_by_split["train"]
    train_rate = (sum(r[TARGET] for r in train_rows) / len(train_rows)) if train_rows else 0.0
    country_table = fit_rate_table(train_rows, "country")
    calendar_table = fit_rate_table(train_rows, "country", "approval_fy")
    agreement_table = fit_rate_table(train_rows, "agreement_type")
    practice_table = fit_rate_table(train_rows, "practice_group")

    def country_fallback(row):
        return country_table.get((row["country"],), train_rate)

    def rounded_auc(labels: list[int], scores: list[float]) -> float | None:
        value = auc(labels, scores)
        return None if value is None else round(value, 4)

    baselines = {"global_rate_train": round(train_rate, 6),
                 "note": ("majority-class rule (no persistence leg exists at "
                          "project grain - each project is evaluated once); "
                          "rate tables estimated on train rows only; stdlib "
                          "rank AUC on the written rows. The full-model leg "
                          "of the triad is the runner-contract baseline job "
                          "on the accepted artifact.")}
    for split in ("eval", "holdout"):
        rows = rows_by_split[split]
        labels = [row[TARGET] for row in rows]
        identity_scores = [country_table.get((row["country"],), train_rate) for row in rows]
        calendar_scores = rate_table_scores(calendar_table, rows, "country", "approval_fy",
                                            fallback=country_fallback)
        agreement_scores = [agreement_table.get((row["agreement_type"],), train_rate)
                            for row in rows]
        practice_scores = [practice_table.get((row["practice_group"],), train_rate)
                           for row in rows]
        baselines[split] = {
            "identity_only_country_auc": rounded_auc(labels, identity_scores),
            "calendar_only_country_approval_fy_auc": rounded_auc(labels, calendar_scores),
            "agreement_type_rule_auc": rounded_auc(labels, agreement_scores),
            "practice_group_rule_auc": rounded_auc(labels, practice_scores),
            "majority_class_accuracy": round(train_rate, 4),
        }
    log("reference baselines: " + json.dumps(baselines))

    # ---- RAP Figure O.3 cross-check ---------------------------------------
    closing_shares = closing_year_shares(ieg_rows)
    share_2013 = closing_shares.get("2013")
    share_2023 = closing_shares.get("2023")
    rap_gap = (share_2023 - share_2013) * 100 if share_2013 is not None and share_2023 is not None else None
    rap_cross_check = {
        "published_series_rap2024_fig_o3": RAP_FIG_O3,
        "source": "IEG, Results and Performance of the World Bank Group 2024, "
                  "Figure O.3 (World Bank Average Rating and Percentage Rated "
                  "MS+, by fiscal year of project closing), "
                  "https://documents1.worldbank.org/curated/en/099845103072525633/pdf/"
                  "SECBOS-e45e1b2e-4fff-4e52-8d27-c33709508fe8.pdf",
        "panel_closing_fy_msplus_shares": closing_shares,
        "panel_fy2013_share": share_2013,
        "panel_fy2023_share": share_2023,
        "panel_gap_points": round(rap_gap, 1) if rap_gap is not None else None,
        "note": "RAP's standardized-methodology cohort is not exactly "
                "reproducible from the CSV columns (measured: the panel runs "
                "3-7 points below the published series under every plausible "
                "cohort restriction, same upward trend); the build asserts "
                "the published trend, not the level.",
    }
    log("RAP cross-check: " + json.dumps(
        {k: v for k, v in rap_cross_check.items()
         if k not in ("published_series_rap2024_fig_o3", "panel_closing_fy_msplus_shares")}))

    # ---- provenance assertions ---------------------------------------------
    total_rows = ieg_info["rows_fetched"]
    rated_all = [r for r in ieg_rows if r["outcome"] in (MS_PLUS | MS_MINUS)]
    msplus_share = (sum(1 for r in rated_all if r["outcome"] in MS_PLUS) / len(rated_all)) \
        if rated_all else 0.0
    stream_msplus = {}
    for stream in sorted(ieg_info["evaluation_type_mix"]):
        members = [r for r in rated_all if r["evaluation_type"] == stream]
        if members:
            stream_msplus[stream] = round(
                sum(1 for r in members if r["outcome"] in MS_PLUS) / len(members), 4)
    per_year_rates = {}
    for split in rows_by_split:
        years = defaultdict(lambda: [0, 0])
        for row in rows_by_split[split]:
            years[row["approval_fy"]][0] += 1
            years[row["approval_fy"]][1] += row[TARGET]
        per_year_rates[split] = {str(year): round(p / n, 4)
                                 for year, (n, p) in sorted(years.items())}

    failures = []
    if ieg_info["outcome_vocabulary_unexpected"]:
        failures.append(f"unexpected outcome values: "
                        f"{ieg_info['outcome_vocabulary_unexpected']}")
    if not (EXPECTED["rows_total"][0] <= total_rows <= EXPECTED["rows_total"][1]):
        failures.append(f"IEG rows {total_rows} outside expected "
                        f"{EXPECTED['rows_total']}")
    for split in ("train", "eval", "holdout"):
        low, high = EXPECTED[f"{split}_rows"]
        if not (low <= stats[split]["rows"] <= high):
            failures.append(f"{split} rows {stats[split]['rows']} outside [{low}, {high}]")
        low, high = EXPECTED[f"{split}_positives"]
        if not (low <= stats[split]["positives"] <= high):
            failures.append(f"{split} positives {stats[split]['positives']} "
                            f"outside [{low}, {high}]")
    if not (EXPECTED["msplus_share_overall"][0] <= msplus_share
            <= EXPECTED["msplus_share_overall"][1]):
        failures.append(f"MS+ share {msplus_share:.4f} outside "
                        f"{EXPECTED['msplus_share_overall']}")
    if not (EXPECTED["not_rated_rows"][0] <= accounting["unobserved_target_not_rated"]
            <= EXPECTED["not_rated_rows"][1]):
        failures.append(f"Not Rated rows {accounting['unobserved_target_not_rated']} "
                        f"outside {EXPECTED['not_rated_rows']}")
    if rap_gap is None or rap_gap < RAP_TREND_MIN_GAP:
        failures.append(f"RAP trend fixture failed: FY13->FY23 closing-share gap "
                        f"{rap_gap} points < {RAP_TREND_MIN_GAP} "
                        f"(published series rises 71 -> 91)")
    for split in ("eval", "holdout"):
        entry = stats[split]
        if entry["positives"] == 0 or entry["positives"] == entry["rows"]:
            failures.append(f"{split} is single-class: {entry}")
    if failures:
        for failure in failures:
            log(f"FAIL: {failure}")
        (out / "summary.json").write_text(json.dumps({
            "name": NAME, "built_at_utc": built_at, "failed": failures,
            "ieg": ieg_info, "splits": stats,
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
        "grain": "one row per project_id (deduped to the latest evaluation_fy), "
                 "rated IEG outcomes, approval FY 1956-2019",
        "ieg": ieg_info,
        "splits": stats,
        "eligibility": diagnostics,
        "msplus_share_overall_rated": round(msplus_share, 6),
        "stream_msplus_shares": stream_msplus,
        "per_year_msplus_rates": per_year_rates,
        "prevalence_shift_note": "positive rate rises train -> eval -> holdout "
                                 "(discovery: 0.707 -> 0.789 -> 0.807); a "
                                 "property of the phenomenon, not a "
                                 "construction fault",
        "reference_baselines": baselines,
        "rap_cross_check": rap_cross_check,
        "vintage": {
            "as_of_date": ieg_info["as_of_date_values"],
            "revision_note": "only the current IEG CSV vintage is "
                             "downloadable (quarterly republication; "
                             "data_as_of 2026-10-20 measured at discovery); "
                             "prior_msplus_share is a conservative lower "
                             "bound because a later re-evaluation removes a "
                             "project from earlier histories rather than "
                             "leaking a future rating",
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": IEG_URL,
        "license": "World Bank IEG data is CC BY 4.0 International (source "
                   "terms preserved; attribution 'Source: World Bank Group - "
                   "Independent Evaluation Group' required). Derived research "
                   "dataset - not a World Bank official product. Our derived "
                   "compilation: CC0-1.0.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by approval fiscal year (Board "
                              "approval instant)",
                  "boundaries": {"train": "approval FY 1956 .. 2009",
                                 "eval": "approval FY 2010 .. 2014",
                                 "holdout": "approval FY 2015 .. 2019",
                                 "excluded": "approval FY 2020+ (counted) and "
                                             "Not Rated rows (counted)"}},
        "label_rule": "msplus = 1 iff the IEG outcome rating is Highly "
                      "Satisfactory, Satisfactory or Moderately Satisfactory; "
                      "MS- outcomes are 0; 'Not Rated' rows are unobserved "
                      "targets and excluded with counts. Every IEG "
                      "evaluation-time column is excluded from the shipped "
                      "files.",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
        "source_sha256": sources["ieg_ratings_csv"]["sha256"],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    feature_doc = (
        "approval_fy is the World Bank fiscal year (1 July - 30 June) of "
        "Board approval, from the IEG CSV (cross-checked against the projects "
        "API approvalfy; mismatches counted in summary.json). approval_month_num "
        "is the calendar month of boardapprovaldate from the projects API "
        "(0 = not recoverable). country, wb_region, agreement_type, "
        "lending_instrument_type, global_practice and practice_group come from "
        "the IEG CSV row: country and the coarse two-level instrument type "
        "(IPF/DPF) are approval-time facts; wb_region, global_practice and "
        "practice_group are the publisher's current taxonomy applied to the "
        "project (a coarsening of approval-time geography/sector content, "
        "re-bucketed through the current lens - the record measured the "
        "vintage-anachronistic columns country_fcs_status, "
        "country_fcs_lending_group and country_lending_group and they never "
        "ship). lending_instrument, prodline, sector1-3 with percentages, "
        "mjsector1/mjtheme1 with counts, and the four commitment/cost "
        "amounts come from the projects API approval record (boardapprovaldate-"
        "era fields; amounts are US dollars converted to millions, 0.0 when "
        "the record carries none, with amounts_missing marking rows where "
        "all four are absent). prior_evals_count and prior_msplus_share are "
        "the borrower country's IEG rating history: ratings of other projects "
        "whose latest evaluation_fy <= this row's approval_fy - 1 (an "
        "evaluation in FY(k-1) or earlier completes before FYk starts on 1 "
        "July, so the history is strictly knowable at the approval instant; "
        "current-vintage, so a conservative lower bound - see summary.json).")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": "approval_fy",
        "event_key_column": "country",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": feature_doc,
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "approval_fy",
             "unit": "World Bank fiscal year (1 July - 30 June)",
             "frame": "the approval instant's own fiscal year; IEG CSV "
                      "approval_fy, corroborated by the projects API approvalfy "
                      "(P008791: board approval 2004-09-16 = FY2005)"},
            {"column": "approval_month_num",
             "unit": "calendar month number (1-12; 0 = not recoverable)",
             "frame": "month of the projects API board_approval_month, the "
                      "Board approval date's month"},
            {"column": "country",
             "unit": "borrower country name (IEG CSV)",
             "frame": "the project's country at approval; also the event key "
                      "(positives cluster by borrower)"},
            {"column": "wb_region",
             "unit": "World Bank region name",
             "frame": "the publisher's current region taxonomy applied to the "
                      "approval-time country - a coarsening of country, "
                      "re-bucketed through the current lens"},
            {"column": "agreement_type",
             "unit": "IEG CSV agreement type (IDA, IBRD, RETF, GEF, ...)",
             "frame": "the financing agreement type at approval"},
            {"column": "lending_instrument_type",
             "unit": "IEG CSV instrument type (IPF / DPF)",
             "frame": "investment vs development policy financing at approval"},
            {"column": "global_practice",
             "unit": "World Bank Global Practice name (empty = not recorded)",
             "frame": "current-practice re-bucketing of the project's "
                      "approval-time sector content; 36.1% empty "
                      "(pre-reorganisation rows), measured at discovery"},
            {"column": "practice_group",
             "unit": "World Bank practice group name (empty = not recorded)",
             "frame": "current-practice-group re-bucketing of the project's "
                      "approval-time sector content"},
            {"column": "lending_instrument",
             "unit": "projects API lending instrument full name",
             "frame": "the instrument named on the approval record "
                      "(e.g. 'Specific Investment Loan'); empty when the API "
                      "record carries none"},
            {"column": "prodline",
             "unit": "projects API product line code (PE = IBRD/IDA, ...)",
             "frame": "the product line of the approval record"},
            {"column": "sector1",
             "unit": "projects API sector board name",
             "frame": "the primary sector assigned to the project at "
                      "approval; empty when absent"},
            {"column": "sector2",
             "unit": "projects API sector board name",
             "frame": "the second sector at approval; empty when absent"},
            {"column": "sector3",
             "unit": "projects API sector board name",
             "frame": "the third sector at approval; empty when absent"},
            {"column": "sector1_pct",
             "unit": "percent of the project in sector1 (0-100; 0 when the "
                     "sector is absent)",
             "frame": "the percentage split recorded at approval"},
            {"column": "sector2_pct",
             "unit": "percent of the project in sector2",
             "frame": "the percentage split recorded at approval"},
            {"column": "sector3_pct",
             "unit": "percent of the project in sector3",
             "frame": "the percentage split recorded at approval"},
            {"column": "mjsector1",
             "unit": "major (top-level) sector name or MJCODE:<code>",
             "frame": "first major sector of the approval record"},
            {"column": "mjsector_count",
             "unit": "count of distinct major sectors (1-5)",
             "frame": "breadth of the approval-time sector assignment"},
            {"column": "mjtheme1",
             "unit": "major theme name or MJTHEME:<code>",
             "frame": "first major theme of the approval record"},
            {"column": "mjtheme_count",
             "unit": "count of distinct major themes",
             "frame": "breadth of the approval-time theme assignment"},
            {"column": "ibrd_commit_musd",
             "unit": "millions of US dollars",
             "frame": "IBRD commitment amount on the approval record "
                      "(ibrdcommamt), 0.0 when absent"},
            {"column": "ida_commit_musd",
             "unit": "millions of US dollars",
             "frame": "IDA commitment amount on the approval record "
                      "(idacommamt), 0.0 when absent"},
            {"column": "grant_commit_musd",
             "unit": "millions of US dollars",
             "frame": "grant amount on the approval record (grantamt; used by "
                      "trust-fund agreement types), 0.0 when absent"},
            {"column": "project_cost_musd",
             "unit": "millions of US dollars",
             "frame": "total estimated project cost at approval "
                      "(lendprojectcost), 0.0 when absent"},
            {"column": "amounts_missing",
             "unit": "binary indicator",
             "frame": "1 iff the API record carries none of the four amounts; "
                      "a data-recoverability marker (amounts are knowable at "
                      "approval but not recoverable from the current record)"},
            {"column": "prior_evals_count",
             "unit": "count of completed IEG evaluations",
             "frame": "evaluations of other projects in the same country whose "
                      "latest evaluation_fy <= this row's approval_fy - 1 - "
                      "strictly complete before the approval fiscal year "
                      "began"},
            {"column": "prior_msplus_share",
             "unit": "share (0-1; 0.0 when prior_evals_count is 0)",
             "frame": "MS+ share among those strictly-prior evaluations; "
                      "current-vintage so a conservative lower bound on the "
                      "knowable track record (a later re-evaluation removes a "
                      "project from earlier histories instead of leaking a "
                      "future rating)"},
            {"column": TARGET,
             "unit": "binary indicator",
             "frame": "1 iff the IEG outcome rating is MS+ (Highly "
                      "Satisfactory / Satisfactory / Moderately Satisfactory); "
                      "the rating and every other evaluation-time field are "
                      "excluded from the shipped columns"},
        ],
        "provenance": {
            "evaluation_type_mix": ieg_info["evaluation_type_mix"],
            "stream_msplus_shares": stream_msplus,
            "note": "the label is the latest IEG outcome rating regardless of "
                    "evaluation stream; PPAR full evaluations oversample "
                    "problem projects (measured at discovery), so the stream "
                    "mixture is part of the task definition",
        },
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "Board approval (the project's own event)",
                "days_after_period_end": 0,
                "citation": "World Bank projects API boardapprovaldate / "
                            "board_approval_month on the approval record "
                            "(e.g. P147864 approved 2019-03-29, "
                            "board_approval_month March); the IEG CSV "
                            "approval_fy is the approval fiscal year",
            },
            "features": {
                "period": "Board approval",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "approval (the row's own "
                                      "boardapprovaldate / approval_fy)",
                "fields": FEATURES,
                "basis": "rows are IEG-rated projects with approval FY <= 2019; "
                         "eligibility reads only approval-time fields plus the "
                         "country's strictly-prior evaluation history. A "
                         "missing outcome ('Not Rated', or a project with no "
                         "IEG row yet) is missing outcome data - counted in "
                         "unobserved_target buckets in summary.json, never a "
                         "membership decision on future data",
            },
            "observations": [],
        },
        "split_windows": {
            "train": {"start": "1956", "end": str(EVAL_START)},
            "eval": {"start": str(EVAL_START), "end": str(EVAL_END)},
            "holdout": {"start": str(HOLDOUT_START), "end": str(HOLDOUT_END)},
        },
        "split_boundaries": {
            "train": "approval FY 1956 .. 2009",
            "eval": "approval FY 2010 .. 2014",
            "holdout": "approval FY 2015 .. 2019",
            "excluded": "approval FY 2020+ (counted per year) and Not Rated "
                        "rows (counted); projects approved <= FY2019 without "
                        "an IEG row yet are counted per window as unobserved",
        },
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "id_columns_note": "project_id is unique by construction (deduped to "
                           "the latest evaluation_fy); no identifier repeats "
                           "inside a split or spans two",
        "positive_events": {split: {"positives": stats[split]["positives"],
                                    "distinct_events": stats[split]["distinct_positive_countries"]}
                            for split in LAYOUT},
        "positive_events_note": "an event is one distinct borrower country "
                                "(event_key_column, first 10 characters as "
                                "the gate recomputes) carrying at least one "
                                "positive: outcomes of a country's projects "
                                "correlate through shared country conditions, "
                                "so the country is the conservative cluster. "
                                "IEG country names are long official forms, so "
                                "the 10-character truncation merges the many "
                                "'Republic of ...' borrowers into shared "
                                "prefixes (measured: eval has 57 distinct "
                                "positive prefixes but 135 distinct positive "
                                "countries) - the clustered count is the "
                                "conservative direction and both counts are "
                                "recorded in summary.json; the record also "
                                "measured (country, approval_fy) cells, a "
                                "finer clustering",
        "splits": LAYOUT,
        "external_threshold": False,
        "cross_check": rap_cross_check,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    log("== done ==")
    log(json.dumps({"splits": stats,
                    "msplus_share_overall_rated": round(msplus_share, 6),
                    "reference_baselines": baselines}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
