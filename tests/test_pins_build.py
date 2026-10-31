"""Offline regression tests for the pins-planning-appeal-outcome rebuild writer.

Why these tests exist
---------------------
pins-planning-baseline-001 burned a worker attempt to discover two writer
defects the local build had passed silently:

* ``num()`` passed the publisher's prose ('Under 200 sq m floorspace', 6 eval
  rows) through into ``floor_space_sqm``; the column arrived object-dtype and
  the verbatim runner's predict path rejected the whole frame. The fix maps
  unparseable cells to missing, and these tests pin that behaviour on the
  exact measured phrase plus generic prose, so a future edit cannot quietly
  restore the pass-through.

* xgboost 3.4.1's ``inplace_predict`` rejected the nine category-dtype columns
  at predict even with ``enable_categorical=True`` at fit. The rebuild settles
  the question with a worker-side probe and, on rejection, integer-codes those
  columns. These tests pin the *documentation contract* the candidate record
  requires (codes documented in ``quality.json`` via ``categorical_coding``,
  ``measurements`` and ``feature_evidence``) and the vocabulary/column
  consistency of the coding declaration, using ``build_quality`` directly -
  no dataset file is read.

The module under test is loaded with ``exec(compile(...))`` rather than an
import, because a normal import writes ``__pycache__`` into the candidate's
source directory and contaminates the worker job bundle (see
``test_austin_build.py``).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates" / "pins-planning-appeal-outcome" / "source"
BUILD = SOURCE / "build.py"


def _load(path: Path, name: str):
    module = type(sys)(name)
    # Compile from bytes so no bytecode cache is written into the source dir.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


pins_build = _load(BUILD, "pins_build")


class NumMapsProseToMissing(unittest.TestCase):
    """Defect 1: publisher prose in numeric fields must ship as missing."""

    def test_measured_phrase_ships_missing(self):
        # the exact phrase measured in 6 eval rows of pins-planning-baseline-001
        self.assertEqual(
            pins_build.num("Under 200 sq m floorspace"), "")

    def test_generic_prose_ships_missing(self):
        for raw in ("Under 1 hectare", "n/a", "see notes", "1,234 sq m approx"):
            self.assertEqual(pins_build.num(raw), "", msg=raw)

    def test_numbers_still_parse(self):
        self.assertEqual(pins_build.num("12.5"), repr(12.5))
        self.assertEqual(pins_build.num(7), repr(7.0))
        self.assertEqual(pins_build.num(" 3.25 "), repr(3.25))

    def test_absent_is_missing(self):
        self.assertEqual(pins_build.num(None), "")
        self.assertEqual(pins_build.num(""), "")
        self.assertEqual(pins_build.num("   "), "")


class CodingDeclarationContract(unittest.TestCase):
    """Defect 2: on a rejected probe the coding must be declared, not implied."""

    PROBE = {"predict_on_category_dtype": "rejected",
             "subtests": {"predict_seen_levels": "ValueError: test"},
             "versions": {"xgboost": "3.4.1"}}

    def _quality(self, code_categoricals, code_maps=None):
        columns = ["row_id", *pins_build.CATEGORICAL_FEATURES, "valid_date",
                   "lpa_allow_rate_prior", "allowed"]
        features = [c for c in columns if c not in pins_build.ID_COLUMNS
                    + [pins_build.TARGET]]
        stats = {"vocab": {}, "presence": {}}
        return pins_build.build_quality(
            columns, features, shipped_flags=[], dropped_flags={},
            ship_enforcement=False,
            split_stats={k: {"rows": 1, "positives": 1, "negatives": 0,
                             "positive_rate": 1.0} for k in ("train", "eval", "holdout")},
            positive_events={k: {"positives": 1, "distinct_events": 1}
                             for k in ("train", "eval", "holdout")},
            per_valid_year={}, minmax_valid={},
            stats=stats, built_at="2026-10-31T00:00:00Z",
            code_categoricals=code_categoricals,
            code_maps=code_maps or ({c: {"x": "1"} for c in pins_build.CATEGORICAL_FEATURES}
                                    if code_categoricals else None),
            category_probe=self.PROBE if code_categoricals else
            {"predict_on_category_dtype": "ok"})

    def test_rejected_probe_documents_coding_everywhere(self):
        quality = self._quality(True)
        coding = quality["categorical_coding"]
        self.assertTrue(coding["applied"])
        self.assertEqual(sorted(coding["columns"]),
                         sorted(pins_build.CATEGORICAL_FEATURES))
        self.assertEqual(coding["probe_evidence"]["predict_on_category_dtype"],
                         "rejected")
        # feature_evidence carries a coding note on every coded column
        for name in pins_build.CATEGORICAL_FEATURES:
            self.assertIn("coding", quality["evaluation_contract"]["feature_evidence"][name],
                          msg=name)
        # measurements carries a unit/frame entry for every coded column
        measured = {m["column"] for m in quality["measurements"]}
        for name in pins_build.CATEGORICAL_FEATURES:
            self.assertIn(name, measured, msg=name)
        self.assertIn("pins-planning-baseline-001", coding["reason"])

    def test_ok_probe_ships_verbatim_and_says_so(self):
        quality = self._quality(False)
        coding = quality["categorical_coding"]
        self.assertFalse(coding["applied"])
        self.assertIsNone(coding["columns"])
        for name in pins_build.CATEGORICAL_FEATURES:
            self.assertNotIn("coding",
                             quality["evaluation_contract"]["feature_evidence"][name])

    def test_nine_coded_columns_are_the_runner_nine(self):
        # the columns the baseline error listed as invalid category dtypes
        self.assertEqual(
            sorted(pins_build.CATEGORICAL_FEATURES),
            sorted(["lpa_name", "ons_lpa_code", "casework_type", "procedure",
                    "development_type", "appeal_type_reason", "appeal_reason",
                    "type_detail", "link_status"]))
        # none of them is the target, an id, or the time column
        for name in pins_build.CATEGORICAL_FEATURES:
            self.assertNotIn(name, pins_build.ID_COLUMNS + [pins_build.TARGET]
                             + [pins_build.TIME_COLUMN])


if __name__ == "__main__":
    unittest.main()
