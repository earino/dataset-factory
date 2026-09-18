"""Offline tests for the austin-911-response construction script.

Covers the pure helpers and the structural guarantees that matter most for this
candidate: the feature list must not overlap the post-hoc exclusions, the target must
never be a feature, and the split windows must be disjoint and ordered.
"""
import contextlib
import csv
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "candidates" / "austin-911-response" / "source"

spec = importlib.util.spec_from_file_location("austin_build", SOURCE / "build.py")
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load build.py from {SOURCE}")
austin_build = importlib.util.module_from_spec(spec)
sys.modules["austin_build"] = austin_build
# Loading the worker source must not create __pycache__ inside its bundle directory.
exec(compile((SOURCE / "build.py").read_bytes(), str(SOURCE / "build.py"), "exec"),
     austin_build.__dict__)


class LeakageDiscipline(unittest.TestCase):
    def test_no_feature_is_also_a_post_hoc_exclusion(self):
        overlap = set(austin_build.FEATURES) & set(austin_build.EXCLUDED_POST_HOC)
        self.assertEqual(overlap, set(), f"features leak post-hoc columns: {overlap}")

    def test_target_source_is_not_a_feature(self):
        # response_time is the label source; priority_level and mental_health_flag were
        # reclassified as post-hoc after the column docs were read.
        for banned in ("response_time", "priority_level", "mental_health_flag",
                       "first_unit_arrived_datetime", "call_closed_datetime"):
            self.assertNotIn(banned, austin_build.FEATURES)
            self.assertIn(banned, austin_build.EXCLUDED_POST_HOC + [austin_build.LABEL_SOURCE])

    def test_dispatch_time_fields_are_present(self):
        for expected in ("initial_problem_description", "initial_problem_category",
                         "sector", "council_district", "response_hour"):
            self.assertIn(expected, austin_build.FEATURES)

    def test_carry_columns_are_not_features(self):
        self.assertEqual(set(austin_build.CARRY_COLUMNS) & set(austin_build.FEATURES), set())


class SplitWindows(unittest.TestCase):
    def test_three_named_splits_in_order(self):
        self.assertEqual([name for name, _ in austin_build.SPLITS],
                         ["train", "eval", "holdout"])

    def test_windows_are_disjoint_and_cover_the_series(self):
        bounds = {
            "train": ("< '2025-01-01", None),
            "eval": (">= '2025-01-01", "< '2026-01-01"),
            "holdout": (">= '2026-01-01", None),
        }
        for name, where in austin_build.SPLITS:
            low, high = bounds[name]
            self.assertIn(low, where)
            if high:
                self.assertIn(high, where)

    def test_threshold_is_frozen_from_the_training_window(self):
        self.assertIn(austin_build.TRAIN_WHERE, austin_build.SPLITS[0][1])


class ThresholdAndLabels(unittest.TestCase):
    def test_eligible_filter_requires_a_usable_target(self):
        self.assertIn("response_time IS NOT NULL", austin_build.ELIGIBLE)

    def test_label_rule_is_a_strict_comparison(self):
        # The label is "> T", so a response of exactly T seconds is not late. This keeps
        # the rule identical to the aggregate used to freeze T.
        threshold = 1200
        self.assertEqual(int(1200.0 > threshold), 0)
        self.assertEqual(int(1201.0 > threshold), 1)


class Auc(unittest.TestCase):
    def test_perfect_separation(self):
        self.assertEqual(austin_build.auc_from_scores([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)

    def test_perfect_inversion(self):
        self.assertEqual(austin_build.auc_from_scores([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]), 0.0)

    def test_all_ties_is_one_half(self):
        self.assertEqual(austin_build.auc_from_scores([0, 1, 0, 1], [0.5] * 4), 0.5)

    def test_single_class_returns_none(self):
        self.assertIsNone(austin_build.auc_from_scores([1, 1, 1], [0.1, 0.2, 0.3]))
        self.assertIsNone(austin_build.auc_from_scores([0, 0], [0.1, 0.2]))

    def test_misaligned_inputs_raise(self):
        with self.assertRaises(ValueError):
            austin_build.auc_from_scores([0, 1], [0.5])


class CategoryBaseline(unittest.TestCase):
    def test_scores_by_training_category_rate(self):
        train = [{"initial_problem_category": "A", "_label": 1},
                 {"initial_problem_category": "A", "_label": 1},
                 {"initial_problem_category": "B", "_label": 0},
                 {"initial_problem_category": "B", "_label": 0}]
        scored = [{"initial_problem_category": "A", "_label": 1},
                  {"initial_problem_category": "B", "_label": 0}]
        result = austin_build.category_rate_baseline(train, scored)
        self.assertEqual(result["categories_in_train"], 2)
        self.assertEqual(result["training_base_rate"], 0.5)
        self.assertEqual(result["auc"], 1.0)

    def test_unseen_category_falls_back_to_the_base_rate(self):
        train = [{"initial_problem_category": "A", "_label": 1},
                 {"initial_problem_category": "B", "_label": 0}]
        scored = [{"initial_problem_category": "Z", "_label": 1},
                  {"initial_problem_category": "Z", "_label": 0}]
        result = austin_build.category_rate_baseline(train, scored)
        self.assertEqual(result["auc"], 0.5)  # one constant score for every row


class ConstructedSplits(unittest.TestCase):
    def test_written_splits_keep_labels_but_exclude_answer_sources(self):
        """Exercise the actual CSV writer, not just the declared feature list."""
        batches = []
        for year in (2024, 2025, 2026):
            batches.append([
                {"incident_number": f"{year}-1",
                 "response_datetime": f"{year}-01-01T00:00:00.000",
                 "response_time": "1200", "initial_problem_category": "A",
                 "priority_level": "P1", "mental_health_flag": "Y"},
                {"incident_number": f"{year}-2",
                 "response_datetime": f"{year}-01-02T00:00:00.000",
                 "response_time": "1201", "initial_problem_category": "B",
                 "first_unit_arrived_datetime": f"{year}-01-02T00:20:01.000"},
            ])
        threshold = {"threshold_seconds": 1200, "threshold_minutes": 20,
                     "training_rate_at_threshold": 0.5, "target_rate": 0.4}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(austin_build, "count", return_value=6), \
                 patch.object(austin_build, "freeze_threshold", return_value=threshold), \
                 patch.object(austin_build, "stream_rows", side_effect=batches) as fetch, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(austin_build.main(["--out", tmp]), 0)

            for call in fetch.call_args_list:
                self.assertIn("response_time", call.args[1].split(", "))
            allowed = {"incident_number", "response_datetime", "incident_type", "sector",
                       "council_district", "geoid", "blkgpnm", "response_day_of_week",
                       "response_hour", "initial_problem_description",
                       "initial_problem_category", "late"}
            for name in ("train", "eval", "holdout"):
                with (Path(tmp) / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    self.assertEqual(set(reader.fieldnames), allowed)
                    self.assertEqual([row["late"] for row in reader], ["0", "1"])

            manifest = json.loads((Path(tmp) / "manifest.json").read_text())
            self.assertEqual(manifest["label_source_column"], "response_time")
            self.assertNotIn("response_time", manifest["carry_columns"])
            self.assertEqual(manifest["baseline"]["auc"], 1.0)
            for split in manifest["splits"]:
                path = Path(tmp) / split["file"]
                self.assertEqual(split["rows"], 2)
                self.assertEqual(split["positives"], 1)
                self.assertEqual(split["sha256"], austin_build.sha256_of(path))


class Helpers(unittest.TestCase):
    def test_sha256_matches_hashlib(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            path.write_bytes(b"abc")
            self.assertEqual(austin_build.sha256_of(path),
                             hashlib.sha256(b"abc").hexdigest())


class WorkerSourceContract(unittest.TestCase):
    """Mirrors factory.worker.source_bundle so a job directory cannot silently fail."""

    ALLOWED = (".py", ".sh", ".json", ".txt", ".toml", ".yaml", ".yml", ".md")

    def test_job_directory_contains_only_bundleable_source(self):
        self.assertTrue(SOURCE.is_dir(), "source directory missing")
        job = SOURCE / "job.json"
        self.assertTrue(job.is_file(), "source/job.json missing")
        total = 0
        names = []
        for path in sorted(SOURCE.rglob("*")):
            self.assertFalse(path.is_symlink(), f"symlink not allowed: {path}")
            if path == job:
                continue
            if path.is_file():
                relative = path.relative_to(SOURCE)
                self.assertFalse(any(p.startswith(".") or p == "__pycache__"
                                     for p in relative.parts),
                                 f"hidden file or cache not allowed: {relative}")
                self.assertIn(path.suffix, self.ALLOWED, f"unexpected source file: {relative}")
                names.append(relative.as_posix())
                total += path.stat().st_size
            else:
                self.assertTrue(path.is_dir())
        self.assertLessEqual(total, 2 * 1024 * 1024, "job source exceeds the 2 MiB bundle cap")
        self.assertIn("build.py", names)

    def test_job_json_declares_a_priced_location_and_type(self):
        import json
        job = json.loads((SOURCE / "job.json").read_text())
        for key in ("id", "candidate", "image", "command", "server_type", "location",
                    "lifetime_minutes", "max_artifact_mb"):
            self.assertIn(key, job)
        self.assertEqual(job["server_type"], "cpx32")
        self.assertEqual(job["location"], "hel1")
        self.assertLessEqual(job["timeout_minutes"], job["lifetime_minutes"])
        self.assertEqual(job["command"][-1], "/output")


if __name__ == "__main__":
    unittest.main()
