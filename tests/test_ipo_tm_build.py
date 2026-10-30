"""Offline tests for the ipo-trademark-registration-outcome construction script.

Bounded synthetic verification of the fixtures stage and the parse/classify
loop, written after ipo-tm-001 failed at 7.3 s: check_fixtures passed a bare
``Counter()`` as iter_records' hazards argument, so
``hazards["field_counts"][len(fields)] += 1`` subscripted the int a Counter
returns for a missing key (TypeError, before any parse). No bulk download
happens here - the tests build small IPO-shaped snapshots in a tempdir and
exercise the real functions against them.

The module is loaded with ``exec(compile(...))`` rather than through an
import, because a normal import writes ``__pycache__`` into the job's source
directory, which breaks the worker's ``source_bundle`` rules.

IPO_TM_BUILD_PATH (env) lets a caller point these tests at a variant of the
script - used to demonstrate that the fixtures-stage guard fails against the
pre-fix implementation (the ipo-tm-001 crash shape).
"""
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates" / "ipo-trademark-registration-outcome" / "source"
BUILD = Path(os.environ.get("IPO_TM_BUILD_PATH") or (SOURCE / "build.py"))

spec_level = "ipo_tm_build"
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(spec_level, BUILD)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load build.py from {BUILD}")
ipo_build = importlib.util.module_from_spec(spec)
sys.modules[spec_level] = ipo_build
exec(compile(BUILD.read_bytes(), str(BUILD), "exec"), ipo_build.__dict__)


# The 62-column register layout: 0 Trade Mark, 7 Status, 14 Registered are
# asserted by iter_records; the class block is the last 45 columns.
def header_names():
    names = [f"c{ i}" for i in range(62)]
    names[0] = "Trade Mark"
    names[7] = "Status"
    names[14] = "Registered"
    return names


def row(tm, mark, filed, status, registered):
    """One register row; pipes inside the mark text split into extra fields,
    which is the embedded-pipe defect shape iter_records recovers from."""
    head = [
        tm,                       # 0 Trade Mark
        f"https://link/{tm}",    # 1 hyperlink
        mark,                     # 2 Mark Text
        "owner name",            # 3 owner name
        "postcode",               # 4
        "region",                 # 5
        "United Kingdom",         # 6 owner country
        status,                   # 7
        "Category A",             # 8
        "Individual",             # 9 mark type
        "Series",                 # 10
        "2",                      # 11 number in series
        filed,                    # 12 Filed
        "",                       # 13 Published
        registered,               # 14 Registered
        "",                       # 15 Expired
        "",                       # 16 Renewal date
    ]
    classes = ["1"] + ["0"] * 44
    return "|".join(head + classes)


def write_snapshot(path, rows):
    """An IPO-shaped zip: one deflated UTF-16LE member, CRLF line endings."""
    lines = ["|".join(header_names())]
    lines.extend(rows)
    text = "\r\n".join(lines) + "\r\n"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("snapshot.txt", text.encode("utf-16-le"))
    return path


class FixturesStageTest(unittest.TestCase):
    """The stage ipo-tm-001 crashed in, verified on bounded synthetic bytes."""

    def test_check_fixtures_passes_all_three_fixtures(self):
        """check_fixtures runs to completion and asserts every fixture."""
        with tempfile.TemporaryDirectory() as tmp:
            snap = write_snapshot(Path(tmp) / "snap.zip", [
                row("UK00000000001", "BASS & Co's PALE ALE", "1876-01-01",
                    "Registered", "1876-01-01"),
                row("UK00003171385", "Brexit", "2016-06-25", "Appealed", ""),
                row("UK00003041794", "ALL NATURAL FRUITY V", "2014-02-11",
                    "Application Published", ""),
            ])
            fixtures = ipo_build.check_fixtures(snap)
        self.assertEqual(len(fixtures), 3)
        self.assertTrue(all(f["ok"] for f in fixtures))

    def test_check_fixtures_fails_loudly_on_a_changed_fixture(self):
        """A mutated snapshot must raise SystemExit, not pass quietly."""
        with tempfile.TemporaryDirectory() as tmp:
            snap = write_snapshot(Path(tmp) / "snap.zip", [
                row("UK00000000001", "NOT BASS", "1876-01-01",
                    "Registered", "1876-01-01"),
                row("UK00003171385", "Brexit", "2016-06-25", "Appealed", ""),
                row("UK00003041794", "ALL NATURAL FRUITY V", "2014-02-11",
                    "Application Published", ""),
            ])
            with self.assertRaises(SystemExit):
                ipo_build.check_fixtures(snap)

    def test_hazards_shape_covers_every_key_iter_records_touches(self):
        """new_hazards() must carry every key iter_records mutates.

        This is the shape drift the ipo-tm-001 crash came from: a caller
        passing anything else (the old bare Counter()) makes iter_records
        subscript an int. Pin the contract on bounded rows, including the
        short-row, pipe-recovery and trailing-tail paths.
        """
        with tempfile.TemporaryDirectory() as tmp:
            snap = write_snapshot(Path(tmp) / "snap.zip", [
                row("UK00000000001", "BASS & Co's PALE ALE", "1876-01-01",
                    "Registered", "1876-01-01"),
                row("UK00003171385", "Brexit", "2016-06-25", "Appealed", ""),
                row("UK00003041794", "ALL NATURAL FRUITY V", "2014-02-11",
                    "Application Published", ""),
                # embedded pipe in the mark text -> 64 fields, recovered
                row("UK00003200001", "A | B | C", "2015-05-05",
                    "Registered", "2016-05-05"),
                # short row (< 17 fields)
                "|".join(["UK00003200002"] * 8),
                # duplicate of the first fixture row
                row("UK00000000001", "BASS & Co's PALE ALE", "1876-01-01",
                    "Registered", "1876-01-01"),
            ])
            hazards = ipo_build.new_hazards()
            n = 0
            for _fields in ipo_build.iter_records(snap, hazards):
                n += 1
        self.assertEqual(n, 5)  # 6 data lines, short row dropped
        self.assertEqual(dict(hazards["field_counts"]),
                         {62: 4, 64: 1, 8: 1})
        self.assertEqual(hazards["short_rows"], 1)
        self.assertEqual(hazards["pipe_recovered"], 1)
        self.assertEqual(hazards["trailing_partial_line"], 0)
        for key in ("field_counts", "short_rows", "pipe_recovered",
                    "trailing_partial_line"):
            self.assertIn(key, ipo_build.new_hazards())

    def test_build_rows_classifies_synthetic_rows(self):
        """build_rows survives the same bytes and classifies them correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            snap = write_snapshot(Path(tmp) / "snap.zip", [
                row("UK00000000001", "BASS & Co's PALE ALE", "1876-01-01",
                    "Registered", "1876-01-01"),          # pre-window
                row("UK00003171385", "Brexit", "2016-06-25", "Appealed", ""),
                row("UK00003041794", "ALL NATURAL FRUITY V", "2014-02-11",
                    "Application Published", ""),        # censored
                row("UK00003200001", "A | B | C", "2015-05-05",
                    "Registered", "2016-05-05"),               # pos, recovered
                row("UK00003200003", "plain", "2014-06-06", "Refused", ""),
                row("UK00003200004A", "series sub-mark", "2015-07-07",
                    "Registered", "2016-07-07"),          # letter suffix
            ])
            out_rows, diag = ipo_build.build_rows(snap)
        self.assertEqual(diag["data_rows"], 6)
        self.assertEqual(diag["distinct_marks"], 6)
        self.assertEqual(diag["hazards"]["pipe_recovered"], 1)
        self.assertEqual(diag["hazards"]["letter_suffix_rows"], 1)
        self.assertEqual(diag["per_year"]["2015"],
                         {"n": 2, "pos": 2, "neg": 0, "cens": 0})
        self.assertEqual(diag["per_year"]["2014"],
                         {"n": 2, "pos": 0, "neg": 1, "cens": 1})
        scored = {r["tm_number"]: r
                  for split in out_rows.values() for r in split}
        self.assertEqual(len(scored), 3)
        self.assertEqual(scored["UK00003200001"]["registered"], 1)
        self.assertEqual(scored["UK00003200003"]["registered"], 0)
        self.assertEqual(scored["UK00003200004A"]["registered"], 1)
        self.assertEqual(scored["UK00003200001"]["nice_class_count"], 1)
        # censored marks must never be scored
        self.assertNotIn("UK00003171385", scored)
        self.assertNotIn("UK00003041794", scored)

    def test_cross_check_measured_keys_match_pinned_int_years(self):
        """ipo-tm-003 regression: the summary cross-check once looked the
        pinned INT years up in the STRING-keyed per_year dict (KeyError:
        2012) after every construction assertion had passed and the five
        artifact files were already written."""
        per_year = {str(y): {"n": 40_000 + y} for y in range(2010, 2017)}
        got = ipo_build.cross_check_measured(per_year)
        self.assertEqual(sorted(got),
                         sorted(str(y) for y in
                                ipo_build.PUBLISHED_NATIONAL_APPLICATIONS))
        for year, n in got.items():
            self.assertEqual(n, 40_000 + int(year))
        # the pre-fix expression shape (int keys into the string-keyed dict)
        # is the crash this guard exists for
        with self.assertRaises(KeyError):
            {y: per_year[y]["n"]
             for y in ipo_build.PUBLISHED_NATIONAL_APPLICATIONS}


if __name__ == "__main__":
    unittest.main()
