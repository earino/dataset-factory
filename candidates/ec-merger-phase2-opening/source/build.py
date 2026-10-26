#!/usr/bin/env python3
"""Construction script for the `ec-merger-phase2-opening` candidate.

Task: for a concentration notified to the European Commission under the EU
Merger Regulation, using only case attributes fixed at notification (the
parties as named in the case title, the case's NACE sector codes, the
applicable regulation, and the notification date), will the Commission open
an in-depth Phase II investigation (adopt an Art. 6(1)(c) decision)?

Where this runs
---------------
On a temporary worker. The construction channel is the publisher's anonymous
bulk open-data feed (DG COMP case register, one GET, ~42 MB, updated daily):

  https://compcases-open-data-portal-files-prod.s3.eu-west-1.amazonaws.com/case-data-M.json

The S3 objects roll over under a 30-day expiry rule, so the build records the
fetch date, byte count and sha256 of the snapshot it used. The distribution
URL from the data.europa.eu record is the stable channel.

Boundaries (fixed order, enforced by run.sh)
-------------------------------------------
This script ONLY constructs files and gate diagnostics: the three split
CSVs in runner layout, meta.json, quality.json and summary.json. It computes
no performance metric of any kind - no AUC, no baseline, no rate presented
as a model result. Reference scoring lives in score.py and runs only after
the qualification gate has passed and --accept has re-verified the exact
bytes.

Frame rules (each measured and reported, never assumed)
------------------------------------------------------
* Grain: one row per notified merger case (caseType Merger + a notification
  date exists). Row key ``case_number`` (the register's case number, unique
  per case).
* Prediction instant: the case's notification date (caseNotificationDate;
  date-only, Brussels local). Every shipped feature is a case attribute
  fixed when the file is registered: the parties in the case title, the
  case's sector codes, the applicable regulation, the notification date.
* Label: the case carries an Art. 6(1)(c) decision (the Phase II opener,
  the same article number under Reg 4064/89 and Reg 139/2004) adopted on or
  after the notification date. Decisions of type "Withdrawal of Art. 6(1)(c)"
  do NOT count as openers (the substring "Art. 6(1)(c)" appears in those
  labels; matching without excluding withdrawals would mislabel). Ever-
  adopted rule: a later withdrawal of an adopted opener (M.10188, after the
  2024 ECJ judgment) leaves the label positive.
* M.3333 rule: label decisions predating the case's notification date do
  not count. M.3333 SONY/BMG is the single measured re-notification carrying
  its 2004-02-12 opener under a 2007-01-31 re-notification; the register also
  carries a 2007-03-01 opener for the re-notified procedure, so the label
  stays positive on that post-notification basis alone. The build asserts it
  is the only pre-notification-opener case.
* Label maturity (pending censoring): a case with no opener is included
  only if some terminal decision exists (Art. 6(1)(a) or Art. 6(1)(b) with
  or without conditions, an Art. 8(1)/(2)/(3)/(4) outcome, a Withdrawal, a
  full Art. 9(3) referral out, or a full Art. 4(4) referral). A notified
  case whose register record establishes neither an opener nor a terminal
  decision (live recent filings; old entries with only partial referrals or
  no decisions at all) has an unobservable label at fetch time: it is
  censored, counted per split and per notification year in summary.json as
  ``pending_censored``, and never used to decide another row's membership.
  This is missing outcome data, not a label.
* Splits: temporal on the notification year, the full-era thirds partition
  pinned in the candidate record - train 1990-2013, eval 2014-2018,
  holdout 2019-snapshot. The Art. 6(1)(c) label is the same legal
  instrument under both regulations.
* Sector features: the register codes sectors as current-vintage NACE Rev 2
  {code,label} objects. The shipped ``sector_divisions`` value is the sorted
  set of division labels (the first two components of the label's code part,
  e.g. "C.20.5 - ..." -> "C.20"; "K.64 - ..." -> "K.64"), '|'-joined, or
  "NONE" when the register carries no sectors for the case. NOTE: the
  discovery probe grouped sectors by the LAST component of the register's
  internal code (rsplit("_", 1)), which mixes divisions, class groups and
  subclass digits; the division-conditional rates it printed are therefore
  grouped on a malformed key. This build derives divisions from the label
  and summary.json re-measures the division inventory; the record's
  learnability claim is re-established (or not) by those numbers and by the
  post-acceptance sector-conditional reference in score.py.
* Leakage discipline: the whole decisions block (decisionTypes,
  decisionAdoptionDate, decision references) is the label source and is
  never shipped. Post-hoc or mutable register fields (caseSimplified,
  caseInvestigationPhase, caseDeadlineDate, caseLastDecisionDate,
  caseLinks, caseCourtCases, caseRenotificationDate, caseInitiationDate,
  caseAttachments) are excluded from shipped columns and their absence is
  asserted in every written header. caseSimplified is additionally an
  upgrade leak (a simplified filing upgraded to Normal during review).
* Known-event fixtures (asserted from the fetched register):
  - M.877 BOEING/McDONNELL DOUGLAS: notif 1997-02-18, opener 1997-03-19,
    Art. 8(2) w/ conditions 1997-07-30 - matches the Commission's own
    decision PDF (m877_19970730_600_fr.pdf) and IP/97/729. Expected:
    positive; sectors C.30.3; Reg 4064/89.
  - M.4731 GOOGLE/DOUBLECLICK: notif 2007-09-21, opener 2007-11-13,
    Art. 8(1) 2008-03-11 - matches IP/07/1695 and IP/08/458. Expected:
    positive; sectors M.73.1; Reg 139/2004. Sector as-of fixture: the OJ
    prior notice (OJ C 230, 2.10.2007, p. 12, CELEX C2007/230/08) documents
    the notification-time activities - Google "Internet search engine and
    online advertising", DoubleClick "ad serving management and reporting
    services" - and the register's current-vintage coding M.73.1
    "Advertising" corresponds to those activities.
  - M.10188 ILLUMINA/GRAIL: notif 2021-06-16, opener 2021-07-22, Art. 8(3)
    2022-09-06, withdrawn 2024-09-06 - matches IP/22/5364. Expected:
    positive under the ever-adopted rule (the withdrawal does not undo the
    opener); sectors C.27.9 + C.21.
* Cross-check fixture: the candidate record measured the 2026-10-24
  snapshot (sha 061027db...) at 10,123 eligible cases / 309 Phase II
  positives / splits 5411+217 / 1770+46 / 2942+46. The live snapshot
  rotates daily, so the build fails only outside tolerance bands wide
  enough for two days of drift and the M.3333 rule (which removes exactly
  one train positive), and summary.json records the measured deltas.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout skills/dataset-qualification gates.

Licence: European Commission reuse notice -> CC BY 4.0 (Commission
Decision 2011/833); attribution "European Commission, Directorate-General
for Competition" and indicating changes. Decision PDFs are not
redistributed - register fields only. Our derived compilation is dedicated
CC0-1.0; this is a derived research dataset, never the Commission's
official product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

NAME = "ec-merger-phase2-opening"
TARGET = "phase2_opened"
POSITIVE_LABEL = 1
ROW_ID = "case_number"
TIME_COL = "notification_date"
REGULATION_COL = "regulation"
SECTORS_COL = "sector_divisions"
TITLE_COL = "case_title"

FEED_URL = ("https://compcases-open-data-portal-files-prod."
            "s3.eu-west-1.amazonaws.com/case-data-M.json")
UA = "dataset-factory-scout/1.0 (+https://github.com/earino/dataset-factory)"

LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

# Full-era thirds on the notification year (candidate record, measured).
SPLIT_END_YEAR = {"train": 2013, "eval": 2018}
SPLIT_START_YEAR = {"eval": 2014, "holdout": 2019}

# Decision-type label matching (substring, as the discovery probes did).
OPENER_TOKEN = "Art. 6(1)(c)"
WITHDRAWAL_TOKEN = "ithdraw"        # Withdrawal / withdrawn, any language form
TERMINAL_TOKENS = ("Art. 6(1)(a)", "Art. 6(1)(b)", "Art. 8(1)", "Art. 8(2)",
                   "Art. 8(3)", "Art. 8(4)", "Art. 9(3) full referral")
# Art. 6(1)(a) = Phase I clearance without doubts; Art. 9(3) FULL referral ends
# the EU procedure (partial referrals do not and stay censored when nothing
# else is recorded). Measured on the 2026-10-26 snapshot: the pending set was
# 50 x Art. 9(3) full referral + 50 x Art. 6(1)(a) + 29 with no decisions
# (26 of them live 2020s filings) + 4 partial referrals.
FULL_REFERRAL_TOKEN = "Art. 4(4)"

REGULATION_RE = re.compile(r"(4064/89|139/2004)")
TITLE_SPLIT_RE = re.compile(r"\s*/\s*")

# Cross-check bands: measured on the 2026-10-24 snapshot, widened for daily
# register rotation and the M.3333 exclusion rule. Outside a band is a
# construction bug, not drift.
CROSS_CHECK = {
    "recorded_on": "2026-10-24 snapshot (sha 061027db...), candidate record",
    "eligible_cases": (10_000, 10_300),
    "phase2_positives": (290, 330),
    "split_positives": {"train": (200, 232), "eval": (40, 52),
                        "holdout": (38, 56)},
    "missing_sector_cases": (60, 100),
    "pending_censored": (0, 150),
}

# Label/sector fixtures with external sources (see module docstring).
FIXTURES = [
    {"case": "M.877", "label": 1, "notif": "1997-02-18",
     "regulation": "4064/89", "sectors": {"C.30.3"},
     "source": "Commission decision PDF m877_19970730_600_fr.pdf + IP/97/729"},
    {"case": "M.4731", "label": 1, "notif": "2007-09-21",
     "regulation": "139/2004", "sectors": {"M.73.1"},
     "source": "IP/07/1695 + IP/08/458; sector as-of fixture vs OJ prior "
               "notice C 230, 2.10.2007, p. 12 (CELEX C2007/230/08)"},
    {"case": "M.10188", "label": 1, "notif": "2021-06-16",
     "regulation": "139/2004", "sectors": {"C.27.9", "C.21"},
     "source": "IP/22/5364; 2024-09-06 post-ECJ withdrawal does not undo the "
               "opener under the ever-adopted rule"},
]

COLUMNS = [ROW_ID, TARGET, TIME_COL, "notification_year", "notification_month",
           REGULATION_COL, SECTORS_COL, "sector_count", "has_sectors",
           "party_count", "title_has_jv", TITLE_COL]

FEATURES = ["notification_year", "notification_month", REGULATION_COL,
            SECTORS_COL, "sector_count", "has_sectors", "party_count",
            "title_has_jv", TITLE_COL]
CARRY_COLUMNS = [TIME_COL]
ID_COLUMNS = [ROW_ID]
HIGH_CARDINALITY = [TIME_COL, SECTORS_COL, TITLE_COL]

LABEL_SOURCE_COLUMNS = ["decisions.decisionTypes",
                        "decisions.decisionAdoptionDate",
                        "decisions.decisionReferences"]
POST_HOC_COLUMNS = ["caseSimplified", "caseInvestigationPhase",
                    "caseDeadlineDate", "caseLastDecisionDate", "caseLinks",
                    "caseCourtCases", "caseRenotificationDate",
                    "caseInitiationDate", "caseAttachments"]


class BuildError(Exception):
    pass


def first(metadata: dict, key: str):
    """The register wraps metadata values in lists; unwrap the first."""
    value = metadata.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(work_dir: Path) -> dict:
    """One anonymous GET; the snapshot identity is recorded, never assumed."""
    work_dir.mkdir(parents=True, exist_ok=True)
    target = work_dir / "case-data-M.json"
    request = urllib.request.Request(FEED_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=300) as response:
        target.write_bytes(response.read())
        headers = {k.lower(): v for k, v in response.headers.items()}
    info = {"url": FEED_URL, "bytes": target.stat().st_size,
            "sha256": sha256_of(target),
            "last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
            "fetched_at_utc": datetime.now(timezone.utc).isoformat()}
    print(json.dumps({"fetch": info}), flush=True)
    return info


def decision_facts(case: dict) -> tuple[list[tuple[str, set]], set]:
    """(adoption_date, {decision type labels}) per decision + all labels."""
    facts = []
    all_labels: set[str] = set()
    for decision in case.get("decisions") or []:
        meta = decision.get("metadata") or {}
        types: set[str] = set()
        for raw in meta.get("decisionTypes") or []:
            try:
                entry = json.loads(raw) if isinstance(raw, str) else raw
                types.add(str(entry.get("label", "")))
            except (ValueError, AttributeError, TypeError):
                types.add(str(raw))
        adopted = first(meta, "decisionAdoptionDate")
        facts.append((adopted, types))
        all_labels |= types
    return facts, all_labels


def sector_codes(metadata: dict) -> list[tuple[str, str]]:
    """[(code-part, label)] parsed from caseSectors (JSON-encoded strings)."""
    out = []
    for raw in metadata.get("caseSectors") or []:
        try:
            entry = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            continue
        label = str(entry.get("label") or "")
        code = str(entry.get("code") or "")
        out.append((label.split(" - ")[0].strip(), label))
        if not code or not label:
            raise BuildError(f"sector entry without code/label: {entry!r}")
    return out


def division_of(code_part: str) -> str:
    """'C.20.5' -> 'C.20'; 'K.64' -> 'K.64' (first two components)."""
    parts = code_part.split(".")
    return ".".join(parts[:2])


def build_row(number: str, metadata: dict) -> dict | None:
    """Eligible-case row, or None with the exclusion reason left to the caller."""
    if "MergerCaseType1" not in str(first(metadata, "caseType") or ""):
        return None
    notif = first(metadata, "caseNotificationDate")
    if not notif:
        return None
    title = str(first(metadata, "caseTitle") or "")
    raw_regulation = str(first(metadata, "caseRegulation") or "")
    match = REGULATION_RE.search(raw_regulation)
    if not match:
        raise BuildError(f"{number}: unrecognised caseRegulation {raw_regulation!r}")
    sectors = sector_codes(metadata)
    divisions = sorted({division_of(code) for code, _ in sectors})
    parties = [p for p in TITLE_SPLIT_RE.split(title) if p.strip()]
    return {
        ROW_ID: number,
        "notification_date": str(notif)[:10],
        "notification_year": int(str(notif)[:4]),
        "notification_month": int(str(notif)[5:7]),
        "regulation": match.group(1),
        "sector_divisions": "|".join(divisions) if divisions else "NONE",
        "sector_count": len(sectors),
        "has_sectors": 1 if sectors else 0,
        "party_count": len(parties),
        "title_has_jv": 1 if re.search(r"\bJV\b", title, re.IGNORECASE) else 0,
        "case_title": title,
    }


def label_of(number: str, facts: list[tuple[str, set]], notif: str) -> tuple[int | None, str, dict]:
    """(label, bucket, diagnostics). label None -> censored (unobserved)."""
    openers = [adopted for adopted, types in facts
               if adopted and OPENER_TOKEN in " || ".join(sorted(types))
               and WITHDRAWAL_TOKEN not in " || ".join(sorted(types))]
    late_openers = [d for d in openers if d[:10] >= notif]
    early_openers = [d for d in openers if d[:10] < notif]
    withdrawals = [adopted for adopted, types in facts
                   if OPENER_TOKEN in " || ".join(sorted(types))
                   and WITHDRAWAL_TOKEN in " || ".join(sorted(types))]
    if late_openers:
        return 1, "labelled", {"openers": late_openers,
                               "opener_withdrawals": withdrawals,
                               "pre_notification_openers": early_openers}
    terminal = [adopted for adopted, types in facts
                if adopted and (any(t in " || ".join(sorted(types))
                                    for t in TERMINAL_TOKENS)
                               or WITHDRAWAL_TOKEN in " || ".join(sorted(types))
                               or (FULL_REFERRAL_TOKEN in " || ".join(sorted(types))
                                   and "full" in " || ".join(sorted(types)).lower()))]
    if terminal:
        return 0, "labelled", {"openers": [], "openers_early_only": early_openers,
                                "terminal": terminal,
                                "opener_withdrawals": withdrawals}
    return None, "pending", {"openers": [], "openers_early_only": early_openers,
                             "decisions": len(facts)}


def check_band(value: int, band: tuple[int, int], what: str) -> None:
    low, high = band
    if not (low <= value <= high):
        raise BuildError(f"cross-check failed: {what} = {value}, expected "
                         f"[{low}, {high}] (recorded on {CROSS_CHECK['recorded_on']})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--built-at", default=None,
                        help="pin the build timestamp (UTC ISO) for reproducible bytes")
    args = parser.parse_args()

    out = Path(args.out)
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)

    fetch_info = fetch(Path(args.work_dir))
    register_path = Path(args.work_dir) / "case-data-M.json"
    loaded = json.loads(register_path.read_text(encoding="utf-8"))
    register_path.unlink()                     # bulk copy never leaves the worker dir
    if not isinstance(loaded, dict):
        raise BuildError("register top level is not a case-number-keyed object")
    print(f"register: {len(loaded)} case records", flush=True)

    rows: list[dict] = []
    eligible = 0
    exclusions = Counter()
    pending_by_split: dict[str, int] = {"train": 0, "eval": 0, "holdout": 0}
    pending_by_year: Counter = Counter()
    pre_notif_opener_cases: list[str] = []
    decision_type_inventory: Counter = Counter()
    case_anomalies: dict[str, dict] = {}
    art8_without_opener: list[str] = []

    for number in sorted(loaded):
        case = loaded[number]
        metadata = case.get("metadata") or {}
        row = build_row(number, metadata)
        if row is None:
            type_label = str(first(metadata, "caseType") or "?")
            has_notif = bool(first(metadata, "caseNotificationDate"))
            exclusions[f"caseType={type_label}" + ("" if has_notif else "+no_notification")] += 1
            continue
        eligible += 1
        facts, all_labels = decision_facts(case)
        for label in sorted(all_labels):
            if label:
                decision_type_inventory[label] += 1
        label, bucket, diag = label_of(number, facts, row["notification_date"])
        if bucket == "pending":
            split = ("train" if row["notification_year"] <= SPLIT_END_YEAR["train"]
                     else "eval" if row["notification_year"] <= SPLIT_END_YEAR["eval"]
                     else "holdout")
            pending_by_split[split] += 1
            pending_by_year[row["notification_year"]] += 1
            continue
        if diag.get("pre_notification_openers") or diag.get("openers_early_only"):
            pre_notif_opener_cases.append(number)
        if label == 0 and any("Art. 8(" in l for l in all_labels):
            art8_without_opener.append(number)
        row[TARGET] = label
        rows.append(row)

    # ---- cross-checks against the recorded discovery measurements --------
    # eligible counts BEFORE censoring: the record measured 10,123 notified
    # Merger cases; shipped rows are eligible minus label-unobservable cases.
    check_band(eligible, CROSS_CHECK["eligible_cases"], "eligible cases")
    pending_total = sum(pending_by_split.values())
    check_band(pending_total, CROSS_CHECK["pending_censored"],
               "pending-censored cases (register does not establish the label)")
    positives = sum(1 for r in rows if r[TARGET] == 1)
    check_band(positives, CROSS_CHECK["phase2_positives"], "Phase II positives")
    missing_sector = sum(1 for r in rows if r["has_sectors"] == 0)
    check_band(missing_sector, CROSS_CHECK["missing_sector_cases"],
               "cases without sectors")
    if sorted(pre_notif_opener_cases) != ["M.3333"]:
        raise BuildError(f"pre-notification opener cases are {sorted(pre_notif_opener_cases)}; "
                         "the record measured exactly M.3333")
    # M.3333 SONY/BMG: re-notified 2007-01-31, carrying its 2004-02-12 opener
    # under the annulled procedure. The exclusion rule drops the 2004 opener as
    # a label basis; the register also carries a 2007-03-01 opener for the
    # re-notified procedure, so the label stays positive on that basis alone.
    if "M.3333" not in {r[ROW_ID] for r in rows}:
        raise BuildError("M.3333 is missing from the built rows")
    m3333 = next(r for r in rows if r[ROW_ID] == "M.3333")
    if m3333[TARGET] != 1:
        raise BuildError("M.3333 must be positive: its label must rest on the "
                         "2007-03-01 post-notification opener, not the excluded "
                         "2004-02-12 one")
    m3333_facts, _ = decision_facts(loaded["M.3333"])
    m3333_label, m3333_bucket, m3333_diag = label_of("M.3333", m3333_facts,
                                                     m3333["notification_date"])
    if (m3333_label != 1 or m3333_bucket != "labelled"
            or not m3333_diag.get("openers")
            or min(m3333_diag["openers"])[:10] < "2007-01-31"):
        raise BuildError(f"M.3333 label diagnostics unexpected: {m3333_diag}")

    # ---- known-event fixtures -------------------------------------------
    fixture_results = []
    by_number = {r[ROW_ID]: r for r in rows}
    for fixture in FIXTURES:
        number = fixture["case"]
        row = by_number.get(number)
        if row is None:
            raise BuildError(f"fixture case {number} missing from the built rows")
        sectors = set(row["sector_divisions"].split("|")) - {"NONE"}
        sector_codes_full = set()
        for code, _ in sector_codes(loaded.get(number, {}).get("metadata") or {}):
            sector_codes_full.add(code)
        problems = []
        if row[TARGET] != fixture["label"]:
            problems.append(f"label {row[TARGET]} != {fixture['label']}")
        if row["notification_date"] != fixture["notif"]:
            problems.append(f"notif {row['notification_date']} != {fixture['notif']}")
        if row["regulation"] != fixture["regulation"]:
            problems.append(f"regulation {row['regulation']} != {fixture['regulation']}")
        if sector_codes_full != fixture["sectors"]:
            problems.append(f"sectors {sorted(sector_codes_full)} != {sorted(fixture['sectors'])}")
        if problems:
            raise BuildError(f"fixture {number} failed: {'; '.join(problems)} "
                             f"(source: {fixture['source']})")
        fixture_results.append({"case": number, "ok": True,
                                "label": row[TARGET],
                                "sectors": sorted(sector_codes_full),
                                "source": fixture["source"]})

    # ---- splits ----------------------------------------------------------
    def split_of(row: dict) -> str:
        year = row["notification_year"]
        if year <= SPLIT_END_YEAR["train"]:
            return "train"
        if year <= SPLIT_END_YEAR["eval"]:
            return "eval"
        return "holdout"

    for row in rows:
        row["_split"] = split_of(row)

    stats = {}
    for split, relative in LAYOUT.items():
        split_rows = sorted((r for r in rows if r["_split"] == split),
                            key=lambda r: (r["notification_date"], r[ROW_ID]))
        pos = sum(1 for r in split_rows if r[TARGET] == 1)
        check_band(pos, CROSS_CHECK["split_positives"][split],
                   f"{split} Phase II positives")
        years = {r["notification_year"] for r in split_rows}
        positive_years = {r["notification_year"] for r in split_rows if r[TARGET] == 1}
        # per-year class coverage is reported in summary.json, not asserted here
        if pos == 0 or pos == len(split_rows):
            raise BuildError(f"{split} carries a single class")
        stats[split] = {"rows": len(split_rows), "positives": pos,
                        "positive_rate": round(pos / len(split_rows), 6),
                        "notification_years": [min(years), max(years)],
                        "years_with_positives": len(positive_years),
                        "years_without_positives": sorted(years - positive_years)}
        path = out / relative
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(COLUMNS)
            for row in split_rows:
                writer.writerow([row[column] for column in COLUMNS])
        # the label source and every post-hoc field must be absent
        header = next(csv.reader(path.open(newline="", encoding="utf-8")))
        forbidden = {"decisions", "decisionTypes", "decisionAdoptionDate",
                    "caseSimplified", "caseInvestigationPhase", "caseDeadlineDate",
                    "caseLastDecisionDate", "caseLinks", "caseCourtCases",
                    "caseRenotificationDate", "caseInitiationDate", "caseAttachments"}
        if header != COLUMNS or set(header) & forbidden:
            raise BuildError(f"{relative} header carries forbidden columns: {header}")

    max_date = max(r["notification_date"] for r in rows)
    windows = {
        "train": {"start": "1990-01-01", "end": "2014-01-01"},
        "eval": {"start": "2014-01-01", "end": "2019-01-01"},
        "holdout": {"start": "2019-01-01",
                    "end": (date.fromisoformat(max_date) + timedelta(days=1)).isoformat()},
    }

    # distinct positive notification dates (the gate's clustered event count)
    positive_events = {}
    for split in ("eval", "holdout"):
        dates = {r["notification_date"] for r in rows
                 if r["_split"] == split and r[TARGET] == 1}
        positive_events[split] = {"positives": stats[split]["positives"],
                                  "distinct_events": len(dates)}

    # division inventory (correct grouping; see module docstring)
    division_inventory = {}
    for row in rows:
        divisions = row["sector_divisions"].split("|")
        label = 1 if row[TARGET] == 1 else 0
        for division in divisions:
            entry = division_inventory.setdefault(division, {"cases": 0, "positives": 0})
            entry["cases"] += 1
            entry["positives"] += label
    for entry in division_inventory.values():
        entry["rate"] = round(entry["positives"] / entry["cases"], 6)
    top_divisions = dict(sorted(division_inventory.items(),
                                 key=lambda kv: -kv[1]["cases"])[:15])

    per_year = {}
    for row in rows:
        year = str(row["notification_year"])
        entry = per_year.setdefault(year, {"rows": 0, "positives": 0, "pending": 0})
        entry["rows"] += 1
        entry["positives"] += row[TARGET]
    for year, count in pending_by_year.items():
        per_year.setdefault(str(year), {"rows": 0, "positives": 0, "pending": 0})
        per_year[str(year)]["pending"] = count

    built_at = args.built_at or datetime.now(timezone.utc).isoformat()

    # ---- meta.json --------------------------------------------------------
    meta = {
        "name": NAME,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split_description": "temporal on the notification year: train 1990-2013, "
                             "eval 2014-2018, holdout 2019-snapshot (full-era thirds, "
                             "pinned in the candidate record)",
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    # ---- quality.json -----------------------------------------------------
    quality = {
        "name": NAME,
        "task": {
            "question": "For a concentration notified to the European Commission "
                        "under the EU Merger Regulation, using only case attributes "
                        "fixed at notification (the parties as named in the case "
                        "title, the case's NACE sector codes, the applicable "
                        "regulation, and the notification date), will the Commission "
                        "open an in-depth Phase II investigation (adopt an "
                        "Art. 6(1)(c) decision) in this case?",
            "prediction_time": "The notification date of the case (caseNotificationDate; "
                               "date-only precision, Brussels local). All shipped features "
                               "are case attributes fixed when the file is registered. The "
                               "label event - an Art. 6(1)(c) decision opening Phase II - "
                               "is adopted after notification (measured 308/309 strictly "
                               "after; the single pre-notification opener M.3333 is "
                               "excluded by rule). No feature's target window precedes "
                               "the instant.",
        },
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": TIME_COL,
        "event_key_column": TIME_COL,
        "event_key_note": "case_number is unique per row, so the conservative "
                          "clustered unit shipped here is the notification DAY "
                          "(cases notified the same day share enforcement "
                          "conditions), following the chilecompra precedent. A "
                          "weaker dependence - enforcement-era and sector "
                          "acquisition waves - crosses day boundaries: "
                          "per-notification-year positive counts are reported "
                          "beside every score in the reference report and the "
                          "wave dependence is recorded in "
                          "evaluation_contract.limitations.",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped feature is a case attribute fixed when the file is "
            "registered, read from the register's metadata block: case_title is "
            "caseTitle (the merging parties, an immutable historical fact; the OJ "
            "prior notice for M.4731 shows the parties and activities at "
            "notification); sector_divisions is the sorted set of NACE division "
            "labels derived from caseSectors (register codes sectors as "
            "current-vintage NACE Rev 2 {code,label}; division = first two "
            "components of the label's code part, e.g. 'C.20.5 - ...' -> 'C.20'; "
            "'NONE' when the register carries no sectors - 79/10,123 measured on "
            "the discovery snapshot); sector_count is the number of caseSectors "
            "entries; has_sectors flags the missing-sector cases; regulation is "
            "caseRegulation (4064/89 or 139/2004); notification_year/month are "
            "calendar decompositions of caseNotificationDate; party_count is the "
            "number of ' / '-separated segments of caseTitle; title_has_jv flags "
            "titles carrying a 'JV' token. caseSimplified is EXCLUDED (upgrade "
            "leak: a simplified filing upgraded to Normal during review would "
            "make the current value post-hoc), as are caseInvestigationPhase, "
            "caseDeadlineDate, caseLastDecisionDate, caseLinks, caseCourtCases, "
            "caseRenotificationDate, caseInitiationDate and caseAttachments "
            "(post-hoc, mutable, or non-pinned)."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": "notification_date is the time column and "
                                 "case_title is the free party-name text; "
                                 "sector_divisions is the fine-grained "
                                 "combination of the case's NACE divisions "
                                 "('C.20|G.47.11'-style), whose level count "
                                 "exceeds rows/5 per split. A per-value AUC on "
                                 "any of these memorises rows, so all three are "
                                 "declared here rather than scored as candidate "
                                 "leaks; the division-level information stays "
                                 "recoverable by splitting the column on '|'. "
                                 "The register's own baseline runner drops "
                                 "string columns with more than 1000 levels; "
                                 "they remain available to agents.",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": TIME_COL, "unit": "ISO date (date-only, Brussels local)",
             "frame": "the case's notification event; case attributes are fixed "
                      "when the file is registered"},
            {"column": "notification_year", "unit": "calendar year (int)",
             "frame": "calendar decomposition of the notification date"},
            {"column": "notification_month", "unit": "calendar month 1-12 (int)",
             "frame": "calendar decomposition of the notification date"},
            {"column": "regulation", "unit": "EU merger regulation instrument "
                                             "(4064/89 or 139/2004)",
             "frame": "the regulation in force, fixed by the notification date"},
            {"column": SECTORS_COL, "unit": "sorted set of NACE Rev 2 division "
                                            "labels, '|'-joined, or NONE",
             "frame": "current-vintage register coding of the parties' activities; "
                      "the industries are notification-time facts (the M.4731 OJ "
                      "prior notice documents them at notification), the taxonomy "
                      "labels are current-vintage"},
            {"column": "sector_count", "unit": "count of caseSectors entries (int)",
             "frame": "number of sector codes the register lists for the case"},
            {"column": "has_sectors", "unit": "flag 0/1",
             "frame": "1 when the register carries sectors for the case; the "
                      "discovery snapshot measured 79/10,123 without"},
            {"column": "party_count", "unit": "count of ' / '-separated title "
                                              "segments (int)",
             "frame": "derived from caseTitle, fixed at registration; a proxy for "
                      "deal complexity, not a verified party census (JV suffixes "
                      "count as segments)"},
            {"column": "title_has_jv", "unit": "flag 0/1",
             "frame": "derived from caseTitle: 1 when the title carries a 'JV' "
                      "token, fixed at registration"},
            {"column": TITLE_COL, "unit": "free text (the merging parties' names)",
             "frame": "caseTitle, fixed at registration (the OJ prior notice for "
                      "M.4731 names the same parties at notification)"},
        ],
        "split_windows": windows,
        "split_boundaries": {
            "train": "notification years 1990-2013 (Reg 4064/89 and early "
                      "Reg 139/2004 era)",
            "eval": "notification years 2014-2018",
            "holdout": "notification years 2019-snapshot (recent-year positives "
                       "1/4/3 in 2024/25/26 on the discovery snapshot reflect "
                       "maturing procedures; per-year reporting is mandatory "
                       "when interpreting it)",
        },
        "positive_events": positive_events,
        "positive_events_note": "distinct_events counts distinct notification "
                                "DATES among positive rows (the event key's date "
                                "part), the clustered unit in event_key_note",
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "splits": LAYOUT,
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "the case's notification event",
                "days_after_period_end": 0,
                "citation": "The register records caseNotificationDate (the date "
                            "the Commission received the notification; date-only, "
                            "Brussels local) and the case attributes fixed at "
                            "registration. The OJ prior notice for M.4731 (OJ C "
                            "230, 2.10.2007, p. 12, CELEX C2007/230/08) shows the "
                            "reference number, parties, activities and "
                            "notification date published within days of the event; "
                            "the three known-event fixtures (M.877 1997, M.4731 "
                            "2007, M.10188 2021) reproduce external "
                            "notification-era sources exactly.",
            },
            "features": {
                "period": "the case's notification event",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "the case's notification event "
                                       "(caseNotificationDate; eligibility reads "
                                       "caseType and caseNotificationDate only)",
                "fields": ["caseType", "caseNotificationDate",
                           "caseTitle", "caseSectors", "caseRegulation",
                           "decisions (label source, read afterwards to compute "
                           "the label and label maturity)"],
                "basis": "membership requires only notification-time fields: "
                         "caseType Merger and a notification date exist. Cases "
                         "whose register record establishes neither an opener "
                         "nor a terminal decision (Art. 6(1)(a)/(b), Art. 8 "
                         "outcomes, withdrawals, full 9(3)/4(4) referrals) are "
                         "missing outcome data at fetch time - live recent "
                         "filings plus old entries with only partial referrals "
                         "or no decisions: censored, counted per split and per "
                         "notification year in summary.json as "
                         "pending_censored, never used to decide another "
                         "row's membership. A missing or thin later period "
                         "never deletes an earlier row.",
            },
            "observations": [],
            "observations_note": "administrative record: the case attributes are "
                                 "recorded at the event, so no publication-lag "
                                 "observations are required. The register itself "
                                 "is a current snapshot (bulk feed since "
                                 "2025-03-18, S3 objects expire after 30 days, "
                                 "regenerated daily); no historical vintages "
                                 "exist, which evaluation_contract.vintage "
                                 "records.",
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": "every feature is a same-row case attribute; no "
                          "cross-row construction exists. Labeled eval is "
                          "development/validation; the holdout is the final "
                          "test and stays outside evaluated agents' workspaces. "
                          "Training-label timing is UNVERIFIED: the register "
                          "is a current snapshot with no historical vintages, "
                          "so no full-row availability ledger can be "
                          "constructed and the artifact is retrospective "
                          "research only, never a certified historical "
                          "forecasting setup.",
            "feature_evidence": {
                "case_number": {
                    "source": "register metadata caseNumber",
                    "availability": "assigned at notification; the OJ prior "
                                     "notice carries the reference COMP/M.4731 "
                                     "at notification",
                    "status": "verified"},
                "notification_date": {
                    "source": "register metadata caseNotificationDate",
                    "availability": "the notification event itself; verified "
                                    "against the M.4731 OJ prior notice "
                                    "(21 September 2007) and the M.877 decision "
                                    "PDF (18 February 1997)",
                    "status": "verified"},
                "notification_year": {
                    "source": "calendar decomposition of caseNotificationDate",
                    "availability": "derivable from the verified notification "
                                     "date at the instant",
                    "status": "verified"},
                "notification_month": {
                    "source": "calendar decomposition of caseNotificationDate",
                    "availability": "derivable from the verified notification "
                                     "date at the instant",
                    "status": "verified"},
                "regulation": {
                    "source": "register metadata caseRegulation",
                    "availability": "the regulation in force is fixed by the "
                                    "notification date; the M.4731 OJ notice "
                                    "cites Reg 139/2004, the M.877 decision "
                                    "cites Reg 4064/89",
                    "status": "verified"},
                "sector_divisions": {
                    "source": "register metadata caseSectors (current-vintage "
                              "NACE Rev 2 {code,label})",
                    "availability": "the industries are notification-time facts; "
                                    "verified for M.4731 against its OJ prior "
                                    "notice activities and for M.877 against its "
                                    "decision PDF; the taxonomy labels are "
                                    "current-vintage (see vintage)",
                    "status": "verified"},
                "sector_count": {
                    "source": "count of caseSectors entries",
                    "availability": "derivable from the verified sector field "
                                    "at the instant",
                    "status": "verified"},
                "has_sectors": {
                    "source": "presence of caseSectors",
                    "availability": "derivable from the verified sector field "
                                    "at the instant",
                    "status": "verified"},
                "party_count": {
                    "source": "caseTitle split on ' / '",
                    "availability": "caseTitle is fixed at registration "
                                    "(M.4731 OJ notice names the same parties); "
                                    "the count is a deterministic derivation",
                    "status": "verified"},
                "title_has_jv": {
                    "source": "caseTitle JV token",
                    "availability": "caseTitle is fixed at registration; the "
                                    "flag is a deterministic derivation",
                    "status": "verified"},
                "case_title": {
                    "source": "register metadata caseTitle",
                    "availability": "fixed at registration; the M.4731 OJ "
                                    "prior notice names Google and DoubleClick "
                                    "at notification",
                    "status": "verified"},
            },
            "vintage": {
                "kind": "current_snapshot",
                "evidence": "The bulk feed has existed since 2025-03-18 and its "
                            "S3 objects expire after 30 days; no historical "
                            "vintages of the register exist, so a reverse-history "
                            "probe is not performable and point-in-time "
                            "reconstruction is not claimed. The register's "
                            "current values reproduce external notification-era "
                            "sources for three fixtures spanning 1997-2022 "
                            "(M.877, M.4731 incl. its OJ prior notice, "
                            "M.10188), evidence that it preserves historical "
                            "procedure facts. Sector coding is current-vintage "
                            "NACE Rev 2 across all eras (M.877 notified 1997 "
                            "coded C.30.3).",
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": "eligibility reads only caseType (Merger) and "
                            "caseNotificationDate, both fixed at registration. "
                            "Label-maturity censoring excludes cases whose label "
                            "cannot be observed at fetch time (no opener, no "
                            "terminal decision) and counts them per split and "
                            "per notification year in summary.json as "
                            "pending_censored; it never decides another row's "
                            "membership and never conditions on the label.",
            },
            "limitations": [
                "No historical vintages of the register exist; this is a "
                "retrospective research dataset over a current snapshot, not a "
                "certified historical forecasting setup.",
                "Sector taxonomy labels are current-vintage NACE Rev 2 applied "
                "across all eras; the underlying industries are "
                "notification-time facts (fixture-verified for M.4731 and "
                "M.877).",
                "Positives cluster by enforcement era and sector waves beyond "
                "the day-level event key; per-notification-year counts are "
                "reported beside every score.",
                "79/10,123 cases (discovery snapshot) carry no sectors; the "
                "NONE bucket is a real category, not missing data to impute.",
                "The ever-adopted label keeps M.10188 positive despite its "
                "2024-09-06 post-ECJ withdrawal of the opener.",
                "M.3333 stays positive through its 2007-03-01 "
                "post-re-notification opener; its 2004-02-12 opener from the "
                "annulled procedure is excluded as a label basis by rule.",
                "Pending-censored cases (register record establishes neither "
                "an opener nor a terminal decision) include live recent "
                "filings and old incomplete entries; their labels are "
                "unobserved, not negative, and their counts are reported "
                "per split and year.",
                "Recent-year positives reflect still-maturing procedures; the "
                "holdout window extends to the fetch snapshot.",
                "The discovery probe's division-conditional rates were grouped "
                "on the last component of the register's internal sector code, "
                "a malformed key; this build re-measures division-conditional "
                "rates from label-derived divisions (summary.json) and the "
                "sector-conditional reference in score.py uses the corrected "
                "grouping.",
            ],
            "cross_row_audit": {
                "probes": [
                    {"name": "unique_case_numbers",
                     "entity_columns": ["case_number"],
                     "time_column": "notification_date",
                     "operation": "copy", "left": "has_sectors",
                     "offset_days": 365,
                     "expectation": "case_number is unique per row, so no donor "
                                    "row can exist; any coverage would be a "
                                    "construction defect"},
                    {"name": "repeat_party_titles",
                     "entity_columns": ["case_title"],
                     "time_column": "notification_date",
                     "operation": "copy", "left": "has_sectors",
                     "offset_days": 365,
                     "expectation": "repeat acquirers exist in the register, but "
                                    "no shipped feature is constructed from "
                                    "another row; coverage would measure whether "
                                    "an exact-year same-title donor exists"},
                ],
                "rationale": "rows are unique notified cases; every feature is "
                             "a same-row attribute fixed at registration, so no "
                             "outcome-bearing cross-row exposure is constructed. "
                             "The probes measure that claim from the artifact "
                             "itself.",
                "auxiliary_files_review": "the artifact ships exactly the runner "
                                          "layout - public/train.csv, "
                                          "public/eval.csv, private/holdout.csv, "
                                          "meta.json, quality.json; no joint "
                                          "label matrices or other solver-visible "
                                          "files exist in the dataset directory",
            },
        },
        "source_snapshot": fetch_info,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    # ---- summary.json (construction diagnostics; no performance numbers) --
    summary = {
        "name": NAME,
        "stage": "construction (no performance metric computed anywhere here)",
        "fetch": fetch_info,
        "eligible_cases": eligible,
        "shipped_rows": len(rows),
        "excluded_cases": dict(sorted(exclusions.items())),
        "phase2_positives": positives,
        "label_rule": "Art. 6(1)(c) decision adopted on/after notification, "
                      "'Withdrawal of Art. 6(1)(c)' decisions excluded; "
                      "ever-adopted (later withdrawal does not undo the opener)",
        "split_stats": stats,
        "positive_events": positive_events,
        "pending_censored": {"by_split": pending_by_split,
                             "by_notification_year": dict(sorted(pending_by_year.items()))},
        "pre_notification_opener_cases": sorted(pre_notif_opener_cases),
        "art8_without_opener_anomalies": art8_without_opener,
        "missing_sector_cases": missing_sector,
        "fixtures": fixture_results,
        "decision_type_inventory": dict(sorted(decision_type_inventory.items(),
                                               key=lambda kv: -kv[1])),
        "sector_division_inventory_top15": top_divisions,
        "sector_division_levels": len(division_inventory),
        "per_notification_year": dict(sorted(per_year.items())),
        "cross_check": {
            "recorded_on": CROSS_CHECK["recorded_on"],
            "bands": {k: v for k, v in CROSS_CHECK.items() if k != "recorded_on"},
            "measured": {
                "eligible_cases": eligible,
                "shipped_rows": len(rows),
                "phase2_positives": positives,
                "split_positives": {s: stats[s]["positives"] for s in LAYOUT},
                "missing_sector_cases": missing_sector,
                "pending_censored": pending_by_split,
            },
            "delta_note": "the live snapshot rotates daily; the record's counts "
                          "were measured on 2026-10-24 (sha 061027db...) and "
                          "this fetch is recorded in fetch. The record's "
                          "'10,123 eligible' counts notified Merger cases "
                          "before censoring; shipped_rows = eligible minus "
                          "pending-censored cases whose register record does "
                          "not establish the label (mostly live 2020s filings "
                          "plus old entries with only partial referrals or no "
                          "decisions). M.3333 stays positive: its label rests "
                          "on the 2007-03-01 post-notification opener, not the "
                          "excluded 2004-02-12 one.",
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({"split_stats": stats,
                      "positives": positives,
                      "pending_censored": pending_by_split,
                      "fixtures": [f["case"] for f in fixture_results],
                      "top_divisions": top_divisions}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as error:
        print(f"BUILD FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
