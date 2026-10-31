#!/usr/bin/env python3
"""End-to-end synthetic test for the acnc-charity-ais-deadline-compliance build.

Drives the real build.py over tiny synthetic AIS year CSVs and group-member
XLSX fixtures (relaxed publisher envelope, every structural/fixture-independent
assertion on), then the real qualification gate over the written extract, then
score.py against the accepted report. This mirrors the fixture-driven tests the
ipo build carries: it exists because four real defects (missing --summary-out,
row-vs-distinct confusion in the ABN-injectivity assertion, a Counter KeyError
on zero-count exclusion buckets, a synthetic-xlsx parse path) were caught by
exactly this loop before any worker launch.

The synthetic charities fail noisily (a hash-conditioned ~70%/~10% mix) so no
shipped feature can perfectly separate the label - the first version of this
fixture had deterministic outcomes and the gate correctly refused it as
leakage, which is also asserted here (a perfect separator must fail the gate).

Run from the repository root:
    python3 tests/test_acnc_build.py
"""
import csv
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "candidates/acnc-charity-ais-deadline-compliance/source/build.py")
GATE = os.path.join(ROOT, "skills/dataset-qualification/scripts/qualify_dataset.py")
SCORE = os.path.join(ROOT, "candidates/acnc-charity-ais-deadline-compliance/source/score.py")

HEADER = ["abn", "charity name", "charity size", "ais due date", "date ais received",
          "fin report from", "fin report to", "type of financial statement",
          "total revenue", "total expenses", "revenue from government", "total assets",
          "total liabilities", "net assets/liabilities", "total full time equivalent staff",
          "staff - volunteers"]


def d(date):
    return f"{date.day:02d}/{date.month:02d}/{date.year:04d}"


def fails(i, year):
    """Deterministic noisy outcome: delinquent cohort ~70%, reliable ~10%."""
    h = int(hashlib.sha256(f"{i}:{year}".encode()).hexdigest()[:8], 16)
    return (h % 1000) / 1000 < (0.70 if i >= 41 else 0.10)


def write_ais(src):
    abns = [f"{i:010d}7" for i in range(1, 81)]
    # two ACNC GROUP head entities sharing a 10-digit ABN prefix: if they ever
    # reached the frame the injectivity assertion must fail; the exclusion must drop them
    heads = ["91111111190", "91111111191"]
    for year in range(2019, 2025):
        rows = []
        for i, abn in enumerate(abns, start=1):
            if i == 41 and year == 2024:
                continue  # never lodges period 2024 -> 'never' positive
            fin_from, fin_to = datetime.date(year - 1, 7, 1), datetime.date(year, 6, 30)
            due = datetime.date(year + 1, 1, 31)
            recv = datetime.date(year + 1, 3, 15) if fails(i, year) else datetime.date(year, 12, 15)
            recv_date = "" if (i == 43 and year == 2022) or (i == 46 and year == 2021) else d(recv)
            financials = [""] * 8 if i == 47 else ["100000", "50000", "10000", "200000", "50000",
                                                   "150000", "5.5", "10"]
            rows.append([abn, f"Charity {i}", "Small" if i % 2 else "Large", d(due), recv_date,
                         d(fin_from), d(fin_to),
                         "General purpose financial statements" if i % 3 == 0
                         else "Special purpose financial statements",
                         *financials])
        for j, head in enumerate(heads):
            rows.append([head, f"Test Group {j}_ACNC GROUP", "Large", d(datetime.date(year + 1, 1, 31)),
                         d(datetime.date(year, 12, 15)), d(datetime.date(year - 1, 7, 1)),
                         d(datetime.date(year, 6, 30)), "Special purpose financial statements",
                         "100000", "50000", "10000", "200000", "50000", "150000", "5", "10"])
        with open(os.path.join(src, f"acnc_ais{year % 100:02d}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)


def write_xlsx(path, members):
    strings = ["ACNC group name", "member ABN", "member name", "membership start", "membership end"]
    for abn, name, start in members:
        strings += [f"Group of {name}", abn, name]
        if not isinstance(start, int):
            strings.append(str(start))
    body = []
    rows_iter = [("ACNC group name", "member ABN", "member name", "membership start", "membership end")] + \
                [(f"Group of {n}", a, n, s) for a, n, s in members]
    for ri, row_vals in enumerate(rows_iter, start=1):
        cells = []
        for ci, val in enumerate(row_vals):
            col = "ABCDE"[ci]
            if isinstance(val, str):
                cells.append(f'<c r="{col}{ri}" t="s"><v>{strings.index(val)}</v></c>')
            else:
                cells.append(f'<c r="{col}{ri}"><v>{val}</v></c>')
        body.append(f"<row>{''.join(cells)}</row>")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("_rels/.rels", "<Relationships/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
        zf.writestr("xl/sharedStrings.xml",
                    "<sst>" + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
        zf.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData>" + "".join(body) + "</sheetData></worksheet>")


def serial(date):
    return (date - datetime.date(1899, 12, 30)).days


def write_groups(src):
    abns = [f"{i:010d}7" for i in range(1, 81)]
    for year in range(2020, 2025):
        if year == 2024:
            members = [(abns[43], "Charity 44", serial(datetime.date(2020, 1, 1))),
                       (abns[44], "Charity 45", serial(datetime.date(2025, 6, 1))),
                       (abns[45], "Charity 46", "not-a-date")]
        elif year == 2023:
            # the 2021-format string dates ('dd/mm/yyyy 00:00:00'), like the real gm2021 file
            members = [(abns[1], "Charity 2", "10/01/2020 00:00:00")]
        else:
            members = [(abns[0], "Charity 1", serial(datetime.date(2015, 1, 1)))]
        write_xlsx(os.path.join(src, f"acnc_gm{year % 100:02d}.xlsx"), members)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    work = tempfile.mkdtemp(prefix="acnc-build-test-")
    try:
        src = os.path.join(work, "src")
        os.makedirs(src)
        write_ais(src)
        write_groups(src)
        extract = os.path.join(work, "extract")
        summary = os.path.join(work, "summary.json")
        r = run([sys.executable, BUILD, "--out", extract, "--work-dir", os.path.join(work, "wd"),
                 "--source-dir", src, "--relax-expected", "--built-at", "2026-10-31T00:00:00Z",
                 "--summary-out", summary])
        assert r.returncode == 0, f"build failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
        qual_path = os.path.join(work, "qual.json")
        r = run([sys.executable, GATE, extract, "--json", "--report", qual_path])
        assert r.returncode == 0, f"gate failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
        qual = json.load(open(qual_path))
        assert not qual["failed_checks"], qual["failed_checks"]
        # the group-head synthetic block must be excluded from the frame
        with open(os.path.join(extract, "public", "train.csv"), newline="") as f:
            shipped_abns = {r["abn"] for r in csv.DictReader(f)}
        assert not any(a.startswith("9111111") for a in shipped_abns), "group heads leaked into the frame"
        probe = next(x for x in qual["results"] if x["check"].startswith("contract.cross_row_probe"))
        ev = probe["evidence"]
        # the adjacent-target-year exposure must be measured, not assumed:
        # covered donor rows recover the earlier row's label with zero mismatches
        assert ev["train"]["covered"] > 0 and ev["train"]["mismatches"] == 0, ev
        assert ev["eval"]["covered"] > 0 and ev["eval"]["mismatches"] == 0, ev
        refs = os.path.join(work, "refs.json")
        r = run([sys.executable, SCORE, "--data", extract, "--accepted-report", qual_path,
                 "--report", refs])
        assert r.returncode == 0, f"score failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
        out = json.load(open(refs))
        assert out["references"]["persistence_momentum"]["eval_auc"] is not None
        assert out["paired_differences"]["persistence_flag_vs_calendar"]["resampler_alignment_ok"]
        # red/green: a perfect separator must be refused by the gate (leakage check bites)
        with open(os.path.join(extract, "public", "eval.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        with open(os.path.join(extract, "public", "eval.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            for row in rows:
                row["prior_lateness_positive"] = row["failed_by_due"]  # the answer itself
                w.writerow(row)
        r = run([sys.executable, GATE, extract, "--json", "--report", os.path.join(work, "q2.json")])
        assert r.returncode != 0, "the gate must refuse a column that reconstructs the label"
        q2 = json.load(open(os.path.join(work, "q2.json")))
        assert "leakage.no_single_column_determines_the_target" in q2["failed_checks"], q2["failed_checks"]
        print("test_acnc_build: OK (build -> gate 0 failed -> references -> leakage red/green)")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
