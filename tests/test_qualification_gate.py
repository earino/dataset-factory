"""Tests for the dataset-qualification gate in `skills/dataset-qualification/`.

Three things are checked:

1. The gate's own fixtures: the deliberately broken dataset is rejected, the corrected one
   is accepted, and each expected failure is actually reported.
2. The gate against **real generated output** - the files Austin's construction script
   writes - so the check is exercised on an artefact rather than on a hand-written sample.
3. That the gate has teeth on that artefact: re-shipping the answer source must turn a pass
   into a specific, named failure.
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


def austin_quality(manifest: dict) -> dict:
    """A quality.json descriptor describing the Austin extract as it was built."""
    return {
        "name": "austin-911-response",
        "task": {
            "question": manifest["prediction_question"],
            "prediction_time": manifest["prediction_time"],
        },
        "target": manifest["label_column"],
        "positive_label": austin_build.POSITIVE_LABEL,
        "features": manifest["features"],
        "features_documented_at": "prediction_time",
        "carry_columns": manifest["carry_columns"],
        "id_columns": ["incident_number"],
        "high_cardinality_columns": ["response_datetime"],
        "label_source_columns": [manifest["label_source_column"]],
        "post_hoc_columns": manifest["excluded_post_hoc"],
        "measurements": [
            {"column": manifest["label_source_column"], "unit": "seconds",
             "frame": "portal column; begins when the 911 call was answered"},
        ],
        "splits": {entry["name"]: entry["file"] for entry in manifest["splits"]},
        "split_boundaries": {name: where for name, where in austin_build.SPLITS},
        # No external_threshold: this threshold is a measured training-window rule, not an
        # external published level, so no known-event fixture is required.
        "positive_events": {
            "eval": {"positives": 30, "distinct_events": 20},
            "holdout": {"positives": 30, "distinct_events": 20},
        },
    }


FIXTURE_ROWS_PER_SPLIT = 40


def fixture_label(index: int) -> str:
    """Period-4 label pattern: 30 of 40 rows positive."""
    return "0" if index % 4 == 0 else "1"


def build_austin_fixture(out_dir: str) -> tuple[Path, dict]:
    """Run the real construction script against a fake API.

    Forty rows per split, with the label uncorrelated with every shipped column so the only
    possible perfect separation is an injected answer source. The size matters: below about
    ten rows per split the categorical-vs-high-cardinality distinction in the gate is not
    meaningful.
    """
    batches = []
    for year in (2024, 2025, 2026):
        batch = []
        for index in range(FIXTURE_ROWS_PER_SPLIT):
            late = fixture_label(index)
            row = {column: "" for column in austin_build.CARRY_COLUMNS + austin_build.FEATURES}
            row["incident_number"] = f"{year}{index:06d}"
            row["response_datetime"] = (f"{year}-01-01T{index // 60:02d}:{index % 60:02d}:00.000")
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
    """The shipped broken/corrected pair."""

    def test_selftest_passes(self):
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            code = qualify_dataset.selftest(FIXTURES)
        self.assertEqual(code, 0, captured.getvalue())

    def test_broken_fixture_is_rejected_with_named_reasons(self):
        report = qualify_dataset.qualify(FIXTURES / "broken")
        self.assertFalse(report.ok)
        failed = {name for name, ok in findings(report).items() if not ok}
        for expected in ("leakage.answer_source_absent",
                         "leakage.no_single_column_determines_the_target",
                         "timing.no_post_hoc_feature",
                         "units.known_event_fixture_recorded",
                         "splits.windows_distinct",
                         "runner.layout"):
            self.assertIn(expected, failed, f"{expected} should have failed")

    def test_corrected_fixture_is_accepted(self):
        report = qualify_dataset.qualify(FIXTURES / "corrected")
        self.assertTrue(report.ok, report.render())


class GateOnGeneratedOutput(unittest.TestCase):
    """The gate against the files Austin's construction script actually writes."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out, self.manifest = build_austin_fixture(self._tmp.name)
        self.quality = austin_quality(self.manifest)
        (self.out / "quality.json").write_text(json.dumps(self.quality))

    def tearDown(self):
        self._tmp.cleanup()

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
                      "runner.layout",
                      "runner.meta_json_keys",
                      "runner.meta_matches_files",
                      "runner.meta_counts_match_files",
                      "runner.id_columns_are_not_features"):
            self.assertTrue(status.get(check), f"{check} failed:\n{report.render()}")

    def test_reshipping_the_answer_source_is_rejected_on_the_real_files(self):
        """The regression that motivated the gate, replayed on generated output."""
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
                    row["response_time"] = "1500" if row["late"] == "1" else "900"
                    writer.writerow(row)

        report = qualify_dataset.qualify(self.out)
        status = findings(report)
        self.assertFalse(status["leakage.answer_source_absent"])
        self.assertFalse(status["leakage.no_single_column_determines_the_target"])
        offender = next(result for result in report.results
                        if result["check"] == "leakage.no_single_column_determines_the_target")
        self.assertIn("response_time", offender["detail"])

    def test_gate_rejects_a_public_holdout(self):
        private = self.out / "private" / "holdout.csv"
        private.rename(self.out / "public" / "holdout.csv")
        self.quality["splits"]["holdout"] = "public/holdout.csv"
        (self.out / "quality.json").write_text(json.dumps(self.quality))
        report = qualify_dataset.qualify(self.out)
        self.assertFalse(findings(report)["runner.layout"])


if __name__ == "__main__":
    unittest.main()
