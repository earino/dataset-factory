#!/usr/bin/env python3
"""Construction of the ocha-fts-appeal-funding-trajectory artifact (fts-appeal-003).

Task: for a primary (single-country) humanitarian appeal plan-year, predict at the
appeal's launch whether the plan-year will reach >= 50% of its ORIGINAL requirements
(launch-vintage origRequirements) in final appeal-linked funding.

fts-appeal-003 is the P0-recovery rebuild the operator chose from the 2026-11-01
queue audit (audits/2026-11-01-queue-audit-codex.md section 5): the 2026.10-era
shipped history features (country_prior_appeals, country_prior_covered_rate,
country_last_prior_covered) let a label-blind attacker recover 120/139 eval and
128/182 holdout labels exactly (count x rounded-rate arithmetic plus the declared
last-prior tie rule, reading only later rows' history features). This version ships
NO outcome-bearing history column: every shipped feature is a function of the
row's own launch record plus the PRESENCE (never the outcome) of the country's
strictly-earlier plan-year appeals - years_since_country_prior is derivable from
the shipped row set itself and carries no label information. The population, the
label arithmetic, the fixtures and the splits are unchanged from the accepted
e7441e1f artifact; only the feature set changed. score.py recomputes the
persistence/prior-mean references scorer-side from prior-in-time labels because
their feature form is exactly the exposure that was removed.

This file ONLY constructs files and gate diagnostics. It computes no performance
metric (no AUC, no accuracy, no model): row and positive counts, fixture assertions
and exclusion buckets are construction diagnostics. The first performance number in
the job is computed by score.py, which run.sh allows to run only after the
qualification gate passed over the full artifact and --accept re-verified the exact
bytes. The holdout is never opened by score.py.

Worker order (run.sh): construct -> qualify -> accept exact bytes -> references.

Harvest (all anonymous, stdlib):
  1. HDX bulk CSV fts_requirements_funding_global.csv (CC BY-IGO) - the panel
     enumerator: one group per (id, year); groups with exactly one country row are
     the primary population; multi-row groups are regional plans (measured slice
     gap, Burundi RRP 2021 fixture).
  2. api.hpc.tools v2/public/plan/{id} per plan - launch-vintage origRequirements
     (NOT the CSV requirements column, which carries the REVISED value in revised
     cases - AFG 2023 fixture proves the difference), planVersion metadata.
  3. api.hpc.tools v1/public/fts/flow?planId={id}&year={year} first page per scored
     plan-year - incoming.fundingTotal = the label numerator (appeal-linked funding).

Every fetched file is pinned by sha256 in summary.json; compact per-record harvest
provenance (plans.jsonl, flows.jsonl) is written next to the summary, and the source
CSV copy is uploaded under /output/source/ for collection. Raw JSON responses are
not retained (the compact records and digests are the evidence).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

NAME = "ocha-fts-appeal-funding-trajectory"
TARGET = "reached_half"
POSITIVE = 1
ID_COLUMNS = ["plan_year_id"]
TIME_COLUMN = "plan_year"
EVENT_KEY_COLUMN = "plan_year_id"
POSITIVE_LABEL_TEXT = "covered (>= 50% of original requirements)"

CSV_URL = ("https://data.humdata.org/dataset/b2bbb33c-2cfb-4809-8dd3-6bbdc080cbb9/"
           "resource/b3232da8-f1e4-41ab-9642-b22dae10a1d7/download/"
           "fts_requirements_funding_global.csv")
PLAN_URL = "https://api.hpc.tools/v2/public/plan/{}"
FLOW_URL = "https://api.hpc.tools/v1/public/fts/flow?planId={}&year={}"
UA = "scout-factory-build/1.0 (dataset-factory worker job; contact via repo)"

# Scored window and splits (the candidate record's measured default).
YEAR_FIRST, YEAR_LAST = 2000, 2025
SPLIT_WINDOWS = {
    "train": {"start": "2000", "end": "2017"},
    "eval": {"start": "2017", "end": "2021"},
    "holdout": {"start": "2021", "end": "2026"},
}
SPLIT_OF_YEAR = {}
for _y in range(YEAR_FIRST, 2017):
    SPLIT_OF_YEAR[_y] = "train"
for _y in range(2017, 2021):
    SPLIT_OF_YEAR[_y] = "eval"
for _y in range(2021, YEAR_LAST + 1):
    SPLIT_OF_YEAR[_y] = "holdout"

# Dated fixtures, measured 2026-10-29 (candidate notes, probes 4-6). Hard asserts;
# a mismatch prints the observed value and stops the build for diagnosis.
AFG = {"country": "AFG", "year": 2023, "orig": 4627363573, "funding": 1678347238,
       "csv_requirements_revised": 3227372908, "label": 0}
YEM = {"country": "YEM", "year": 2023, "funding": 1774327599}
BDI = {"name_contains": "Burundi", "year": 2021, "slice_sum": 14978233,
       "plan_total": 19282778}

COLUMNS = ["plan_year_id", "plan_year_anchor", "country_iso3", "plan_year",
           "plan_type", "is_part_of_gho", "orig_requirements_usd",
           "years_since_country_prior", TARGET]
FEATURES = [c for c in COLUMNS if c not in (TARGET, *ID_COLUMNS)]


class BuildError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_bytes(url: str, tries: int = 4) -> bytes:
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - diagnostics must carry the cause
            last = exc
            time.sleep(2 * (attempt + 1))
    raise BuildError(f"fetch failed after {tries} tries: {url} ({last})")


def fetch_json(url: str, tries: int = 4):
    raw = fetch_bytes(url, tries)
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise BuildError(f"non-JSON response from {url}: {exc}") from exc


def money(value) -> int:
    """FTS dollar amounts are integral; keep exact integer arithmetic for labels."""
    rounded = int(round(float(value)))
    if abs(float(value) - rounded) > 0.001:
        raise BuildError(f"non-integral dollar amount: {value!r}")
    return rounded


def plan_year_id(year: int, plan_id: str) -> str:
    pid = str(plan_id).strip()
    if not pid or len(pid) > 5 or not pid.isdigit():
        raise BuildError(f"plan id {plan_id!r} outside the expected numeric width; "
                         "the id scheme (year-pid, <= 10 chars) must stay unique")
    return f"{year}-{pid}"


def load_resume(path: Path, key_fields):
    done = {}
    if path.is_file():
        with path.open() as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                done[tuple(record[f] for f in key_fields)] = record
    return done


def harvest(work: Path):
    """Fetch the enumerator CSV, plan records and flow totals, with resume caches."""
    stats = {"requests": 0, "errors": 0, "csv_bytes": None, "csv_sha256": None}

    csv_path = work / "reqfund_global.csv"
    if not csv_path.is_file():
        csv_path.write_bytes(fetch_bytes(CSV_URL))
        stats["requests"] += 1
    stats["csv_bytes"] = csv_path.stat().st_size
    stats["csv_sha256"] = sha256_of(csv_path)
    if stats["csv_bytes"] < 200_000:
        raise BuildError(f"enumerator CSV is only {stats['csv_bytes']} bytes; "
                         "expected ~279,849 (2026-10-29 measurement)")

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.DictReader(handle))
    eligible = [r for r in raw_rows if (r.get("id") or "").strip()
                and (r.get("requirements") or "").strip()]
    groups = defaultdict(list)
    for row in eligible:
        groups[(row["id"].strip(), int(row["year"]))].append(row)
    stats["csv_rows"] = len(raw_rows)
    stats["eligible_rows"] = len(eligible)
    stats["plan_year_groups"] = len(groups)

    plans_cache = work / "plans.jsonl"
    plans_done = load_resume(plans_cache, ["plan"])
    plans = {}
    for pid in sorted({pid for pid, _ in groups}):
        if pid in plans_done and "error" not in plans_done[pid]:
            plans[pid] = plans_done[pid]
            continue
        try:
            document = fetch_json(PLAN_URL.format(pid))
            data = document.get("data", document) or {}
            version = data.get("planVersion") or {}
            record = {
                "plan": pid,
                "orig": data.get("origRequirements"),
                "revised": data.get("revisedRequirements"),
                "revision_state": data.get("revisionState"),
                "name": (version.get("name") or "")[:80],
                "version_start": version.get("startDate"),
                "version_end": version.get("endDate"),
                "gho": version.get("isPartOfGHO"),
                "top_level_keys": sorted(k for k in data.keys())[:24],
            }
        except BuildError as exc:
            stats["errors"] += 1
            record = {"plan": pid, "error": str(exc)}
        stats["requests"] += 1
        with plans_cache.open("a") as handle:
            handle.write(json.dumps(record) + "\n")
        if "error" not in record:
            plans[pid] = record
        time.sleep(0.1)

    flows_cache = work / "flows.jsonl"
    return stats, raw_rows, eligible, groups, plans, flows_cache


def flow_total(plan_id: str, year: int, flows_cache: Path, stats: dict,
               resume: dict) -> int:
    key = (str(plan_id), year)
    if key in resume:
        return int(resume[key]["funding"])
    try:
        document = fetch_json(FLOW_URL.format(plan_id, year))
        data = (document.get("data") or {})
        incoming = data.get("incoming") or {}
        total = incoming.get("fundingTotal")
        funding = money(total) if total is not None else 0
        record = {"plan": str(plan_id), "year": year, "funding": funding,
                  "had_incoming": total is not None}
    except BuildError as exc:
        stats["errors"] += 1
        record = {"plan": str(plan_id), "year": year, "error": str(exc)}
    stats["requests"] += 1
    with flows_cache.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    time.sleep(0.1)
    if "error" in record:
        raise BuildError(f"flow fetch failed for {key}: {record['error']}")
    return int(record["funding"])


def build_panel(eligible, groups, plans, flows_cache: Path, stats: dict):
    """Assemble the primary plan-year panel with launch attributes + prior history."""
    buckets = defaultdict(list)

    def bucket(name, key, reason):
        buckets[name].append({"group": f"{key[0]}-{key[1]}", "reason": reason})

    primary = []
    for key in sorted(groups, key=lambda k: (k[1], k[0])):
        pid, year = key
        rows = groups[key]
        plan = plans.get(pid)
        if len(rows) > 1:
            bucket("regional_multi_country", key,
                   f"{len(rows)} country slice rows (regional plan)")
            continue
        if plan is None:
            bucket("plan_fetch_error", key, "plan endpoint fetch failed")
            continue
        orig = plan.get("orig")
        if orig is None or money(orig) <= 0:
            bucket("no_orig_requirements", key, "launch ask missing or zero")
            continue
        if year < YEAR_FIRST:
            bucket("pre_window", key, f"plan year {year} before {YEAR_FIRST}")
            continue
        if year > YEAR_LAST:
            bucket("live_edge_unobserved", key,
                   f"plan year {year} still running at the snapshot; outcome "
                   "unobserved - counted, never scored")
            continue
        primary.append({
            "plan_id": pid, "year": year, "row": rows[0], "plan": plan,
            "orig": money(orig), "revised": plan.get("revised"),
        })

    # Flow funding (label numerator) for every scored plan-year.
    flows_resume = load_resume(flows_cache, ["plan", "year"])
    zero_funding_rows = 0
    csv_flow_mismatches = []
    for entry in primary:
        funding = flow_total(entry["plan_id"], entry["year"], flows_cache, stats,
                             flows_resume)
        entry["funding"] = funding
        if funding == 0:
            zero_funding_rows += 1
        csv_funding = entry["row"].get("funding") or "0"
        try:
            csv_value = money(csv_funding)
        except (ValueError, TypeError):
            csv_value = None
        if csv_value is not None and abs(csv_value - funding) > 1:
            csv_flow_mismatches.append({
                "plan_year_id": plan_year_id(entry["year"], entry["plan_id"]),
                "flow": funding, "csv": csv_value})
        # label: exact integer arithmetic, covered iff 2*funding >= orig
        entry["label"] = 1 if 2 * funding >= entry["orig"] else 0

    mismatch_rate = (len(csv_flow_mismatches) / len(primary)) if primary else 1.0
    if mismatch_rate > 0.10:
        raise BuildError(
            f"flow-vs-CSV funding mismatch rate {mismatch_rate:.1%} "
            f"({len(csv_flow_mismatches)} of {len(primary)}); the label pipeline is "
            "probably reading the wrong field - refusing to write the artifact")

    # Prior-history features: strictly-earlier plan years of the same country.
    by_country = defaultdict(list)
    for entry in primary:
        by_country[entry["row"]["countryCode"].strip()].append(entry)
    for entries in by_country.values():
        entries.sort(key=lambda e: (e["year"], e["plan_id"]))

    for entries in by_country.values():
        for index, entry in enumerate(entries):
            prior = [e for e in entries[:index] if e["year"] < entry["year"]]
            if prior:
                last_year = max(e["year"] for e in prior)
                entry["years_since_prior"] = entry["year"] - last_year
            else:
                entry["years_since_prior"] = -1

    # Brute-force recompute: the recency feature must equal a from-scratch
    # recompute over strictly-earlier plan years only, and must never read any
    # row's label (the P0-recovery guard: no shipped feature may be a function
    # of another row's outcome - the 2026.10 history features that were, are gone).
    for entries in by_country.values():
        for entry in entries:
            earlier = [e for e in entries if e["year"] < entry["year"]]
            if earlier:
                last_year = max(e["year"] for e in earlier)
                if entry["years_since_prior"] != entry["year"] - last_year:
                    raise BuildError(f"years_since_prior recompute mismatch for {entry}")
            elif entry["years_since_prior"] != -1:
                raise BuildError(f"sentinel mismatch for a no-prior row: {entry}")

    stats["zero_funding_rows"] = zero_funding_rows
    stats["csv_flow_mismatches"] = csv_flow_mismatches
    stats["buckets"] = {name: len(items) for name, items in buckets.items()}
    stats["bucket_groups"] = {name: items[:40] for name, items in buckets.items()}
    return primary, dict(buckets)


def check_fixtures(primary, groups, plans, flows_cache: Path, stats: dict):
    """Dated cross-check fixtures; every one is a hard assert with observed values."""
    # AFG 2023: launch-vintage denominator + label + the forbidden CSV column.
    afg = [e for e in primary if e["row"]["countryCode"].strip() == AFG["country"]
           and e["year"] == AFG["year"]]
    if len(afg) != 1:
        raise BuildError(f"AFG {AFG['year']} primary rows: {len(afg)} (expected 1)")
    afg = afg[0]
    if afg["orig"] != AFG["orig"]:
        raise BuildError(f"AFG orig {afg['orig']} != fixture {AFG['orig']}")
    if afg["funding"] != AFG["funding"]:
        raise BuildError(f"AFG flow funding {afg['funding']} != fixture "
                         f"{AFG['funding']}")
    if afg["label"] != AFG["label"]:
        raise BuildError(f"AFG label {afg['label']} != fixture {AFG['label']}")
    csv_req = money(afg["row"]["requirements"])
    if csv_req != AFG["csv_requirements_revised"]:
        raise BuildError(f"AFG CSV requirements {csv_req} != the recorded revised "
                         f"value {AFG['csv_requirements_revised']} - the vintage "
                         "separation has drifted; diagnose before writing anything")
    if money(afg["row"]["funding"]) != AFG["funding"]:
        raise BuildError("AFG CSV funding disagrees with the flow total")
    if afg["orig"] == csv_req:
        raise BuildError("AFG orig equals the CSV requirements column - the launch-"
                         "vintage separation is not exercising")

    # YEM 2023: flow funding to the dollar (the 2026-10-29 cross-source check).
    yem = [e for e in primary if e["row"]["countryCode"].strip() == YEM["country"]
           and e["year"] == YEM["year"]]
    if len(yem) != 1:
        raise BuildError(f"YEM {YEM['year']} primary rows: {len(yem)} (expected 1)")
    if yem[0]["funding"] != YEM["funding"]:
        raise BuildError(f"YEM flow funding {yem[0]['funding']} != fixture "
                         f"{YEM['funding']}")

    # Burundi RRP 2021 regional slice gap: the fixture that justifies excluding
    # multi-country groups from the primary population.
    bdi_groups = [(key, rows) for key, rows in groups.items()
                  if key[1] == BDI["year"] and len(rows) > 1
                  and any(BDI["name_contains"] in (r.get("name") or "")
                          for r in rows)]
    if len(bdi_groups) != 1:
        raise BuildError(f"Burundi {BDI['year']} regional groups: "
                         f"{len(bdi_groups)} (expected 1)")
    key, rows = bdi_groups[0]
    slice_sum = sum(money(r["funding"]) for r in rows if (r.get("funding") or "").strip())
    if slice_sum != BDI["slice_sum"]:
        raise BuildError(f"Burundi slice sum {slice_sum} != fixture "
                         f"{BDI['slice_sum']} (group {key})")
    plan_total = flow_total(key[0], key[1], flows_cache, stats,
                            load_resume(flows_cache, ["plan", "year"]))
    if plan_total != BDI["plan_total"]:
        raise BuildError(f"Burundi plan flow total {plan_total} != fixture "
                         f"{BDI['plan_total']}")
    stats["fixtures"] = {
        "afg_2023": {"orig": afg["orig"], "funding": afg["funding"],
                     "label": afg["label"],
                     "csv_requirements_revised": csv_req,
                     "ratio_coverage_of_orig": round(afg["funding"] / afg["orig"], 6)},
        "yem_2023": {"funding": yem[0]["funding"]},
        "burundi_rrp_2021": {"slice_sum": slice_sum, "plan_total": plan_total,
                             "slice_ratio": round(slice_sum / plan_total, 6)},
    }


def split_rows(primary):
    splits = {"train": [], "eval": [], "holdout": []}
    for entry in primary:
        splits[SPLIT_OF_YEAR[entry["year"]]].append(entry)
    for name, rows in splits.items():
        rows.sort(key=lambda e: (e["year"], e["row"]["countryCode"].strip(),
                                 e["plan_id"]))
    return splits


def write_artifact(out: Path, splits, built_at: str):
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)

    rows_by_split, stats_by_split = {}, {}
    for name, entries in splits.items():
        rows = []
        for entry in entries:
            rows.append({
                "plan_year_id": plan_year_id(entry["year"], entry["plan_id"]),
                "plan_year_anchor": f"{entry['year']}-01-01",
                "country_iso3": entry["row"]["countryCode"].strip(),
                "plan_year": str(entry["year"]),
                "plan_type": (entry["row"].get("typeName") or "").strip(),
                "is_part_of_gho": 1 if entry["plan"].get("gho") else 0,
                "orig_requirements_usd": str(entry["orig"]),
                "years_since_country_prior": str(entry["years_since_prior"]),
                TARGET: str(entry["label"]),
            })
        rows_by_split[name] = rows
        positives = sum(1 for row in rows if row[TARGET] == str(POSITIVE))
        countries = {row["country_iso3"] for row in rows}
        stats_by_split[name] = {
            "rows": len(rows), "positives": positives,
            "negatives": len(rows) - positives,
            "positive_rate": round(positives / len(rows), 6) if rows else None,
            "distinct_countries": len(countries),
            "year_min": min((int(r["plan_year"]) for r in rows), default=None),
            "year_max": max((int(r["plan_year"]) for r in rows), default=None),
        }

    if any(not rows_by_split[name] for name in rows_by_split):
        raise BuildError("a scored split is empty; the panel cannot carry a score")

    destinations = {"train": "public/train.csv", "eval": "public/eval.csv",
                    "holdout": "private/holdout.csv"}
    for name, relative in destinations.items():
        path = out / relative
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for row in rows_by_split[name]:
                writer.writerow(row)

    meta = {
        "name": NAME,
        "description": (
            "For a UN-coordinated humanitarian appeal or response plan "
            "(HRP/CAP/flash appeal and similar single-country plans) at its "
            "public launch instant (requirements first published - GHO early "
            "December for the following year, or the plan's own release, "
            "whichever the record dates), will the plan receive funding equal "
            "to at least 50% of its ORIGINAL (launch-vintage) requirements by "
            "the close of its plan year? Features are launch-time attributes "
            "(original requirements, plan type, GHO membership, country, plan "
            "year) plus the appeal-recency gap to the country's most recent "
            "strictly-earlier appeal (years_since_country_prior; -1 when the "
            "country has no prior appeal). No prior-outcome history ships: the "
            "2026.10-era prior-outcome features allowed exact cross-row label "
            "recovery and were removed after the 2026-11-01 queue audit. A useful "
            "prediction identifies, months ahead, which appeals will end the "
            "year underfunded - the quantity GHO gap analysis reports after "
            "the fact - enabling donor advocacy and fundraising prioritization."),
        "target": TARGET,
        "positive_label": POSITIVE,
        "positive_label_text": POSITIVE_LABEL_TEXT,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {name: stats_by_split[name]["rows"] for name in stats_by_split},
        "positive_rate": {name: stats_by_split[name]["positive_rate"]
                          for name in stats_by_split},
        "split": ("temporal on the plan year: train 2000-2016, eval 2017-2020, "
                  "holdout 2021-2025"),
        "split_description": (
            "temporal on the plan year: train 2000-2016, eval 2017-2020, "
            "holdout 2021-2025 (the 2026+ live edge is excluded until those years "
            "close; exclusions are counted, never scored)"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n",
                                   encoding="utf-8")
    return stats_by_split


def build_quality(stats_by_split, harvest_stats, built_at: str) -> dict:
    launch_group = {
        "source": ("the appeal's own launch record: the FTS plan endpoint "
                   "(api.hpc.tools v2/public/plan) origRequirements and planVersion "
                   "metadata plus the HDX requirements-and-funding CSV row that "
                   "enumerates the (plan, year) group"),
        "availability": (
            "recorded at the appeal's launch: the requirements ask, plan type, GHO "
            "membership and plan year are published with the appeal itself (an "
            "administrative record written at the launch event)"),
        "status": "assumed",
        "assumption": (
            "current-snapshot vintage: values are as published at construction time "
            "(built_at pinned, every fetched file sha256-pinned in summary.json); "
            "the publisher exposes no version history (checked 2026-10-29), so no "
            "historical vintage proves the API state at past instants"),
    }
    history_group = {
        "source": ("the PRESENCE of strictly-earlier plan-years of the same "
                   "country in the same primary panel (which appeals existed, "
                   "never their funding outcomes)"),
        "availability": (
            "an earlier appeal's existence and plan year are launch-time facts; "
            "the only history-derived feature reads the year of the country's "
            "most recent strictly-earlier appeal, never any row's label "
            "(asserted by brute-force recompute in construction)"),
        "status": "assumed",
        "assumption": (
            "current-snapshot row set: the appeal inventory is as published at "
            "construction time (built_at pinned, every fetched file sha256-pinned "
            "in summary.json). This evidence group carried the 2026.10-era "
            "prior-outcome features that the 2026-11-01 queue audit recovered "
            "labels through (120/139 eval, 128/182 holdout, 0 errors); those "
            "columns no longer exist, and what remains is presence-only"),
    }
    fe = {
        "plan_year_id": {
            "source": "row key <plan year>-<FTS plan id>; the identity of one "
                      "primary plan-year appeal",
            "availability": "identity of the row, known at launch",
            "status": "verified"},
        "plan_year_anchor": {
            "source": "derived calendar key: January 1 of the plan year, derived "
                      "from plan_year; NOT the publisher's per-plan start date "
                      "(flash appeals start mid-year; the anchor is the annual "
                      "grain the task predicts at)",
            "availability": "derived from the row's own plan year; trivially known "
                            "at launch",
            "status": "verified"},
        "country_iso3": {
            **launch_group,
            "source": launch_group["source"] + " -> country_iso3: the CSV "
            "countryCode of the single-country group"},
        "plan_year": {
            **launch_group,
            "source": launch_group["source"] + " -> plan_year: the appeal's "
            "plan year"},
        "plan_type": {
            **launch_group,
            "source": launch_group["source"] + " -> plan_type: the CSV typeName "
            "(Humanitarian response plan, Flash appeal, ...)"},
        "is_part_of_gho": {
            **launch_group,
            "source": launch_group["source"] + " -> is_part_of_gho: planVersion."
            "isPartOfGHO, 1 when the appeal is part of the Global Humanitarian "
            "Overview, else 0"},
        "orig_requirements_usd": {
            "source": "the FTS plan endpoint origRequirements - the launch ask",
            "availability": (
                "launch vintage, externally cross-checked: the AFG HNP 2023 ask "
                "4,627,363,573 matches the documented December-2022/January-2023 "
                "ask (UNICEF sitrep #12, US$4.62B) to the dollar, asserted in-build; "
                "orig/revised separation measured on 836 plans (286 revised up, 166 "
                "down, 384 unchanged, 2026-10-29 sweep)"),
            "status": "verified",
            "assumption": "the current API value of the launch ask; the publisher "
                          "could restate it, which the sha256-pinned harvest and "
                          "fixture asserts would surface"},
        "years_since_country_prior": {
            **history_group,
            "source": history_group["source"] + " -> years_since_country_prior: "
            "years between the row and that most recent prior plan-year; -1 "
            "sentinel when none exists"},
    }

    measurements = [
        {"column": "orig_requirements_usd",
         "unit": "US dollars (integer; the launch ask)",
         "frame": "requirements stated at the appeal's launch (launch vintage, "
                  "externally cross-checked; NOT the CSV requirements column, "
                  "which carries the revised value in revised cases)"},
        {"column": "years_since_country_prior",
         "unit": "years (-1 sentinel when no prior appeal)",
         "frame": "gap to the most recent strictly-earlier same-country "
                  "plan-year; a function of which appeals exist, never of any "
                  "row's funding outcome"},
        {"column": "plan_year", "unit": "calendar year (integer)",
         "frame": "the appeal's plan year; the split key"},
        {"column": "plan_year_anchor",
         "unit": "ISO date (derived: January 1 of the plan year)",
         "frame": "the annual grain's calendar anchor; the gate's time-column "
                  "join key for any cross-row review"},
        {"column": "is_part_of_gho", "unit": "binary indicator",
         "frame": "appeal is part of the Global Humanitarian Overview"},
        {"column": "country_iso3", "unit": "ISO 3166-1 alpha-3 country code",
         "frame": "the single affected country of the primary appeal"},
        {"column": "plan_type", "unit": "publisher plan type name",
         "frame": "appeal instrument type (HRP, Flash appeal, ...)"},
    ]

    positive_events = {}
    for name in ("train", "eval", "holdout"):
        positive_events[name] = {
            "positives": stats_by_split[name]["positives"],
            "distinct_events": stats_by_split[name]["positives"],
        }

    quality = {
        "name": NAME,
        "built_at_utc": built_at,
        "task": {
            "question": (
                "For a primary (single-country) humanitarian appeal plan-year "
                "launched by OCHA/FTS, will the plan-year end with appeal-linked "
                "funding at >= 50% of its ORIGINAL (launch) requirements? A useful "
                "prediction at launch lets financing analysts flag underfunded "
                "appeals months before the year-end gap is reported."),
            "prediction_time": (
                "the appeal's launch: the requirements announcement at or before "
                "the plan year starts (GHO launches 1 December of the prior year - "
                "GHO 2023 launched 2022-12-01; HRPs launch end-December to early "
                "January; flash appeals launch at event onset mid-year). Features "
                "are the launch attributes plus strictly-earlier same-country "
                "appeal PRESENCE (the recency gap only; the prior-outcome "
                "features that the 2026-11-01 queue audit recovered labels "
                "through were removed in fts-appeal-003). The shipped plan_year_anchor (Jan 1 of the plan year) "
                "is the conservative annual-grain join key, not a claim that every "
                "appeal launched on that day. Worked example (UTC dates, annual "
                "grain): Afghanistan HNP 2023, plan id 1117, asked US$4,627,363,573 "
                "at launch (external December-2022 documentation matches), ended "
                "2023 at US$1,678,347,238 funding = 36.3% of the original ask -> "
                "label 0 (below half)."),
        },
        "target": TARGET,
        "positive_label": POSITIVE,
        "positive_label_text": POSITIVE_LABEL_TEXT,
        "id_columns": ID_COLUMNS,
        "id_columns_are_entity_keys": True,
        "id_columns_note": ("plan_year_id = <plan year>-<FTS plan id> names one "
                            "primary plan-year appeal with one label; unique "
                            "across the panel, asserted at construction"
                            " (country, plan year) is NOT the grain and is not unique: 41 country-"
                            "year groups carry more than one appeal (43 excess rows "
                            "- e.g. Tanzania 2001-43 and 2001-73, Indonesia 2002-85 "
                            "and 2002-94, distinct appeals within the same country-"
                            "year), per the 2026-11-03 independent re-audit"),
        "time_column": TIME_COLUMN,
        "event_key_column": EVENT_KEY_COLUMN,
        "event_key_note": (
            "an event is one positive plan-year appeal (the gate's clustering takes "
            "the id's first 10 characters, which is the whole 9-10 char id here, so "
            "the recomputed count equals the positive count at appeal grain). The "
            "scientifically relevant dependence structure is coarser and is used "
            "for clustered intervals in reporting: same-country series (83 "
            "distinct countries measured) and same-year global funding cycles "
            "(measured positive rate drifts 68.3% 2000-2013 -> 42.5% 2023-2025)"),
        "split_windows": SPLIT_WINDOWS,
        "split_boundaries": {
            "train": "plan years 2000-2016 (window end exclusive)",
            "eval": "plan years 2017-2020 (window end exclusive)",
            "holdout": "plan years 2021-2025 (window end exclusive; the 2026+ live "
                       "edge is excluded until those years close)",
        },
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "positive_events": positive_events,
        "positive_events_note": (
            "each positive is one distinct plan-year appeal; the clustered counts "
            "that matter for inference are the country series and funding-cycle "
            "years declared in event_key_note and measured in summary.json"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "shipped_columns": COLUMNS,
        "label_source_columns": [
            "the FTS flow endpoint's per-plan-year incoming.fundingTotal "
            "(api.hpc.tools/v1/public/fts/flow?planId=<id>&year=<year>) - the label "
            "numerator; never shipped in any split",
            "the HDX CSV funding column (cross-check only; flow and CSV agreed to "
            "the dollar on the 2026-10-29 fixtures and are cross-checked on every "
            "row at construction)",
        ],
        "post_hoc_columns": [
            "revisedRequirements and the CSV requirements column (post-launch "
            "revisions; the CSV column carries the REVISED value in revised cases - "
            "AFG 2023: CSV 3,227,372,908 vs orig 4,627,363,573, a fixture that "
            "would flip the label to 1 if used as the denominator)",
            "per-plan-year funding totals in any form (the label numerator; "
            "funding appears in no shipped column)",
            "percentFunded (the CSV's current mixed-vintage ratio)",
            "revisionState, planVersion start/end dates of the CURRENT version "
            "(mutable post-launch metadata; only isPartOfGHO, the launch ask and "
            "the year ship)",
        ],
        "high_cardinality_columns": ["country_iso3"],
        "high_cardinality_columns_note": (
            "country_iso3 is the identity FEATURE (it appears in all three splits "
            "by design and is never an id column). On this small panel it exceeds "
            "the gate's relative categorical threshold (distinct levels > rows/5 "
            "in a split - measured 51 countries over 139 eval rows against the "
            "threshold 27), so it is declared here as a free high-cardinality "
            "field, not treated as a leak: the column is the country identity the "
            "task predicts on, per-level statistics are too thin to memorise "
            "individual rows, and its AUC is reported as a measured property"),
        "expected_duplicate_ids": 0,
        "external_threshold": False,
        "threshold_note": (
            "the 0.5 x ORIGINAL requirements threshold is a task-defined policy "
            "fraction (half the launch ask), fixed before construction and not "
            "data-derived; both operands are US dollars from the same publisher, "
            "and the AFG 2023 + YEM 2023 + Burundi RRP 2021 fixtures pin the unit "
            "and frame to exact dollar values asserted in-build"),
        "measurements": measurements,
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "the appeal's launch (requirements announcement), at or "
                          "before the plan year starts",
                "days_after_period_end": 0,
                "citation": (
                    "FTS launch evidence: GHO 2023 launched 2022-12-01 (reliefweb "
                    "press release); the Afghanistan HNP 2023 ask of US$4.62 "
                    "billion is documented in UNICEF sitrep #12 (January 2023) and "
                    "matches plan origRequirements 4,627,363,573 to the dollar "
                    "(the in-build fixture); HRP launches run end-December to early "
                    "January; flash appeals launch at event onset"),
            },
            "features": {
                "period": "the appeal's own launch record plus the PRESENCE of "
                          "strictly-earlier plan-years of the same country "
                          "(years only; no prior outcome ships)",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": (
                    "the row's own plan-year launch attributes; the only "
                    "history-derived column reads the YEAR of the country's most "
                    "recent strictly-earlier appeal, never any row's outcome"),
                "fields": [
                    "CSV (id, year) group carries exactly one country row (primary "
                    "population; multi-country regional groups excluded, counted)",
                    "plan endpoint origRequirements > 0 (no-orig groups excluded "
                    "as unobserved denominators, counted)",
                    "plan year within 2000..2025 (pre-window groups and the 2026+ "
                    "live edge excluded, counted)",
                ],
                "basis": (
                    "eligibility reads only the appeal's own launch record; the "
                    "live-edge and no-orig exclusions are unobserved-target "
                    "censoring counted in their own buckets, never scored as "
                    "negatives - a running 2026 appeal is excluded because its "
                    "outcome does not exist yet, not because it failed"),
            },
            "observations": [],
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one primary plan-year appeal. The 2026.10-era "
                "prior-outcome features (country_prior_appeals, "
                "country_prior_covered_rate, country_last_prior_covered) allowed "
                "a label-blind attacker to recover earlier rows' labels exactly "
                "from later rows' features (2026-11-01 queue audit: 120/139 eval, "
                "128/182 holdout, 0 errors) and were REMOVED in fts-appeal-003; "
                "no shipped column is any longer a function of another row's "
                "outcome (asserted by construction: the only history-derived "
                "column reads prior appeal YEARS, never labels). The "
                "isolated-rows access declaration is retained as the CONSERVATIVE "
                "posture, not as an enforcement claim: the illustrative runner "
                "still passes the whole eval feature table to the predictor in "
                "one call, nothing in this package enforces isolation, and the "
                "absence of a known recovery is not a proof against future "
                "attacks - the fresh independent pre-flip audit must attack the "
                "shipped bytes before any publication. Labeled eval is "
                "development/validation; the holdout is the final test and stays "
                "outside evaluated agents' workspaces. Training-label timing is "
                "UNVERIFIED: the split key is the plan year and a train "
                "plan-year's final funding can complete during the first eval "
                "appeals' launch window (train 2016 outcomes closed during 2017 "
                "while GHO 2017 launched December 2016), so no full-row "
                "availability ledger is claimed and the artifact is retrospective "
                "research only, never a certified historical forecasting setup"),
            "feature_evidence": fe,
            "vintage": {
                "kind": "mixed",
                "evidence": (
                    "launch attributes are launch-vintage, externally cross-checked "
                    "(AFG HNP 2023 orig 4,627,363,573 matches the documented "
                    "December-2022/January-2023 ask; orig/revised separation "
                    "measured on 836 plans: 286 revised up, 166 down, 384 unchanged; "
                    "the CSV requirements column carries the revised value in "
                    "revised cases and is excluded as a denominator). Funding totals "
                    "are CURRENT-SNAPSHOT vintage: api.hpc.tools exposes no version "
                    "history (checked 2026-10-29), the HDX resource was observed "
                    "refreshed 2026-10-30, and late-reported flows can shift a "
                    "completed year's total; this build pins every fetched file by "
                    "sha256 at construction time (summary.json) and states all "
                    "values as construction-time vintage"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "membership is decidable from the appeal's own launch record: a "
                    "single-country CSV group with a positive launch ask in the "
                    "scored year range. The exclusions are unobserved-target "
                    "censoring counted in their own buckets - 2026+ live-edge rows "
                    "(outcome not yet observable at the snapshot), no-orig groups "
                    "(denominator not stated), regional multi-country groups "
                    "(excluded by design after measuring the Burundi RRP 2021 slice "
                    "gap: country slices sum to 14,978,233 against the plan total "
                    "19,282,778, ratio 0.78, so per-country slices cannot carry the "
                    "plan-level label) - no row is excluded for a low outcome. "
                    "Funded and unfunded appeals are both retained whenever the "
                    "launch record exists"),
            },
            "limitations": [
                "the 2026+ live edge is excluded until those plan years close; the "
                "panel is a snapshot of complete plan years 2000-2025",
                "funding totals are current-snapshot vintage (no publisher version "
                "history): late-reported flows mean a completed year's total can "
                "differ from any past instant's running value, and the immediately-"
                "preceding plan year's outcome was still accruing at December "
                "launches - training-label timing is unverified and no operational "
                "forecasting claim is made",
                "prior-history exposure CLOSED by fts-appeal-003: the 2026.10-era "
                "prior-outcome features let a label-blind attacker recover "
                "earlier rows' labels exactly (2026-11-01 queue audit: 120/139 "
                "eval, 128/182 holdout, 0 errors) and were removed; the only "
                "history-derived column left (years_since_country_prior) reads "
                "prior appeal YEARS, is derivable from the shipped row set "
                "itself, and carries no outcome - but the whole-table runner "
                "still presents every row at once, so isolated rows remain the "
                "declared conservative requirement with no enforcement claim",
                "regional multi-country appeals are out of scope (measured slice "
                "gap 0.78); the task is about single-country appeals only",
                "the label counts appeal-linked funding only (FTS incoming "
                "fundingTotal); internal transfers, CBPF allocations and "
                "non-appeal funding are out of scope, as are requirements outside "
                "FTS (e.g. regional RRPs' host-government shares)",
                "prevalence is NOT stationary across eras: measured positive rate "
                "at the 50% threshold drifts 68.3% (2000-2013) -> 52.3% "
                "(2014-2018) -> 63.8% (2019-2022) -> 42.5% (2023-2025); intervals "
                "must be country-clustered and year-aware, and a single-window "
                "holdout reads as an era as much as a test",
                "origRequirements is verified launch-vintage on dated external "
                "evidence for sampled cohorts, not for every row; a restated ask "
                "would surface as a fixture failure",
            ],
            "cross_row_audit": {
                "probes": [],
                "rationale": (
                    "the within-country prior-outcome join that previously "
                    "exposed one row's label through a later row's features was "
                    "removed in fts-appeal-003 together with its operand columns "
                    "(country_last_prior_covered, country_prior_covered_rate, "
                    "country_prior_appeals): the 2026-11-01 queue audit recovered "
                    "120/139 eval and 128/182 holdout labels exactly through "
                    "count x rounded-rate arithmetic plus the declared last-prior "
                    "tie rule, reading only shipped features of later rows. No "
                    "declared probe remains because no shipped column reads "
                    "another row's outcome: every remaining feature is a function "
                    "of the row's own launch record, except "
                    "years_since_country_prior, which reads only WHICH "
                    "strictly-earlier same-country appeals exist (their years, "
                    "never their labels), is derivable by any reader from the "
                    "shipped row set itself, and is asserted label-free by "
                    "brute-force recompute at construction. Row presence is "
                    "launch-decidable (single-country CSV group, positive launch "
                    "ask, plan year in window; the live-edge and no-orig "
                    "exclusions are unobserved-target censoring, never "
                    "outcome-based), so no missing-row rule encodes any label. "
                    "Same-instant joins are unique by construction (plan_year_id "
                    "unique, one row per plan-year appeal). The FTS API exposes "
                    "no historical vintages (checked), so no as-of "
                    "reconstruction is claimed and the restricted retrospective "
                    "posture stands. The pre-flip independent audit must "
                    "re-attack these bytes label-blind before any publication"),
                "auxiliary_files_review": (
                    "the artifact ships exactly public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json and quality.json; no auxiliary "
                    "solver-visible file exists (summary.json, the harvest "
                    "provenance JSONLs and the source CSV copy are written outside "
                    "the extract under /output, and no funding value or prior "
                    "outcome appears in any shipped column)"),
            },
        },
        "source_snapshot": {
            "publisher": (
                "UN OCHA Financial Tracking Service (fts.unocha.org / "
                "api.hpc.tools), enumerated via the HDX distribution 'Global "
                "requirements and funding data' (data.humdata.org, resource "
                "fts_requirements_funding_global.csv)"),
            "files": [
                {"kind": "hdx-bulk-csv", "name": "fts_requirements_funding_global.csv",
                 "url": CSV_URL, "bytes": harvest_stats["csv_bytes"],
                 "sha256": harvest_stats["csv_sha256"]},
                {"kind": "api-endpoint", "name": "v2/public/plan/{id}",
                 "url": "https://api.hpc.tools/v2/public/plan/{id}",
                 "note": "launch-vintage origRequirements + planVersion metadata; "
                         "per-plan compact records in the collected "
                         "harvest_plans.jsonl"},
                {"kind": "api-endpoint", "name": "v1/public/fts/flow",
                 "url": FLOW_URL,
                 "note": "first page only; incoming.fundingTotal per scored "
                         "plan-year; per-plan-year compact records in the "
                         "collected harvest_flows.jsonl"},
            ],
            "licence_note": (
                "FTS 'Using FTS data' page answers 'Can I use and republish the "
                "data and information published on FTS website/API?' with 'Yes' "
                "plus a citation request; the identical HDX dataset record carries "
                "CC BY-IGO (licence_class A, read 2026-10-29)"),
            "snapshot_note": (
                "current-vintage source re-fetched at build time and pinned by "
                "sha256; the publisher revises the live database continuously and "
                "no historical vintages exist"),
        },
        "splits_stats": stats_by_split,
    }
    return quality


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="extract directory")
    parser.add_argument("--work-dir", required=True, help="harvest/cache directory")
    parser.add_argument("--built-at", required=True,
                        help="pinned build timestamp (ISO 8601, UTC)")
    parser.add_argument("--summary-out", required=True,
                        help="where to write summary.json (outside the extract)")
    args = parser.parse_args()

    out = Path(args.out)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    started = time.time()

    harvest_stats, raw_rows, eligible, groups, plans, flows_cache = harvest(work)
    print(f"harvest: {harvest_stats['csv_rows']} CSV rows, "
          f"{harvest_stats['eligible_rows']} eligible, "
          f"{harvest_stats['plan_year_groups']} (id,year) groups, "
          f"{len(plans)} plans, requests {harvest_stats['requests']}, "
          f"errors {harvest_stats['errors']}", flush=True)

    primary, buckets = build_panel(eligible, groups, plans, flows_cache,
                                   harvest_stats)
    check_fixtures(primary, groups, plans, flows_cache, harvest_stats)
    print(f"fixtures: AFG/YEM/Burundi all pinned to the dollar; "
          f"primary panel {len(primary)} rows", flush=True)

    splits = split_rows(primary)
    stats_by_split = write_artifact(out, splits, args.built_at)
    for name in ("train", "eval", "holdout"):
        entry = stats_by_split[name]
        print(f"split {name}: {entry['rows']} rows, {entry['positives']} positives "
              f"({entry['positive_rate']}), {entry['distinct_countries']} countries, "
              f"years {entry['year_min']}..{entry['year_max']}", flush=True)

    quality = build_quality(stats_by_split, harvest_stats, args.built_at)
    (out / "quality.json").write_text(json.dumps(quality, indent=1, sort_keys=True)
                                      + "\n", encoding="utf-8")

    per_year = defaultdict(lambda: {"rows": 0, "positives": 0})
    for entry in primary:
        per_year[entry["year"]]["rows"] += 1
        per_year[entry["year"]]["positives"] += entry["label"]

    summary = {
        "name": NAME,
        "built_at_utc": args.built_at,
        "job": "fts-appeal-003",
        "harvest": harvest_stats,
        "exclusion_buckets": {k: len(v) for k, v in buckets.items()},
        "flow_vs_csv_funding_mismatches": harvest_stats["csv_flow_mismatches"],
        "zero_funding_rows": harvest_stats["zero_funding_rows"],
        "splits": stats_by_split,
        "per_year": {str(y): per_year[y] for y in sorted(per_year)},
        "artifacts": {
            rel: {"sha256": sha256_of(out / rel), "bytes": (out / rel).stat().st_size}
            for rel in ("public/train.csv", "public/eval.csv",
                        "private/holdout.csv", "meta.json", "quality.json")},
        "elapsed_seconds": round(time.time() - started, 1),
        "fixture_values": harvest_stats.get("fixtures", {}),
    }
    Path(args.summary_out).write_text(json.dumps(summary, indent=1, sort_keys=True)
                                      + "\n", encoding="utf-8")

    # provenance copies for collection (outside the extract)
    source_dir = Path(args.summary_out).parent / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    for name in ("reqfund_global.csv", "plans.jsonl", "flows.jsonl"):
        copied = source_dir / name
        if not copied.is_file():
            copied.write_bytes((work / name).read_bytes())
    print(json.dumps({"status": "built", "summary": args.summary_out,
                      "elapsed_seconds": summary["elapsed_seconds"]}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr, flush=True)
        sys.exit(3)
