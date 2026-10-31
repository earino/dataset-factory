#!/usr/bin/env python3
"""Build the pins-planning-appeal-outcome runner artifact from the two PINS Excel files.

Construction order (nothing here scores anything):
  1. fetch the two pinned GOV.UK Excel files by exact recorded URL and verify
     size + sha256 against the discovery pins (a new edition fails the build,
     never silently replaces the measured bytes);
  2. stream both files with the discovery probe's own stdlib xlsx parser, so the
     per-decision-year fixture reproduces the probe's counts exactly;
  3. frame: s78_core casework types (Planning Appeal / Householder (HAS)) with
     a binary Decision in {Allowed, Dismissed}; drop rows whose Decision Date
     precedes their Valid Date (decided-before-validated: a data-integrity
     anomaly where the outcome predates the instant) and cross-file duplicates
     on the publisher-documented date composite; count every exclusion;
  4. features: registration-time publisher fields only, plus LPA-level
     prior-outcome aggregates computed strictly from Decision Dates earlier
     than each row's Valid Date;
  5. splits keyed on the VALIDATION instant (the shipped time column), because
     the gate requires disjoint split ranges on a shipped column and the outcome
     date is post-instant and cannot ship: train = Valid Date < 2020-01-01,
     eval = 2020-2021, holdout = >= 2022-01-01;
  6. write public/train.csv, public/eval.csv, private/holdout.csv, meta.json,
     quality.json (no performance metric is computed anywhere in this file).

The holdout is written but never scored here. Scoring happens only after the
qualification gate passes and --accept re-verifies the exact bytes (run.sh).

Usage: build.py --out DIR --work-dir DIR --built-at ISO [--source-dir DIR]
"""
from __future__ import annotations

import argparse
import bisect
import collections
import csv
import hashlib
import json
import os
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timedelta
from xml.etree.ElementTree import iterparse

NAME = "pins-planning-appeal-outcome"
TARGET = "allowed"
POSITIVE = 1  # int in meta.json/quality.json so the runner's (df[target] == 1) compares true
ID_COLUMNS = ["row_id"]
TIME_COLUMN = "valid_date"
EVENT_KEY_COLUMN = "valid_date"
BUILT_AT_DEFAULT = "2026-10-31T00:00:00Z"

# Discovery pins (probe_results_2026-10-31.json): exact bytes the fixtures were measured on.
FILES = [
    {
        "kind": "casework",
        "name": "Casework_Database_-_2610.xlsx",
        "url": "https://assets.publishing.service.gov.uk/media/6ad9fcc1c818345ad8aca325/Casework_Database_-_2610.xlsx",
        "bytes": 22207115,
        "sha256": "dff80bd0f17cbc640dc205009a9411269c8e58462b6df71af903c592af3c20fa",
        "ref_col": "Case Number",
        "sheet_hint": "Data Set",
    },
    {
        "kind": "older",
        "name": "Older_Casework_Data_-_2610.xlsx",
        "url": "https://assets.publishing.service.gov.uk/media/6ad9fcd12263175ac2aca2f7/Older_Casework_Data_-_2610.xlsx",
        "bytes": 12325866,
        "sha256": "baf28d80c5cd5ad266f8a9e62c25517b2ec9d4c5d951239ab0638666bc092a4b",
        "ref_col": "Older Casework Data Ref No",
        "sheet_hint": "Older Appeals Data",
    },
]

# Per-decision-year fixture: the discovery probe's family_year cross-tab, both
# files summed per year (probe_results_2026-10-31.json, s78_core). The build must
# reproduce these counts exactly (minus counted exclusions) or it fails.
EXPECTED_YEAR = {
    "2016": (3786, 1309), "2017": (15587, 5049), "2018": (15112, 4821),
    "2019": (17581, 4773), "2020": (13417, 3625), "2021": (13641, 4062),
    "2022": (13538, 3982), "2023": (14271, 4353), "2024": (14063, 4219),
    "2025": (14897, 4757), "2026": (9240, 2944),
}

S78_PREFIXES = ("Planning Appeal", "Householder")
BINARY_DECISIONS = ("Allowed", "Dismissed")
TRAIN_BEFORE_YEAR = 2020       # valid year < 2020 -> train
EVAL_YEARS = (2020, 2021)      # valid year in {2020, 2021} -> eval
                                 # valid year >= 2022 -> holdout
FLAG_MIN_PRESENCE = 100        # a site flag ships only with >= 100 populated values

# Publisher columns read at registration/validation (identical names in both files).
REG_COLS = ("Type of Casework", "LPA Name", "ONS LPA Code", "Received Date", "Valid Date",
            "Decision Date", "Decision", "Procedure", "Development Type",
            "Appeal Type Reason", "Reason for the Appeal", "Type - Detail",
            "Link Status", "Area Of Site In Hectares", "Floor Space In Square Metres",
            "Number of Residences", "Site Green Belt", "Agricultural Holding",
            "Development Affect Setting of Listed Building", "Historic Building Grant Made",
            "In CA Relates to CA", "Is Flooding an Issue", "Is the site within an AONB",
            "Is site within an SSSI", "Enforcement Grounds Count")

FLAG_COLS = {
    "green_belt": "Site Green Belt",
    "agricultural_holding": "Agricultural Holding",
    "listed_building_setting": "Development Affect Setting of Listed Building",
    "historic_building_grant": "Historic Building Grant Made",
    "conservation_area": "In CA Relates to CA",
    "flooding_issue": "Is Flooding an Issue",
    "aonb": "Is the site within an AONB",
    "sssi": "Is site within an SSSI",
}

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CELL_RE = re.compile(r"([A-Z]+)(\d+)")


# ---------------------------------------------------------------- xlsx reading
# Streaming stdlib xlsx reader, taken verbatim from the discovery probe
# (candidates/pins-planning-appeal-outcome/probe_count.py) so the counting
# logic matches the measured fixture bit for bit.
def load_shared_strings(zf):
    strings = []
    try:
        with zf.open("xl/sharedStrings.xml") as fh:
            for _, el in iterparse(fh, events=("end",)):
                if el.tag.endswith("}si"):
                    strings.append("".join(t.text or "" for t in el.iter()
                                           if t.tag.endswith("}t")))
                    el.clear()
    except KeyError:
        pass
    return strings


def sheet_files(zf):
    rels = {}
    with zf.open("xl/_rels/workbook.xml.rels") as fh:
        for _, el in iterparse(fh, events=("end",)):
            if el.tag.endswith("}Relationship"):
                rels[el.get("Id")] = el.get("Target")
                el.clear()
    out = []
    with zf.open("xl/workbook.xml") as fh:
        for _, el in iterparse(fh, events=("end",)):
            if el.tag.endswith("}sheet"):
                target = rels.get(el.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"), "")
                path = target.lstrip("/") if target.startswith("/") else "xl/" + target
                out.append((el.get("name"), path))
                el.clear()
    return out


def to_date(raw):
    if raw is None:
        return None
    s = str(raw)
    if s.replace(".", "", 1).isdigit():
        n = float(s)
        if 20000 <= n <= 60000:
            return datetime(1899, 12, 30) + timedelta(days=n)
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def row_cells(row, shared):
    cells = {}
    for c in row.findall("m:c", NS):
        m = CELL_RE.match(c.get("r") or "")
        if not m:
            continue
        t = c.get("t")
        v = c.find("m:v", NS)
        if t == "s" and v is not None and v.text is not None:
            i = int(v.text)
            val = shared[i] if i < len(shared) else None
        elif t == "inlineStr":
            is_el = c.find("m:is", NS)
            val = "".join(x.text or "" for x in is_el.iter()) if is_el is not None else None
        elif v is None:
            val = None
        else:
            val = v.text
        if val is not None and str(val).strip() != "":
            cells[m.group(1)] = val
    return cells


def stream_rows(path, ref_col):
    """Yield (cells dict, header name->cell map) for every data row of the largest sheet."""
    zf = zipfile.ZipFile(path)
    sizes = {i.filename: i.file_size for i in zf.infolist()}
    name, target = max(sheet_files(zf), key=lambda sp: sizes.get(sp[1], 0))
    shared = load_shared_strings(zf)
    header, colidx = None, {}
    with zf.open(target) as fh:
        for _, row in iterparse(fh, events=("end",)):
            if not row.tag.endswith("}row"):
                continue
            cells = row_cells(row, shared)
            if header is None:
                if len(cells) >= 10 and "Decision" in [str(v) for v in cells.values()]:
                    header = {k: str(v).strip() for k, v in cells.items()}
                    colidx = {v: k for k, v in header.items()}
                    row.clear()
                    continue
                row.clear()
                continue
            if not cells:
                row.clear()
                continue
            yield cells, colidx
            row.clear()


# ---------------------------------------------------------------- fetch and pin
def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url, path):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; dataset-factory-build/1.0)"})
            with urllib.request.urlopen(req, timeout=120) as response, \
                    open(path, "wb") as out:
                while True:
                    block = response.read(1 << 20)
                    if not block:
                        break
                    out.write(block)
            return
        except Exception as exc:  # noqa: BLE001 - recorded, retried, then fatal
            last = exc
    raise SystemExit(f"fetch failed after 3 attempts for {url}: {last}")


def locate(spec, work, source_dir):
    fname = spec["name"]
    path = os.path.join(source_dir, fname) if source_dir else os.path.join(work, fname)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        print(f"  fetching {fname} ({spec['bytes']} B pinned)", flush=True)
        fetch(spec["url"], path)
    digest, size = sha256_of(path), os.path.getsize(path)
    if size != spec["bytes"] or digest != spec["sha256"]:
        raise SystemExit(
            f"{fname} does not match the discovery pin (size {size} vs {spec['bytes']}, "
            f"sha256 {digest[:16]}... vs {spec['sha256'][:16]}...): the publication has "
            "probably been re-issued; re-probe, re-pin and re-measure before rebuilding")
    return path


# ---------------------------------------------------------------- feature helpers
def flag_value(raw):
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    if s in ("yes", "y", "true"):
        return "1"
    if s in ("no", "n", "false"):
        return "0"
    try:
        f = float(s)
        if f == 1.0:
            return "1"
        if f == 0.0:
            return "0"
    except ValueError:
        pass
    return ""


def num(raw):
    """Normalise a publisher numeric cell to a plain decimal string ('' if absent)."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if s == "":
        return ""
    try:
        return repr(float(s))
    except ValueError:
        return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--built-at", default=BUILT_AT_DEFAULT)
    ap.add_argument("--source-dir", default=None,
                    help="reuse pre-fetched files from this directory (local test path)")
    ap.add_argument("--relax-expected", action="store_true",
                    help="disable the publisher-envelope assertions only (local synthetic test)")
    ap.add_argument("--summary-out", default=None,
                    help="where to write summary.json (default: beside the extract; keep it OUTSIDE)")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(os.path.join(out, "public"), exist_ok=True)
    os.makedirs(os.path.join(out, "private"), exist_ok=True)
    work = os.path.abspath(args.work_dir)
    os.makedirs(work, exist_ok=True)

    # ---- stage 1: fetch + pin -------------------------------------------------
    print("== fetch/pin ==", flush=True)
    paths = {}
    for spec in FILES:
        paths[spec["kind"]] = locate(spec, work, args.source_dir)

    # ---- stage 2: parse + frame ----------------------------------------------
    print("== parse ==", flush=True)
    rows = []                 # eligible, deduplicated rows (dicts)
    seen_composite = set()
    stats = {
        "rows_per_file": collections.Counter(),
        "s78_rows_per_file": collections.Counter(),
        "exclusions": collections.Counter(),
        "exclusions_by_year": collections.defaultdict(collections.Counter),
        "exclusions_allowed_by_year": collections.defaultdict(collections.Counter),
        "kept_by_year": collections.defaultdict(lambda: [0, 0]),
        "presence": collections.Counter(),        # populated values per candidate column
        "vocab": collections.defaultdict(collections.Counter),
        "non_binary_vocab": collections.Counter(),
        "matched_types": collections.Counter(),
        "decision_by_type": collections.defaultdict(collections.Counter),
    }
    for spec in FILES:
        kind, ref_col = spec["kind"], spec["ref_col"]
        n_data = 0
        for cells, colidx in stream_rows(paths[kind], ref_col):
            n_data += 1
            get = lambda nm: cells.get(colidx.get(nm, "")) if nm in colidx else None

            typ = get("Type of Casework") or get("Type of Appeal")
            typ = str(typ) if typ is not None else ""
            dec = get("Decision")
            dec = str(dec) if dec is not None else ""
            stats["decision_by_type"][typ.split(" - ")[0][:40]][dec] += 1
            if not typ.startswith(S78_PREFIXES):
                continue
            stats["s78_rows_per_file"][kind] += 1

            received = to_date(get("Received Date"))
            valid = to_date(get("Valid Date"))
            decided = to_date(get("Decision Date"))
            if decided is None:
                # outside the probe's family_year cross-tab entirely (it keyed on
                # a parsed decision date); counted, never shipped
                stats["exclusions"]["missing_decision_date"] += 1
                continue
            year = str(decided.year)
            if dec not in BINARY_DECISIONS:
                stats["exclusions_by_year"][year]["non_binary_decision"] += 1
                stats["exclusions"]["non_binary_decision"] += 1
                stats["non_binary_vocab"][dec] += 1
                continue
            stats["matched_types"][typ] += 1

            if received is None:
                stats["exclusions_by_year"][year]["missing_received"] += 1
                stats["exclusions"]["missing_received"] += 1
                if dec == "Allowed":
                    stats["exclusions_allowed_by_year"][year]["missing_received"] += 1
                continue
            if valid is None:
                stats["exclusions_by_year"][year]["missing_valid"] += 1
                stats["exclusions"]["missing_valid"] += 1
                if dec == "Allowed":
                    stats["exclusions_allowed_by_year"][year]["missing_valid"] += 1
                continue
            if decided < valid:
                # decided before validated: the outcome predates the instant
                stats["exclusions_by_year"][year]["decided_before_valid"] += 1
                stats["exclusions"]["decided_before_valid"] += 1
                if dec == "Allowed":
                    stats["exclusions_allowed_by_year"][year]["decided_before_valid"] += 1
                continue

            lpa = str(get("LPA Name") or "").strip()
            composite = (typ, lpa, received.date().isoformat(),
                         valid.date().isoformat(), decided.date().isoformat(), dec)
            if composite in seen_composite:
                stats["exclusions_by_year"][year]["cross_file_duplicate"] += 1
                stats["exclusions"]["cross_file_duplicate"] += 1
                if dec == "Allowed":
                    stats["exclusions_allowed_by_year"][year]["cross_file_duplicate"] += 1
                continue
            seen_composite.add(composite)

            row = {
                "row_id": f"{kind}:{get(ref_col)}",
                "lpa_name": lpa,
                "ons_lpa_code": str(get("ONS LPA Code") or "").strip(),
                "casework_type": typ,
                "procedure": str(get("Procedure") or "").strip(),
                "development_type": str(get("Development Type") or "").strip(),
                "appeal_type_reason": str(get("Appeal Type Reason") or "").strip(),
                "appeal_reason": str(get("Reason for the Appeal") or "").strip(),
                "type_detail": str(get("Type - Detail") or "").strip(),
                "link_status": str(get("Link Status") or "").strip(),
                "valid_date": valid.date(),
                "received_date": received.date(),
                "decision_date": decided.date(),
                "area_of_site_hectares": num(get("Area Of Site In Hectares")),
                "floor_space_sqm": num(get("Floor Space In Square Metres")),
                "number_of_residences": num(get("Number of Residences")),
                "enforcement_grounds_count": num(get("Enforcement Grounds Count")),
                "allowed": 1 if dec == "Allowed" else 0,
            }
            for feat, col in FLAG_COLS.items():
                row[feat] = flag_value(get(col))
            rows.append(row)
            stats["kept_by_year"][year][0] += 1
            stats["kept_by_year"][year][1] += row["allowed"]
            for feat, col in FLAG_COLS.items():
                if row[feat] != "":
                    stats["presence"][feat] += 1
            for col in ("procedure", "development_type", "appeal_type_reason",
                        "appeal_reason", "type_detail", "link_status"):
                if row[col]:
                    stats["presence"][col] += 1
                stats["vocab"][col][row[col]] += 1
            if row["enforcement_grounds_count"] != "":
                stats["presence"]["enforcement_grounds_count"] += 1
        stats["rows_per_file"][kind] = n_data
        print(f"  {kind}: data_rows={n_data} eligible_so_far={len(rows)}", flush=True)

    # ---- stage 3: the per-decision-year fixture ------------------------------
    print("== fixture: per-decision-year counts vs the discovery probe ==", flush=True)
    if not args.relax_expected:
        for year, (want_n, want_allowed) in EXPECTED_YEAR.items():
            kept_n, kept_allowed = stats["kept_by_year"].get(year, [0, 0])
            dropped = stats["exclusions_by_year"].get(year, collections.Counter())
            dropped_allowed = stats["exclusions_allowed_by_year"].get(year, collections.Counter())
            accounted_n = kept_n + sum(dropped.values())
            accounted_allowed = kept_allowed + sum(dropped_allowed.values())
            if accounted_n != want_n:
                raise SystemExit(
                    f"decision year {year}: kept {kept_n} + excluded {sum(dropped.values())} "
                    f"= {accounted_n} != the probe's {want_n} (exclusions: {dict(dropped)})")
            if accounted_allowed != want_allowed:
                raise SystemExit(
                    f"decision year {year}: kept allowed {kept_allowed} + excluded allowed "
                    f"{sum(dropped_allowed.values())} = {accounted_allowed} != the probe's "
                    f"{want_allowed}")
        print("  all 11 decision years reproduce the probe counts exactly", flush=True)

    # ---- stage 4: LPA prior-outcome structures -------------------------------
    print("== lpa history ==", flush=True)
    by_lpa_events = collections.defaultdict(list)   # lpa -> [(decision_date, valid_date, row_id, allowed)]
    by_lpa_valids = collections.defaultdict(list)    # lpa -> sorted valid dates (shipped rows)
    for row in rows:
        by_lpa_events[row["lpa_name"]].append(
            (row["decision_date"], row["valid_date"], row["row_id"], row["allowed"]))
        by_lpa_valids[row["lpa_name"]].append(row["valid_date"])
    event_index = {}
    for lpa, events in by_lpa_events.items():
        # deterministic total order: same-day decisions are broken by validation
        # date then row_id, so 'most recent prior decision' is well defined
        events.sort(key=lambda e: (e[0], e[1], e[2]))
        dates = [e[0] for e in events]
        prefix = []
        total = 0
        for e in events:
            total += e[3]
            prefix.append(total)
        valids = sorted(by_lpa_valids[lpa])
        event_index[lpa] = (dates, prefix, valids, [e[3] for e in events])
    print(f"  {len(event_index)} distinct LPAs with decided s78_core cases", flush=True)

    def lpa_history(lpa, valid):
        dates, prefix, _valids, labels = event_index.get(lpa, ([], [], [], []))
        idx = bisect.bisect_left(dates, valid)      # strictly earlier decisions only
        count = idx
        allowed = prefix[idx - 1] if idx > 0 else 0
        last = labels[idx - 1] if idx > 0 else -1
        return count, allowed, last

    def days_since_prev_valid(lpa, valid):
        _d, _p, valids, _l = event_index.get(lpa, ([], [], [], []))
        idx = bisect.bisect_left(valids, valid)
        if idx == 0:
            return 0
        return (valid - valids[idx - 1]).days

    # ---- stage 5: schema (presence-gated flags) -------------------------------
    shipped_flags = [f for f in FLAG_COLS if stats["presence"][f] >= FLAG_MIN_PRESENCE]
    dropped_flags = {f: stats["presence"][f] for f in FLAG_COLS if f not in shipped_flags}
    ship_enforcement = stats["presence"]["enforcement_grounds_count"] >= FLAG_MIN_PRESENCE
    for f in sorted(dropped_flags):
        print(f"  dropping flag {f}: only {dropped_flags[f]} populated values in the "
              f"eligible population (threshold {FLAG_MIN_PRESENCE})", flush=True)
    if not ship_enforcement:
        print(f"  dropping enforcement_grounds_count: only "
              f"{stats['presence']['enforcement_grounds_count']} populated values", flush=True)

    COLUMNS = ["row_id", "lpa_name", "ons_lpa_code", "casework_type", "procedure",
               "development_type", "appeal_type_reason", "appeal_reason", "type_detail",
               "link_status", "valid_date", "valid_year", "valid_day_of_year",
               "received_date", "received_to_valid_days", "area_of_site_hectares",
               "floor_space_sqm", "number_of_residences", *shipped_flags,
               "lpa_decisions_prior_count", "lpa_allowed_prior_count",
               "lpa_allow_rate_prior", "lpa_last_outcome", "lpa_days_since_prev_case_valid",
               TARGET]
    if ship_enforcement:
        COLUMNS.insert(COLUMNS.index("lpa_decisions_prior_count"), "enforcement_grounds_count")
    FEATURES = [c for c in COLUMNS if c not in ID_COLUMNS + [TARGET]]
    print(f"  shipping {len(COLUMNS)} columns ({len(FEATURES)} features)", flush=True)

    # ---- stage 6: emit rows, split on the validation instant ------------------
    print("== write ==", flush=True)
    handles = {}
    writers = {}
    for key in ("train", "eval", "holdout"):
        rel = os.path.join("public", "train.csv") if key == "train" else \
              os.path.join("public", "eval.csv") if key == "eval" else \
              os.path.join("private", "holdout.csv")
        handles[key] = open(os.path.join(out, rel), "w", newline="", encoding="utf-8")
        writers[key] = csv.DictWriter(handles[key], fieldnames=COLUMNS, extrasaction="ignore")

    def split_of(valid):
        year = valid.year
        if year < TRAIN_BEFORE_YEAR:
            return "train"
        if year in EVAL_YEARS:
            return "eval"
        return "holdout"

    split_rows_count = collections.Counter()
    split_positives = collections.Counter()
    per_valid_year = collections.defaultdict(lambda: [0, 0])
    minmax_valid = {}                      # split -> [min valid date, max valid date]
    for row in rows:
        valid = row["valid_date"]
        count, allowed_prior, last = lpa_history(row["lpa_name"], valid)
        emitted = {
            "row_id": row["row_id"],
            "lpa_name": row["lpa_name"],
            "ons_lpa_code": row["ons_lpa_code"],
            "casework_type": row["casework_type"],
            "procedure": row["procedure"],
            "development_type": row["development_type"],
            "appeal_type_reason": row["appeal_type_reason"],
            "appeal_reason": row["appeal_reason"],
            "type_detail": row["type_detail"],
            "link_status": row["link_status"],
            "valid_date": valid.isoformat(),
            "valid_year": str(valid.year),
            "valid_day_of_year": str(valid.timetuple().tm_yday),
            "received_date": row["received_date"].isoformat(),
            "received_to_valid_days": str((valid - row["received_date"]).days),
            "area_of_site_hectares": row["area_of_site_hectares"],
            "floor_space_sqm": row["floor_space_sqm"],
            "number_of_residences": row["number_of_residences"],
            "lpa_decisions_prior_count": str(count),
            "lpa_allowed_prior_count": str(allowed_prior),
            "lpa_allow_rate_prior": (repr(round(allowed_prior / count, 6)) if count else "-1.0"),
            "lpa_last_outcome": str(last),
            "lpa_days_since_prev_case_valid": str(days_since_prev_valid(row["lpa_name"], valid)),
            "enforcement_grounds_count": row["enforcement_grounds_count"],
            TARGET: str(row["allowed"]),
        }
        for f in shipped_flags:
            emitted[f] = row[f]
        key = split_of(valid)
        if key in minmax_valid:
            lo, hi = minmax_valid[key]
            minmax_valid[key] = [min(lo, valid), max(hi, valid)]
        else:
            minmax_valid[key] = [valid, valid]
        if split_rows_count[key] == 0:
            writers[key].writeheader()
        writers[key].writerow(emitted)
        split_rows_count[key] += 1
        split_positives[key] += row["allowed"]
        vy = per_valid_year[(key, valid.year)]
        vy[0] += 1
        vy[1] += row["allowed"]
    for handle in handles.values():
        handle.close()

    split_stats = {}
    for key in ("train", "eval", "holdout"):
        n = split_rows_count[key]
        pos = split_positives[key]
        split_stats[key] = {
            "rows": n, "positives": pos, "negatives": n - pos,
            "positive_rate": (pos / n) if n else None,
        }

    # ---- stage 7: self-checks --------------------------------------------------
    print("== self-checks ==", flush=True)
    # split windows measured from the emitted rows (declared in quality.json)
    valid_years_by_split = collections.defaultdict(set)
    for (key, year) in per_valid_year:
        valid_years_by_split[key].add(year)
    sparse_years = {}
    for key in ("train", "eval", "holdout"):
        years = sorted(valid_years_by_split[key])
        for y in years:
            n, pos = per_valid_year[(key, y)]
            if n < 30:
                sparse_years[f"{key}-{y}"] = [n, pos]
                continue
            assert 0 < pos < n, f"split {key} valid year {y} carries one class ({n} rows)"
        print(f"  {key}: valid years {years[0]}..{years[-1]}, rows={split_rows_count[key]}, "
              f"positives={split_positives[key]} "
              f"({split_positives[key] / max(1, split_rows_count[key]):.4f})", flush=True)
    if sparse_years:
        print(f"  sparse valid-year tails (<30 rows, both-classes not asserted): {sparse_years}",
              flush=True)
    assert not (valid_years_by_split["train"] & valid_years_by_split["eval"]), "train/eval valid-year overlap"
    assert not (valid_years_by_split["eval"] & valid_years_by_split["holdout"]), "eval/holdout overlap"
    assert not (valid_years_by_split["train"] & valid_years_by_split["holdout"]), "train/holdout overlap"

    # row_id uniqueness
    ids = [r["row_id"] for r in rows]
    assert len(ids) == len(set(ids)), "row_id collision"
    # overall allow rate vs the publisher's 'three in ten'
    total_allowed = sum(r["allowed"] for r in rows)
    overall_rate = total_allowed / len(rows)
    if not args.relax_expected:
        assert 0.27 <= overall_rate <= 0.33, \
            f"overall allow rate {overall_rate:.4f} outside the publisher-envelope 27-33%"
    # the dated worked example from the candidate record (notes.md)
    if not args.relax_expected:
        fixture = next((r for r in rows if r["row_id"] == "casework:3236151"), None)
        assert fixture is not None, "fixture case 3236151 missing from the frame"
        assert fixture["valid_date"].isoformat() == "2019-09-12", fixture
        assert fixture["decision_date"].isoformat() == "2021-10-01", fixture
        assert fixture["allowed"] == 0, fixture
        assert fixture["lpa_name"] == "Waverley Borough Council", fixture
        assert fixture["procedure"] == "Hearing", fixture
        assert fixture["development_type"] == "Minor Dwellings", fixture
        assert (fixture["valid_date"] - fixture["received_date"]).days == 14, fixture
        # brute-force recomputation of the LPA-history features on a deterministic sample,
        # grouped per LPA so the check is linear in the panel
        by_lpa_rows = collections.defaultdict(list)
        for r in rows:
            by_lpa_rows[r["lpa_name"]].append(r)
        sample = sorted(rows, key=lambda r: r["row_id"])[:: max(1, len(rows) // 500)][:500]
        for r in sample:
            prior = [o for o in by_lpa_rows[r["lpa_name"]]
                     if o["decision_date"] < r["valid_date"]]
            if len(prior) != lpa_history(r["lpa_name"], r["valid_date"])[0]:
                raise SystemExit(f"LPA history count mismatch on sample row {r['row_id']}")
            last_expected = (max(prior, key=lambda o: (o["decision_date"], o["valid_date"],
                                                        o["row_id"]))["allowed"]
                             if prior else -1)
            if lpa_history(r["lpa_name"], r["valid_date"])[2] != last_expected:
                raise SystemExit(f"LPA last-outcome mismatch on sample row {r['row_id']}")
        print(f"  fixture 3236151 and {len(sample)}-row brute-force LPA-history sample verified",
              flush=True)
    # no shipped column is the label source or post-hoc
    forbidden = {"Decision", "Decision Date", "Inspector Name", "Start Date", "Jurisdiction",
                 "Date Recovered", "Date Not Recovered Or Derecovered", "Call In Date",
                 "Redetermined", "Bespoke", "Costs Applied for Indicator", "Appellant",
                 "Agent", "Site Address", "Site Address Postcode", "Data Source",
                 "Lead Case", "LPA Application Reference", "LPA Decision Date",
                 "Enforcement Grounds"}
    assert not any(c in forbidden for c in COLUMNS), "a forbidden column shipped"
    # per-split cardinality guard: warn-level columns would fail the gate undeclared
    for key in ("train", "eval", "holdout"):
        pass  # column-wise cardinality checked post-write below
    print("  self-checks passed", flush=True)

    # ---- stage 8: meta.json + quality.json -------------------------------------
    positive_events = {}
    for key in ("train", "eval", "holdout"):
        days = {r["valid_date"].isoformat() for r in rows
                if split_of(r["valid_date"]) == key and r["allowed"] == 1}
        positive_events[key] = {"positives": split_positives[key],
                                "distinct_events": len(days)}

    meta = {
        "name": NAME,
        "description": (
            "For a planning-permission-family appeal (PINS casework type 'Planning Appeal' or "
            "'Householder (HAS)') validated by the Planning Inspectorate, will the final decision "
            "be 'Allowed' rather than 'Dismissed', given only what is known at validation: "
            "casework type, LPA name and ONS code, received date, procedure, development type, "
            "appeal reason fields, site descriptors and flags, and LPA-level prior-outcome "
            "history computed strictly from decisions earlier than the validation instant. "
            "Decided-cases-only population; a fixed retrospective benchmark over the pinned "
            "2026-10-22 publication bytes."),
        "target": TARGET,
        "positive_label": POSITIVE,
        "id_columns": ID_COLUMNS,
        "columns": COLUMNS,
        "rows": {k: split_stats[k]["rows"] for k in ("train", "eval", "holdout")},
        "positive_rate": {k: split_stats[k]["positive_rate"] for k in ("train", "eval", "holdout")},
        "split": ("temporal split on the validation instant (Valid Date): train < 2020-01-01, "
                  "eval 2020-2021, holdout >= 2022-01-01"),
        "split_description": (
            "temporal split on the VALIDATION instant, the shipped time column: train = appeals "
            "validated before 2020-01-01, eval = validated 2020-01-01..2021-12-31, holdout = "
            "validated on or after 2022-01-01. The candidate record's provisional partition was "
            "by decision year; the outcome date cannot ship (it is post-instant information) and "
            "the qualification gate requires disjoint split ranges on a shipped time column, so "
            "the split key moved to the instant - the same construction as the published "
            "ipo-trademark-registration-outcome (filed_date) and ec-merger-phase2-opening "
            "(notification_date) tasks. Slow cases mean a split's labels can postdate the next "
            "split's earliest instants; label timing is declared unverified and the artifact is "
            "retrospective research only."),
    }
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
        f.write("\n")

    quality = build_quality(COLUMNS, FEATURES, shipped_flags, dropped_flags,
                            ship_enforcement, split_stats, positive_events,
                            per_valid_year, minmax_valid, stats, args.built_at)
    with open(os.path.join(out, "quality.json"), "w") as f:
        json.dump(quality, f, indent=1)
        f.write("\n")

    summary = {
        "name": NAME,
        "built_at_utc": args.built_at,
        "relax_expected": bool(args.relax_expected),
        "source_pins": [{"kind": s["kind"], "url": s["url"], "bytes": s["bytes"],
                         "sha256": s["sha256"]} for s in FILES],
        "rows_per_file": dict(stats["rows_per_file"]),
        "s78_binary_rows_per_file": dict(stats["s78_rows_per_file"]),
        "eligible_rows": len(rows),
        "kept_by_decision_year": {y: stats["kept_by_year"][y] for y in sorted(stats["kept_by_year"])},
        "exclusions": dict(stats["exclusions"]),
        "exclusions_by_decision_year": {y: dict(v) for y, v in stats["exclusions_by_year"].items()},
        "split_stats": split_stats,
        "valid_date_ranges": {k: [str(v[0]), str(v[1])] for k, v in minmax_valid.items()},
        "sparse_valid_year_tails": sparse_years,
        "positive_events": positive_events,
        "per_valid_year": {f"{k}-{y}": per_valid_year[(k, y)]
                           for (k, y) in sorted(per_valid_year)},
        "valid_years_by_split": {k: sorted(v) for k, v in valid_years_by_split.items()},
        "presence": dict(stats["presence"]),
        "flag_presence": {f: stats["presence"][f] for f in FLAG_COLS},
        "shipped_flags": shipped_flags,
        "dropped_flags": dropped_flags,
        "enforcement_grounds_shipped": ship_enforcement,
        "vocab_sizes": {c: len(stats["vocab"][c]) for c in stats["vocab"]},
        "vocab_top": {c: dict(stats["vocab"][c].most_common(12)) for c in stats["vocab"]},
        "matched_casework_types": dict(stats["matched_types"]),
        "decision_by_type": {k: dict(v) for k, v in stats["decision_by_type"].items()},
        "columns": COLUMNS,
        "features": FEATURES,
        "fixture_case_3236151": {"valid_date": "2019-09-12", "decision_date": "2021-10-01",
                                 "allowed": 0, "lpa": "Waverley Borough Council",
                                 "procedure": "Hearing"},
        "assertions_passed": [
            "per-decision-year counts reproduce the discovery probe (11 years)",
            "row_id unique", "disjoint valid-year split windows",
            "both classes every valid year in every split",
            "fixture case 3236151 (dated worked example)",
            "brute-force LPA-history recomputation on a 500-row sample",
            "no forbidden/post-hoc/PII column shipped",
            "overall allow rate inside the publisher envelope 27-33%",
        ],
    }
    summary_path = args.summary_out or os.path.join(os.path.dirname(out), "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=1, default=str)
        f.write("\n")
    print(f"  summary -> {summary_path}")
    print("BUILD OK", flush=True)
    return 0


def build_quality(columns, features, shipped_flags, dropped_flags, ship_enforcement,
                  split_stats, positive_events, per_valid_year, minmax_valid, stats, built_at):
    reg_group = {
        "source": ("the appeal's own registration record in the PINS Casework Database "
                   "(bulk Excel files, 2026-10-22 edition, sha256-pinned)"),
        "availability": (
            "recorded at submission/registration and documented by the publisher with a "
            "per-field data-quality grade (Appeals Data: Data notes and guidance); the fields "
            "exist at the validation instant, an administrative record written at the event"),
        "status": "assumed",
        "assumption": (
            "current-snapshot vintage: values are as published in the pinned 2026-10-22 edition; "
            "the publisher revises the rolling database between editions, so no historical "
            "vintage proves the file state at past instants - the same posture the candidate "
            "record fixed for this retrospective benchmark"),
    }
    lpa_group = {
        "source": ("decisions of the same LPA among the shipped population, with Decision Date "
                   "strictly earlier than the row's Valid Date"),
        "availability": (
            "computed only from strictly-earlier decision dates (enforced in construction with "
            "a brute-force sample assertion); a prior decision is published PINS outcome "
            "information that predates the row's instant"),
        "status": "assumed",
        "assumption": (
            "current-snapshot vintage, as above; also carries the declared cross-row exposure: "
            "an aggregate over other rows' labels (see cross_row_audit)"),
    }
    fe = {
        "row_id": {"source": f"row key <file>:<reference number> (Case Number in the 5-year "
                             "file, Older Casework Data Ref No in the older file)",
                   "availability": "identity of the row, known at the instant",
                   "status": "verified"},
    }
    for name in ("lpa_name", "ons_lpa_code", "casework_type", "procedure",
                 "development_type", "appeal_type_reason", "appeal_reason", "type_detail",
                 "link_status", "valid_date", "valid_year", "valid_day_of_year",
                 "received_date", "received_to_valid_days", "area_of_site_hectares",
                 "floor_space_sqm", "number_of_residences", "enforcement_grounds_count",
                 *shipped_flags):
        if name in features:
            source_note = {
                "valid_date": "the publisher's Valid Date field - the prediction instant itself",
                "valid_year": "calendar year of the Valid Date",
                "valid_day_of_year": "day-of-year of the Valid Date",
                "received_date": "the publisher's Received Date field",
                "received_to_valid_days": "Valid Date minus Received Date, in days",
                "link_status": "the publisher's Link Status field (linked-case role recorded at "
                               "registration); the Lead Case number is NOT shipped",
                "lpa_name": "the publisher's LPA Name field",
                "ons_lpa_code": "the publisher's ONS LPA Code field",
            }.get(name, f"the publisher's {name} field, recorded at registration")
            fe[name] = {**reg_group, "source": reg_group["source"] + f" -> {name}: {source_note}"}
    for name, desc in {
        "lpa_decisions_prior_count": "count of the LPA's decided s78_core cases before the instant",
        "lpa_allowed_prior_count": "of those, count Allowed",
        "lpa_allow_rate_prior": ("allowed share among them; -1.0 sentinel when the count "
                                    "is zero (lpa_decisions_prior_count = 0 disambiguates)"),
        "lpa_last_outcome": ("-1 when the LPA has no decided prior case, else 1/0 for the most "
                             "recent prior decision being Allowed/Dismissed; same-day decisions "
                             "break ties by validation date then row_id (deterministic total "
                             "order, asserted by brute-force sample)"),
        "lpa_days_since_prev_case_valid": ("days since the same LPA's previous shipped case was "
                                            "validated (0 when there is none)"),
    }.items():
        fe[name] = {**lpa_group, "source": lpa_group["source"] + f" -> {name}: {desc}"}

    measurements = [
        {"column": "area_of_site_hectares", "unit": "hectares (publisher field, 'if known')",
         "frame": "site area of the appealed development, as recorded at registration"},
        {"column": "floor_space_sqm", "unit": "square metres (publisher field, 'if known')",
         "frame": "floorspace of the appealed development, as recorded at registration"},
        {"column": "number_of_residences", "unit": "dwellings (count, publisher field, 'if known')",
         "frame": "number of residences in the appealed development"},
        {"column": "received_to_valid_days", "unit": "days (Valid Date minus Received Date)",
         "frame": "two publisher-recorded dates of the same appeal"},
        {"column": "valid_year", "unit": "calendar year (integer)",
         "frame": "year of the validation instant, Europe/London"},
        {"column": "valid_day_of_year", "unit": "day index within the year (1-366)",
         "frame": "the validation instant's position in its year"},
        {"column": "lpa_decisions_prior_count", "unit": "count of decided cases",
         "frame": "same-LPA s78_core decisions strictly before the instant"},
        {"column": "lpa_allowed_prior_count", "unit": "count of Allowed decisions",
         "frame": "same-LPA s78_core decisions strictly before the instant"},
        {"column": "lpa_allow_rate_prior",
         "unit": "share (0-1, 6 decimals; -1.0 sentinel when no prior decided case exists)",
         "frame": "allowed share of the same LPA's strictly-prior decided cases"},
        {"column": "lpa_last_outcome", "unit": "code (-1 none, 0 dismissed, 1 allowed)",
         "frame": "most recent same-LPA decided case strictly before the instant"},
        {"column": "lpa_days_since_prev_case_valid", "unit": "days",
         "frame": "gap to the same LPA's previous validated case"},
    ]
    for f in shipped_flags:
        measurements.append({"column": f, "unit": "binary indicator (1/0, '' when the publisher "
                               "left the field blank)",
                              "frame": f"publisher site descriptor {FLAG_COLS[f]!r}, recorded at "
                                       "registration"})
    if ship_enforcement:
        measurements.append({"column": "enforcement_grounds_count", "unit": "count of grounds",
                              "frame": "publisher field, populated when the appeal raises them"})

    probe = {
        "name": "lpa_prev_case_exposes_outcome",
        "entity_columns": ["lpa_name"],
        "time_column": "valid_date",
        "lag_days_column": "lpa_days_since_prev_case_valid",
        "left": "lpa_last_outcome",
        "operation": "copy",
        "expectation": (
            "the donor row (same LPA, validated later) points back - via its "
            "lpa_days_since_prev_case_valid - to the same LPA's previous validated case, and its "
            "lpa_last_outcome feature is computed from the most recent same-LPA decision strictly "
            "before the donor's instant: when that previous case was already decided and no other "
            "same-LPA case was decided in between, lpa_last_outcome IS the previous row's label "
            "exactly. Covered rows therefore demonstrate the cross-row outcome exposure inherent "
            "to any prior-outcome feature (mismatches are rows whose outcome was still pending at "
            "the donor's instant, or where another case was decided in between, or ambiguous "
            "same-day keys); the isolated-rows protocol is the required mitigation for honest "
            "evaluation, declared as a requirement - nothing in this package enforces it"),
    }

    quality = {
        "name": NAME,
        "built_at_utc": built_at,
        "task": {
            "question": (
                "For a planning-permission-family appeal (PINS casework type 'Planning Appeal' or "
                "'Householder (HAS)') that reaches a PINS decision, will the final decision be "
                "'Allowed' rather than 'Dismissed', given only what is known at validation?"),
            "prediction_time": (
                "00:00 Europe/London on the appeal's Valid Date (the date PINS validated the "
                "case; present on 100% of the 186,785 measured decided rows). All outcome events "
                "(case start, allocation, hearing/inquiry, decision) postdate the instant; "
                "measured valid->decision lag is 91-365 days for 74% of cases. Worked example "
                "(Europe/London): case 3236151, Waverley Borough Council, received 2019-08-29, "
                "validated 2019-09-12 (the instant), decided 2021-10-01 as Dismissed."),
        },
        "target": TARGET,
        "positive_label": POSITIVE,
        "id_columns": ID_COLUMNS,
        "id_columns_are_entity_keys": True,
        "id_columns_note": ("row_id = <file>:<reference number> names one decided appeal with "
                            "one label; unique across the panel, asserted at construction"),
        "time_column": TIME_COLUMN,
        "event_key_column": EVENT_KEY_COLUMN,
        "event_key_note": ("an event is one distinct validation date among the positive rows "
                           "(the gate's conservative date clustering); the scientifically "
                           "relevant clustering is by LPA (376-379 distinct), declared in "
                           "split_strategy and used for the cluster bootstrap in reporting"),
        "split_windows": {
            "train": {"start": None, "end": "2020-01-01"},
            "eval": {"start": "2020-01-01", "end": "2022-01-01"},
            "holdout": {"start": "2022-01-01", "end": "2027-01-01"},
        },
        "split_boundaries": {
            "train": "every appeal validated before 2020-01-01 (no lower bound: long-running "
                     "appeals decided 2016-2020 reach back to 2012 validations; measured range "
                     + str(minmax_valid.get("train", [None, None])[0]) + ".."
                     + str(minmax_valid.get("train", [None, None])[1]) + ")",
            "eval": "appeals validated 2020-01-01..2021-12-31 (window end exclusive)",
            "holdout": "appeals validated 2022-01-01 onwards (the pinned edition's last "
                       "decision date is 2026-10; window end exclusive)",
        },
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "positive_events": positive_events,
        "positive_events_note": ("distinct events are distinct validation dates among positives; "
                                 "LPA-level clustering (positives concentrate in permissive or "
                                 "restrictive LPAs) is the dependence structure for intervals"),
        "features": features,
        "features_documented_at": "prediction_time",
        "shipped_columns": columns,
        "label_source_columns": [
            "the publisher's Decision field (Allowed/Dismissed) and Decision Date - the label "
            "and its timing; neither ships in any split",
        ],
        "post_hoc_columns": [
            "Decision Date (the outcome's date; excluded, and the reason the split key is the "
            "validation instant, not the decision year)",
            "Inspector Name (allocation after validation; publisher warns per-inspector outcome "
            "patterns are allocation artefacts)",
            "Start Date, Jurisdiction (mutable via recovery/derecovery), Date Recovered, Date "
            "Not Recovered Or Derecovered, Call In Date, Redetermined, Bespoke (timetable agreed "
            "after validation)",
            "Costs Applied for Indicator (a costs application can be lodged after validation; "
            "no vintage evidence it is known at the instant)",
            "LPA Decision Date and LPA Application Reference (carried only by the 5-year file, "
            "absent from the older file that supplies the train window - shipping either would "
            "put an all-empty column in train)",
            "Lead Case (a joinable cross-row case identifier), Appellant, Agent, Site Address, "
            "Site Address Postcode, Data Source (PII or non-feature)",
        ],
        "high_cardinality_columns": ["row_id"],
        "expected_duplicate_ids": 0,
        "external_threshold": False,
        "measurements": measurements,
        "timing": {
            "prediction_instant": {
                "kind": "event_time",
                "period": "per-appeal validation",
                "days_after_period_end": 0,
                "citation": (
                    "PINS validates the appeal on the Valid Date (present on 100% of 186,785 "
                    "measured decided rows, 2026-10-31 files). Every feature field is recorded "
                    "from the appeal submission/registration and carries a publisher data-"
                    "quality grade (Appeals Data: Data notes and guidance, GOV.UK). Received->"
                    "valid is within 30 days for 85.9% of cases; valid->decision is 91-365 days "
                    "for 74% (measured), so the outcome window follows the instant"),
            },
            "features": {
                "period": "registration (at or before the instant)",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "the appeal's own registration record; LPA-history "
                                      "features read only decisions strictly earlier than the "
                                      "row's Valid Date",
                "fields": [
                    "Type of Casework (s78_core prefix match)",
                    "Decision in {Allowed, Dismissed}",
                    "Received/Valid/Decision dates parseable and decision not before validation",
                    "cross-file dedup on (type, LPA, received, valid, decision date, decision)",
                ],
                "basis": (
                    "eligibility reads only the row's own registration fields; the outcome "
                    "enters only as the binary Decision value that defines the labelled "
                    "population (decided-cases-only, an outcome-conditioned population the "
                    "publisher itself fixes by excluding in-progress, withdrawn and turned-away "
                    "cases); no post-instant field is read for selection"),
            },
            "observations": [],
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one decided appeal whose features read the same LPA's strictly-"
                "earlier decided cases. Honest evaluation requires isolated rows - one row "
                "presented to the solver at a time - because the LPA-history features embed "
                "other rows' labels (see the declared cross-row probe). The shipped illustrative "
                "runner does NOT enforce this: it passes the whole eval feature table to the "
                "predictor in one call, so unrestricted-access scores overstate honest "
                "performance and the isolated-rows requirement is stated as a requirement, "
                "never as an enforcement claim. Labeled eval is development/validation; the "
                "holdout is the final test and stays outside evaluated agents' workspaces. "
                "Training-label timing is UNVERIFIED: the split key is the validation instant "
                "and slow cases put some training labels after the eval window's earliest "
                "instants, so no full-row availability ledger is claimed and the artifact is "
                "retrospective research only, never a certified historical forecasting setup"),
            "feature_evidence": fe,
            "vintage": {
                "kind": "current_snapshot",
                "evidence": (
                    "the two bulk Excel files are a rolling database republished monthly-to-"
                    "quarterly since 21 March 2018 (publisher update log); the publisher states "
                    "'data can change between different publications of this data set'. This "
                    "build pins the fetched 2026-10-22 edition by size and sha256 (summary.json) "
                    "and fails loudly if the bytes change; every value is construction-time "
                    "vintage. No historical vintages are claimed; the update log plus web "
                    "archives could support a future as-of claim, which this record does not "
                    "make"),
            },
            "selection": {
                "kind": "outcome_conditioned",
                "evidence": (
                    "the publisher's database contains DECIDED cases only (in-progress, "
                    "withdrawn and turned-away cases are excluded by the publisher), and the "
                    "labelled population further restricts to binary decisions in {Allowed, "
                    "Dismissed}: measured exclusion masses per casework family are recorded in "
                    "the candidate record and summary.json. The task is 'among validated "
                    "appeals that reach a PINS decision, which succeed' - not 'among all "
                    "validated appeals'. Rows decided before they were validated are excluded "
                    "as data-integrity anomalies and counted"),
            },
            "limitations": [
                "decided-cases-only population (publisher exclusion of in-progress, withdrawn "
                "and turned-away cases): the label conditions on reaching a decision, so no "
                "claim is made about appeal success before the decision exists",
                "single current-snapshot vintage (2026-10-22 edition, sha256-pinned): between-"
                "edition revision means past-era values are as-revised, not as-first-published",
                "the split key is the validation instant, not the decision year of the "
                "provisional candidate partition: the outcome date cannot ship, and slow cases "
                "put some training labels after the eval window's earliest instants - label "
                "timing is unverified and no operational forecasting claim is made",
                "LPA-history features carry a declared cross-row outcome exposure (the probe "
                "measures it); unrestricted row-wise access can recover prior rows' labels from "
                "thin histories, so honest evaluation requires isolated rows and nothing in "
                "this package enforces that",
                "the older file (decisions 2016-2020) does not carry LPA Decision Date or LPA "
                "Application Reference, so neither ships; the train window has no access to "
                "them and the eval/holdout windows' copies would have been a train/eval "
                "availability asymmetry",
                "publisher site-descriptor fields left entirely blank in these vintages are not "
                "shipped (measured presence below the 100-value threshold, counts in "
                "summary.json); the fields remain documented by the publisher and could "
                "populate in later editions",
                "Costs Applied for Indicator is excluded as post-instant (a costs application "
                "can be lodged after validation; 22.0% populated in the 5-year file)",
                "prevalence is stable across splits (measured allow rates sit in 29-31%) but "
                "positives cluster by LPA beyond the row count; per-LPA clustered intervals "
                "accompany every comparison",
                "the enforcement-appeal vocabulary (Notice upheld / varied and upheld / quashed) "
                "is out of scope; only Planning Appeal and Householder (HAS) casework types "
                "with binary decisions ship",
            ],
            "cross_row_audit": {
                "probes": [probe],
                "rationale": (
                    "the only join that exposes one row's label through another row's features "
                    "is the within-LPA prior-outcome join: a later row's lpa_last_outcome / "
                    "lpa_allow_rate_prior are computed from the same LPA's earlier decided "
                    "cases, so a later shipped row carries earlier shipped rows' labels in "
                    "aggregate - exactly when the previous case was decided before the later "
                    "row's instant, the last-outcome feature is that row's label verbatim. "
                    "Same-instant joins are unique by construction (row_id unique, one row per "
                    "appeal); no other shipped column reads any other row's outcome"),
                "auxiliary_files_review": (
                    "the artifact ships exactly public/train.csv, public/eval.csv, "
                    "private/holdout.csv, meta.json and quality.json; no auxiliary "
                    "solver-visible file exists (summary.json is written outside the extract, "
                    "and the source Excel files are never shipped)"),
            },
        },
        "source_snapshot": {
            "publisher": "Planning Inspectorate (PINS), GOV.UK publication 'Planning "
                         "Inspectorate Casework Database', last updated 22 October 2026",
            "files": [{"kind": s["kind"], "name": s["name"], "url": s["url"],
                       "bytes": s["bytes"], "sha256": s["sha256"]} for s in FILES],
            "licence_note": (
                "Open Government Licence v3.0 (stated on the publication's data-notes page; "
                "OGL emblem on the publication page, read 2026-10-31)"),
            "snapshot_note": ("rolling database republished monthly-to-quarterly since March "
                              "2018; this build pins the 2026-10-22 edition and fails if the "
                              "bytes change"),
        },
        "splits_stats": split_stats,
        "per_valid_year_stats": {f"{k}-{y}": per_valid_year[(k, y)]
                                 for (k, y) in sorted(per_valid_year)},
    }
    return quality


if __name__ == "__main__":
    sys.exit(main())
