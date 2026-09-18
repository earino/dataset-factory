"""Offline tests for the austin-911-response construction script.

Two levels of checking:

* **Structural** - the declared feature list must not overlap the post-hoc exclusions, the
  label source must not be shipped, and the split windows must be disjoint.
* **Constructed output** - the writer is actually executed against a fixture and the files
  it produces are inspected, then validated against the input contract of the existing
  runner in `../harness_benchmark`. Declared lists alone are not evidence; the bug these
  tests exist for shipped a leaking CSV while every declared list looked correct.

The module is loaded with `exec(compile(...))` rather than through an import, because a
normal import writes `__pycache__` into the job's source directory, which breaks the
worker's `source_bundle` rules and contaminates the bundle.
"""
import contextlib
import csv
import hashlib
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
BUILD = SOURCE / "build.py"
GATE = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"

spec = importlib.util.spec_from_file_location("austin_build", BUILD)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load build.py from {SOURCE}")
austin_build = importlib.util.module_from_spec(spec)
sys.modules["austin_build"] = austin_build
# Compile from bytes so no bytecode cache is written inside the worker source directory.
exec(compile(BUILD.read_bytes(), str(BUILD), "exec"), austin_build.__dict__)

# The leakage detector is shared with the qualification gate, so both stay in step.
gate_spec = importlib.util.spec_from_file_location("qualify_dataset_shared", GATE)
if gate_spec is None or gate_spec.loader is None:
    raise RuntimeError(f"cannot load the qualification gate from {GATE}")
gate = importlib.util.module_from_spec(gate_spec)
sys.modules["qualify_dataset_shared"] = gate
exec(compile(GATE.read_bytes(), str(GATE), "exec"), gate.__dict__)


def rows_for(year: int, incident_type: str = "Dispatched Incident") -> list[dict]:
    """A fixture batch shaped like a Socrata row, including columns that must not ship.

    Six rows per split with the label deliberately uncorrelated with every other column,
    so a perfect single-column separation can only come from a genuine answer source.
    `response_time` is the leak the detector must catch: `late` is 1 exactly when it
    exceeds 1200, and those rows are 0, 2 and 5.
    """
    plan = [
        # (response_time, category)
        ("1201", "A"),  # late = 1
        ("1200", "A"),  # late = 0
        ("1300", "B"),  # late = 1
        ("900", "B"),   # late = 0
        ("1200", "A"),  # late = 0
        ("1500", "B"),  # late = 1
    ]
    rows = []
    for index, (response_time, category) in enumerate(plan):
        rows.append({
            "incident_number": f"{year}-{index:03d}",
            "response_datetime": f"{year}-01-{index + 1:02d}T00:00:00.000",
            "response_time": response_time,
            "incident_type": incident_type,
            "initial_problem_category": category,
            "sector": ["North", "South", "East"][index % 3],
            "priority_level": "Priority 1",
            "mental_health_flag": "Not Mental Health Incident",
            "first_unit_arrived_datetime": f"{year}-01-{index + 1:02d}T00:20:00.000",
            "final_problem_category": "Z",
            "call_disposition_description": "MH - something",
        })
    return rows


FIXTURE_THRESHOLD = {"threshold_seconds": 1200, "threshold_minutes": 20,
                     "training_rate_at_threshold": 0.5, "target_rate": 0.4}

# `late` for the plan above, against T = 1200.
FIXTURE_LABELS = ["1", "0", "1", "0", "0", "1"]
FIXTURE_ROWS = len(FIXTURE_LABELS)
FIXTURE_POSITIVES = FIXTURE_LABELS.count("1")


def build_fixture(out_dir: str) -> Path:
    """Run main() against a fake API and return the output directory."""
    batches = [rows_for(2024), rows_for(2025), rows_for(2026)]
    with patch.object(austin_build, "count", return_value=6), \
         patch.object(austin_build, "freeze_threshold", return_value=FIXTURE_THRESHOLD), \
         patch.object(austin_build, "stream_rows", side_effect=batches), \
         contextlib.redirect_stdout(io.StringIO()):
        code = austin_build.main(["--out", out_dir])
    if code != 0:
        raise AssertionError(f"build returned {code}")
    return Path(out_dir)


def shipped_columns(out_dir: Path) -> list[str]:
    with (Path(out_dir) / "public" / "train.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


class LeakageDiscipline(unittest.TestCase):
    def test_no_feature_is_also_a_post_hoc_exclusion(self):
        overlap = set(austin_build.FEATURES) & set(austin_build.EXCLUDED_POST_HOC)
        self.assertEqual(overlap, set(), f"features leak post-hoc columns: {overlap}")

    def test_label_source_is_declared_and_excluded_from_every_shipped_list(self):
        self.assertEqual(austin_build.LABEL_SOURCE, "response_time")
        self.assertNotIn(austin_build.LABEL_SOURCE, austin_build.FEATURES)
        self.assertNotIn(austin_build.LABEL_SOURCE, austin_build.CARRY_COLUMNS)
        self.assertIn(austin_build.LABEL_SOURCE, austin_build.EXCLUDED_POST_HOC)

    def test_post_hoc_columns_are_neither_features_nor_carried(self):
        for banned in ("priority_level", "mental_health_flag",
                       "first_unit_arrived_datetime", "call_closed_datetime",
                       "final_problem_category", "call_disposition_description"):
            self.assertNotIn(banned, austin_build.FEATURES)
            self.assertNotIn(banned, austin_build.CARRY_COLUMNS)
            self.assertIn(banned, austin_build.EXCLUDED_POST_HOC)

    def test_dispatch_time_fields_are_present(self):
        for expected in ("initial_problem_description", "initial_problem_category",
                         "sector", "council_district", "response_hour"):
            self.assertIn(expected, austin_build.FEATURES)

    def test_carry_columns_are_not_features(self):
        self.assertEqual(set(austin_build.CARRY_COLUMNS) & set(austin_build.FEATURES), set())


class SplitWindows(unittest.TestCase):
    def test_three_named_splits_in_runner_order(self):
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

    def test_holdout_is_private_and_the_rest_are_public(self):
        self.assertEqual(austin_build.LAYOUT["holdout"], Path("private") / "holdout.csv")
        self.assertEqual(austin_build.LAYOUT["train"], Path("public") / "train.csv")
        self.assertEqual(austin_build.LAYOUT["eval"], Path("public") / "eval.csv")


class ThresholdAndLabels(unittest.TestCase):
    def test_eligible_filter_requires_a_usable_label_source(self):
        self.assertIn("response_time IS NOT NULL", austin_build.ELIGIBLE)

    def test_label_rule_is_a_strict_comparison(self):
        # The label is "> T", so a response of exactly T seconds is not late. This keeps
        # the rule identical to the aggregate used to freeze T.
        self.assertEqual(austin_build.label_for("1200", 1200), 0)
        self.assertEqual(austin_build.label_for("1201", 1200), 1)
        self.assertEqual(austin_build.label_for("0", 1200), 0)

    def test_construction_has_no_host_timezone_dependence(self):
        # The old parse_iso helper interpreted a naive timestamp in the host timezone,
        # which moved a January 1 instant into the previous year under TZ=Asia/Tokyo.
        # Nothing in the construction may parse the timestamp.
        self.assertFalse(hasattr(austin_build, "parse_iso"),
                         "the host-timezone-dependent helper must stay removed")
        source = BUILD.read_text()
        self.assertNotIn("fromisoformat", source)
        self.assertNotIn("astimezone", source)
        self.assertNotIn("datetime.now()", source)


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
        train = [{"initial_problem_category": "A", "late": 1},
                 {"initial_problem_category": "A", "late": 1},
                 {"initial_problem_category": "B", "late": 0},
                 {"initial_problem_category": "B", "late": 0}]
        scored = [{"initial_problem_category": "A", "late": 1},
                  {"initial_problem_category": "B", "late": 0}]
        result = austin_build.category_rate_baseline(train, scored)
        self.assertEqual(result["categories_in_train"], 2)
        self.assertEqual(result["training_base_rate"], 0.5)
        self.assertEqual(result["auc"], 1.0)

    def test_unseen_category_falls_back_to_the_base_rate(self):
        train = [{"initial_problem_category": "A", "late": 1},
                 {"initial_problem_category": "B", "late": 0}]
        scored = [{"initial_problem_category": "Z", "late": 1},
                  {"initial_problem_category": "Z", "late": 0}]
        result = austin_build.category_rate_baseline(train, scored)
        self.assertEqual(result["auc"], 0.5)  # one constant score for every row


class ConstructedFiles(unittest.TestCase):
    """Exercise the writer and inspect what it actually produced."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = build_fixture(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_runner_layout_is_produced(self):
        for relative in ("public/train.csv", "public/eval.csv", "private/holdout.csv"):
            self.assertTrue((self.out / relative).is_file(), f"missing {relative}")
        self.assertTrue((self.out / "meta.json").is_file())

    def test_answer_source_is_absent_from_every_shipped_csv(self):
        self.assertNotIn(austin_build.LABEL_SOURCE, shipped_columns(self.out))
        for name in ("train", "eval", "holdout"):
            path = self.out / austin_build.LAYOUT[name]
            with path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
            self.assertNotIn(austin_build.LABEL_SOURCE, header, f"{name} leaks the label source")
            self.assertNotIn("priority_level", header)
            self.assertNotIn("mental_health_flag", header)
            self.assertEqual(header[-1], austin_build.LABEL_COLUMN)

    def test_shipped_columns_are_exactly_carry_plus_features_plus_label(self):
        expected = austin_build.CARRY_COLUMNS + austin_build.FEATURES + [austin_build.LABEL_COLUMN]
        for name in ("train", "eval", "holdout"):
            path = self.out / austin_build.LAYOUT[name]
            with path.open(newline="", encoding="utf-8") as handle:
                fieldnames = csv.DictReader(handle).fieldnames
            self.assertIsNotNone(fieldnames, f"{name} has no header")
            self.assertEqual(list(fieldnames or []), expected)

    def test_labels_follow_the_frozen_threshold(self):
        for name in ("train", "eval", "holdout"):
            path = self.out / austin_build.LAYOUT[name]
            with path.open(newline="", encoding="utf-8") as handle:
                labels = [row[austin_build.LABEL_COLUMN] for row in csv.DictReader(handle)]
            # Fixture response times are 1201/1200/1300/900/1200/1500 against T=1200.
            self.assertEqual(labels, FIXTURE_LABELS, f"{name} labels wrong")

    def test_manifest_records_checksums_that_match_the_files(self):
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["label_source_column"], austin_build.LABEL_SOURCE)
        self.assertNotIn(austin_build.LABEL_SOURCE, manifest["carry_columns"])
        self.assertNotIn(austin_build.LABEL_SOURCE, manifest["shipped_columns"])
        for split in manifest["splits"]:
            path = self.out / split["file"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(split["sha256"], digest, f"{split['name']} checksum mismatch")
            self.assertEqual(split["rows"], FIXTURE_ROWS)
            self.assertEqual(split["positives"], FIXTURE_POSITIVES)
            self.assertEqual(split["positive_rate"],
                             round(FIXTURE_POSITIVES / FIXTURE_ROWS, 6))

    def test_manifest_keeps_the_label_source_for_provenance(self):
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertIn(austin_build.LABEL_SOURCE, manifest["excluded_post_hoc"])
        self.assertIn(austin_build.LABEL_SOURCE, manifest["label_rule"])
        # It must still be fetched, or the label could not be derived at all.
        self.assertTrue(manifest["threshold"]["threshold_seconds"])

    def test_baseline_is_a_real_but_imperfect_single_feature_rule(self):
        manifest = json.loads((self.out / "manifest.json").read_text())
        # The category baseline is not perfect on the fixture, so it is exercising a real
        # signal rather than a leaked one.
        self.assertAlmostEqual(manifest["baseline"]["auc"], round(2 / 3, 6), places=6)

    def test_stale_output_is_removed_before_a_rebuild(self):
        stale = self.out / "public" / "stale.csv"
        stale.write_text("left over\n")
        build_fixture(str(self.out))
        self.assertFalse(stale.exists(), "a rebuild must not leave previous files behind")


class RunnerContract(unittest.TestCase):
    """The extracts must be consumable by ../harness_benchmark as it actually reads them.

    Contract sources in the runner: `datasets/common.py` (write_split layout and meta.json
    keys), `task_template/train.py` (feature_cols = every column except id_columns and the
    target) and `task_template/validate.py` (drops only the target before calling
    predict_proba).
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = build_fixture(self._tmp.name)
        self.meta = json.loads((self.out / "meta.json").read_text())

    def tearDown(self):
        self._tmp.cleanup()

    def test_meta_json_carries_the_keys_the_runner_reads(self):
        for key in ("target", "positive_label", "id_columns", "columns", "rows",
                    "positive_rate"):
            self.assertIn(key, self.meta, f"meta.json missing {key}")
        self.assertEqual(self.meta["target"], austin_build.LABEL_COLUMN)
        self.assertEqual(self.meta["positive_label"], austin_build.POSITIVE_LABEL)
        self.assertEqual(self.meta["id_columns"], ["incident_number"])

    def test_target_column_is_present_in_all_three_splits(self):
        target = self.meta["target"]
        for name in ("train", "eval", "holdout"):
            path = self.out / austin_build.LAYOUT[name]
            with path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
            self.assertIn(target, header, f"{name} lacks the target column")

    def test_meta_rows_and_rates_match_the_files(self):
        for name in ("train", "eval", "holdout"):
            path = self.out / austin_build.LAYOUT[name]
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            target = self.meta["target"]
            positive = self.meta["positive_label"]
            rate = sum(int(row[target] == str(positive)) for row in rows) / len(rows)
            self.assertEqual(self.meta["rows"][name], len(rows))
            self.assertAlmostEqual(self.meta["positive_rate"][name], rate, places=6)

    def test_runner_feature_selection_exposes_no_answer_source(self):
        # train.py: feature_cols = [c for c in columns if c not in ID_COLS + [TARGET]]
        features = [c for c in self.meta["columns"]
                    if c not in self.meta["id_columns"] + [self.meta["target"]]]
        self.assertNotIn(austin_build.LABEL_SOURCE, features)
        self.assertNotIn("priority_level", features)
        self.assertNotIn("mental_health_flag", features)
        # The identifier is declared as an id, so the runner excludes it.
        for carried in self.meta["id_columns"]:
            self.assertNotIn(carried, features)
        # The prediction-time snapshot is a legitimate feature.
        self.assertIn("response_datetime", features)
        self.assertIn("initial_problem_category", features)
        # Nothing beyond the declared features and carried columns may reach the runner.
        self.assertEqual(set(features) - set(austin_build.FEATURES + austin_build.CARRY_COLUMNS),
                         set())

    def test_no_shipped_column_reconstructs_the_label(self):
        """The leakage check that would have caught the original bug.

        For every shipped column, the best single-column AUC on the extract must not be a
        perfect score. A column that separates the classes exactly is an answer source
        whatever the declared feature list says. Unique-valued columns are scored by the
        shared gate logic, which treats them as high-cardinality rather than as leaks.
        """
        path = self.out / austin_build.LAYOUT["train"]
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        target = self.meta["target"]
        labels = [int(row[target]) for row in rows]
        offenders = []
        for column in rows[0]:
            if column == target:
                continue
            finding = gate.column_leak_score([row[column] for row in rows], labels)
            if finding["determines_label"]:
                offenders.append((column, finding["auc"]))
        self.assertEqual(offenders, [], f"columns determine the label: {offenders}")

    def test_the_leak_detector_has_teeth(self):
        """Re-ship the answer source and confirm the detector rejects it."""
        path = self.out / austin_build.LAYOUT["train"]
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        target = self.meta["target"]
        labels = [int(row[target]) for row in rows]
        leaked = [row["response_time"] for row in rows_for(2024)]
        self.assertTrue(gate.column_leak_score(leaked, labels)["determines_label"],
                        "a shipped response_time must be reported as an answer source")
        self.assertEqual(gate.column_leak_score(leaked, labels)["auc"], 1.0)
        # And the same detector does not cry wolf on an honest column.
        honest = gate.column_leak_score([row["initial_problem_category"] for row in rows], labels)
        self.assertFalse(honest["determines_label"])


class SafeOutputHandling(unittest.TestCase):
    """`--out` must never be recursively deleted just because it was passed in."""

    def test_refuses_an_unowned_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            precious = Path(tmp) / "work"
            precious.mkdir()
            (precious / "uncommitted-notes.md").write_text("do not delete me\n")
            with self.assertRaises(SystemExit) as caught:
                austin_build.prepare_output(precious)
            self.assertIn("refusing to clear", str(caught.exception))
            self.assertTrue((precious / "uncommitted-notes.md").is_file(),
                            "uncommitted work must survive")

    def test_refuses_a_directory_containing_a_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            (checkout / ".git").mkdir(parents=True)
            (checkout / "code.py").write_text("x = 1\n")
            with self.assertRaises(SystemExit) as caught:
                austin_build.prepare_output(checkout)
            self.assertIn(".git", str(caught.exception))
            self.assertTrue((checkout / "code.py").is_file())

    def test_refuses_a_protected_path(self):
        with self.assertRaises(SystemExit) as caught:
            austin_build.prepare_output(Path("/opt/data"))
        self.assertIn("protected path", str(caught.exception))

    def test_clears_only_its_own_generated_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "extract"
            out.mkdir()
            (out / austin_build.OWNED_MARKER).write_text("owned\n")
            (out / "public").mkdir()
            (out / "public" / "train.csv").write_text("late\n0\n")
            (out / "meta.json").write_text("{}\n")
            # An unrelated file in an owned directory is left alone: only named entries go.
            (out / "operator-notes.txt").write_text("keep me\n")

            austin_build.prepare_output(out)

            self.assertFalse((out / "public").exists(), "generated split directory should be gone")
            self.assertFalse((out / "meta.json").exists())
            self.assertTrue((out / "operator-notes.txt").is_file(),
                            "only the named generated entries are removed")
            self.assertTrue((out / austin_build.OWNED_MARKER).is_file())

    def test_an_empty_directory_is_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fresh"
            out.mkdir()
            austin_build.prepare_output(out)
            self.assertTrue((out / austin_build.OWNED_MARKER).is_file())


class WorkerSourceHygiene(unittest.TestCase):
    """A test run must not contaminate the job's source directory."""

    def test_loading_the_module_wrote_no_bytecode(self):
        caches = list(SOURCE.rglob("__pycache__")) + list(SOURCE.rglob("*.pyc"))
        self.assertEqual(caches, [],
                         f"importing the worker source created caches in the bundle: {caches}")

    def test_job_directory_contains_only_bundleable_source(self):
        allowed = (".py", ".sh", ".json", ".txt", ".toml", ".yaml", ".yml", ".md")
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
                self.assertIn(path.suffix, allowed, f"unexpected source file: {relative}")
                names.append(relative.as_posix())
                total += path.stat().st_size
            else:
                self.assertTrue(path.is_dir())
        self.assertLessEqual(total, 2 * 1024 * 1024, "job source exceeds the 2 MiB bundle cap")
        self.assertIn("build.py", names)

    def test_job_json_declares_a_priced_location_and_type(self):
        job = json.loads((SOURCE / "job.json").read_text())
        for key in ("id", "candidate", "image", "command", "server_type", "location",
                    "lifetime_minutes", "max_artifact_mb"):
            self.assertIn(key, job)
        self.assertEqual(job["server_type"], "cpx32")
        self.assertEqual(job["location"], "hel1")
        self.assertLessEqual(job["timeout_minutes"], job["lifetime_minutes"])
        self.assertEqual(job["command"][-1], "/output")


class Sha256(unittest.TestCase):
    def test_sha256_matches_hashlib(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            path.write_bytes(b"abc")
            self.assertEqual(austin_build.sha256_of(path),
                             hashlib.sha256(b"abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
