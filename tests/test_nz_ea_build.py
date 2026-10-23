"""Offline regression tests for the nz-ea-wholesale-price-exceedance build.

Why these tests exist
---------------------

The nz-ea-001 worker attempt crashed *after* the panel and the split CSVs were
complete: ``build.py`` called ``list.append`` with four arguments instead of one
4-tuple, inside the publication-lag assembly that produces
``quality.json``'s ``timing.observations``. A paid worker was spent to discover
a syntax-shaped defect.

The synthetic-fixture smoke had passed 38/38 anyway, because fixture mode
**hardcoded** its observations and never ran the assembly. These tests pin both
gaps closed:

* ``assemble_lag_observations`` - the real lag assembly runs on listing
  metadata and returns the measured distribution and selected observations
  ( reintroducing the four-argument append fails here with TypeError );
* ``fixture_listing_entry`` + the fixture-mode integration - fixture mode
  synthesises listing metadata and runs the *same* assembly, so its written
  ``quality.json`` observations are derived, not hardcoded ( the pre-fix
  hardcoded pair had ``note`` keys, no ``source_file``, and an empty lag
  summary, all asserted against here ).

Also pins the column-list contract (one list in one place, no label source
shipped) that the first smoke round caught as a duplicate ``island`` header.

The modules under test are loaded with ``exec(compile(...))`` rather than an
import, because a normal import writes ``__pycache__`` into the candidate's
source directory and contaminates the worker job bundle (see
``test_austin_build.py``).
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates" / "nz-ea-wholesale-price-exceedance" / "source"
BUILD = SOURCE / "build.py"
FIXTURE_GEN = SOURCE / "make_fixture.py"


def _load(path: Path, name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # Compile from bytes so no bytecode cache is written into the source dir.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


nz_build = _load(BUILD, "nz_ea_build")
nz_fixture_gen = _load(FIXTURE_GEN, "nz_ea_fixture_gen")


def _http_stamp(day: date) -> str:
    """RFC 7231 date string for midnight UTC on ``day`` (English, like Azure)."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return (f"{names[day.weekday()]}, {day.day:02d} {months[day.month - 1]} "
            f"{day.year} 00:00:00 GMT")


class ColumnContractTest(unittest.TestCase):
    """One column list in one place; nothing post-hoc or label-source ships."""

    def test_no_duplicates_and_exactly_declared_parts(self):
        columns = nz_build.COLUMNS
        self.assertEqual(len(columns), len(set(columns)),
                         "duplicate column in the shipped header")
        self.assertEqual(set(columns),
                         {nz_build.ROW_ID, nz_build.TARGET}
                         | set(nz_build.CARRY_COLUMNS) | set(nz_build.FEATURES))
        self.assertEqual(set(nz_build.CARRY_COLUMNS) & set(nz_build.FEATURES),
                         set(), "carry columns and features overlap")

    def test_label_source_absent_from_shipped_columns(self):
        self.assertEqual(set(nz_build.LABEL_SOURCE_COLUMNS) & set(nz_build.COLUMNS),
                         set())


class AssembleLagObservationsTest(unittest.TestCase):
    """The branch that crashed nz-ea-001, exercised directly."""

    METADATA = {
        # daily files with hand-computed lags 4, 1 and 2 days
        "20260901_FinalEnergyPrices.csv":
            {"last_modified": _http_stamp(date(2026, 9, 5))},
        "20260929_FinalEnergyPrices.csv":
            {"last_modified": _http_stamp(date(2026, 9, 30))},
        "20260930_FinalEnergyPrices.csv":
            {"last_modified": _http_stamp(date(2026, 10, 2))},
        # every entry below must be skipped, not scored:
        "202609_FinalEnergyPrices.csv":               # monthly shape
            {"last_modified": _http_stamp(date(2026, 10, 1))},
        "20260929_FinalEnergyPrices_I.csv":            # interim variant
            {"last_modified": _http_stamp(date(2026, 9, 30))},
        "20260928_FinalEnergyPrices.csv":              # unparseable timestamp
            {"last_modified": "not-a-date"},
        "20260927_FinalEnergyPrices.csv":              # published before trade
            {"last_modified": _http_stamp(date(2026, 9, 20))},
    }

    def test_measures_distribution_and_selects_observations(self):
        result = nz_build.assemble_lag_observations(self.METADATA)
        self.assertIsNotNone(result)
        observations, summary = result
        self.assertEqual(summary["files"], 3)
        self.assertEqual(summary["min"], 1)
        self.assertEqual(summary["max"], 4)
        self.assertEqual(summary["distribution"], {1: 1, 2: 1, 4: 1})
        by_file = {entry["source_file"]: entry for entry in observations}
        self.assertEqual(set(by_file), {
            "20260901_FinalEnergyPrices.csv",
            "20260929_FinalEnergyPrices.csv",
            "20260930_FinalEnergyPrices.csv"})
        expected_lag = {"20260901_FinalEnergyPrices.csv": 4,
                        "20260929_FinalEnergyPrices.csv": 1,
                        "20260930_FinalEnergyPrices.csv": 2}
        for name, entry in by_file.items():
            self.assertEqual(entry["period"], entry["period_end"])
            self.assertNotIn("note", entry, "hardcoded fixture observation")
            self.assertEqual(
                (date.fromisoformat(entry["published"])
                 - date.fromisoformat(entry["period_end"])).days,
                expected_lag[name])

    def test_no_usable_daily_entries_returns_none(self):
        self.assertIsNone(nz_build.assemble_lag_observations({}))
        monthly_only = {"202609_FinalEnergyPrices.csv":
                        {"last_modified": _http_stamp(date(2026, 10, 1))}}
        self.assertIsNone(nz_build.assemble_lag_observations(monthly_only))


class FixtureListingEntryTest(unittest.TestCase):
    """The synthetic listing metadata fixture mode feeds the assembly."""

    def test_lag_comes_from_the_cycle_and_roundtrips_http_date(self):
        entry = nz_build.fixture_listing_entry("20251105_FinalEnergyPrices.csv", 3)
        self.assertEqual(entry["name"], "20251105_FinalEnergyPrices.csv")
        parsed = nz_build.http_date(entry["last_modified"])
        self.assertEqual(parsed, date(2025, 11, 10))  # 2025-11-05 + cycle[3]=5
        self.assertIn((parsed - date(2025, 11, 5)).days, nz_build.FIXTURE_LAG_CYCLE)

    def test_rejects_non_daily_name(self):
        with self.assertRaises(ValueError):
            nz_build.fixture_listing_entry("202511_FinalEnergyPrices.csv", 0)


class FixtureModeIntegrationTest(unittest.TestCase):
    """Fixture mode must run the real assembly, not hardcode observations.

    This is the gap that let the nz-ea-001 smoke pass 38/38 while the real run
    crashed: hardcoded fixture observations never reached the assembly branch.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="nz-ea-fixture-test-")
        base = Path(cls._tmp.name)
        cls.fixture_dir = base / "fixture"
        cls.out_dir = base / "extract"
        cls.work_dir = base / "work"
        nz_fixture_gen.main(str(cls.fixture_dir))
        argv = ["build.py", "--out", str(cls.out_dir),
                "--work-dir", str(cls.work_dir),
                "--fixture-dir", str(cls.fixture_dir),
                "--built-at", "2026-01-01T00:00:00Z"]
        with patch.object(sys, "argv", argv):
            cls.exit_code = nz_build.main()
        cls.quality = json.loads((cls.out_dir / "quality.json").read_text())
        cls.summary = json.loads((cls.out_dir / "summary.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_build_succeeded(self):
        self.assertEqual(self.exit_code, 0, "fixture-mode build must succeed")

    def test_observations_are_derived_not_hardcoded(self):
        observations = self.quality["timing"]["observations"]
        self.assertTrue(observations, "no observations written")
        for entry in observations:
            self.assertNotIn("note", entry,
                             "hardcoded fixture observation survived")
            self.assertIn("source_file", entry)
            self.assertRegex(entry["source_file"], r"^\d{8}_FinalEnergyPrices\.csv$")
            self.assertEqual(entry["period"], entry["period_end"])
            lag = (date.fromisoformat(entry["published"])
                   - date.fromisoformat(entry["period_end"])).days
            self.assertIn(lag, nz_build.FIXTURE_LAG_CYCLE)
        # the pre-fix hardcoded pair must not be present under any shape
        periods = {entry["period"] for entry in observations}
        self.assertNotIn("2026-06-28", periods)
        self.assertNotIn("2026-06-29", periods)

    def test_lag_summary_matches_synthesised_metadata(self):
        daily_names = sorted(
            path.name for path in self.fixture_dir.glob("*.csv")
            if nz_build.DAILY_RE.match(path.name))
        self.assertTrue(daily_names)
        expected_distribution = {}
        for index in range(len(daily_names)):
            lag = nz_build.FIXTURE_LAG_CYCLE[index % len(nz_build.FIXTURE_LAG_CYCLE)]
            expected_distribution[str(lag)] = expected_distribution.get(str(lag), 0) + 1
        summary = self.summary["daily_channel_lag_days"]
        self.assertEqual(summary["files"], len(daily_names))
        self.assertEqual(summary["distribution"], expected_distribution)
        self.assertEqual(summary["min"], min(nz_build.FIXTURE_LAG_CYCLE))
        self.assertEqual(summary["max"], max(nz_build.FIXTURE_LAG_CYCLE))

    def test_written_observations_equal_the_assembly_output(self):
        daily_names = sorted(
            path.name for path in self.fixture_dir.glob("*.csv")
            if nz_build.DAILY_RE.match(path.name))
        metadata = {name: nz_build.fixture_listing_entry(name, index)
                    for index, name in enumerate(daily_names)}
        expected, _summary = nz_build.assemble_lag_observations(metadata)
        self.assertEqual(self.quality["timing"]["observations"], expected)


if __name__ == "__main__":
    unittest.main()
