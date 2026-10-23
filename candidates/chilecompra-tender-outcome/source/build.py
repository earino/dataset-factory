#!/usr/bin/env python3
"""Construction script for the `chilecompra-tender-outcome` candidate.

Task: a Chilean public-sector tender (licitacion) is published on Mercado
Publico. At that instant, given only publication-time context - the buying
unit's region, the item list with UNSPSC categories and quantities, the
estimated value and currency, the procedure type, the tender period and the
publication calendar position - will the process end DESERTED (desierta: no
valid bids, Ley 19.886 art. 3 or 9) rather than adjudicated?

Where this runs
---------------
On a temporary worker. The construction channel is the publisher's monthly OCDS
bulk zips (https://ocds.blob.core.windows.net/ocds/yyyymm.zip, anonymous Azure
blob, one JSON record package per process, entries STORED so the central
directory is readable by ranged GET - measured 2026-10-23). Each zip is
downloaded, stream-parsed member by member, the row extracted, and the zip
deleted before the next month, so peak disk holds one month at a time.

`--members-dir` reads already-saved member documents from a directory instead
of the network (a bounded parse exercise for a tiny fixture; `--smoke` relaxes
the capacity assertions such a fixture cannot carry).

Frame rules (each is measured and reported, never assumed)
----------------------------------------------------------
* Grain: one row per tender (OCDS record, ocid). Row key `tender_id`.
* Population: records whose FIRST tender release falls inside a cohort month.
  Membership is decided by the publication timestamp only - no later field is
  read to decide whether a row exists. The record package's own `publishedDate`
  is later than the first release and is not used.
* Prediction instant: the timestamp of the first `tender` release - the instant
  the platform publishes the process. Every shipped feature is taken from THAT
  release; later `tenderUpdate` releases (which carry the closing act and the
  final status) are never read for features.
* Label: the terminal award state within HORIZON_DAYS (180) of publication,
  read from award-side releases only. Award releases dated inside the horizon
  are walked in date order and the LAST release carrying a terminal status
  decides: any `active` entry -> adjudicated (0); all entries `unsuccessful`
  -> deserted (1, the OCDS encoding of desierta); all `cancelled` -> revoked
  (a terminal state that is neither class). Revoked rows, rows with only
  pending entries, and rows with no award release inside the horizon are
  excluded from the scored files and counted per split (outcome:revoked,
  unobserved_target:*) - right-censored or other-outcome data, never a
  membership decision. The horizon is uniform across splits and covered by
  every cohort zip's vintage (measured: rows published up to 2021-06-30 need
  award data to 2021-12-27; the 2021 zips' latest release is 2021-12-30).
* Splits: temporal by publication month - train 2019-05..2019-06,
  eval 2020-05..2020-06, holdout 2021-05..2021-06. Each month's zip vintage
  (blob Last-Modified, recorded by HEAD) is reported so the observation window
  behind each label is visible.
* Leakage discipline: tender.status / statusDetails, awards, bids,
  numberOfTenderers, contract fields, award dates and every release after the
  first tender release are excluded from the shipped columns and asserted
  absent from each written CSV header.

Runner contract: public/train.csv, public/eval.csv, private/holdout.csv,
meta.json, quality.json - the layout `skills/dataset-qualification/` gates.

Licence: CC0-1.0, recorded inside every record package (`license` field,
measured 2026-10-23) and by the OCP publication registry; publisher's open-data
terms contemplate reuse. Our derived compilation is dedicated CC0-1.0; this is
a derived research dataset, never ChileCompra's official product.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NAME = "chilecompra-tender-outcome"
TARGET = "deserted"
POSITIVE_LABEL = 1
TENDER_ID = "tender_id"
PUB_DATE = "pub_date"

BASE = "https://ocds.blob.core.windows.net/ocds/{ym}.zip"
UA = "dataset-factory-scout/1.0 (+https://github.com/earino/dataset-factory)"

# split -> ([(year, month), ...], window start, window end)
COHORTS = {
    "train": ([(2019, 5), (2019, 6)], "2019-05-01", "2019-07-01"),
    "eval": ([(2020, 5), (2020, 6)], "2020-05-01", "2020-07-01"),
    "holdout": ([(2021, 5), (2021, 6)], "2021-05-01", "2021-07-01"),
}
# Uniform label horizon: the terminal award state must be observable within
# this many days of publication. Chosen from measured evidence, frozen before
# any scoring: publisher records show first-award-release lags of p50 33-41
# days and p90 <= 102 days (probe_horizon.py, 2026-10-23, n=119 processes
# across the three cohort months), and every cohort zip's vintage covers
# publication + 180 days for every row (train vintage 2021-01-13, eval
# 2021-01-14, holdout latest release 2021-12-30 vs 2021-06-30 + 180d =
# 2021-12-27). A longer horizon would NOT be covered for holdout rows
# published at the end of June 2021, so 180 is the maximum uniform horizon
# the source supports.
HORIZON_DAYS = 180
TERMINAL_STATUSES = ("active", "unsuccessful", "cancelled")
LAYOUT = {"train": "public/train.csv", "eval": "public/eval.csv",
          "holdout": "private/holdout.csv"}

ID_COLUMNS = [TENDER_ID]
CARRY_COLUMNS = [PUB_DATE]
# Columns that carry the answer or the future and must never be shipped.
LABEL_SOURCE_COLUMNS = ["award_status", "award_status_details", "tender_final_status"]
POST_HOC_COLUMNS = ["award_date", "award_value", "supplier_rut", "bid_count",
                    "number_of_tenderers", "contract_status", "closing_date"]

FEATURES = [
    "buyer_region", "procedure_code", "procedure_detail", "procurement_method",
    "item_count", "unspsc_distinct", "unspsc_segment", "quantity_sum",
    "has_quantity", "estimated_value_clp", "value_currency", "value_missing",
    "tender_period_days", "title_chars", "title_words", "description_chars",
    "pub_month", "pub_week", "pub_dow", "pub_dom",
]
COLUMNS = [TENDER_ID, TARGET] + CARRY_COLUMNS + FEATURES

# Declared, not mistaken for leaks: pub_date is the time/event key (a per-value
# AUC on it would measure memorisation of the calendar) and estimated_value_clp
# is a continuous monetary feature whose per-value AUC would do the same.
HIGH_CARDINALITY = [PUB_DATE, "estimated_value_clp"]

PROCEDURE_CODES = ("L1", "LE", "LP", "LQ", "LR", "E2", "CO", "B2", "H2", "I2", "LS")
CODE_RE = re.compile(r"\(?\b(" + "|".join(PROCEDURE_CODES) + r")\b\)?")

PREDICTION_QUESTION = (
    "A Chilean public-sector tender is published on Mercado Publico. At the "
    "publication instant, given only publication-time context (buyer region, "
    "item list with UNSPSC categories and quantities, estimated value and "
    "currency, procedure type, tender period, calendar position), will the "
    "process end deserted (desierta) rather than adjudicated?")

PREDICTION_TIME = (
    "the timestamp of the first OCDS `tender` release for the process - the "
    "instant the platform publishes it. Later tenderUpdate releases, the "
    "award releases and every contract field are excluded from shipped "
    "features; award-side status is the label source.")


def log(message: str) -> None:
    print(f"[build] {message}", flush=True)


def head(url: str) -> tuple[int, str | None]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as response:
        return int(response.headers["Content-Length"]), response.headers.get("Last-Modified")


def fetch(url: str, path: Path) -> tuple[int, str, str]:
    """Stream a URL to disk; return (bytes, sha256, last-modified)."""
    digest = hashlib.sha256()
    total = 0
    started = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as response, path.open("wb") as handle:
        modified = response.headers.get("Last-Modified")
        while True:
            chunk = response.read(4 * 1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            total += len(chunk)
    log(f"  downloaded {path.name}: {total:,} B in {time.time() - started:.1f}s")
    return total, digest.hexdigest(), modified or ""


def week_of_year(when: date) -> int:
    return when.isocalendar()[1]


def parse_instant(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def vintage_observations(sources: dict) -> list[dict]:
    """Turn the measured zip vintages into timing observations.

    Each observation records when the monthly blob that carries a cohort's
    label window was last modified: the published date of the LABEL channel,
    not of the features (those are administrative records written at the
    publication instant itself). Measured blob Last-Modified values, not an
    assumed schedule.
    """
    out: list[dict] = []
    for ym in sorted(sources):
        modified = (sources[ym] or {}).get("last_modified") or ""
        try:
            published = parsedate_to_datetime(modified).date().isoformat()
        except (TypeError, ValueError):
            continue
        year, month = int(ym[:4]), int(ym[4:])
        period_end = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        out.append({"period": f"{year}-{month:02d}", "period_end": period_end,
                    "published": published,
                    "channel": "monthly bulk zip blob Last-Modified (vintage of the "
                               "label window; the features are administrative records "
                               "written at publication)"})
    return out


def first_tender_release(record: dict) -> dict | None:
    releases = [r for r in (record.get("releases") or [])
                if "tender" in (r.get("tag") or []) and r.get("date")]
    if not releases:
        return None
    releases.sort(key=lambda r: r["date"])
    return releases[0]


def buyer_region(release: dict) -> str:
    buyer = release.get("buyer") or {}
    buyer_id = buyer.get("id")
    parties = release.get("parties") or []
    candidates = []
    for party in parties:
        roles = party.get("roles") or []
        if buyer_id and party.get("id") == buyer_id:
            candidates.insert(0, party)
        elif "buyer" in roles:
            candidates.append(party)
    for party in candidates:
        region = ((party.get("address") or {}).get("region") or "").strip()
        if region:
            return region
    region = ((buyer.get("address") or {}).get("region") or "").strip()
    return region or "UNKNOWN"


def procedure_fields(tender: dict) -> tuple[str, str]:
    detail = (tender.get("procurementMethodDetails") or "").strip()
    match = CODE_RE.search(detail)
    code = match.group(1) if match else "UNK"
    detail_norm = re.sub(r"\s+", " ", detail)[:120] or "UNK"
    return code, detail_norm


def numeric(value) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out


def terminal_outcome(record: dict, published: datetime) -> tuple[int | None, str, str]:
    """Reduce the award side to ONE terminal state within the horizon.

    Returns (label, outcome_key, award_status_details): label is 1 deserted,
    0 adjudicated, or None when the process has no terminal adjudicated or
    deserted state within HORIZON_DAYS of publication. Reads award-side
    releases only - never used for features.

    Rule (defined, not pooled): walk the award releases dated inside
    pub+HORIZON in date order; the LAST release that carries a terminal
    status decides the outcome - a `pending`-only release never decides, and a
    later terminal release supersedes an earlier one. Within that deciding
    release: any `active` entry -> adjudicated; all entries `unsuccessful` ->
    deserted; all `cancelled` -> revoked (terminal, neither class); anything
    else -> mixed. A process with no award release inside the horizon is
    right-censored at the horizon; late-only awards, undated-only awards and
    compiled-only awards are counted in distinct censored buckets so the old
    artifact's label sources are measurable. The compiledRelease fallback the
    previous build used is deliberately NOT used for labels: a compiled award
    cannot always be dated into the horizon, and the impact of dropping it is
    measured by the compiled_only bucket instead of being assumed away.
    """
    cutoff = published + timedelta(days=HORIZON_DAYS)
    # Award-side releases are every release tagged with an OCDS award-prefixed
    # tag: `award`, `awardUpdate`, `awardCancellation`. The previous build
    # filtered on the exact tag `award` and so silently ignored update-only
    # releases - the defect that made "later state supersedes earlier"
    # unmeasurable. `contractTermination` etc. do not match the prefix.
    award_releases = [r for r in (record.get("releases") or [])
                      if any(str(tag).startswith("award")
                             for tag in (r.get("tag") or [])) and r.get("date")]
    dated: list[tuple[datetime, list[dict]]] = []
    unparseable = 0
    for release in award_releases:
        stamp = parse_instant(release["date"])
        if stamp is None:
            unparseable += 1
            continue
        dated.append((stamp, release.get("awards") or []))
    dated.sort(key=lambda pair: pair[0])
    within = [pair for pair in dated if pair[0] <= cutoff]
    if not within:
        if any(stamp > cutoff for stamp, _entries in dated):
            return None, "unobserved_target:award_beyond_horizon", ""
        if award_releases:
            return None, "unobserved_target:award_date_unparseable", ""
        compiled = (record.get("compiledRelease") or {}).get("awards") or []
        if compiled:
            return None, "unobserved_target:compiled_only_awards", ""
        return None, "unobserved_target:no_award_within_horizon", ""
    details = ""
    decided: tuple[int | None, str] | None = None
    for _stamp, release_entries in within:
        statuses = [(entry.get("status") or "").strip().lower()
                    for entry in release_entries]
        if not statuses or not any(status in TERMINAL_STATUSES for status in statuses):
            continue
        if "active" in statuses:
            decided = (0, "outcome:adjudicated")
        elif all(status == "unsuccessful" for status in statuses):
            decided = (1, "outcome:deserted")
        elif all(status == "cancelled" for status in statuses):
            decided = (None, "outcome:revoked")
        else:
            decided = (None, "outcome:mixed_terminal")
        details = ";".join(sorted({str(entry.get("statusDetails") or "")
                                   for entry in release_entries
                                   if entry.get("statusDetails")}))
    if decided is None:
        return None, "unobserved_target:pending_within_horizon", details
    label, key = decided
    if unparseable and label is not None:
        key += "+undated_release"
    return label, key, details


def extract(record: dict, split: str, month: str) -> tuple[dict | None, str]:
    """Build one row, or return (None, reason)."""
    ocid = record.get("ocid")
    first = first_tender_release(record)
    if not first or not ocid:
        return None, "no_tender_release"
    published = parse_instant(first.get("date"))
    if published is None:
        return None, "unparseable_publication_date"
    if published.strftime("%Y-%m") != month:
        return None, "publication_month_outside_cohort"
    tender = first.get("tender") or {}
    # The publication state must be evidenced, not assumed: a release written at
    # publication carries status "active". The 2016 bulk zips were rebuilt at
    # migration (blob vintage 2020-03, single release stamped 2018-12-31, status
    # "complete" and the final text) - those rows are excluded rather than
    # presented as publication-time features. Measured 2026-10-23.
    if (tender.get("status") or "").strip().lower() != "active":
        return None, "publication_state_not_evidenced"
    items = tender.get("items") or []
    segments = Counter()
    quantity = 0.0
    has_quantity = 0
    unspsc = set()
    for item in items:
        classification = item.get("classification") or {}
        code = str(classification.get("id") or "")
        if code:
            unspsc.add(code)
            segments[code[:2]] += 1
        qty = numeric(item.get("quantity"))
        if qty is not None:
            quantity += qty
            has_quantity = 1
    value = tender.get("value") or {}
    amount = numeric(value.get("amount"))
    currency = (value.get("currency") or "").strip().upper()
    value_clp = amount if (amount is not None and currency == "CLP") else None
    period = tender.get("tenderPeriod") or {}
    days = numeric(period.get("durationInDays"))
    if days is None:
        start, end = parse_instant(period.get("startDate")), parse_instant(period.get("endDate"))
        if start and end:
            days = (end - start).total_seconds() / 86400.0
    title = (tender.get("title") or "").strip()
    description = (tender.get("description") or "").strip()
    code, detail = procedure_fields(tender)

    label, outcome_key, award_details = terminal_outcome(record, published)
    row = {
        TENDER_ID: ocid,
        TARGET: "" if label is None else label,
        PUB_DATE: published.astimezone(timezone.utc).strftime("%Y-%m-%d"),
        "buyer_region": buyer_region(first),
        "procedure_code": code,
        "procedure_detail": detail,
        "procurement_method": (tender.get("procurementMethod") or "UNKNOWN").strip() or "UNKNOWN",
        "item_count": len(items),
        "unspsc_distinct": len(unspsc),
        "unspsc_segment": segments.most_common(1)[0][0] if segments else "UNK",
        "quantity_sum": round(quantity, 3),
        "has_quantity": has_quantity,
        "estimated_value_clp": "" if value_clp is None else round(value_clp, 2),
        "value_currency": currency or "UNK",
        "value_missing": 1 if value_clp is None else 0,
        "tender_period_days": "" if days is None else round(days, 2),
        "title_chars": len(title),
        "title_words": len(title.split()),
        "description_chars": len(description),
        "pub_month": published.month,
        "pub_week": week_of_year(published.date()),
        "pub_dow": published.weekday(),
        "pub_dom": published.day,
    }
    row["_outcome_key"] = outcome_key
    row["_award_details"] = award_details
    row["_split"] = split
    return row, "ok"


def write_split(out: Path, rel: str, rows: list[dict]) -> dict:
    path = out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in COLUMNS})
    positives = sum(1 for row in rows if row[TARGET] == POSITIVE_LABEL)
    days = {row[PUB_DATE] for row in rows if row[TARGET] == POSITIVE_LABEL}
    return {"rows": len(rows), "positives": positives,
            "positive_rate": round(positives / len(rows), 6) if rows else None,
            "distinct_positive_days": len(days)}


def iter_members(path: Path):
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.filename.lower().endswith(".json"):
                continue
            with archive.open(info) as handle:
                yield info.filename, json.loads(handle.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", default="/tmp/cl")
    parser.add_argument("--members-dir", default=None,
                        help="read saved member JSON documents instead of downloading")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--built-at", default=None)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    built_at = args.built_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    rows_by_split: dict[str, list[dict]] = {key: [] for key in COHORTS}
    sources: dict[str, dict] = {}
    buckets: dict[str, Counter] = {key: Counter() for key in COHORTS}
    eligible: dict[str, int] = {key: 0 for key in COHORTS}
    seen: dict[str, str] = {}
    max_release: dict[str, str] = {}
    tender_status_disagreement = Counter()

    for split, (months, _start, _end) in COHORTS.items():
        for year, month in months:
            ym = f"{year}{month:02d}"
            members: list[tuple[str, dict]] = []
            if args.members_dir:
                for path in sorted(Path(args.members_dir).glob("*.json")):
                    members.append((path.name, json.loads(path.read_text(encoding="utf-8"))))
                log(f"{split} {ym}: {len(members)} saved members from {args.members_dir}")
            else:
                url = BASE.format(ym=ym)
                size, modified = head(url)
                log(f"{split} {ym}: {size:,} B vintage={modified}")
                zpath = work / f"{ym}.zip"
                got, digest, modified = fetch(url, zpath)
                sources[ym] = {"url": url, "bytes": got, "sha256": digest,
                               "last_modified": modified}
                started = time.time()
                try:
                    for name, doc in iter_members(zpath):
                        members.append((name, doc))
                finally:
                    zpath.unlink(missing_ok=True)
                log(f"{split} {ym}: parsed {len(members)} members in {time.time() - started:.1f}s")

            for name, doc in members:
                for record in (doc.get("records") or []):
                    ocid = record.get("ocid") or name
                    for release in (record.get("releases") or []):
                        stamp = release.get("date") or ""
                        if stamp > max_release.get(split, ""):
                            max_release[split] = stamp
                    row, reason = extract(record, split, f"{ym[:4]}-{ym[4:]}")
                    if row is None:
                        buckets[split][reason] += 1
                        continue
                    eligible[split] += 1
                    outcome_key = row.pop("_outcome_key")
                    row.pop("_award_details", None)
                    row.pop("_split", None)
                    final_status = ((record.get("compiledRelease") or {}).get("tender") or {}).get("status")
                    if outcome_key == "outcome:deserted" and \
                            final_status not in (None, "unsuccessful", "complete"):
                        tender_status_disagreement[f"unsuccessful->{final_status}"] += 1
                    if row[TARGET] == "":
                        buckets[split][outcome_key] += 1
                        continue
                    if ocid in seen:
                        buckets[split]["duplicate_ocid"] += 1
                        continue
                    seen[ocid] = split
                    buckets[split][outcome_key] += 1
                    rows_by_split[split].append(row)

    stats = {}
    for split, rel in LAYOUT.items():
        stats[split] = write_split(out, rel, rows_by_split[split])
        log(f"{split}: {stats[split]}")

    outcome_accounting = {}
    for split, counter in buckets.items():
        revoked = counter.get("outcome:revoked", 0)
        mixed = counter.get("outcome:mixed_terminal", 0)
        duplicates = counter.get("duplicate_ocid", 0)
        censored_detail = {key: value for key, value in counter.items()
                           if key.startswith("unobserved_target:")}
        censored = sum(censored_detail.values())
        base = eligible[split] or 1
        outcome_accounting[split] = {
            "eligible_rows": eligible[split],
            "scored_rows": stats[split]["rows"],
            "positives": stats[split]["positives"],
            "revoked": revoked,
            "mixed_terminal": mixed,
            "duplicate_ocid": duplicates,
            "censored": censored,
            "revoked_rate": round(revoked / base, 6),
            "censored_rate": round(censored / base, 6),
            "scored_share": round(stats[split]["rows"] / base, 6),
            "censored_detail": censored_detail,
        }

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "horizon_days": HORIZON_DAYS,
        "sources": sources,
        "grain": "one row per OCDS record (ocid) whose first tender release falls in the cohort month",
        "splits": stats,
        "cohorts": {split: [f"{y}-{m:02d}" for y, m in months]
                    for split, (months, _s, _e) in COHORTS.items()},
        "buckets": {split: dict(counter) for split, counter in buckets.items()},
        "outcome_accounting": outcome_accounting,
        "max_release_date_seen": max_release,
        "tender_final_status_disagreements": dict(tender_status_disagreement),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")

    if not args.smoke:
        problems = []
        for split in ("train", "eval", "holdout"):
            if stats[split]["rows"] == 0:
                problems.append(f"{split} has no rows")
        for split in ("eval", "holdout"):
            if stats[split]["positives"] < 30:
                problems.append(f"{split} has {stats[split]['positives']} positives (<30)")
            if stats[split]["distinct_positive_days"] < 20:
                problems.append(f"{split} has {stats[split]['distinct_positive_days']} "
                                f"positive days (<20)")
        if problems:
            log("FAIL: " + "; ".join(problems))
            return 2

    observed_now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = {
        "name": NAME,
        "description": PREDICTION_QUESTION,
        "source": "ChileCompra / Mercado Publico OCDS monthly bulk zips",
        "source_urls": [BASE.format(ym=f"{y}{m:02d}")
                        for _s, (months, _a, _b) in COHORTS.items() for y, m in months],
        "license": "CC0-1.0 (each record package states "
                   "https://creativecommons.org/publicdomain/zero/1.0/; our derived "
                   "compilation also CC0-1.0). Derived research dataset - not "
                   "ChileCompra's official product.",
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {split: stats[split]["rows"] for split in LAYOUT},
        "positive_rate": {split: stats[split]["positive_rate"] for split in LAYOUT},
        "split": {"strategy": "temporal by tender publication month",
                  "boundaries": {split: f"{start} .. {end}"
                                 for split, (_m, start, end) in COHORTS.items()}},
        "label_rule": "terminal award state within 180 days of publication: award "
                      "releases dated inside pub+180d are walked in date order and "
                      "the last release carrying a terminal status decides - any "
                      "'active' entry -> adjudicated=0, all 'unsuccessful' -> "
                      "deserted=1, all 'cancelled' -> revoked (excluded from scored "
                      "rows, counted); only pending entries or no award release "
                      "inside the horizon -> right-censored (excluded, counted)",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "prediction_time": PREDICTION_TIME,
        "features": FEATURES,
        "built_at_utc": built_at,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    quality = {
        "name": NAME,
        "task": {"question": PREDICTION_QUESTION, "prediction_time": PREDICTION_TIME},
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "time_column": PUB_DATE,
        "event_key_column": PUB_DATE,
        "event_key_note": "the gate reads the first ten characters of the event key "
                          "as its independence unit; tender_id is unique per row, so "
                          "the conservative clustered unit shipped here is the "
                          "publication DAY (tenders published the same day share "
                          "market conditions). tender_id remains the row key.",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "feature_documentation": (
            "every shipped field is taken from the first OCDS `tender` release of the "
            "process (the publication instant): buyer_region from the buyer party's "
            "address.region; procedure_code/procedure_detail from "
            "tender.procurementMethodDetails (the publisher's L1/LE/LP/LQ/LR/E2/CO/B2/"
            "H2/I2/LS code table, licence-code UNK when absent); procurement_method from "
            "tender.procurementMethod; item_count/unspsc_*/quantity_* aggregated from "
            "tender.items[].classification (UNSPSC) and quantity; estimated_value_clp "
            "from tender.value.amount only when currency is CLP (other currencies ship "
            "empty plus value_currency, so no mixed-unit column exists); "
            "tender_period_days from tender.tenderPeriod.durationInDays (computed from "
            "the period dates when absent); title_chars/title_words/description_chars "
            "are lengths of tender.title/description; pub_* are calendar fields of the "
            "publication timestamp. Field meanings come from the OCDS 1.1 standard and "
            "the publisher's Licitaciones field dictionary (recorded in the candidate "
            "record)."),
        "carry_columns": CARRY_COLUMNS,
        "id_columns": ID_COLUMNS,
        "high_cardinality_columns": HIGH_CARDINALITY,
        "high_cardinality_note": "pub_date is the publication day (time column and "
                                 "clustered event key), estimated_value_clp is a "
                                 "continuous monetary feature; both reach a high "
                                 "level count by construction, so they are declared "
                                 "here instead of being scored as candidate leaks. "
                                 "Every other shipped column is scored single-column "
                                 "against the target by the gate.",
        "label_source_columns": LABEL_SOURCE_COLUMNS,
        "post_hoc_columns": POST_HOC_COLUMNS,
        "measurements": [
            {"column": "estimated_value_clp",
             "unit": "Chilean pesos (CLP), nominal",
             "frame": "tender.value.amount with tender.value.currency == 'CLP'; amounts "
                      "in any other currency (UTM/USD) are left empty and flagged in "
                      "value_missing so no mixed-unit column is shipped"},
            {"column": "quantity_sum",
             "unit": "sum of the item quantities in the units the publisher states per "
                     "item (mixed item units)",
             "frame": "tender.items[].quantity summed; has_quantity records whether any "
                      "item carried a numeric quantity, so a zero is not read as missing"},
            {"column": "tender_period_days",
             "unit": "days between tenderPeriod.startDate and endDate",
             "frame": "publisher's durationInDays where present, otherwise computed from "
                      "the two timestamps in UTC"},
            {"column": "pub_date",
             "unit": "calendar date in UTC",
             "frame": "date part of the first tender release timestamp (the publication "
                      "instant); split windows are month boundaries in this frame"},
        ],
        "timing": {
            "prediction_instant": {
                "kind": "publication",
                "period": "instant",
                "days_after_period_end": 0,
                "citation": "timestamp of the first OCDS `tender` release for the "
                            "process, i.e. the moment the platform publishes the "
                            "tender (observed values shipped in pub_date; the record "
                            "package's publishedDate is later and unused)",
            },
            "features": {
                "period": "instant",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "the publication instant of the row itself "
                                      "(first tender release; cohort months "
                                      + "; ".join(
                                          f"{split} " + ", ".join(f"{y}-{m:02d}"
                                                                 for y, m in months)
                                          for split, (months, _s, _e)
                                          in COHORTS.items()) + ")",
                "fields": ["first tender release date", "ocid"],
                "basis": "MEMBERSHIP is decided by publication-time fields only: "
                         "the first tender release's month (the cohort windows) "
                         "plus its publication state ('active'); the award side is "
                         "never read to decide whether a row exists. The scored "
                         "CSVs are then the subset of those eligible rows whose "
                         f"award process reaches a terminal adjudicated or deserted "
                         f"state within {HORIZON_DAYS} days of publication. That "
                         "restriction is OUTCOME-DEPENDENT, and it is declared "
                         "here rather than presented as a timing-neutral filter: "
                         "rows whose terminal state is revoked, and rows "
                         "right-censored at the horizon (no award release inside "
                         "it, awards only after it, only pending entries, undated "
                         "or compiled-only awards), are excluded from the scored "
                         "files and counted per split in summary.json buckets and "
                         "the outcome_conditioning block. The rates in that block "
                         "must be quoted beside any score taken from this artifact.",
                "horizon_days": HORIZON_DAYS,
                "horizon_basis": "measured first-award-release lag p50 33-41 days, "
                                 "p90 <= 102 days (probe_horizon.py 2026-10-23, "
                                 "n=119 processes across the three cohort months); "
                                 "every cohort zip's vintage covers publication + "
                                 "180 days for every row (train vintage 2021-01-13, "
                                 "eval 2021-01-14, holdout latest release "
                                 "2021-12-30 vs 2021-06-30 + 180d = 2021-12-27), so "
                                 "180 is the maximum uniform horizon this source "
                                 "supports and no split's labels depend on data "
                                 "its zip vintage does not contain",
            },
            "observations": vintage_observations(sources),
            "observations_note": "features are administrative records written by the "
                                 "platform at the publication instant, so no "
                                 "statistical-release lag applies to them; the "
                                 "observations above record each cohort zip's "
                                 "measured blob Last-Modified - the vintage of the "
                                 "label window - and summary.json also records the "
                                 "latest release date seen inside each zip",
        },
        "horizon_days": HORIZON_DAYS,
        "outcome_conditioning": outcome_accounting,
        "outcome_conditioning_note": "scored rows are the eligible "
                                      "(publication-time membership) rows whose "
                                      "award process reaches a terminal "
                                      "adjudicated/deserted state within "
                                      f"{HORIZON_DAYS} days of publication; these "
                                      "measured rates quantify the "
                                      "outcome-dependent share excluded from each "
                                      "split (revoked, right-censored), from the "
                                      "same rows the gate reads",
        "split_windows": {split: {"start": start, "end": end}
                          for split, (_m, start, end) in COHORTS.items()},
        "split_boundaries": {split: f"tenders first published {start} .. {end}"
                             for split, (_m, start, end) in COHORTS.items()},
        "positive_events": {
            split: {"positives": stats[split]["positives"],
                    "distinct_events": stats[split]["distinct_positive_days"]}
            for split in ("eval", "holdout")},
        "positive_events_note": "distinct_events counts distinct publication days among "
                                "positive rows, the conservative independence unit "
                                "described in event_key_note",
        "expected_duplicate_ids": 0,
        "id_columns_are_entity_keys": True,
        "splits": LAYOUT,
        "built_at_utc": built_at,
        "shipped_columns": COLUMNS,
    }
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    headers_ok = True
    for split, rel in LAYOUT.items():
        with (out / rel).open(encoding="utf-8") as handle:
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
    log(json.dumps({"splits": stats, "buckets": {k: dict(v) for k, v in buckets.items()}},
                   indent=1))
    return 0 if headers_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
