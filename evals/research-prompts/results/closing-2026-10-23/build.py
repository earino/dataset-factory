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
* Label: from the award-side releases. Positive = every award entry is
  `unsuccessful` (the OCDS encoding of desierta). Negative = at least one
  `active` award. Processes whose award is `cancelled` (revocada) are excluded
  from the scored population; processes with no award release at all are
  `unobserved_target` and excluded. Both exclusions are counted per split and
  reported in summary.json and the candidate notes - they are missing outcome
  data, not a membership decision.
* Splits: temporal by publication month - train 2016-05..2016-06,
  eval 2019-05..2019-06, holdout 2021-01..2021-02. Each month's zip vintage
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
from datetime import date, datetime, timezone
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


def label_from(record: dict) -> tuple[int | None, str, str]:
    """Return (label, award_status, award_status_details).

    label: 1 deserted, 0 adjudicated, None when the outcome is cancelled or
    unobserved. Reads award-side releases only - never used for features.
    """
    award_releases = [r for r in (record.get("releases") or [])
                      if "award" in (r.get("tag") or []) and r.get("date")]
    award_releases.sort(key=lambda r: r["date"])
    entries: list[dict] = []
    for release in award_releases:
        entries.extend(release.get("awards") or [])
    if not entries:
        compiled = (record.get("compiledRelease") or {}).get("awards") or []
        entries.extend(compiled)
    if not entries:
        return None, "none", ""
    statuses = [(entry.get("status") or "").strip().lower() for entry in entries]
    details = ";".join(sorted({str(entry.get("statusDetails") or "") for entry in entries
                               if entry.get("statusDetails")}))
    observed = sorted(set(statuses))
    if "active" in statuses:
        return 0, "active", details
    if statuses and all(status == "unsuccessful" for status in statuses):
        return 1, "unsuccessful", details
    if statuses and all(status == "cancelled" for status in statuses):
        return None, "cancelled", details
    return None, "|".join(observed) or "unknown", details


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

    label, award_status, award_details = label_from(record)
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
    row["_award_status"] = award_status
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
                    status = row.pop("_award_status")
                    details = row.pop("_award_details")
                    row.pop("_split", None)
                    final_status = ((record.get("compiledRelease") or {}).get("tender") or {}).get("status")
                    if status == "unsuccessful" and final_status not in (None, "unsuccessful", "complete"):
                        tender_status_disagreement[f"{status}->{final_status}"] += 1
                    if row[TARGET] == "":
                        buckets[split][f"unobserved:{status}"] += 1
                        continue
                    if ocid in seen:
                        buckets[split]["duplicate_ocid"] += 1
                        continue
                    seen[ocid] = split
                    buckets[split][f"label:{status}"] += 1
                    rows_by_split[split].append(row)

    stats = {}
    for split, rel in LAYOUT.items():
        stats[split] = write_split(out, rel, rows_by_split[split])
        log(f"{split}: {stats[split]}")

    summary = {
        "name": NAME,
        "built_at_utc": built_at,
        "sources": sources,
        "grain": "one row per OCDS record (ocid) whose first tender release falls in the cohort month",
        "splits": stats,
        "cohorts": {split: [f"{y}-{m:02d}" for y, m in months]
                    for split, (months, _s, _e) in COHORTS.items()},
        "buckets": {split: dict(counter) for split, counter in buckets.items()},
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
        "label_rule": "deserted=1 iff every award entry is 'unsuccessful'; "
                      "adjudicated=0 iff any award entry is 'active'; cancelled and "
                      "processes without an award release are excluded as unobserved",
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
                                      "(cohort months 2016-05..2016-06, "
                                      "2019-05..2019-06, 2021-01..2021-02)",
                "fields": ["first tender release date", "ocid"],
                "basis": "membership is decided by the first tender release's month "
                         "only; the award release is read afterwards solely to compute "
                         "the label, and a process without an outcome is counted as "
                         "unobserved_target rather than dropped on a future condition",
            },
            "observations": [],
            "observations_note": "administrative record written by the platform at "
                                 "publication, so no statistical-release lag applies; "
                                 "each month's zip vintage (blob Last-Modified) and the "
                                 "latest release date seen inside it are recorded in "
                                 "summary.json so the observation window behind each "
                                 "label is visible",
        },
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
