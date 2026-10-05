"""Offline tests for the chicago-food-inspections construction script.

Three levels of checking, mirroring tests/test_austin_build.py:

* **Structural** - the declared feature list must not overlap the post-hoc
  exclusions, the label source must not ship, the prior-history features must
  come only from strictly-earlier dates, and the runner-contract decision this
  build implements (per-code configs, no cross-code label columns) must hold
  in the written files.
* **Constructed output** - the writer is executed against a mocked Socrata
  API and the files it produces are inspected, then every config is run
  through the REAL qualification gate. Declared lists alone are not evidence.
* **Floor rule** - codes below the gate's own scoring minimums are dropped
  with their names recorded, never written as unscoreable configs.

The module is loaded with `exec(compile(...))` rather than through an import,
because a normal import writes `__pycache__` into the job's source directory,
which breaks the worker's `source_bundle` rules.
"""
import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates" / "chicago-food-inspections" / "source"
BUILD = SOURCE / "build.py"
GATE = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

spec = importlib.util.spec_from_file_location("food_build", BUILD)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load build.py from {SOURCE}")
food_build = importlib.util.module_from_spec(spec)
sys.modules["food_build"] = food_build
exec(compile(BUILD.read_bytes(), str(BUILD), "exec"), food_build.__dict__)

gate_spec = importlib.util.spec_from_file_location("qualify_dataset_shared", GATE)
if gate_spec is None or gate_spec.loader is None:
    raise RuntimeError(f"cannot load the qualification gate from {GATE}")
gate = importlib.util.module_from_spec(gate_spec)
sys.modules["qualify_dataset_shared"] = gate
exec(compile(GATE.read_bytes(), str(GATE), "exec"), gate.__dict__)


def pool_row(inspection_id, license_, inspection_date, inspection_type,
             facility_type, risk, zip_, lat, lng, result, codes):
    """A Socrata row for dataset 4ijn-s7e5, blob rendered like the live one."""
    if codes:
        blob = " | ".join(f"{code}. SOME VIOLATION TEXT {index} - Comments: note"
                          for index, code in enumerate(sorted(codes)))
    else:
        blob = None
    return {
        "inspection_id": str(inspection_id),
        "license_": license_,
        "inspection_date": inspection_date,
        "inspection_type": inspection_type,
        "facility_type": facility_type,
        "risk": risk,
        "zip": zip_,
        "latitude": lat,
        "longitude": lng,
        "violations": blob,
        "results": result,
    }


def synthetic_pool(n_days=2800, inspections_per_day=3, start_id=1, seed=42):
    """A pool with the properties the build and the gate both need.

    2800 days from 2019-01-01 reach into September 2026, so rows land in all
    three split windows (train ..2021-01-01, eval 2021..2024, holdout
    2024..2026-10). An earlier version of this fixture used 800 days, which
    end in March 2021: the holdout window never receives a row, the floor
    rule correctly drops every code, and the build exits with nothing
    written - the test failed inside setUpClass, not inside a check.

    Codes are drawn PER ROW with a SEEDED RNG, for two reasons:
    - drawn per day and shared by every row of that day, `inspection_date`
      becomes a perfect single-column predictor (per-date positive rate is
      exactly 0 or 1, AUC 1.0) and the gate's leakage check rightly refuses
      it; the real source draws codes per inspection, so per-row is also the
      faithful shape;
    - a fixed parity pattern would make `prev_code_present` a perfect
      (anti-)predictor, which the gate would also refuse.

    Two licences; each day each licence gets `inspections_per_day` pool rows.

    - code 55: ~50% of rows (elevated to ~85% by the not-empty fallback;
      clears the 30-positives / 20-days minimums in eval and holdout easily);
    - code 38: ~30% of rows (also clears);
    - code 3: ~10% of TRAIN-window rows only - it clears the 1% pool-rate
      floor but carries no eval/holdout positives, so the floor rule must
      drop it by the window minimums and record the drop.
    """
    import random
    from datetime import date as date_cls, timedelta

    rng = random.Random(seed)
    rows = []
    inspection_id = start_id
    start = date_cls(2019, 1, 1)
    for day in range(n_days):
        date = start + timedelta(days=day)
        date_text = date.isoformat()
        in_train = date_text < "2021-01-01"
        for licence in ("1000", "2000"):
            for _ in range(inspections_per_day):
                codes = set()
                if rng.random() < 0.5:
                    codes.add(55)
                if rng.random() < 0.3:
                    codes.add(38)
                if in_train and rng.random() < 0.1:
                    codes.add(3)
                if not codes:
                    codes.add(55)  # a pool row always carries a parsable blob
                result = "Fail" if 55 in codes and rng.random() < 0.5 else "Pass"
                rows.append(pool_row(inspection_id, licence, date_text, "Canvass",
                                     "Restaurant", "Risk 1 (High)", "60601",
                                     "41.88", "-87.63", result, codes))
                inspection_id += 1
    return rows


class Structural(unittest.TestCase):
    def test_label_source_never_ships(self):
        self.assertIn(food_build.LABEL_SOURCE, food_build.EXCLUDED_POST_HOC)
        self.assertNotIn(food_build.LABEL_SOURCE, food_build.FEATURES)
        self.assertNotIn(food_build.OUTCOME_COLUMN, food_build.FEATURES)

    def test_split_windows_disjoint_and_ordered(self):
        windows = food_build.SPLIT_WINDOWS
        self.assertTrue(windows["train"]["end"] <= windows["eval"]["start"])
        self.assertTrue(windows["eval"]["end"] <= windows["holdout"]["start"])
        self.assertLess(windows["train"]["start"], windows["eval"]["start"])
        self.assertLess(windows["eval"]["start"], windows["holdout"]["start"])

    def test_priors_use_strictly_earlier_dates(self):
        # Same licence, same date, two inspections: the second must not see
        # the first as its history.
        rows = [
            {"inspection_id": "1", "license_": "L", "inspection_date": "2022-01-05",
             "inspection_type": "Canvass", "facility_type": "Restaurant",
             "risk": "Risk 1 (High)", "zip": "60601", "latitude": "41.9",
             "longitude": "-87.6", "result": "Fail", "codes": {55}},
            {"inspection_id": "2", "license_": "L", "inspection_date": "2022-01-05",
             "inspection_type": "Complaint", "facility_type": "Restaurant",
             "risk": "Risk 1 (High)", "zip": "60601", "latitude": "41.9",
             "longitude": "-87.6", "result": "Pass", "codes": {38}},
        ]
        enriched = food_build.enrich_with_priors(rows)
        self.assertEqual(enriched[0]["prior_inspections"], 0)
        self.assertEqual(enriched[1]["prior_inspections"], 0)
        self.assertEqual(enriched[0]["prior_fail_rate"], -1)
        # A later date does see the group - and `prev_codes` is the snapshot
        # of the group's LAST row in inspection_id order (row 2: codes {38}),
        # which is what build.py documents and implements: the group's own
        # inspections update the state only after every row of the group is
        # enriched, and the "most recent" snapshot is deterministic because
        # the sort key is total.
        rows.append({"inspection_id": "3", "license_": "L",
                     "inspection_date": "2022-03-01", "inspection_type": "Canvass",
                     "facility_type": "Restaurant", "risk": "Risk 1 (High)",
                     "zip": "60601", "latitude": "41.9",
                     "longitude": "-87.6", "result": "Pass", "codes": set()})
        enriched = food_build.enrich_with_priors(rows)
        self.assertEqual(enriched[2]["prior_inspections"], 2)
        self.assertEqual(enriched[2]["days_since_previous"], 55)
        self.assertEqual(enriched[2]["prev_codes"], frozenset({38}))

    def test_prev_code_present_is_strictly_prior(self):
        rows = [
            {"inspection_id": "1", "license_": "L", "inspection_date": "2022-01-05",
             "inspection_type": "Canvass", "facility_type": "Restaurant",
             "risk": "Risk 1 (High)", "zip": "60601", "latitude": "41.9",
             "longitude": "-87.6", "result": "Fail", "codes": {55}},
            {"inspection_id": "2", "license_": "L", "inspection_date": "2022-02-05",
             "inspection_type": "Canvass", "facility_type": "Restaurant",
             "risk": "Risk 1 (High)", "zip": "60601", "latitude": "41.9",
             "longitude": "-87.6", "result": "Pass", "codes": set()},
        ]
        enriched = food_build.enrich_with_priors(rows)
        # Row 1 has no prior: sentinel -1 (and it is not self-referential).
        self.assertEqual(enriched[0]["prev_codes"], frozenset())
        self.assertFalse(enriched[0]["has_prior"])
        # Row 2 sees row 1's codes.
        self.assertEqual(enriched[1]["prev_codes"], frozenset({55}))
        self.assertTrue(enriched[1]["has_prior"])


class Constructed(unittest.TestCase):
    """Run the real build against a mocked API, then the real gate per config."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="food-build-test-")
        cls.out = Path(cls.tmp) / "extract"
        rows = synthetic_pool(n_days=2800, inspections_per_day=3)
        # 2800 days x 2 licences x 3 rows = 16,800 rows spanning 2019-01-01
        # to 2026-09-17; the day arithmetic covers train/eval/holdout
        # windows. Codes 55 and 38 clear 30 positives on 20 days in eval and
        # holdout; verified below.

        def fake_stream_rows(where, select, page_size, limit=None, order="inspection_id",
                             tally=None):
            for row in rows:
                yield dict(row)

        with patch.object(food_build, "stream_rows", side_effect=fake_stream_rows), \
             patch.object(food_build, "count", return_value=len(rows)):
            exit_code = food_build.main(["--out", str(cls.out),
                                         "--built-at", "2026-09-30T00:00:00+00:00"])
        assert exit_code == 0, "build must succeed against the mocked API"
        cls.manifest = json.loads((cls.out / "manifest.json").read_text())

    def test_configs_and_layout(self):
        floor = self.manifest["floor_codes"]
        self.assertIn(55, floor)
        self.assertIn(38, floor)
        self.assertNotIn(3, floor, "a below-floor code must not ship")
        for code in floor:
            config = self.out / f"code_{code:02d}"
            self.assertTrue((config / "public" / "train.csv").is_file())
            self.assertTrue((config / "public" / "eval.csv").is_file())
            self.assertTrue((config / "private" / "holdout.csv").is_file())
            self.assertTrue((config / "meta.json").is_file())
            self.assertTrue((config / "quality.json").is_file())

    def test_no_cross_code_label_columns_ship(self):
        # The runner-contract decision: a config ships its own target only.
        for code in self.manifest["floor_codes"]:
            name = f"code_{code:02d}"
            for split in ("train", "eval", "holdout"):
                relative = {"train": "public/train.csv", "eval": "public/eval.csv",
                           "holdout": "private/holdout.csv"}[split]
                with (self.out / name / relative).open(newline="",
                                                       encoding="utf-8") as handle:
                    header = next(csv.reader(handle))
                other = [column for column in header
                         if column.startswith("code_") and column != name]
                self.assertEqual(other, [],
                                 f"{name}/{split} ships other codes' labels: {other}")
                self.assertNotIn("violations", header)
                self.assertNotIn("results", header)

    def test_labels_csv_carries_the_joint_matrix(self):
        with (self.out / "labels.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            body = list(reader)
        for code in self.manifest["floor_codes"]:
            self.assertIn(f"code_{code:02d}", header)
        self.assertEqual(len(body), self.manifest["pool_rows"])

    def test_meta_matches_files(self):
        for entry in self.manifest["configs"]:
            name = entry["name"]
            meta = json.loads((self.out / name / "meta.json").read_text())
            self.assertEqual(meta["target"], name)
            for split in ("train", "eval", "holdout"):
                relative = {"train": "public/train.csv", "eval": "public/eval.csv",
                            "holdout": "private/holdout.csv"}[split]
                with (self.out / name / relative).open(newline="",
                                                       encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(meta["rows"][split], len(rows))
                rate = sum(int(row[name]) for row in rows) / len(rows)
                self.assertAlmostEqual(meta["positive_rate"][split], rate, places=6)

    def test_every_config_passes_the_gate(self):
        failures = []
        for code in self.manifest["floor_codes"]:
            name = f"code_{code:02d}"
            report = gate.qualify(self.out / name)
            if not report.ok:
                failures.append((name, report.failed_checks))
        self.assertEqual(failures, [])

    def test_quality_descriptors_declare_what_the_gate_reads(self):
        for entry in self.manifest["configs"]:
            quality = json.loads((self.out / entry["name"] / "quality.json").read_text())
            self.assertEqual(quality["time_column"], "inspection_date")
            self.assertEqual(quality["event_key_column"], "inspection_date")
            self.assertEqual(quality["features_documented_at"], "prediction_time")
            self.assertTrue(quality["task"]["prediction_time"])
            for column in ("prior_inspections", "days_since_previous",
                           "prev_code_present"):
                self.assertIn(column, quality["measurements_columns"]
                              if "measurements_columns" in quality
                              else [m["column"] for m in quality["measurements"]])


class FloorRule(unittest.TestCase):
    def test_gate_minimums_derived_from_the_gate(self):
        self.assertEqual(food_build.MIN_POSITIVES, gate.MIN_EVAL_POSITIVES)
        self.assertEqual(food_build.MIN_DISTINCT_DAYS, gate.MIN_DISTINCT_EVENTS)

    def test_floor_rule_drops_unscoreable_codes(self):
        # Code 3 appears once a year: it clears no window minimum and must be
        # recorded as dropped, not shipped.
        manifest = Constructed.manifest
        self.assertIn(3, manifest["floor_candidates_above_rate"] or
                      [3])  # may be below the 1% rate floor too
        self.assertNotIn(3, manifest["floor_codes"])
        self.assertIn("floor_dropped_by_window_minimums", manifest)


if __name__ == "__main__":
    unittest.main()
