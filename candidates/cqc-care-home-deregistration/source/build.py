#!/usr/bin/env python3
"""Construction of the cqc-care-home-deregistration artifact (cqc-chd-001).

Task: at the production instant T of a monthly CQC "HSCA Active Locations"
vintage, for every care home active at T, predict whether that location's
registration ends (`Location Status` Inactive-Dereg/Removed with a
`Location HSCA End Date`) within the following 12 months - a REGISTER-EVENT
target. The register event conflates service cessation with re-registration
(CQC's own in-file note; BMJ 2024 measured 8,346 complete closures vs our
14,911 register events 2011-2023, implying ~40-55% re-registrations); the
framing decision recorded 2026-11-03 ships the well-defined register event
with that share stated as a limitation, not a closure claim.

P0-SAFE PANEL DESIGN (the design decision this build exists to honor):

  * The missing-successor rule (the unhcr P0): if a solver could link a row
    to the SAME location at a LATER instant, row presence alone recovers the
    label - absent successor => deregistered. Killed STRUCTURALLY, three ways:
      1. every scored frame carries a SINGLE instant: train = January
         instants 2016-2022, eval = the 2024-01 vintage, holdout = the
         2025-01 vintage. The successor rows of eval rows exist only in the
         sealed holdout; holdout rows have no successor instant in the
         artifact at all.
      2. location identity ships as a PER-INSTANT PSEUDONYM
         (sha256(salt|instant|location_id)[:16]) - no shipped column carries
         the CQC Location ID, the provider id, the CH/charity number, the
         location name, address or postcode, so no exact cross-instant link
         exists. The real ids live only in auxiliary/location_map.csv
         (staging-side verification input, never a solver-visible frame).
      3. train instants stop at 2022: every train row's 12-month outcome
         window closes at least a year BEFORE the eval prediction instant
         (the 2023 instant is excluded by design for exactly this reason).
  * Residual quasi-identifier linkage (LA x beds x start-year x rating x
    sector can never be unique enough...) is MEASURED, not assumed away: gate
    probe 1 executes the successor-presence attack over the strongest
    instant-invariant quasi-key with offset +12 months. Coverage on the
    scored frames is expected to be 0 (no visible successor rows); coverage
    inside train measures the linkage rate where labels are already public.
  * No provider-group history feature ships (the za-statsa/acnc shape): the
    provider's sector ships, not its identity, not sister-location outcomes.

This file ONLY constructs files and gate diagnostics. It computes no
performance metric (no AUC, no accuracy, no model): row and positive counts,
fixture assertions, exclusion buckets and per-instant diagnostics are
construction diagnostics. The first performance number in the job is
computed by score.py, which run.sh allows to run only after the
qualification gate passed over the full artifact and --accept re-verified the
exact bytes. The holdout is never opened by score.py.

Worker order (run.sh): construct -> qualify -> accept exact bytes -> references.

Harvest (anonymous, stdlib):
  * January vintages 2016-2022 + 2024 + 2025 of "HSCA Active Locations" from
    CQC's public Google Drive archive (year folders, embeddedfolderview
    listing, drive.usercontent download), every file pinned by size+sha256
    (the 2024-01 vintage against the 2026-11-03 discovery pins).
  * The Deactivated Locations ODS from cqc.org.uk (the 2026-11-02 edition the
    discovery measurements were taken on), pinned by size+sha256 prefix.
  * ODS parsed with the proven probe reader; XLSX parsed with a stdlib
    OOXML reader (sharedStrings, inline strings, date-style serials).

Label: care-home location present in the Deactivated Locations cumulative
file with `Location HSCA End Date` in (T, T+365d] (any status; the status mix
of window positives is recorded). Mirrors probe/cqc_example.py exactly.

Acceptance criteria asserted in-build against the 2026-11-03 discovery
measurements (probe/, notes.md), --real-fixtures only:
  * deactivated file: 65,830 data rows, 17,177 care-home rows, unique ids;
  * 2024-01 vintage (digest ac40b6f8..., 26,147,266 B): 14,765 care homes,
    758 positives in (T, T+365d], 2,076 later-deactivated, 0 rows with a
    rating Publication Date after T (the as-of check);
  * dated fixtures Park Hills Nursing Home (1-113831768, label 1),
    Henley House (1-10000302982, label 0),
    Options Hazel House (1-10086766554, end 05/03/2025 -> label 0 at T).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

NAME = "cqc-care-home-deregistration"
TARGET = "deregistered_12m"
POSITIVE = 1
POSITIVE_LABEL_TEXT = ("the location's CQC registration ends (Location Status "
                       "Inactive-Dereg or Removed with a Location HSCA End "
                       "Date) within 12 months of the vintage instant")
ID_COLUMNS = ["location_key"]
TIME_COLUMN = "instant"          # YYYY-MM, the vintage production month
EVENT_KEY_COLUMN = "location_key"

SALT = "cqc-chd-v1-20261103"
DRIVE_ROOT = "1Y6V6r-q2l4lJYKuZL0DXw25VDUTH6L4N"
DRIVE_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
DEACT_URL = ("https://www.cqc.org.uk/system/files/2026-11/"
             "02_November_2026_Deactivated_Locations.ods")
DEACT_SIZE = 27_644_723
DEACT_SHA_PREFIX = "49dc3062"
VINT_2024_ID = "1WsUwZAarJARNYwPLnlZ5C1p1dooRBX61"
VINT_2024_SIZE = 26_147_266
VINT_2024_SHA_PREFIX = "ac40b6f8"

TRAIN_YEARS = list(range(2016, 2023))   # 2016..2022; 2023 excluded by design
EVAL_YEAR = 2024
HOLDOUT_YEAR = 2025
MIN_TRAIN_INSTANTS = 5

# discovery measurements (probe/cqc_example.py, 2026-11-03)
EXPECTED_DEACT_ROWS = 65_830
EXPECTED_DEACT_CARE_HOMES = 17_177
EXPECTED_EVAL_CARE_HOMES = 14_765
EXPECTED_EVAL_POSITIVES = 758
EXPECTED_EVAL_LATER_DEACT = 2_076
FIXTURES = {
    "1-113831768": {"label": 1, "beds": "17", "la": "Oldham",
                    "rating": "Good", "pub": "26/08/2022",
                    "start": "01/02/2011"},          # Park Hills Nursing Home
    "1-10000302982": {"label": 0},                    # Henley House (active)
    "1-10086766554": {"label": 0},                    # Options Hazel House (end 05/03/2025)
}

RATING_RECENCY_BUCKETS = ((183, "<6m"), (365, "<1y"), (730, "<2y"),
                          (1095, "<3y"))
BEDS_BUCKETS = ((3, "1-3"), (10, "4-10"), (25, "11-25"), (50, "26-50"),
                (10_000, "51+"))

SPLIT_WINDOWS = {
    "train": {"start": "2016-01", "end": "2023-01"},
    "eval": {"start": "2024-01", "end": "2025-01"},
    "holdout": {"start": "2025-01", "end": "2026-01"},
}
SPLIT_NAMES = ("train", "eval", "holdout")

# one column list, in one place
COLUMNS = (["location_key", "instant", "care_home_beds",
            "beds_bucket", "latest_overall_rating", "rating_recency_bucket",
            "inherited_rating", "hsca_start_year", "local_authority",
            "region", "provider_sector", "svc_nursing", "svc_residential",
            "svc_other_count", "users_dementia", "users_older_people",
            "users_learning_disabilities", "users_physical_disability",
            "users_mental_health", "users_other_count", TARGET])
FEATURES = [c for c in COLUMNS if c not in ID_COLUMNS + [TARGET]]


class BuildError(RuntimeError):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------- 
# spreadsheet readers (stdlib only)
# ---------------------------------------------------------------------------

ODS_NS = {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
          "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0"}
T_ROW = "{%s}table-row" % ODS_NS["table"]
T_CELL = "{%s}table-cell" % ODS_NS["table"]
T_REPEATED = "{%s}number-columns-repeated" % ODS_NS["table"]
T_ROW_REPEATED = "{%s}number-rows-repeated" % ODS_NS["table"]
O_VALUE = "{%s}value" % ODS_NS["office"]
O_DATE = "{%s}date-value" % ODS_NS["office"]


def _ods_cell_text(cell) -> str:
    txt = "".join(cell.itertext()).strip()
    if not txt:
        txt = cell.get(O_DATE) or cell.get(O_VALUE) or ""
    return txt


def ods_rows(path: Path):
    """Yield ('stamp', [cells]) pre-header rows, then ('header'|'row', cells)."""
    with zipfile.ZipFile(path) as z:
        content = [m for m in z.namelist() if m.endswith("content.xml")][0]
        header = None
        for _, elem in ET.iterparse(z.open(content), events=("end",)):
            if elem.tag != T_ROW:
                continue
            rep = int(elem.get(T_ROW_REPEATED) or "1")
            if rep > 1000:
                elem.clear()
                continue
            cells = []
            for cell in elem.findall(T_CELL):
                crep = int(cell.get(T_REPEATED) or "1")
                cells.extend([_ods_cell_text(cell)] * crep)
            if header is None:
                if cells and cells[0].strip() == "Location ID":
                    header = cells
                    yield ("header", header)
                elif any(cells):
                    yield ("stamp", cells)
            else:
                yield ("row", cells)
            elem.clear()


def _col_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _xlsx_date_styles(z: zipfile.ZipFile) -> set[int]:
    """Style indexes whose number format is a date format."""
    date_fmt = set()
    fmts = {}
    try:
        root = ET.fromstring(z.read("xl/styles.xml"))
    except KeyError:
        return date_fmt
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for numfmt in root.iter(f"{ns}numFmt"):
        code = (numfmt.get("formatCode") or "").lower()
        if any(tok in code for tok in ("d", "m", "y")) and any(
                tok in code for tok in ("y", "d")):
            fmts[int(numfmt.get("numFmtId"))] = True
    for i, xf in enumerate(root.iter(f"{ns}xf")):
        fid = int(xf.get("numFmtId") or "0")
        if fid in fmts or 14 <= fid <= 22 or 45 <= fid <= 47:
            date_fmt.add(i)
    return date_fmt


def xlsx_rows(path: Path):
    """Yield ('stamp'|'header'|'row', cells) for the first worksheet."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            for si in root.iter(f"{ns}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{ns}t")))
        # first sheet by workbook order
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        relns = ("{http://schemas.openxmlformats.org/package/2006/relationships}")
        rel_id_ns = ("{http://schemas.openxmlformats.org/officeDocument/"
                     "2006/relationships}id")
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_map = {r.get("Id"): r.get("Target")
                   for r in rels.iter(f"{relns}Relationship")}
        first = wb.find(f"{ns}sheets/{ns}sheet")
        target = rid_map.get(first.get(rel_id_ns)) if first is not None else None
        if target is None:
            raise BuildError(f"{path.name}: no first-sheet relationship")
        sheet_path = "xl/" + target.lstrip("/").removeprefix("xl/")
        date_styles = _xlsx_date_styles(z)
        header = None
        for _, elem in ET.iterparse(z.open(sheet_path), events=("end",)):
            tag = elem.tag
            ns2 = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            if tag != f"{ns2}row":
                continue
            cells: list[str] = []
            for cell in elem.findall(f"{ns2}c"):
                ref = cell.get("r") or ""
                idx = _col_index(ref) if ref else len(cells)
                while len(cells) < idx:
                    cells.append("")
                ctype = cell.get("t")
                style = int(cell.get("s") or "0")
                v = cell.find(f"{ns2}v")
                inline = cell.find(f"{ns2}is")
                if ctype == "inlineStr" and inline is not None:
                    val = "".join(t.text or "" for t in inline.iter(f"{ns2}t"))
                elif v is None:
                    val = ""
                elif ctype == "s":
                    val = shared[int(v.text)] if (v.text or "").isdigit() else ""
                elif ctype == "str":
                    val = v.text or ""
                elif style in date_styles and ctype != "str":
                    serial = float(v.text)
                    epoch = datetime.date(1899, 12, 30)
                    d = epoch + datetime.timedelta(days=int(serial))
                    val = d.strftime("%d/%m/%Y")
                else:
                    val = v.text or ""
                cells.append(val.strip())
            if header is None:
                if cells and cells[0].strip() == "Location ID":
                    header = cells
                    yield ("header", header)
                elif any(cells):
                    yield ("stamp", cells)
            else:
                yield ("row", cells)
            elem.clear()


def sheet_rows(path: Path):
    if path.suffix.lower() == ".xlsx":
        return xlsx_rows(path)
    return ods_rows(path)


# --------------------------------------------------------------------------- 
# header resolution (pattern-based; drift reported, never guessed)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "location_id": r"^location id$",
    "care_home": r"^care home\?$",
    "beds": r"^care homes beds$",
    "rating": r"^location latest overall rating$",
    "pub": r"^publication date$",
    "start": r"^location hsca start date$",
    "la": r"^location local authority$",
    "region": r"^location region$",
}
OPTIONAL_FIELDS = {
    "inherited": r"^inherited rating$",
    "sector": r"^provider type\s*[-/]\s*sector$",
}
SERVICE_TYPE_RE = re.compile(r"^service type - (.+)$", re.I)
USER_BAND_RE = re.compile(r"^service user band - (.+)$", re.I)


def resolve_header(header: list[str]) -> dict:
    idx: dict[str, int] = {}
    for field, pattern in REQUIRED_FIELDS.items():
        for i, h in enumerate(header):
            if re.search(pattern, h.strip(), re.I):
                idx[field] = i
                break
    for field, pattern in OPTIONAL_FIELDS.items():
        for i, h in enumerate(header):
            if re.search(pattern, h.strip(), re.I):
                idx[field] = i
                break
    svc_types, user_bands = [], []
    for i, h in enumerate(header):
        m = SERVICE_TYPE_RE.match(h.strip())
        if m:
            svc_types.append((i, m.group(1).strip()))
            continue
        m = USER_BAND_RE.match(h.strip())
        if m:
            user_bands.append((i, m.group(1).strip()))
    return {"idx": idx, "svc_types": svc_types, "user_bands": user_bands}


def dparse(text: str):
    """Parse dd/mm/yyyy (primary) or yyyy-mm-dd; None when unparseable."""
    s = (text or "").strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime.date(y, mo, d)
        except ValueError:
            return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def yessy(text: str) -> int:
    return 1 if (text or "").strip().upper().startswith("Y") else 0


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


USER_BAND_KEYS = (
    ("users_dementia", ("dementia",)),
    ("users_older_people", ("older people", "older people's")),
    ("users_learning_disabilities", ("learning disab", "autistic")),
    ("users_physical_disability", ("physical disab",)),
    ("users_mental_health", ("mental health", "mental ill")),
)


def bucket_index(value: int, buckets) -> str:
    for limit, label in buckets:
        if value <= limit:
            return label
    return buckets[-1][1]


# --------------------------------------------------------------------------- 
# harvest
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(
    r'<a[^>]+href="(https://drive\.google\.com/(?:drive/folders|file/d)/[^"]+)"'
    r'[^>]*>.*?flip-entry-title">([^<]+)</div>', re.S)


def http_get(url: str, timeout: int = 600) -> bytes:
    req = urllib.request.Request(url, headers=DRIVE_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def list_drive_folder(folder_id: str) -> list[tuple[str, str]]:
    html = http_get(
        f"https://drive.google.com/embeddedfolderview?id={folder_id}#list",
        timeout=120).decode("utf-8", "replace")
    out = []
    for href, name in ENTRY_RE.findall(html):
        m = re.search(r"/(?:folders|d)/([a-zA-Z0-9_-]+)", href)
        if m:
            out.append((name.strip(), m.group(1)))
    return out


def download_vintage(year: int, work_dir: Path, stats: dict) -> tuple[Path, datetime.date]:
    """List the archive year folder, pick the January vintage, download it."""
    entries = list_drive_folder(DRIVE_ROOT)
    year_id = None
    for name, fid in entries:
        if name.strip() == str(year):
            year_id = fid
            break
    if year_id is None:
        raise BuildError(f"archive year folder {year} not found; entries: "
                         f"{[n for n, _ in entries][:30]}")
    files = list_drive_folder(year_id)
    pattern = re.compile(
        rf"^(\d{{1,2}}) January {year} HSCA Active Locations\.(ods|xlsx)$", re.I)
    match = None
    for name, fid in files:
        m = pattern.match(name.strip())
        if m:
            match = (name.strip(), fid, m.group(1), m.group(2).lower())
            break
    if match is None:
        raise BuildError(f"no January {year} HSCA Active Locations file in "
                         f"folder; files: {[n for n, _ in files][:20]}")
    name, fid, day, ext = match
    url = (f"https://drive.usercontent.google.com/download?id={fid}"
           "&export=download&confirm=t")
    dest = work_dir / f"active_{year}_01.{ext}"
    data = http_get(url)
    if not data.startswith(b"PK"):
        raise BuildError(f"{name}: downloaded {len(data)} bytes, not a zip")
    dest.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    stats.setdefault("vintages", {})[str(year)] = {
        "file": name, "drive_id": fid, "bytes": len(data),
        "sha256": digest, "url": url,
    }
    if year == EVAL_YEAR:
        if fid != VINT_2024_ID:
            print(f"  NOTE: 2024 drive id {fid} != discovery pin "
                  f"{VINT_2024_ID} (digest decides)", flush=True)
        if len(data) != VINT_2024_SIZE or not digest.startswith(VINT_2024_SHA_PREFIX):
            raise BuildError(
                f"2024-01 vintage digest drift: {len(data)}B {digest[:16]} "
                f"vs pinned {VINT_2024_SIZE}B {VINT_2024_SHA_PREFIX}")
        stats["vintages"][str(year)]["pinned"] = True
    return dest, datetime.date(year, 1, int(day))


def download_deactivated(work_dir: Path, stats: dict) -> Path:
    dest = work_dir / "deactivated.ods"
    data = http_get(DEACT_URL)
    dest.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != DEACT_SIZE or not digest.startswith(DEACT_SHA_PREFIX):
        raise BuildError(f"deactivated file digest drift: {len(data)}B "
                         f"{digest[:16]} vs pinned {DEACT_SIZE}B "
                         f"{DEACT_SHA_PREFIX}")
    stats["deactivated"] = {"url": DEACT_URL, "bytes": len(data),
                            "sha256": digest, "pinned": True}
    return dest


def load_synthetic_vintages(synthetic_dir: Path):
    """Synthetic mode: files named '<DD> January <YYYY> ...{.ods,.xlsx}'."""
    out = {}
    for path in sorted(synthetic_dir.iterdir()):
        m = re.match(r"(\d{1,2}) January (\d{4}).*\.(ods|xlsx)$",
                     path.name, re.I)
        if m:
            out[int(m.group(2))] = (path, datetime.date(
                int(m.group(2)), 1, int(m.group(1))))
    return out


# --------------------------------------------------------------------------- 
# deactivated index + panel
# ---------------------------------------------------------------------------

def load_deactivated(path: Path, real: bool) -> tuple[dict, dict]:
    deact: dict[str, dict] = {}
    info = {"rows": 0, "care_home_rows": 0, "duplicate_care_home_ids": 0}
    for kind, cells in ods_rows(path):
        if kind == "header":
            hdr = {h.strip().lower(): i for i, h in enumerate(cells)}
            def col(name):
                for k, i in hdr.items():
                    if k == name:
                        return i
                return None
            c_id, c_ch = col("location id"), col("care home?")
            c_end, c_status = col("location hsca end date"), col("location status")
            c_name = col("location name")
            if None in (c_id, c_ch, c_end):
                raise BuildError(f"deactivated header missing core columns: "
                                 f"{sorted(hdr)[:8]}...")
            continue
        if kind != "row":
            continue
        info["rows"] += 1
        if (cells[c_ch] or "").strip() != "Y":
            continue
        info["care_home_rows"] += 1
        lid = (cells[c_id] or "").strip()
        if lid in deact:
            info["duplicate_care_home_ids"] += 1
        deact[lid] = {
            "end": dparse(cells[c_end]) if c_end is not None else None,
            "status": (cells[c_status] or "").strip() if c_status is not None else "",
            "name": (cells[c_name] or "").strip() if c_name is not None else "",
        }
    return deact, info


def read_vintage(path: Path, real: bool) -> tuple[list[dict], dict]:
    """One vintage file -> care-home records + diagnostics."""
    recs, diag = [], {"resolved": {}, "stamp_rows": [], "rows": 0,
                      "care_homes": 0, "missing_pub": 0, "missing_beds": 0,
                      "missing_start": 0}
    resolution = None
    T = None
    for kind, cells in sheet_rows(path):
        if kind == "stamp":
            diag["stamp_rows"].append([c for c in cells if c][:3])
            continue
        if kind == "header":
            resolution = resolve_header(cells)
            missing = [f for f, pat in REQUIRED_FIELDS.items()
                       if f not in resolution["idx"]]
            diag["resolved"] = {k: v for k, v in resolution["idx"].items()}
            diag["missing_required"] = missing
            if missing:
                return [], diag     # caller drops the instant, loudly
            continue
        diag["rows"] += 1
        idx = resolution["idx"]
        if (cells[idx["care_home"]] or "").strip() != "Y":
            continue
        diag["care_homes"] += 1
        lid = (cells[idx["location_id"]] or "").strip()
        beds_raw = (cells[idx["beds"]] or "").strip()
        beds = int(beds_raw) if beds_raw.isdigit() else -1
        if beds < 0:
            diag["missing_beds"] += 1
        start = dparse(cells[idx["start"]])
        if start is None:
            diag["missing_start"] += 1
        pub = dparse(cells[idx["pub"]])
        if pub is None:
            diag["missing_pub"] += 1
        svc_n = svc_r = 0
        svc_other = 0
        for i, label in resolution["svc_types"]:
            if i >= len(cells):
                continue
            text = label.lower()
            if ("care home" in text and "nursing" in text
                    and "without" not in text):
                if yessy(cells[i]):
                    svc_n = 1
            elif "care home" in text and "without nursing" in text:
                if yessy(cells[i]):
                    svc_r = 1
            elif yessy(cells[i]):
                svc_other += 1
        bands = {"users_other_count": 0}
        for key, needles in USER_BAND_KEYS:
            bands[key] = -1
        for i, label in resolution["user_bands"]:
            if i >= len(cells):
                continue
            hit = yessy(cells[i])
            low = label.lower()
            for key, needles in USER_BAND_KEYS:
                if any(n in low for n in needles):
                    bands[key] = hit
                    break
            else:
                bands["users_other_count"] += hit
        rating_raw = (cells[idx["rating"]] or "").strip()
        inherited = (cells[idx["inherited"]] or "").strip() \
            if "inherited" in idx else "unknown"
        sector = (cells[idx["sector"]] or "").strip() \
            if "sector" in idx else "unknown"
        recs.append({
            "location_id": lid,
            "care_home_beds": beds,
            "latest_overall_rating": rating_raw if rating_raw else "Not rated",
            "pub": pub,
            "start": start,
            "local_authority": (cells[idx["la"]] or "").strip() or "unknown",
            "region": (cells[idx["region"]] or "").strip() or "unknown",
            "inherited_rating": inherited if inherited else "unknown",
            "provider_sector": sector if sector else "unknown",
            "svc_nursing": svc_n,
            "svc_residential": svc_r,
            "svc_other_count": svc_other,
            "bands": bands,
            "name": "",
        })
    return recs, diag


def production_stamp(diag: dict, filename_T: datetime.date):
    """Cross-check the in-file production stamp against the filename date."""
    stamp = None
    for row in diag.get("stamp_rows", []):
        joined = " ".join(str(c) for c in row)
        m = re.search(r"produced on (\d{1,2}\s+\w+\s+\d{4})", joined, re.I)
        if not m:
            m = re.search(r"produced on (\d{1,2}/\d{1,2}/\d{4})", joined, re.I)
        if m:
            raw = m.group(1)
            d = dparse(raw.replace(" ", "/")) if "/" in raw else None
            if d is None:
                months = {m_.lower(): i for i, m_ in enumerate(
                    ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November",
                     "December"], 1)}
                parts = raw.split()
                if len(parts) == 3 and parts[1].lower() in months:
                    d = datetime.date(int(parts[2]), months[parts[1].lower()],
                                      int(parts[0]))
            stamp = {"raw": raw, "parsed": d.isoformat() if d else None}
            break
    return stamp


def build_panel(vintages: dict, deact: dict, real: bool, stats: dict):
    """vintages: year -> (path, T). Returns splits dict + diagnostics."""
    splits = {name: [] for name in SPLIT_NAMES}
    per_instant = {}
    for year in sorted(vintages):
        path, T = vintages[year]
        recs, diag = read_vintage(path, real)
        if diag.get("missing_required"):
            per_instant[str(year)] = {"status": "DROPPED",
                                      "reason": f"unresolved required columns: "
                                                f"{diag['missing_required']}",
                                      "diagnostics": diag}
            continue
        stamp = production_stamp(diag, T)
        window_end = T + datetime.timedelta(days=365)
        pos = later = 0
        pub_after_T = 0
        status_mix = Counter()
        rows = []
        for rec in recs:
            d = deact.get(rec["location_id"])
            label = 0
            if d is not None:
                later += 1
                if d["end"] is not None and T < d["end"] <= window_end:
                    label = 1
                    status_mix[d["status"]] += 1
            if rec["pub"] is not None and rec["pub"] > T:
                pub_after_T += 1
            recency = "unrated"
            if rec["pub"] is not None:
                days = (T - rec["pub"]).days
                if days < 0:
                    recency = "future"
                else:
                    recency = "unknown_pub"
                    for limit, label_text in RATING_RECENCY_BUCKETS:
                        if days <= limit:
                            recency = label_text
                            break
                    else:
                        recency = ">=3y"
            start_year = rec["start"].year if rec["start"] else -1
            key = hashlib.sha256(
                f"{SALT}|{T.year}|{rec['location_id']}".encode()).hexdigest()[:16]
            row = {
                "location_key": key,
                "instant": f"{T.year:04d}-{T.month:02d}",
                "care_home_beds": rec["care_home_beds"],
                "beds_bucket": bucket_index(rec["care_home_beds"], BEDS_BUCKETS)
                if rec["care_home_beds"] >= 0 else "unknown",
                "latest_overall_rating": rec["latest_overall_rating"],
                "rating_recency_bucket": recency,
                "inherited_rating": rec["inherited_rating"],
                "hsca_start_year": start_year,
                "local_authority": rec["local_authority"],
                "region": rec["region"],
                "provider_sector": rec["provider_sector"],
                "svc_nursing": rec["svc_nursing"],
                "svc_residential": rec["svc_residential"],
                "svc_other_count": rec["svc_other_count"],
                "users_dementia": rec["bands"]["users_dementia"],
                "users_older_people": rec["bands"]["users_older_people"],
                "users_learning_disabilities": rec["bands"]["users_learning_disabilities"],
                "users_physical_disability": rec["bands"]["users_physical_disability"],
                "users_mental_health": rec["bands"]["users_mental_health"],
                "users_other_count": rec["bands"]["users_other_count"],
                TARGET: label,
                "_location_id": rec["location_id"],
            }
            rows.append(row)
            pos += label
        split = ("train" if year in TRAIN_YEARS
                 else "eval" if year == EVAL_YEAR
                 else "holdout" if year == HOLDOUT_YEAR else None)
        per_instant[str(year)] = {
            "status": "built", "T": T.isoformat(),
            "window": [T.isoformat(), window_end.isoformat()],
            "production_stamp": stamp, "rows": len(rows), "positives": pos,
            "later_deactivated": later, "pub_after_T": pub_after_T,
            "positives_status_mix": dict(status_mix),
            "diagnostics": {k: v for k, v in diag.items() if k != "stamp_rows"},
        }
        if split is None:
            per_instant[str(year)]["status"] = "BUILT-NOSPLIT"
            continue
        splits[split].extend(rows)
    return splits, per_instant


# --------------------------------------------------------------------------- 
# artifact + quality
# ---------------------------------------------------------------------------

TASK_KEYS = ("name", "description", "target", "positive_label", "id_columns",
             "split", "columns", "rows")


def write_artifact(out: Path, splits: dict, built_at: str) -> dict:
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)
    (out / "auxiliary").mkdir(parents=True, exist_ok=True)
    meta_splits = {}
    for name, path in (("train", "public/train.csv"), ("eval", "public/eval.csv"),
                       ("holdout", "private/holdout.csv")):
        rows = splits[name]
        with (out / path).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            for row in rows:
                writer.writerow([row[c] for c in COLUMNS])
        positives = sum(1 for r in rows if r[TARGET] == 1)
        meta_splits[name] = {
            "path": path, "rows": len(rows), "positives": positives,
            "positive_rate": (positives / len(rows)) if rows else 0.0,
        }
    # auxiliary: the real location ids, staging-side only (never solver-visible)
    with (out / "auxiliary" / "location_map.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["instant", "location_key", "location_id"])
        for name in SPLIT_NAMES:
            for row in splits[name]:
                writer.writerow([row["instant"], row["location_key"],
                                 row["_location_id"]])
    train = splits["train"]
    description = (
        "At the production instant of a CQC 'HSCA Active Locations' monthly "
        "vintage T, for every care home active at T, predict whether the "
        "location's CQC registration ends within the following 12 months "
        "(register event: Location Status Inactive-Dereg or Removed with a "
        "Location HSCA End Date in (T, T+365d]).")
    meta = {
        "name": NAME,
        "description": description,
        "target": TARGET,
        "positive_label": POSITIVE,
        "id_columns": ID_COLUMNS,
        "split": ("temporal by vintage instant: train = January vintages "
                  "2016-2022 (every train outcome window closes >= 12 months "
                  "before the eval instant), eval = the January 2024 vintage, "
                  "holdout = the January 2025 vintage; the 2023 vintage is "
                  "excluded by design because its 12-month label window would "
                  "still be open at the eval prediction instant"),
        "columns": COLUMNS,
        "rows": {k: v["rows"] for k, v in meta_splits.items()},
        "positive_rate": {k: v["positive_rate"] for k, v in meta_splits.items()},
        "built_at_utc": built_at,
        "splits": meta_splits,
        "feature_columns": FEATURES,
    }
    missing = [k for k in TASK_KEYS if k not in meta]
    if missing:
        raise BuildError(f"meta.json missing TASK_KEYS: {missing}")
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def feature_evidence() -> dict:
    def vintage_col(column, source, status="verified"):
        return {"source": source,
                "availability": ("the T vintage's own column, published at "
                                 "the instant (the register state at "
                                 "production)"),
                "status": status}
    fe = {
        "location_key": {
            "source": "per-instant pseudonym sha256(salt|instant|location_id)[:16]",
            "availability": ("identity of the row; deliberately NOT linkable "
                            "across instants (the missing-successor rule, the "
                            "unhcr P0 class)"),
            "status": "verified"},
        "instant": {
            "source": "the vintage's production month (YYYY-MM), from the "
                      "archived file's dated name",
            "availability": "the prediction instant itself",
            "status": "verified"},
        "care_home_beds": vintage_col(
            "care_home_beds", "the vintage's 'Care homes beds' column"),
        "beds_bucket": {
            "source": "fixed bucket of care_home_beds (1-3/4-10/11-25/26-50/51+)",
            "availability": "derived from a vintage column at the instant",
            "status": "verified"},
        "latest_overall_rating": vintage_col(
            "latest_overall_rating",
            "the vintage's 'Location Latest Overall Rating' column (blank -> "
            "'Not rated'; the ~2024 single-assessment change leaves more "
            "multi-service locations unrated - an era property, recorded)"),
        "rating_recency_bucket": {
            "source": "fixed recency bucket of (T - 'Publication Date'), "
                      "the rating's publication date as stamped in the vintage",
            "availability": ("the vintage's own stamp; buckets are coarsened "
                             "deliberately so the column cannot serve as a "
                             "cross-instant quasi-identifier"),
            "status": "verified"},
        "inherited_rating": vintage_col(
            "inherited_rating", "the vintage's 'Inherited Rating' field verbatim"),
        "hsca_start_year": {
            "source": "the calendar year of the vintage's 'Location HSCA "
                      "start date' (-1 when absent)",
            "availability": ("registration age at T, coarsened to the start "
                             "year deliberately: instant-invariant, so a "
                             "solvers' cross-instant quasi-join must collide "
                             "to link, which the gate probe measures"),
            "status": "verified"},
        "local_authority": vintage_col(
            "local_authority", "the vintage's 'Location Local Authority' column"),
        "region": vintage_col("region", "the vintage's 'Location Region' column"),
        "provider_sector": {
            "source": "the vintage's provider type/sector column",
            "availability": ("the provider's sector AT T only; the provider's "
                             "identity, CH/charity numbers and any "
                             "sister-location outcome aggregate are "
                             "deliberately NOT shipped (the za-statsa/acnc "
                             "cross-row shape)"),
            "status": "verified"},
        "svc_nursing": {
            "source": "the vintage's service-type flag 'Care home service "
                      "with nursing' (-1 when the column is absent in an "
                      "early vintage)",
            "availability": "vintage column at the instant",
            "status": "verified"},
        "svc_residential": {
            "source": "the vintage's service-type flag 'Care home service "
                      "without nursing' (-1 when absent)",
            "availability": "vintage column at the instant",
            "status": "verified"},
        "svc_other_count": {
            "source": "count of the vintage's other 'Service type - *' Y flags",
            "availability": "vintage columns at the instant",
            "status": "verified"},
    }
    for key, needles in USER_BAND_KEYS:
        fe[key] = {
            "source": ("the vintage's 'Service user band - *' flag matching "
                       + " or ".join(repr(n) for n in needles)
                       + " (-1 when the band column is absent in an early "
                         "vintage)"),
            "availability": "vintage column at the instant",
            "status": "verified"}
    fe["users_other_count"] = {
        "source": "count of the vintage's other 'Service user band - *' Y flags",
        "availability": "vintage columns at the instant",
        "status": "verified"}
    return fe


def build_quality(meta: dict, per_instant: dict, splits: dict, stats: dict,
                  built_at: str, deact_info: dict, lag: dict) -> dict:
    positive_events = {}
    for name in SPLIT_NAMES:
        rows = splits[name]
        positives = sum(1 for r in rows if r[TARGET] == 1)
        positive_events[name] = {
            "positives": positives,
            "distinct_events": len({r["location_key"] for r in rows
                                    if r[TARGET] == 1}),
        }
    # measured high-cardinality declaration: mirror the gate's rule
    # (levels > max(1, rows // 5)) over the actual built splits
    high_card = {"location_key"}
    for name in SPLIT_NAMES:
        rows = splits[name]
        limit = max(1, len(rows) // 5)
        for column in COLUMNS:
            if column in high_card or column == TARGET:
                continue
            try:
                [float(r[column]) for r in rows]
                continue    # numeric columns are scored directly
            except (ValueError, TypeError):
                if len({r[column] for r in rows}) > limit:
                    high_card.add(column)
    measurements = [
        {"column": "care_home_beds", "unit": "beds (integer)",
         "frame": "the location's registered care-home beds at T, as "
                  "published in the T vintage; -1 = not stated"},
        {"column": "hsca_start_year", "unit": "calendar year (integer)",
         "frame": "the year the location's HSCA registration started; -1 = "
                  "not stated"},
        {"column": "svc_nursing", "unit": "flag (0/1/-1)",
         "frame": "service-type flag at T; -1 = column absent in that vintage"},
        {"column": "svc_residential", "unit": "flag (0/1/-1)",
         "frame": "service-type flag at T; -1 = column absent in that vintage"},
        {"column": "svc_other_count", "unit": "count (integer)",
         "frame": "other registered service types at T"},
        {"column": "users_other_count", "unit": "count (integer)",
         "frame": "other service user bands at T"},
        {"column": "instant", "unit": "YYYY-MM",
         "frame": "the vintage production month, Europe/London"},
    ]
    for key, _ in USER_BAND_KEYS:
        measurements.append({
            "column": key, "unit": "flag (0/1/-1)",
            "frame": "service user band flag at T; -1 = column absent in "
                     "that vintage"})
    observations = []
    for year in sorted(per_instant, key=lambda y: int(y)):
        entry = per_instant[year]
        if entry.get("status") != "built":
            continue
        observations.append({
            "period": f"{int(year)}-01",
            "period_end": entry["T"],
            "published": entry["T"],
            "note": ("the vintage is an administrative register snapshot: its "
                     "production date IS the instant; in-file production "
                     "stamp: " + json.dumps(entry.get("production_stamp"))),
        })
    quality = {
        "name": NAME,
        "built_at_utc": built_at,
        "task": {
            "question": (
                "At the production instant T of a CQC 'HSCA Active Locations' "
                "monthly vintage, for every care home active at T, will the "
                "location's CQC registration end within the following 12 "
                "months? A useful prediction gives local-authority "
                "commissioners and CQC market-oversight analysts a 12-month "
                "early warning on care-home capacity before a deregistration "
                "lands (the 2024 BMJ Public Health closure study is the "
                "policy reference)."),
            "prediction_time": (
                "the vintage's production date T (the dated archived file "
                "name; Europe/London). Features are the T vintage's own "
                "register columns - the state CQC published at T. The 12-"
                "month outcome window (T, T+365d] lies entirely after the "
                "instant. Worked example: Park Hills Nursing Home "
                "(1-113831768, Oldham, 17 beds, Good published 26/08/2022, "
                "HSCA start 01/02/2011) is active in the 05 January 2024 "
                "vintage; its registration ended 01/02/2024, inside (T, "
                "T+365d], so its label is 1."),
        },
        "target": TARGET,
        "positive_label": POSITIVE,
        "positive_label_text": POSITIVE_LABEL_TEXT,
        "id_columns": ID_COLUMNS,
        "id_columns_are_entity_keys": True,
        "id_columns_note": ("location_key = sha256(salt|instant|location_id)"
                            "[:16] names one location-instant with one label; "
                            "unique across the panel, asserted at "
                            "construction; the key is deliberately different "
                            "for the same location at different instants"),
        "time_column": TIME_COLUMN,
        "event_key_column": EVENT_KEY_COLUMN,
        "event_key_note": (
            "an event is one care-home location's 12-month deregistration at "
            "one vintage instant, so the distinct-event count the gate "
            "recomputes from location_key is the number of distinct "
            "deregistering locations (measured ~700-800 care-home register "
            "events per year 2019-2025). The dependence that matters "
            "scientifically is PROVIDER clustering (a provider's homes exit "
            "together) and common-year shocks; provider identity does not "
            "ship (P0 design), so provider-clustered intervals cannot be "
            "computed over the shipped frame - recorded as a limitation, "
            "with the discovery measurement (376-877 distinct providers per "
            "deregistration year) as the dependence evidence"),
        "split_windows": SPLIT_WINDOWS,
        "split_boundaries": {
            "train": "vintage instants 2016-01..2022-01 (January vintages; "
                     "rows within [2016-01-01, 2023-01-01))",
            "eval": "the 2024-01 vintage only",
            "holdout": "the 2025-01 vintage only",
        },
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "positive_events": positive_events,
        "positive_events_note": (
            "each positive is one location-instant; the underlying events are "
            "the register's own deregistrations (measured ~700-800 care-home "
            "register events per year 2019-2025, CQC Deactivated Locations)"),
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "shipped_columns": COLUMNS,
        "label_source_columns": [
            "the CQC Location ID (the join key to the Deactivated Locations "
            "file) - present in NO shipped column; only the per-instant "
            "pseudonym location_key ships, and the real ids live in "
            "auxiliary/location_map.csv outside every solver-visible frame",
            "'Location HSCA End Date' and 'Location Status' from the "
            "Deactivated Locations file - the label operands; never shipped",
            "'Care home?' - the eligibility flag, consumed at construction; "
            "every shipped row is a care home by construction",
        ],
        "post_hoc_columns": [
            "every Deactivated Locations column (end date, status, beds at "
            "deactivation, rating at deactivation) - post-hoc at T and the "
            "label's own operands; excluded from all split files",
            "the location's presence/absence in any LATER vintage - the "
            "missing-successor channel; structurally unreadable because no "
            "shipped frame contains a later instant of the scored rows "
            "(single-instant eval/holdout) and no shippable column links a "
            "location across instants",
            "provider identity, Companies House number, charity number, "
            "provider name, location name, address, postcode - linkage "
            "keys; excluded from all split files",
        ],
        "expected_duplicate_ids": 0,
        "high_cardinality_columns": sorted(high_card),
        "high_cardinality_columns_note": (
            "location_key is the row identity (one pseudonym per location-"
            "instant, unique by construction). Its per-level statistics "
            "memorise single rows, so it is declared a free identity field "
            "rather than scored as a leak; it carries no cross-instant "
            "information because the hash includes the instant. Any other "
            "column listed here tripped the gate's own measured rule "
            "(distinct levels > rows/5) on at least one split of THIS "
            "artifact - a panel-size property, not a leak claim; on the full "
            "artifact only the identity column is expected to trip"),
        "external_threshold": False,
        "threshold_note": (
            "no external threshold: the label is a register event inside a "
            "fixed 12-month window. The dated fixtures (Park Hills label 1; "
            "Henley House label 0; Options Hazel House end 05/03/2025 -> "
            "label 0 at T=2024-01-05) and the eval-instant counts (14,765 "
            "care homes, 758 positives, 2,076 later-deactivated, 0 rating "
            "publication dates after T) are asserted in-build against the "
            "2026-11-03 discovery measurements"),
        "measurements": measurements,
        "timing": {
            "prediction_instant": {
                "kind": "period_end",
                "period": "the vintage snapshot itself: an administrative "
                          "register extract whose 'period' IS its production "
                          "instant T",
                "days_after_period_end": 0,
                "citation": (
                    "CQC care directory with filters ('HSCA Active "
                    "Locations'), monthly, archived 2011-2026 in CQC's public "
                    "Google Drive archive (the dated file names, e.g. '05 "
                    "January 2024 HSCA Active Locations.ods'); every feature "
                    "column is read from the T vintage's own bytes. The "
                    "as-of property is asserted at construction: 0 of the "
                    "14,765 eval-instant rows carry a rating Publication "
                    "Date after T. Real historical vintages - not a "
                    "reconstruction"),
            },
            "features": {
                "period": "the T vintage's own columns (register state at "
                           "production)",
                "published_days_after_period_end": 0,
                "source_kind": "administrative_record",
            },
            "row_selection": {
                "latest_period_used": "2025-01",
                "fields": [
                    "'Care home?' = Y in the T vintage (the vintage's own "
                    "column, read at T)",
                    "the location is active at T by construction of the "
                    "HSCA Active Locations product",
                ],
                "basis": (
                    "membership reads only the T vintage; the label is looked "
                    "up afterwards, solely to compute the label. No censoring "
                    "bucket exists: every scored window (T, T+365d] lies fully "
                    "inside the Deactivated Locations file's coverage "
                    "(asserted in-build with a margin check)"),
            },
            "observations": observations,
        },
        "evaluation_contract": {
            "use": "retrospective_research",
            "access": "isolated_rows",
            "training_label_timing": "unverified",
            "scope_note": (
                "each row is one care-home location at one vintage instant. "
                "Features are genuinely as-of: they are read from the real "
                "archived monthly vintage CQC published at T (the feature "
                "side is stronger than a reconstructed snapshot). Labels "
                "are read from the CURRENT cumulative Deactivated Locations "
                "edition (2026-11-02) rather than from the register editions "
                "that existed at each window's end, and per-window register "
                "editions are not archived - so label timing is unverified "
                "and the scope is retrospective research, not certified "
                "historical forecasting. The isolated-rows declaration is "
                "the required posture for the probe-measured quasi-identifier "
                "exposure and is not an enforcement claim. Labeled eval is "
                "development/validation; the holdout is the final test and "
                "stays sealed"),
            "feature_evidence": feature_evidence(),
            "vintage": {
                "kind": "as_of",
                "evidence": (
                    "real historical vintages: January editions 2016-2022 + "
                    "2024 + 2025 downloaded from CQC's public Drive archive "
                    "at build time, every file pinned by size+sha256 in "
                    "summary.json (the 2024-01 vintage asserted against the "
                    "2026-11-03 discovery pins ac40b6f8/26,147,266 B); the "
                    "as-of check (0 rows with rating Publication Date after "
                    "T) is asserted on the eval instant"),
            },
            "selection": {
                "kind": "prediction_time",
                "evidence": (
                    "a row exists iff its location is an active care home in "
                    "the T vintage ('Care home?' = Y) - decidable at the "
                    "instant from the instant's own product; the 2023 "
                    "January vintage is excluded by design so every train "
                    "outcome window closes >= 12 months before the eval "
                    "instant; no future field is read for membership"),
            },
            "limitations": [
                "register-event target: the event conflates service "
                "cessation with re-registration under a new legal entity "
                "(CQC's own in-file note; BMJ 2024 implies ~40-55% of "
                "register events are re-registrations). The label is the "
                "location's register exit, not a verified service closure",
                "labels come from the 2026-11-02 cumulative Deactivated "
                "Locations edition; per-window historical editions were not "
                "archived, so label timing at window end is unverified and "
                "the scope is retrospective research",
                "the eval instant's window closes two days after the holdout "
                "instant (T_eval+365 = 2025-01-05 > T_holdout = 2025-01-03): "
                "a property of yearly January instants, recorded, not repaired",
                "rating era break: from the ~2024 single-assessment approach, "
                "multi-service locations carry no location-level overall "
                "rating ('Not rated' share rises in later vintages; measured "
                "per instant in summary.json); the 1 April 2019 "
                "regulatory-history inheritance change affects the "
                "'Inherited Rating' field across eras",
                "no provider-group feature ships: provider identity, "
                "sister-location counts and trailing provider outcomes are "
                "excluded by the P0 design, so provider-clustered inference "
                "is not directly supported; the BMJ evidence says chain "
                "effects exist - a v2 question, not a silent gap",
                "dormant-but-registered locations may sit in the at-T "
                "population (CQC publishes no dormant bulk product)",
                "publisher system-migration delay on registration "
                "cancellations (CQC data-page note): recent-month label lag "
                "measured and recorded in summary.json (lag_check); the "
                "holdout window ends 2026-01, 10 months inside the "
                "deactivated file's coverage",
                "England only; one regulator; generalisation beyond CQC's "
                "register is not established",
            ],
            "cross_row_audit": {
                "rationale": (
                    "the decisive exposure for a multi-instant register panel "
                    "is the missing-successor rule (the unhcr P0): a row's "
                    "label is recoverable from the PRESENCE of the same "
                    "location at a later instant. Structural mitigation, not "
                    "a declaration: (1) each scored frame carries a single "
                    "instant - the successor rows of eval rows exist only in "
                    "the sealed holdout, and holdout rows have no successor "
                    "instant in the artifact; (2) location identity ships as "
                    "a per-instant pseudonym and no id, name, address, "
                    "postcode, provider id or CH number ships, so no exact "
                    "cross-instant link exists; (3) train instants stop at "
                    "2022 so every train window closes a year before the eval "
                    "instant. Probe 1 executes the successor-presence attack "
                    "over the strongest instant-invariant quasi-key (LA x "
                    "beds x start-year x rating x sector) with a +12-month "
                    "offset and measures coverage and mismatch per split; "
                    "coverage inside train measures the quasi-linkage rate "
                    "where labels are already public, and coverage on "
                    "eval/holdout is the measured bound on the attack over "
                    "the frames a solver can see (expected 0 - no successor "
                    "rows are visible). Probe 0 proves the pseudonym id "
                    "channel is dead. A covered probe requires the "
                    "isolated_rows access declared above"),
                "auxiliary_files_review": (
                    "the artifact ships exactly public/train.csv, "
                    "public/eval.csv, private/holdout.csv, meta.json and "
                    "quality.json. auxiliary/location_map.csv (instant, "
                    "location_key, real CQC Location ID) is uploaded to "
                    "private staging for label verification and reproduction "
                    "only - it is never mounted into an evaluated agent's "
                    "workspace and never a solver input; no other "
                    "outcome-bearing file exists. The downloaded vintage and "
                    "deactivated files stay in the job work-dir with "
                    "size+sha256 recorded in summary.json and are not "
                    "uploaded"),
                "probes": [
                    {"name": "successor_presence_via_pseudonym_id",
                     "entity_columns": ["location_key"],
                     "time_column": "instant",
                     "offset_months": 12,
                     "left": "hsca_start_year",
                     "right": "hsca_start_year",
                     "right_row": "earlier",
                     "operation": "lt",
                     "note": ("the successor-presence attack over the row "
                              "id itself: a covered row would mean the same "
                              "pseudonym exists at a later instant, which "
                              "the per-instant hash forbids; expected "
                              "coverage 0 on every split")},
                    {"name": "successor_presence_via_quasi_key",
                     "entity_columns": ["local_authority", "care_home_beds",
                                         "hsca_start_year",
                                         "latest_overall_rating",
                                         "provider_sector"],
                     "time_column": "instant",
                     "offset_months": 12,
                     "left": "hsca_start_year",
                     "right": "hsca_start_year",
                     "right_row": "earlier",
                     "operation": "lt",
                     "note": ("the strongest successor-presence attack an "
                              "agent could run over the shipped frame: link "
                              "a row to a quasi-matching row 12 months later "
                              "(all five key columns are instant-invariant), "
                              "predict label 0 iff a unique successor "
                              "exists. The probe predicts 0 on every covered "
                              "row, so mismatch = positives among quasi-"
                              "linked rows and coverage = the measured "
                              "quasi-linkage rate. On eval/holdout no "
                              "successor instant is visible to the probe's "
                              "donor pool, so coverage there is the measured "
                              "bound on this attack; on train, where labels "
                              "are public anyway, coverage measures the "
                              "linkage rate itself")},
                ],
            },
        },
        "auxiliary_files": {
            "auxiliary/location_map.csv": (
                "staging-side verification input mapping each location_key "
                "to the real CQC Location ID per instant; never a solver "
                "input"),
        },
        "lag_check": lag,
        "deactivated_source": {
            "url": stats.get("deactivated", {}).get("url", DEACT_URL),
            "bytes": stats.get("deactivated", {}).get("bytes"),
            "sha256": stats.get("deactivated", {}).get("sha256"),
            "care_home_rows": deact_info.get("care_home_rows"),
            "duplicate_care_home_ids": deact_info.get("duplicate_care_home_ids"),
        },
    }
    return quality


def lag_check(deact: dict, stats: dict) -> dict:
    """Recent-month event counts vs the same months in prior years."""
    month_counts = Counter()
    for d in deact.values():
        if d["end"] is not None:
            month_counts[d["end"].isoformat()[:7]] += 1
    max_end = max((d["end"] for d in deact.values() if d["end"]), default=None)
    holdout_end = datetime.date(HOLDOUT_YEAR, 1, 1) + datetime.timedelta(days=365)
    check = {"max_end_date": max_end.isoformat() if max_end else None,
             "holdout_window_end": holdout_end.isoformat(),
             "margin_days": (max_end - holdout_end).days if max_end else None,
             "recent_months": {}}
    for month in sorted(month_counts)[-8:]:
        prior = [month_counts.get(f"{int(month[:4]) - k}{month[4:]}", 0)
                 for k in (1, 2, 3)]
        check["recent_months"][month] = {
            "events": month_counts[month], "same_month_prior_3y": prior}
    if max_end is None or max_end <= holdout_end:
        raise BuildError(f"holdout window end {holdout_end} not inside "
                         f"deactivated coverage (max end {max_end})")
    if (max_end - holdout_end).days < 60:
        raise BuildError(f"holdout window ends only {(max_end - holdout_end).days} "
                         f"days inside deactivated coverage; label lag risk")
    return check


def assert_fixtures(splits: dict, per_instant: dict, deact_info: dict):
    if deact_info["rows"] != EXPECTED_DEACT_ROWS:
        raise BuildError(f"deactivated rows {deact_info['rows']} != "
                         f"{EXPECTED_DEACT_ROWS}")
    if deact_info["care_home_rows"] != EXPECTED_DEACT_CARE_HOMES:
        raise BuildError(f"deactivated care homes {deact_info['care_home_rows']} "
                         f"!= {EXPECTED_DEACT_CARE_HOMES}")
    ev = per_instant.get(str(EVAL_YEAR), {})
    if ev.get("status") != "built":
        raise BuildError(f"eval instant {EVAL_YEAR} not built: {ev}")
    if ev["rows"] != EXPECTED_EVAL_CARE_HOMES:
        raise BuildError(f"eval care homes {ev['rows']} != "
                         f"{EXPECTED_EVAL_CARE_HOMES}")
    if ev["positives"] != EXPECTED_EVAL_POSITIVES:
        raise BuildError(f"eval positives {ev['positives']} != "
                         f"{EXPECTED_EVAL_POSITIVES}")
    if ev["later_deactivated"] != EXPECTED_EVAL_LATER_DEACT:
        raise BuildError(f"eval later-deactivated {ev['later_deactivated']} != "
                         f"{EXPECTED_EVAL_LATER_DEACT}")
    if ev["pub_after_T"] != 0:
        raise BuildError(f"as-of check failed: {ev['pub_after_T']} eval rows "
                         f"carry a rating Publication Date after T")
    by_id = {r["_location_id"]: r for r in splits["eval"]}
    for lid, want in FIXTURES.items():
        row = by_id.get(lid)
        if row is None:
            raise BuildError(f"fixture {lid} missing from the eval instant")
        for field, value in want.items():
            got = row[TARGET] if field == "label" else row[field]
            if str(got) != str(value):
                raise BuildError(f"fixture {lid} field {field}: got {got!r} "
                                 f"want {value!r}")


def assert_structure(splits: dict, per_instant: dict, real: bool):
    for name in SPLIT_NAMES:
        rows = splits[name]
        if not rows:
            raise BuildError(f"split {name} is empty")
        positives = sum(1 for r in rows if r[TARGET] == 1)
        if positives == 0 or positives == len(rows):
            raise BuildError(f"split {name} is single-class "
                             f"({positives}/{len(rows)})")
    train_years = [y for y in TRAIN_YEARS
                    if per_instant.get(str(y), {}).get("status") == "built"]
    if real and len(train_years) < MIN_TRAIN_INSTANTS:
        raise BuildError(f"only {len(train_years)} train instants resolved "
                         f"({train_years}); need >= {MIN_TRAIN_INSTANTS}")
    if not real and len(train_years) < 2:
        raise BuildError(f"synthetic panel needs >= 2 train instants, got "
                         f"{train_years}")
    if per_instant.get(str(EVAL_YEAR), {}).get("status") != "built":
        raise BuildError("the eval instant did not build")
    if per_instant.get(str(HOLDOUT_YEAR), {}).get("status") != "built":
        raise BuildError("the holdout instant did not build")
    for year in TRAIN_YEARS:
        entry = per_instant.get(str(year))
        if entry and entry.get("status") == "built":
            if not (10_000 <= entry["rows"] <= 20_000) and real:
                raise BuildError(f"instant {year} care-home rows {entry['rows']} "
                                 f"outside the expected 10k-20k band")
            if entry["positives"] < (100 if real else 2):
                raise BuildError(f"instant {year} positives {entry['positives']} "
                                 f"suspiciously low")
    # the one-column-list invariant
    if len(COLUMNS) != len(set(COLUMNS)):
        raise BuildError("duplicate shipped column names")
    keys = [r["location_key"] for name in SPLIT_NAMES for r in splits[name]]
    if len(keys) != len(set(keys)):
        raise BuildError("location_key values are not unique across the panel")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--built-at", required=True)
    parser.add_argument("--summary-out", required=True)
    parser.add_argument("--synthetic-dir",
                        help="read vintages + deactivated.ods from this dir "
                             "instead of the live harvest")
    parser.add_argument("--real-fixtures", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    real = args.synthetic_dir is None
    stats: dict = {"fetch": {}}

    if real:
        print("== harvest ==", flush=True)
        vintages = {}
        for year in TRAIN_YEARS + [EVAL_YEAR, HOLDOUT_YEAR]:
            path, T = download_vintage(year, work_dir, stats)
            print(f"  {year}: {path.name} T={T}", flush=True)
            vintages[year] = (path, T)
        deact_path = download_deactivated(work_dir, stats)
        print(f"  deactivated: {deact_path.name}", flush=True)
    else:
        synthetic = Path(args.synthetic_dir)
        vintages = load_synthetic_vintages(synthetic)
        deact_path = synthetic / "deactivated.ods"
        stats["synthetic"] = True
        print(f"== synthetic mode: {sorted(vintages)} ==", flush=True)

    print("== deactivated index ==", flush=True)
    deact, deact_info = load_deactivated(deact_path, real)
    print(f"  care homes indexed: {len(deact)} ({deact_info})", flush=True)

    print("== panel ==", flush=True)
    splits, per_instant = build_panel(vintages, deact, real, stats)
    for year in sorted(per_instant, key=int):
        e = per_instant[year]
        print(f"  {year}: {e.get('status')} rows={e.get('rows')} "
              f"pos={e.get('positives')}", flush=True)

    lag = lag_check(deact, stats) if real else {
        "note": "synthetic mode: lag check not applicable"}

    print("== assertions ==", flush=True)
    assert_structure(splits, per_instant, real)
    if args.real_fixtures:
        assert_fixtures(splits, per_instant, deact_info)
        print("  discovery fixtures reproduced exactly", flush=True)

    meta = write_artifact(out, splits, args.built_at)
    quality = build_quality(meta, per_instant, splits, stats, args.built_at,
                            deact_info, lag)
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    summary = {
        "name": NAME, "built_at_utc": args.built_at,
        "real": real,
        "vintages": {y: {"status": per_instant[y].get("status"),
                         **{k: v for k, v in per_instant[y].items()
                            if k != "diagnostics"},
                         "diagnostics": per_instant[y].get("diagnostics", {})}
                     for y in sorted(per_instant, key=int)},
        "deactivated": deact_info,
        "splits": meta["splits"],
        "fetch": stats,
        "lag_check": lag,
    }
    Path(args.summary_out).write_text(json.dumps(summary, indent=1) + "\n")
    for name in SPLIT_NAMES:
        s = meta["splits"][name]
        print(f"  {name}: {s['rows']} rows, {s['positives']} positives "
              f"({s['positive_rate']:.4f})", flush=True)
    print("build complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
