"""Tests for the dataset-qualification gate in `skills/dataset-qualification/`.

Four things are checked:

1. The gate's own fixtures: each deliberately broken dataset is rejected with the checks it
   is meant to exercise, and the corrected one is accepted. Two of the broken fixtures are
   regression cases for false passes the gate was previously blind to - evaluation rows
   inside the training period, and an evaluation split with no negative examples.
2. The gate against **real generated output** - the files Austin's construction script
   writes, together with the `quality.json` the script writes for them - so the check runs on
   an artefact rather than a hand-written sample.
3. That the gate has teeth on that artefact: re-shipping the answer source, moving the eval
   rows back into the training period, or emptying a class must each turn a pass into a
   specific, named failure.
4. The `--accept` path that downstream scoring depends on: a report is only good for the
   exact artifact version it was written for.
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
SKILL = ROOT / "skills" / "dataset-qualification"
CHECKER = SKILL / "scripts" / "qualify_dataset.py"
FIXTURES = SKILL / "fixtures"
AUSTIN_SOURCE = ROOT / "candidates" / "austin-911-response" / "source"

spec = importlib.util.spec_from_file_location("qualify_dataset", CHECKER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load the checker from {CHECKER}")
qualify_dataset = importlib.util.module_from_spec(spec)
sys.modules["qualify_dataset"] = qualify_dataset
# Compile from bytes so no bytecode cache lands beside the skill.
exec(compile(CHECKER.read_bytes(), str(CHECKER), "exec"), qualify_dataset.__dict__)


def load_austin_build():
    build = AUSTIN_SOURCE / "build.py"
    build_spec = importlib.util.spec_from_file_location("austin_build_for_gate", build)
    if build_spec is None or build_spec.loader is None:
        raise RuntimeError("cannot load the Austin construction script")
    module = importlib.util.module_from_spec(build_spec)
    sys.modules["austin_build_for_gate"] = module
    exec(compile(build.read_bytes(), str(build), "exec"), module.__dict__)
    return module


austin_build = load_austin_build()

FIXTURE_ROWS_PER_SPLIT = 40
FIXTURE_BASE_DAY = {"train": 1, "eval": 100, "holdout": 200}


def fixture_label(index: int) -> str:
    """Period-4 label pattern: 30 of 40 rows positive."""
    return "0" if index % 4 == 0 else "1"


def build_austin_fixture(out_dir: str, *, spread_days: bool = True) -> tuple[Path, dict]:
    """Run the real construction script against a fake API.

    Forty rows per split, one per calendar day when `spread_days`, with the label
    uncorrelated with every shipped column so the only possible perfect separation is an
    injected answer source. Spreading the rows over distinct days gives the gate the
    clustered event count it requires.
    """
    batches = []
    for year, split in ((2024, "train"), (2025, "eval"), (2026, "holdout")):
        batch = []
        for index in range(FIXTURE_ROWS_PER_SPLIT):
            late = fixture_label(index)
            row = {column: "" for column in austin_build.CARRY_COLUMNS + austin_build.FEATURES}
            row["incident_number"] = f"{year}{index:06d}"
            if spread_days:
                row["response_datetime"] = (f"{year}-01-01T00:00:00.000"
                                            if index == 0 else
                                            f"{year}-{2 + index // 28:02d}-"
                                            f"{1 + index % 28:02d}T00:00:00.000")
            else:
                row["response_datetime"] = f"{year}-01-01T{index // 60:02d}:{index % 60:02d}:00.000"
            row["response_time"] = "1500" if late == "1" else "900"
            row["initial_problem_category"] = ["Alpha", "Beta", "Gamma"][index % 3]
            row["sector"] = ["North", "South", "East"][(index // 3) % 3]
            row["incident_type"] = "Dispatched Incident"
            batch.append(row)
        batches.append(batch)

    with patch.object(austin_build, "count", return_value=FIXTURE_ROWS_PER_SPLIT), \
         patch.object(austin_build, "freeze_threshold",
                      return_value={"threshold_seconds": 1200, "threshold_minutes": 20,
                                    "training_rate_at_threshold": 0.75, "target_rate": 0.4}), \
         patch.object(austin_build, "stream_rows", side_effect=batches), \
         contextlib.redirect_stdout(io.StringIO()):
        assert austin_build.main(["--out", out_dir]) == 0
    manifest = json.loads((Path(out_dir) / "manifest.json").read_text())
    return Path(out_dir), manifest


def findings(report) -> dict:
    return {result["check"]: result["ok"] for result in report.results}


class GateFixtures(unittest.TestCase):
    """The shipped broken/corrected fixtures."""

    def test_selftest_passes(self):
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            code = qualify_dataset.selftest(FIXTURES)
        self.assertEqual(code, 0, captured.getvalue())

    def test_corrected_fixture_is_accepted(self):
        report = qualify_dataset.qualify(FIXTURES / "corrected")
        self.assertTrue(report.ok, report.render())

    def test_general_broken_fixture_is_rejected_with_named_reasons(self):
        report = qualify_dataset.qualify(FIXTURES / "broken")
        self.assertFalse(report.ok)
        failed = {name for name, ok in findings(report).items() if not ok}
        for expected in ("leakage.answer_source_absent",
                         "leakage.no_single_column_determines_the_target",
                         "timing.no_post_hoc_feature",
                         "units.known_event_fixture_recorded",
                         "splits.positive_events_match_rows",
                         "runner.layout"):
            self.assertIn(expected, failed, f"{expected} should have failed")

    def test_regression_evaluation_rows_inside_the_training_period(self):
        """A false pass the gate was previously blind to.

        Every declaration is the clean one, so nothing but the rows themselves reveals that
        the eval split sits inside the training period.
        """
        report = qualify_dataset.qualify(FIXTURES / "broken-overlap")
        self.assertFalse(report.ok)
        failed = {name for name, ok in findings(report).items() if not ok}
        self.assertIn("splits.actual_ranges_disjoint", failed)
        self.assertIn("splits.rows_within_declared_windows", failed)
        detail = next(r["detail"] for r in report.results
                      if r["check"] == "splits.rows_within_declared_windows")
        self.assertIn("eval starts", detail)
        # The declaration-based checks all still pass, which is the point of the case.
        for check in ("splits.machine_readable_windows", "splits.files_present",
                      "splits.positive_events_match_rows", "splits.time_column_declared"):
            self.assertTrue(findings(report).get(check), f"{check} should have passed")

    def test_regression_evaluation_split_with_no_negatives(self):
        """The other false pass: an eval split that contains only positives."""
        report = qualify_dataset.qualify(FIXTURES / "broken-single-class")
        self.assertFalse(report.ok)
        failed = {name for name, ok in findings(report).items() if not ok}
        self.assertIn("splits.eval_and_holdout_have_both_classes", failed)
        detail = next(r["detail"] for r in report.results
                      if r["check"] == "splits.eval_and_holdout_have_both_classes")
        self.assertIn("eval has 40 positives and 0 negatives", detail)

    def test_regression_repeated_identifier_inside_a_split(self):
        """A repeat inside one split is the source's grain, not split leakage.

        The earlier version of this check reported both with the same message, which read
        "... in train and train" and failed a usable dataset for the wrong reason.
        """
        report = qualify_dataset.qualify(FIXTURES / "broken-duplicates")
        self.assertFalse(report.ok)
        failed = {name for name, ok in findings(report).items() if not ok}
        self.assertIn("splits.duplicate_entities_within_splits", failed)
        self.assertTrue(findings(report).get("splits.no_cross_split_entities"),
                        "a repeat inside one split must not be reported as leakage")
        detail = next(r["detail"] for r in report.results
                      if r["check"] == "splits.duplicate_entities_within_splits")
        self.assertIn("expected_duplicate_ids", detail)

    def test_regression_contradictory_labels_on_a_tolerated_repeat(self):
        """Accepting a repeat must not mean accepting contradictory labels for it."""
        report = qualify_dataset.qualify(FIXTURES / "broken-duplicate-labels")
        self.assertFalse(report.ok)
        failed = {name for name, ok in findings(report).items() if not ok}
        self.assertIn("splits.duplicate_entities_single_label", failed)
        self.assertTrue(findings(report).get("splits.duplicate_entities_within_splits"),
                        "the repeat itself was declared and is within tolerance")


class GateOnGeneratedOutput(unittest.TestCase):
    """The gate against the files Austin's construction script actually writes."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out, self.manifest = build_austin_fixture(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_script_writes_the_gate_descriptor_itself(self):
        quality = json.loads((self.out / "quality.json").read_text())
        for key in ("target", "positive_label", "time_column", "split_windows",
                    "features", "positive_events", "post_hoc_columns"):
            self.assertIn(key, quality)
        self.assertEqual(quality["splits"],
                         {"train": "public/train.csv", "eval": "public/eval.csv",
                          "holdout": "private/holdout.csv"})
        # The declared windows come from the same declaration as the query predicates.
        self.assertEqual(quality["split_windows"], austin_build.SPLIT_WINDOWS)

    def test_real_extract_passes_the_whole_gate(self):
        report = qualify_dataset.qualify(self.out)
        self.assertTrue(report.ok, report.render())

    def test_real_extract_passes_every_check_it_is_responsible_for(self):
        report = qualify_dataset.qualify(self.out)
        status = findings(report)
        for check in ("leakage.declared_columns",
                      "leakage.answer_source_absent",
                      "leakage.no_single_column_determines_the_target",
                      "leakage.high_cardinality_declared",
                      "timing.prediction_time_declared",
                      "timing.no_post_hoc_feature",
                      "timing.label_source_is_not_a_feature",
                      "timing.every_feature_documented",
                      "splits.actual_ranges_disjoint",
                      "splits.rows_within_declared_windows",
                      "splits.eval_and_holdout_have_both_classes",
                      "splits.no_cross_split_entities",
                      "splits.duplicate_entities_within_splits",
                      "runner.layout",
                      "runner.meta_json_keys",
                      "runner.meta_matches_files",
                      "runner.meta_counts_match_files",
                      "runner.id_columns_are_not_features"):
            self.assertTrue(status.get(check), f"{check} failed:\n{report.render()}")

    def test_reshipping_the_answer_source_is_rejected_on_the_real_files(self):
        """The regression that motivated the gate, replayed on generated output."""
        self._inject_response_time()
        report = qualify_dataset.qualify(self.out)
        status = findings(report)
        self.assertFalse(status["leakage.answer_source_absent"])
        self.assertFalse(status["leakage.no_single_column_determines_the_target"])
        offender = next(result for result in report.results
                        if result["check"] == "leakage.no_single_column_determines_the_target")
        self.assertIn("response_time", offender["detail"])

    def test_moving_the_eval_rows_into_the_training_period_is_rejected(self):
        """The overlap false pass, replayed on generated output rather than on a fixture."""
        path = self.out / austin_build.LAYOUT["eval"]
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = list(rows[0])
        for row in rows:
            # Inside the training period, and inside the train rows' actual range.
            row["response_datetime"] = "2024-01-01T00:00:00.000"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        report = qualify_dataset.qualify(self.out)
        self.assertFalse(findings(report)["splits.actual_ranges_disjoint"])
        self.assertFalse(findings(report)["splits.rows_within_declared_windows"])

    def test_emptying_the_eval_negatives_is_rejected(self):
        path = self.out / austin_build.LAYOUT["eval"]
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = list(rows[0])
        for row in rows:
            row[austin_build.LABEL_COLUMN] = "1"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        report = qualify_dataset.qualify(self.out)
        self.assertFalse(findings(report)["splits.eval_and_holdout_have_both_classes"])

    def test_moving_an_incident_across_splits_is_rejected_as_leakage(self):
        """A real cross-split identifier, on generated output.

        The same incident appearing in train and eval is leakage; a repeat *inside* one split
        is not, and the two must not be reported by the same check.
        """
        train = self.out / austin_build.LAYOUT["train"]
        with train.open(newline="", encoding="utf-8") as handle:
            train_ids = [row["incident_number"] for row in csv.DictReader(handle)]
        path = self.out / austin_build.LAYOUT["eval"]
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = list(rows[0])
        rows[0]["incident_number"] = train_ids[0]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        report = qualify_dataset.qualify(self.out)
        status = findings(report)
        self.assertFalse(status["splits.no_cross_split_entities"])
        detail = next(r["detail"] for r in report.results
                      if r["check"] == "splits.no_cross_split_entities")
        self.assertIn("in train and eval", detail)

    def test_repeating_an_identifier_inside_train_is_not_reported_as_leakage(self):
        train = self.out / austin_build.LAYOUT["train"]
        with train.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = list(rows[0])
        rows.append(dict(rows[0]))                      # the same incident, reported twice
        with train.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        report = qualify_dataset.qualify(self.out)
        status = findings(report)
        # Not leakage - nothing spans two splits.
        self.assertTrue(status["splits.no_cross_split_entities"])
        # But it exceeds the count the build declared, so it is refused.
        self.assertFalse(status["splits.duplicate_entities_within_splits"])

    def test_inflating_the_clustered_event_count_is_rejected(self):
        """The clustered count is a declaration too, so it is recomputed from the rows."""
        path = self.out / "quality.json"
        quality = json.loads(path.read_text())
        quality["positive_events"]["eval"]["distinct_events"] = 999
        path.write_text(json.dumps(quality))
        report = qualify_dataset.qualify(self.out)
        self.assertFalse(findings(report)["splits.distinct_events_match_rows"])

    def test_missing_event_key_column_is_rejected(self):
        path = self.out / "quality.json"
        quality = json.loads(path.read_text())
        quality.pop("event_key_column")
        path.write_text(json.dumps(quality))
        report = qualify_dataset.qualify(self.out)
        self.assertFalse(findings(report)["splits.event_key_column_declared"])

    def test_gate_rejects_a_public_holdout(self):
        private = self.out / "private" / "holdout.csv"
        private.rename(self.out / "public" / "holdout.csv")
        quality_path = self.out / "quality.json"
        quality = json.loads(quality_path.read_text())
        quality["splits"]["holdout"] = "public/holdout.csv"
        quality_path.write_text(json.dumps(quality))
        report = qualify_dataset.qualify(self.out)
        self.assertFalse(findings(report)["runner.layout"])

    def _inject_response_time(self):
        for name in ("train", "eval", "holdout"):
            path = self.out / austin_build.LAYOUT[name]
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            fieldnames = list(rows[0])
            fieldnames.insert(len(fieldnames) - 1, "response_time")
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    row["response_time"] = "1500" if row[austin_build.LABEL_COLUMN] == "1" else "900"
                    writer.writerow(row)


class AcceptanceGate(unittest.TestCase):
    """`--accept` is what downstream scoring depends on: report AND artifact must agree."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out, _ = build_austin_fixture(self._tmp.name)
        self.report = Path(self._tmp.name) / "qualification.json"
        self.assertTrue(qualify_dataset.main(
            [str(self.out), "--json", "--report", str(self.report)]) == 0)

    def tearDown(self):
        self._tmp.cleanup()

    def test_passing_report_accepts_the_matching_artifact(self):
        self.assertEqual(qualify_dataset.accept(self.report, self.out), 0)

    def test_changed_artifact_is_refused(self):
        path = self.out / austin_build.LAYOUT["eval"]
        with path.open("a", encoding="utf-8") as handle:
            handle.write("")  # no content change
        path.write_text(path.read_text().replace("Alpha", "Alpha ").strip() + "\n")
        self.assertEqual(qualify_dataset.accept(self.report, self.out), 1)

    def test_failed_report_is_refused(self):
        failed = dict(json.loads(self.report.read_text()))
        failed["ok"] = False
        failed["failed_checks"] = ["leakage.answer_source_absent"]
        path = Path(self._tmp.name) / "failed.json"
        path.write_text(json.dumps(failed))
        self.assertEqual(qualify_dataset.accept(path, self.out), 1)

    def test_report_from_a_different_gate_version_is_refused(self):
        stale = dict(json.loads(self.report.read_text()))
        stale["gate_version"] = "0.9.0"
        path = Path(self._tmp.name) / "stale.json"
        path.write_text(json.dumps(stale))
        self.assertEqual(qualify_dataset.accept(path, self.out), 1)


class ScanCost(unittest.TestCase):
    """The categorical scan must be linear, not quadratic, on a full dataset."""

    def test_group_rate_is_computed_once_per_level(self):
        calls = {"n": 0}
        original = qualify_dataset.group_rates

        def counting(values, labels):
            calls["n"] += 1
            return original(values, labels)

        values = [f"level-{index % 20}" for index in range(5000)]
        labels = [index % 2 for index in range(5000)]
        qualify_dataset.group_rates = counting
        try:
            finding = qualify_dataset.column_leak_score(values, labels)
        finally:
            qualify_dataset.group_rates = original
        self.assertEqual(calls["n"], 1, "level statistics must be built once per column")
        self.assertIsNotNone(finding["auc"])

    def test_a_wide_column_does_not_quadratically_blow_up(self):
        # 200k rows over 40 levels: the old per-row re-summing did 200k x 5k operations.
        values = [f"level-{index % 40}" for index in range(200_000)]
        labels = [(index // 3) % 2 for index in range(200_000)]
        finding = qualify_dataset.column_leak_score(values, labels)
        self.assertEqual(finding["kind"], "categorical")
        self.assertIsNotNone(finding["auc"])


if __name__ == "__main__":
    unittest.main()
