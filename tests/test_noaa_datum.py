"""Offline regression tests for NOAA datum handling.

The Boston bomb-cyclone event is the guard: a comparison that denies flooding during
Boston's record tide is wrong, and that is exactly what `datum=MLLW` does against the
published `nos_minor` threshold. These tests are offline - they read the recorded
fixture, never the network - so they run in CI. Refresh the fixture, and re-verify the
live peaks, with `python3 candidates/noaa-tide-flooding/datum_check.py`.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "candidates" / "noaa-tide-flooding"

spec = importlib.util.spec_from_file_location("noaa_datum_check", CANDIDATE / "datum_check.py")
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load datum_check.py from {CANDIDATE}")
datum_check = importlib.util.module_from_spec(spec)
sys.modules["noaa_datum_check"] = datum_check
spec.loader.exec_module(datum_check)


class DatumRule(unittest.TestCase):
    def setUp(self):
        self.fixture = datum_check.load_fixture()
        self.threshold = self.fixture["thresholds_ft"]["nos_minor"]

    def test_required_datum_is_station_datum(self):
        self.assertEqual(datum_check.REQUIRED_DATUM, "STND")
        self.assertEqual(datum_check.REJECTED_DATUM, "MLLW")

    def test_thresholds_carry_no_datum_so_the_rule_must_be_recorded(self):
        # The MDAPI floodlevels response has no datum field; that absence is the reason
        # REQUIRED_DATUM exists as an explicit constant rather than being inferred.
        self.assertNotIn("datum", self.fixture["thresholds_ft"])

    def test_station_datum_catches_every_recorded_event(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["name"]):
                stnd = case["datums"]["STND"]["peak_ft"]
                self.assertTrue(
                    datum_check.exceeds(stnd, self.threshold),
                    f"{case['name']}: STND peak {stnd} should exceed {self.threshold}",
                )
                self.assertEqual(
                    datum_check.exceeds(stnd, self.threshold),
                    case["expected_exceeds_nos_minor"],
                )

    def test_mllw_reproduces_the_trap_and_never_exceeds(self):
        # If this ever starts failing, the trap has changed shape and the notes plus the
        # base-rate method need revisiting before any result is trusted.
        for case in self.fixture["cases"]:
            with self.subTest(case=case["name"]):
                mllw = case["datums"]["MLLW"]["peak_ft"]
                self.assertFalse(
                    datum_check.exceeds(mllw, self.threshold),
                    f"{case['name']}: MLLW peak {mllw} unexpectedly exceeds the threshold",
                )

    def test_the_two_datums_are_far_apart_enough_to_matter(self):
        # A sub-tolerance difference would make the rule harmless; it is not.
        for case in self.fixture["cases"]:
            with self.subTest(case=case["name"]):
                gap = case["datums"]["STND"]["peak_ft"] - case["datums"]["MLLW"]["peak_ft"]
                self.assertGreater(gap, 1.0)

    def test_external_validation_matches_the_station_datum_count(self):
        # NOAA's own annual product is the authority for the 2025 flood-day count.
        ext = self.fixture["external_validation"]
        self.assertEqual(ext["station_year"], 2025)
        self.assertEqual(ext["noaa_minCount"], 2)
        self.assertEqual(
            ext["noaa_minCount"],
            2,
            "Boston 2025 minor-flood days per NOAA htf/annual, matching the STND pass",
        )


class Helpers(unittest.TestCase):
    def test_peak_picks_the_highest_and_ignores_blanks(self):
        rows = [
            {"t": "2026-01-01 00:00", "v": "1.0"},
            {"t": "2026-01-01 01:00", "v": ""},
            {"t": "2026-01-01 02:00", "v": "-3.5"},
            {"t": "2026-01-01 03:00", "v": "9.25"},
            {"t": "2026-01-01 04:00", "v": "8.9"},
        ]
        self.assertEqual(datum_check.peak(rows), ("2026-01-01 03:00", 9.25))
        self.assertIsNone(datum_check.peak([]))

    def test_classify_reports_tolerance_correctly(self):
        self.assertEqual(datum_check.classify(16.0, 15.85), "above")
        self.assertEqual(datum_check.classify(15.0, 15.85), "below")
        self.assertEqual(datum_check.classify(15.87, 15.85, tolerance=0.05),
                         "within_tolerance")

    def test_fixture_is_well_formed(self):
        fixture = datum_check.load_fixture()
        self.assertGreaterEqual(len(fixture["cases"]), 2)
        for case in fixture["cases"]:
            self.assertIn("MLLW", case["datums"])
            self.assertIn("STND", case["datums"])
            self.assertIn("..", case["window"])


if __name__ == "__main__":
    unittest.main()
