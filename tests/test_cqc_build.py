"""Synthetic rehearsal for the cqc-care-home-deregistration construction.

Real build.py over synthetic vintages (one plain XLSX, one XLSX carrying a
leading 'Readme' sheet before its data sheet - the real January 2019/2020/
2021 shape - and one README-only XLSX that must be dropped loudly, the rest
ODS) + a synthetic Deactivated Locations ODS -> the real qualification gate
over the full synthetic artifact -> exact-byte --accept -> score.py
references -> structural P0 assertions -> byte-identical rebuild -> red/green
mutations the gate must catch. No real data, no network.

The P0 properties this test pins (the design decisions of cqc-chd-001):

  * eval and holdout each carry a SINGLE instant - the successor rows of eval
    rows do not exist in any solver-visible frame;
  * the same location at different instants ships under DIFFERENT
    location_key values (per-instant pseudonym), and no raw CQC Location ID
    appears anywhere in the split CSVs;
  * the gate's successor probes read coverage 0 on eval/holdout (no visible
    successor rows) and measure the in-train quasi-linkage rate;
  * a mutated extract that smuggles a second instant into eval (re-opening
    the missing-successor channel) is REFUSED by the gate's split-window
    check;
  * a mutated extract with the timing block removed is REFUSED (the timing
    gate is never weakened to pass).
"""

import csv
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "candidates" / "cqc-care-home-deregistration" / "source" / "build.py"
SCORE = REPO / "candidates" / "cqc-care-home-deregistration" / "source" / "score.py"
GATE = REPO / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

# synthetic panel ------------------------------------------------------------
# location id -> (hsca start date, end date or None, beds, rating, pub, LA)
# Hand-named rows pin the fixture semantics; generated rows scale the panel
# past the gate's clustered-positive minimums (the za-cct rehearsal lesson).
def _make_locations():
    import random
    rng = random.Random(20261103)
    las = ["Oldham", "Suffolk", "Plymouth", "Lincolnshire", "Trafford", "Wirral"]
    ratings = ["Good", "Good", "Good", "Requires improvement", "Inadequate",
               "Outstanding", "Not rated"]
    locs = {
        # positive at the 2016 instant (ends inside (2016-01-08, 2017-01-08])
        "L001": ("2010-03-01", "2016-06-01", 17, "Good", "2014-05-01", "Oldham"),
        "L002": ("2011-07-01", "2016-11-20", 4, "Requires improvement",
                 "2015-02-11", "Suffolk"),
        # positive at the 2021 instant
        "L003": ("2012-01-05", "2021-09-15", 26, "Inadequate", "2020-08-02",
                 "Plymouth"),
        "L004": ("2013-02-01", "2021-12-30", 8, "Good", "2019-04-19", "Oldham"),
        # positive at the 2024 instant (ends inside (2024-01-05, 2025-01-05])
        "L005": ("2011-02-01", "2024-02-01", 17, "Good", "2022-08-26", "Oldham"),
        "L006": ("2014-10-01", "2024-11-05", 45, "Good", "2021-03-15", "Suffolk"),
        # positive at the 2025 instant
        "L007": ("2015-06-01", "2025-08-01", 12, "Inadequate", "2024-02-02",
                 "Plymouth"),
        "L008": ("2016-03-01", "2025-12-19", 6, "Good", "2023-11-11", "Wirral"),
        # survivors (label 0 everywhere they appear)
        "L010": ("2010-01-15", None, 66, "Good", "2022-04-20", "Suffolk"),
        "L011": ("2011-11-12", None, 4, "Good", "2022-07-09", "Lincolnshire"),
        "L012": ("2012-05-05", None, 39, "Good", "2023-08-10", "Trafford"),
        "L013": ("2013-07-07", None, 103, "Outstanding", "2018-06-01", "Wirral"),
        "L014": ("2014-04-04", None, 22, "Not rated", "", "Oldham"),
        "L015": ("2015-09-09", None, 9, "Requires improvement", "2024-12-01",
                 "Plymouth"),
    }
    _vintage_T = {2016: datetime.date(2016, 1, 8),
                  2021: datetime.date(2021, 1, 1),
                  2024: datetime.date(2024, 1, 5),
                  2025: datetime.date(2025, 1, 3)}
    end_windows = (
        [(2016, 35), (2021, 8), (2024, 35), (2025, 35), (None, 40)]
    )
    counter = 0
    for year, count in end_windows:
        for _ in range(count):
            counter += 1
            lid = f"G{counter:03d}"
            start_year = rng.choice([2010, 2011, 2012, 2013, 2014, 2015, 2016])
            start = f"{start_year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
            if year is None:
                end = None
            else:
                T = _vintage_T[year]
                offset = rng.randint(20, 360)
                e = T + datetime.timedelta(days=offset)
                # keep the end strictly inside (T, T+365d]
                end = e.isoformat()
            beds = rng.choice([3, 4, 6, 9, 12, 17, 22, 26, 39, 45, 52, 66, 103])
            rating = rng.choice(ratings)
            pub = ("" if rating == "Not rated"
                   else f"{rng.randint(2018, 2024)}-{rng.randint(1, 12):02d}-"
                        f"{rng.randint(1, 28):02d}")
            locs[lid] = (start, end, beds, rating, pub, rng.choice(las))
    return locs


LOCATIONS = _make_locations()
VINTAGES = {  # year -> (production date, format)
    2016: (datetime.date(2016, 1, 8), "xlsx"),
    # README-only workbook: no 'Location ID' header anywhere -> the instant
    # must be DROPPED loudly, never silently built as 0/0 (cqc-chd-001)
    2019: (datetime.date(2019, 1, 3), "xlsx-noheader"),
    # leading 'Readme' sheet before the data sheet - the real January
    # 2019/2020/2021 vintages' shape (probe/vintage_schema2_out.json)
    2021: (datetime.date(2021, 1, 1), "xlsx-readme"),
    2024: (datetime.date(2024, 1, 5), "ods"),
    2025: (datetime.date(2025, 1, 3), "ods"),
}
README_ROWS = [
    ["Active locations for providers registered under the Health and "
     "Social Care Act 2008"],
    ["Source: CQC database at 3 January 2019"],
    ["Management Information Requests Team/Performance and Planning"],
]
# active at instant = end date is None or end date > T
SERVICE_TYPES = ["Care home service with nursing", "Care home service without nursing",
                 "Shared lives", "Supported living"]
USER_BANDS = ["Dementia", "Older People", "Learning disabilities or autistic people",
             "Physical disability", "Mental health", "Acute", "Sensory"]


def active_at(end, T):
    return end is None or datetime.date.fromisoformat(end) > T


def vintage_rows(year):
    T, _ = VINTAGES[year]
    rows = []
    for lid, (start, end, beds, rating, pub, la) in LOCATIONS.items():
        if not active_at(end, T):
            continue
        svc = {"Care home service with nursing": "Y" if beds >= 20 else "N",
               "Care home service without nursing": "Y" if beds < 20 else "N",
               "Shared lives": "N", "Supported living": "N"}
        bands = {"Dementia": "Y" if beds >= 20 else "N", "Older People": "Y",
                 "Learning disabilities or autistic people": "N",
                 "Physical disability": "N", "Mental health": "N",
                 "Acute": "N", "Sensory": "N"}
        rows.append([
            lid, f"Home {lid}", "Y", str(beds), "RM " + lid, rating, pub, "No",
            start, la, "North West" if la in ("Oldham", "Trafford",
            "Lincolnshire", "Wirral") else "East of England" if la == "Suffolk"
            else "South West", "Private",
        ] + [svc[s] for s in SERVICE_TYPES] + [bands[b] for b in USER_BANDS])
    return rows


HEADER = (["Location ID", "Location Name", "Care home?", "Care homes beds",
           "Registered manager", "Location Latest Overall Rating",
           "Publication Date", "Inherited Rating", "Location HSCA start date",
           "Location Local Authority", "Location Region", "Provider Type-Sector"]
          + [f"Service type - {s}" for s in SERVICE_TYPES]
          + [f"Service user band - {b}" for b in USER_BANDS])

DEACT_HEADER = ["Location ID", "Location Name", "Location Status",
                "Location HSCA start date", "Location HSCA End Date",
                "Care home?", "Location Local Authority"]


def ods_writer(path, header, rows):
    def esc(text):
        return (str(text).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    body = ["<table:table table:name='T'>"]
    for row in [header] + rows:
        cells = "".join(
            f"<table:table-cell office:value-type='string'><text:p>{esc(v)}</text:p>"
            f"</table:table-cell>" for v in row)
        body.append(f"<table:table-row>{cells}</table:table-row>")
    body.append("</table:table>")
    content = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<office:document-content xmlns:office='urn:oasis:names:tc:opendocument:"
        "xmlns:office:1.0' xmlns:table='urn:oasis:names:tc:opendocument:xmlns:"
        "table:1.0' xmlns:text='urn:oasis:names:tc:opendocument:xmlns:text:1.0' "
        "xmlns:style='urn:oasis:names:tc:opendocument:xmlns:style:1.0'>"
        "<office:body><office:spreadsheet>" + "".join(body) +
        "</office:spreadsheet></office:body></office:document-content>")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("content.xml", content)


def xlsx_writer(path, header, rows, readme_rows=None, include_data_sheet=True):
    """Minimal OOXML: shared strings for text, serial dates for date columns.

    readme_rows: when given, a leading 'Readme' sheet is written before the
    data sheet - the real January 2019/2020/2021 vintages' shape (first
    sheet a README, data sheet second). With include_data_sheet=False the
    workbook carries ONLY the Readme sheet: a vintage with no 'Location ID'
    header anywhere (the loud-drop pin)."""
    date_cols = {HEADER.index("Location HSCA start date"),
                 HEADER.index("Publication Date")}
    shared: list[str] = []
    shared_idx: dict[str, int] = {}

    def s(text):
        if text not in shared_idx:
            shared_idx[text] = len(shared)
            shared.append(str(text))
        return shared_idx[text]

    def col_ref(i):
        letters = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            letters = chr(65 + r) + letters
        return letters

    def sheet_xml(all_rows, date_cells=True):
        xml_rows = []
        for r, row in enumerate(all_rows, 1):
            cells = []
            for c, value in enumerate(row):
                ref = f"{col_ref(c)}{r}"
                if date_cells and c in date_cols and value:
                    try:
                        serial = (datetime.date.fromisoformat(value)
                                  - datetime.date(1899, 12, 30)).days
                    except ValueError:
                        cells.append(f"<c r='{ref}' t='s'><v>{s(value)}</v></c>")
                    else:
                        cells.append(f"<c r='{ref}' s='1'><v>{serial}</v></c>")
                else:
                    cells.append(f"<c r='{ref}' t='s'><v>{s(value)}</v></c>")
            xml_rows.append(f"<row r='{r}'>{''.join(cells)}</row>")
        return ("<?xml version='1.0'?><worksheet xmlns='http://schemas."
                "openxmlformats.org/spreadsheetml/2006/main'><sheetData>"
                + "".join(xml_rows) + "</sheetData></worksheet>")

    sheets = []
    if readme_rows is not None:
        sheets.append(("Readme", sheet_xml(readme_rows, date_cells=False)))
    if include_data_sheet:
        sheets.append(("HSCA Active Locations", sheet_xml([header] + rows)))
    if not sheets:
        raise ValueError("xlsx_writer: no sheets requested")
    shared_xml = "".join(f"<si><t>{v}</t></si>" for v in shared)
    n = len(sheets)
    sheet_parts = [f"xl/worksheets/sheet{i + 1}.xml" for i in range(n)]
    overrides = "".join(
        f"<Override PartName='/{p}' ContentType='application/vnd."
        "openxmlformats-officedocument.spreadsheetml.worksheet+xml'/>"
        for p in sheet_parts)
    workbook = ("<?xml version='1.0'?><workbook xmlns='http://schemas."
                "openxmlformats.org/spreadsheetml/2006/main' xmlns:r='http://"
                "schemas.openxmlformats.org/officeDocument/2006/relationships'"
                "><sheets>"
                + "".join(f"<sheet name='{name}' r:id='rId{i + 1}'/>"
                          for i, (name, _) in enumerate(sheets))
                + "</sheets></workbook>")
    sheet_rels = "".join(
        f"<Relationship Id='rId{i + 1}' Type='http://schemas.openxmlformats."
        "org/officeDocument/2006/relationships/worksheet' "
        f"Target='worksheets/sheet{i + 1}.xml'/>" for i in range(n))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml",
                   "<?xml version='1.0'?><Types xmlns='http://schemas."
                   "openxmlformats.org/package/2006/content-types'>"
                   "<Default Extension='rels' ContentType='application/vnd."
                   "openxmlformats-package.relationships+xml'/><Default "
                   "Extension='xml' ContentType='application/xml'/><Override "
                   "PartName='/xl/workbook.xml' ContentType='application/vnd."
                   "openxmlformats-officedocument.spreadsheetml.sheet.main+xml'"
                   f"/>{overrides}<Override PartName='/xl/styles."
                   "xml' ContentType='application/vnd.openxmlformats-officedocument"
                   ".spreadsheetml.styles+xml'/><Override PartName='/xl/"
                   "sharedStrings.xml' ContentType='application/vnd."
                   "openxmlformats-officedocument.spreadsheetml.sharedStrings+xml'"
                   "/></Types>")
        z.writestr("_rels/.rels",
                   "<?xml version='1.0'?><Relationships xmlns='http://schemas."
                   "openxmlformats.org/package/2006/relationships'>"
                   "<Relationship Id='rId1' Type='http://schemas.openxmlformats."
                   "org/officeDocument/2006/relationships/officeDocument' "
                   "Target='xl/workbook.xml'/></Relationships>")
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels",
                   "<?xml version='1.0'?><Relationships xmlns='http://schemas."
                   "openxmlformats.org/package/2006/relationships'>"
                   + sheet_rels
                   + f"<Relationship Id='rId{n + 1}' Type='http://schemas."
                   "openxmlformats.org/officeDocument/2006/relationships/styles' "
                   f"Target='styles.xml'/><Relationship Id='rId{n + 2}' "
                   "Type='http://schemas.openxmlformats.org/officeDocument/2006/"
                   "relationships/sharedStrings' Target='sharedStrings.xml'/>"
                   "</Relationships>")
        z.writestr("xl/styles.xml",
                   "<?xml version='1.0'?><styleSheet xmlns='http://schemas."
                   "openxmlformats.org/spreadsheetml/2006/main'><cellXfs "
                   "count='2'><xf numFmtId='0'/><xf numFmtId='14'/></cellXfs>"
                   "</styleSheet>")
        z.writestr("xl/sharedStrings.xml",
                   "<?xml version='1.0'?><sst xmlns='http://schemas.openxmlformats."
                   "org/spreadsheetml/2006/main' count='1' uniqueCount='1'>"
                   f"{shared_xml}</sst>")
        for part, (_, xml) in zip(sheet_parts, sheets):
            z.writestr(part, xml)


def write_synthetic(root: Path):
    for year, (T, fmt) in VINTAGES.items():
        ext = "xlsx" if fmt.startswith("xlsx") else fmt
        name = f"{T.day:02d} January {year} HSCA Active Locations.{ext}"
        path = root / name
        if fmt == "ods":
            ods_writer(path, HEADER, vintage_rows(year))
        elif fmt == "xlsx":
            xlsx_writer(path, HEADER, vintage_rows(year))
        elif fmt == "xlsx-readme":
            xlsx_writer(path, HEADER, vintage_rows(year), readme_rows=README_ROWS)
        elif fmt == "xlsx-noheader":
            xlsx_writer(path, HEADER, [], readme_rows=README_ROWS,
                        include_data_sheet=False)
        else:
            raise ValueError(fmt)
    deact_rows = []
    for lid, (start, end, beds, rating, pub, la) in LOCATIONS.items():
        if end is None:
            continue
        deact_rows.append([lid, f"Home {lid}", "Inactive-Dereg", start, end,
                           "Y", la])
    ods_writer(root / "deactivated.ods", DEACT_HEADER, deact_rows)


def run(cmd, **kw):
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return proc


class CQCSyntheticRehearsal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="cqc-synth-"))
        cls.synth = cls.tmp / "synthetic"
        cls.synth.mkdir()
        write_synthetic(cls.synth)
        cls.out = cls.tmp / "extract"
        cls.summary = cls.tmp / "summary.json"
        proc = run([sys.executable, "-u", str(BUILD), "--out", str(cls.out),
                    "--work-dir", str(cls.tmp / "work"), "--built-at",
                    "2026-11-03T00:00:00Z", "--synthetic-dir", str(cls.synth),
                    "--summary-out", str(cls.summary)])
        assert proc.returncode == 0, f"build failed:\n{proc.stdout}\n{proc.stderr}"
        cls.build_log = proc.stdout
        cls.report = cls.tmp / "qualification.json"
        proc = run([sys.executable, str(GATE), str(cls.out), "--json",
                    "--report", str(cls.report)])
        assert proc.returncode == 0, f"gate failed:\n{proc.stdout}\n{proc.stderr}"
        cls.gate_report = json.loads(cls.report.read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def read_split(self, rel):
        with (self.out / rel).open() as handle:
            return list(csv.DictReader(handle))

    def test_01_gate_passed_with_zero_failed_checks(self):
        self.assertEqual(self.gate_report.get("failed_checks"), [])
        self.assertTrue(self.gate_report.get("ok"))

    def test_02_single_instant_scored_frames(self):
        evald = self.read_split("public/eval.csv")
        holdout = self.read_split("private/holdout.csv")
        self.assertEqual({r["instant"] for r in evald}, {"2024-01"})
        self.assertEqual({r["instant"] for r in holdout}, {"2025-01"})
        train = self.read_split("public/train.csv")
        self.assertEqual({r["instant"] for r in train}, {"2016-01", "2021-01"})

    def test_03_pseudonym_unlinkability_and_no_raw_ids(self):
        # a location active at several instants must carry a DIFFERENT key at
        # each instant, and no raw location id may appear in any split file
        with (self.out / "auxiliary" / "location_map.csv").open() as handle:
            mapping = list(csv.DictReader(handle))
        per_loc = {}
        key_instants = {}
        for row in mapping:
            per_loc.setdefault(row["location_id"], set()).add(
                row["location_key"])
            key_instants.setdefault(row["location_key"], set()).add(
                row["instant"])
        multi = {lid for lid, keys in per_loc.items() if len(keys) >= 1}
        seen_multi = 0
        for lid, keys in per_loc.items():
            n_instants = sum(1 for r in mapping if r["location_id"] == lid)
            if n_instants >= 2:
                seen_multi += 1
                self.assertGreaterEqual(len(keys), 2,
                                        f"{lid} carries one key across instants")
        self.assertGreater(seen_multi, 0, "no multi-instant location to test")
        for key, instants in key_instants.items():
            self.assertEqual(len(instants), 1,
                             f"pseudonym {key} appears at {instants}")
        raw = "\n".join((self.out / f).read_text() for f in
                        ("public/train.csv", "public/eval.csv",
                         "private/holdout.csv"))
        for lid in LOCATIONS:
            self.assertNotIn(lid, raw, f"raw location id {lid} shipped")

    def test_04_labels_match_the_deactivated_events(self):
        evald = self.read_split("public/eval.csv")
        with (self.out / "auxiliary" / "location_map.csv").open() as handle:
            mapping = list(csv.DictReader(handle))
        key_to_id = {m["location_key"]: m["location_id"] for m in mapping
                     if m["instant"] == "2024-01"}
        T = datetime.date(2024, 1, 5)
        end = T + datetime.timedelta(days=365)
        for row in evald:
            lid = key_to_id[row["location_key"]]
            end_date = LOCATIONS[lid][1]
            want = 1 if end_date and T < datetime.date.fromisoformat(end_date) <= end else 0
            self.assertEqual(int(row["deregistered_12m"]), want, lid)

    def test_05_successor_probes_no_eval_holdout_coverage(self):
        results = self.gate_report["results"]
        probe_results = {}
        for check in results:
            if check["check"].startswith("contract.cross_row_probe_"):
                probe_results[check["check"]] = check["evidence"]
        self.assertTrue(probe_results, "no probe results in the gate report")
        for name, results_per_split in probe_results.items():
            self.assertEqual(results_per_split["eval"]["covered"], 0,
                             f"{name}: eval successor coverage must be 0")
            self.assertEqual(results_per_split["holdout"]["covered"], 0,
                             f"{name}: holdout successor coverage must be 0")

    def test_06_accept_exact_bytes_then_score_references(self):
        proc = run([sys.executable, str(GATE), "--accept", str(self.report),
                    str(self.out)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        refs = self.tmp / "references.json"
        proc = run([sys.executable, str(SCORE), "--data", str(self.out),
                    "--accepted-report", str(self.report),
                    "--report", str(refs)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(refs.read_text())
        self.assertEqual(data["rows"]["eval"], len(self.read_split("public/eval.csv")))
        for name in ("local_authority_rate", "last_rating_rate",
                     "beds_bucket_rate", "hsca_start_year_rate"):
            self.assertIn(name, data["references"])

    def test_07_byte_identical_rebuild(self):
        out2 = self.tmp / "extract2"
        proc = run([sys.executable, "-u", str(BUILD), "--out", str(out2),
                    "--work-dir", str(self.tmp / "work2"), "--built-at",
                    "2026-11-03T00:00:00Z", "--synthetic-dir", str(self.synth),
                    "--summary-out", str(self.tmp / "summary2.json")])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for rel in ("public/train.csv", "public/eval.csv",
                    "private/holdout.csv", "meta.json", "quality.json",
                    "auxiliary/location_map.csv"):
            a = hashlib.sha256((self.out / rel).read_bytes()).hexdigest()
            b = hashlib.sha256((out2 / rel).read_bytes()).hexdigest()
            self.assertEqual(a, b, f"{rel} not byte-identical on rebuild")

    def test_08_red_second_eval_instant_refused_by_window_check(self):
        mutated = self.tmp / "mutated-window"
        shutil.copytree(self.out, mutated)
        with (mutated / "public/eval.csv").open() as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0].keys())
        dupes = [dict(r, instant="2023-01") for r in rows[:5]]
        with (mutated / "public/eval.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows + dupes)
        proc = run([sys.executable, str(GATE), str(mutated), "--json",
                    "--report", str(self.tmp / "m1.json")])
        self.assertNotEqual(proc.returncode, 0,
                             "a second eval instant must fail the gate")
        report = json.loads((self.tmp / "m1.json").read_text())
        names = [c["check"] for c in report["results"] if not c["ok"]]
        self.assertTrue(any("rows_within_declared_windows" in n or
                            "no_cross_split_entities" in n for n in names),
                        f"unexpected failure set: {names}")

    def test_09_red_timing_block_removed_refused(self):
        mutated = self.tmp / "mutated-timing"
        shutil.copytree(self.out, mutated)
        quality = json.loads((mutated / "quality.json").read_text())
        quality.pop("timing")
        (mutated / "quality.json").write_text(json.dumps(quality, indent=1))
        proc = run([sys.executable, str(GATE), str(mutated), "--json",
                    "--report", str(self.tmp / "m2.json")])
        self.assertNotEqual(proc.returncode, 0,
                            "removing the timing block must fail the gate")

    def test_10_stale_report_refused(self):
        # accept a report written for the ORIGINAL bytes against mutated bytes
        mutated = self.tmp / "mutated-bytes"
        shutil.copytree(self.out, mutated)
        quality = json.loads((mutated / "quality.json").read_text())
        quality["built_at_utc"] = "2026-11-04T00:00:00Z"
        (mutated / "quality.json").write_text(json.dumps(quality, indent=1))
        proc = run([sys.executable, str(GATE), "--accept", str(self.report),
                    str(mutated)])
        self.assertNotEqual(proc.returncode, 0,
                             "a report for different bytes must be refused")

    def test_11_leading_readme_sheet_built_and_no_header_dropped(self):
        # The cqc-chd-001 real-data drift, pinned on synthetic bytes: the
        # 2021-01 train instant must build from the SECOND sheet past a
        # leading 'Readme' sheet, and a vintage with no 'Location ID'
        # header anywhere must be DROPPED loudly - never silently built 0/0.
        summary = json.loads((self.tmp / "summary.json").read_text())
        vint = summary["vintages"]
        self.assertEqual(vint["2021"]["status"], "built")
        self.assertGreater(vint["2021"]["rows"], 0,
                           "the 2021 instant built no rows past the Readme sheet")
        self.assertEqual(vint["2019"]["status"], "DROPPED",
                         f"2019 was not dropped: {vint['2019']}")
        self.assertIn("no header row", vint["2019"]["reason"])
        train = self.read_split("public/train.csv")
        self.assertEqual({r["instant"] for r in train}, {"2016-01", "2021-01"})


if __name__ == "__main__":
    unittest.main()
