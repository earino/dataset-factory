"""Tests for the smoke artifact builder and the smoke job assembler (issue #17).

The gate tests are the required integration proof: a software fixture is built
THROUGH workers.smoke_artifact.build_derivative, then the REAL qualification
gate must pass it two-phase (report ok, then --accept), and a mutated CSV after
the report must be refused by --accept. The assembler tests exercise the real
read-only pinned harness checkout and the exact source/pinned.json runtime
schema. No selftest or --help invocation counts as the gate proof.
"""
import base64
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workers"))
sys.path.insert(0, str(ROOT))

import smoke_artifact

GATE = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"
HARNESS = ROOT.parent / "harness_benchmark"
if not HARNESS.is_dir():
    HARNESS = Path("/opt/data/harness_benchmark")
HARNESS_COMMIT = "58b434fee9b53eab953b6a3d84baf5cbeb01bc6e"
ASSEMBLER = ROOT / "scripts" / "assemble-smoke-job.py"

COLUMNS = ["incident_number", "response_datetime", "incident_type", "sector",
           "council_district", "geoid", "blkgpnm", "response_day_of_week",
           "response_hour", "initial_problem_description",
           "initial_problem_category", "late"]
FEATURES = COLUMNS[2:9] + [COLUMNS[9], COLUMNS[10]]


def _stamp(year: int, month: int, day: int, hour: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:00:00.000"


def _rows(years_months: list[tuple[int, int]], start_index: int = 0):
    """Deterministic Austin-shaped rows; labels uncorrelated with any column."""
    i = start_index
    for year, month in years_months:
        for _ in range(40):
            day = i % 28 + 1
            hour = i % 24
            yield {
                "incident_number": f"FIX{i:07d}",
                "response_datetime": _stamp(year, month, day, hour),
                "incident_type": f"type{i % 5}",
                "sector": f"sector{i % 6}",
                "council_district": f"d{i % 5}",
                "geoid": f"g{i % 10}",
                "blkgpnm": f"b{i % 8}",
                "response_day_of_week": str(i % 7),
                "response_hour": str(hour),
                "initial_problem_description": f"problem {i}",
                "initial_problem_category": f"cat{i % 4}",
                "late": str(int((i * 2654435761) % 100 < 45)),
            }
            i += 1


def _months(start: tuple[int, int], count: int) -> list[tuple[int, int]]:
    year, month = start
    out = []
    for _ in range(count):
        out.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def _write_csv(path: Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _fixture_input(directory: Path) -> None:
    """A synthetic Austin-shaped source release with truthful declarations."""
    train_months = _months((2023, 1), 24)
    eval_months = _months((2025, 1), 8)
    _write_csv(directory / "train.csv", _rows(train_months))
    _write_csv(directory / "eval.csv", _rows(eval_months, start_index=10_000))
    meta = {
        "name": "austin-911-response",
        "description": "Software fixture for the adapter smoke; synthetic rows.",
        "source": "synthetic fixture (issue #17)",
        "license": "MIT",
        "target": "late",
        "positive_label": 1,
        "id_columns": ["incident_number"],
        "columns": COLUMNS,
        "rows": {"train": 960, "eval": 320, "holdout": 0},
        "positive_rate": {"train": 0.45, "eval": 0.45, "holdout": 0.45},
        "split": {"strategy": "temporal by response_datetime",
                  "boundaries": {"train": "response_datetime < '2025-01-01T00:00:00.000'",
                                 "eval": "response_datetime >= '2025-01-01T00:00:00.000'",
                                 "holdout": "not shipped in the public release"}},
        "threshold_seconds": 1200,
        "label_rule": "late = 1 if response_time > 1200 else 0",
        "label_source_column": "response_time",
        "prediction_time": "At dispatch: the moment the call-taker screen opens "
                           "(response_datetime). Only fields known then are shipped.",
        "features": FEATURES,
        "excluded_post_hoc": ["response_time", "first_unit_arrived_datetime"],
        "carry_columns": ["incident_number", "response_datetime"],
        "built_at_utc": "2026-10-24T00:00:00+00:00",
    }
    (directory / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    quality = {
        "name": "austin-911-response",
        "task": {"question": "Will the first officer arrive late?",
                 "prediction_time": meta["prediction_time"]},
        "target": "late",
        "positive_label": 1,
        "threshold_seconds": 1200,
        "time_column": "response_datetime",
        "event_key_column": "response_datetime",
        "features": FEATURES,
        "features_documented_at": "prediction_time",
        "carry_columns": meta["carry_columns"],
        "id_columns": ["incident_number"],
        "expected_duplicate_ids": 0,
        "expected_duplicate_ids_by_split": {"train": 0, "eval": 0, "holdout": 0},
        "high_cardinality_columns": ["response_datetime",
                                      "initial_problem_description"],
        "label_source_columns": ["response_time"],
        "post_hoc_columns": ["response_time", "first_unit_arrived_datetime"],
        "measurements": [{"column": "response_time", "unit": "seconds",
                          "frame": "fixture: portal response seconds"}],
        "splits": {"train": "public/train.csv", "eval": "public/eval.csv",
                   "holdout": "private/holdout.csv"},
        "split_boundaries": meta["split"]["boundaries"],
        "split_windows": {"train": {"start": None, "end": "2025-01-01T00:00:00.000"},
                          "eval": {"start": "2025-01-01T00:00:00.000", "end": None},
                          "holdout": {"start": "2025-01-01T00:00:00.000", "end": None}},
        "positive_events": {"eval": {"positives": 1, "distinct_events": 1},
                            "holdout": {"positives": 1, "distinct_events": 1}},
        "built_at_utc": meta["built_at_utc"],
        "shipped_columns": COLUMNS,
    }
    (directory / "quality.json").write_text(json.dumps(quality, indent=2) + "\n")


SMOKE = {"time_column": "response_datetime", "target": "late", "positive_label": 1,
         "dev_months": 6, "dataset": "austin-911-response", "release_tag": "vTEST"}


class BuildDerivativeTests(unittest.TestCase):
    """Structure and honesty checks for the derivative construction."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.input = self.base / "input"
        self.input.mkdir()
        _fixture_input(self.input)
        self.output = self.base / "derivative"

    def test_runtime_dir_contract_marker_only(self):
        """The runtime pre-creates derivative_dir with only .smoke-owned."""
        self.output.mkdir()
        (self.output / ".smoke-owned").write_text("owned\n")
        result = smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        self.assertTrue((self.output / ".smoke-owned").is_file())
        self.assertEqual(result["boundary_month"], "2024-07")
        self.assertTrue((self.output / "public" / "train.csv").is_file())
        self.assertTrue((self.output / "meta.json").is_file())

    def test_selection_preserves_outcome_availability_condition(self):
        smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        contract=json.loads((self.output/'quality.json').read_text())['evaluation_contract']
        self.assertEqual(contract['selection']['kind'],'outcome_conditioned')
        self.assertIn('response_time IS NOT NULL',contract['selection']['evidence'])

    def test_refuses_foreign_directory(self):
        self.output.mkdir()
        (self.output / "someone-elses-file").write_text("keep me\n")
        with self.assertRaises(FileExistsError):
            smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        self.assertTrue((self.output / "someone-elses-file").is_file())

    def test_holdout_bytes_are_the_published_eval_unchanged(self):
        smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        source = hashlib.sha256((self.input / "eval.csv").read_bytes()).hexdigest()
        copied = hashlib.sha256((self.output / "private" / "holdout.csv").read_bytes()).hexdigest()
        self.assertEqual(source, copied)

    def test_measured_counts_and_windows(self):
        result = smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        self.assertEqual(result["counts"]["train"]["rows"], 18 * 40)
        self.assertEqual(result["counts"]["eval"]["rows"], 6 * 40)
        self.assertEqual(result["counts"]["holdout"]["rows"], 8 * 40)
        self.assertEqual(sum(result["counts"][s]["positives"] for s in result["counts"])
                         - result["counts"]["holdout"]["positives"],
                         result["counts"]["train"]["positives"] + result["counts"]["eval"]["positives"])
        self.assertGreaterEqual(result["counts"]["eval"]["positives"], 30)
        self.assertGreaterEqual(result["distinct_events"]["eval"], 20)
        self.assertGreaterEqual(result["counts"]["holdout"]["positives"], 30)
        self.assertGreaterEqual(result["distinct_events"]["holdout"], 20)
        self.assertEqual(result["windows"]["train"]["end"],
                         "2024-07-01T00:00:00.000")
        self.assertEqual(result["windows"]["eval"]["start"],
                         "2024-07-01T00:00:00.000")
        self.assertEqual(result["windows"]["eval"]["end"],
                         "2025-01-01T00:00:00.000")
        self.assertEqual(result["cross_split_entities"]["count"], 0)
        meta = json.loads((self.output / "meta.json").read_text())
        self.assertEqual(meta["id_columns"], ["incident_number"])
        self.assertEqual(meta["columns"], COLUMNS)
        self.assertEqual(meta["rows"]["eval"], 6 * 40)
        quality = json.loads((self.output / "quality.json").read_text())
        evidence = quality["evaluation_contract"]["feature_evidence"]
        self.assertEqual(sorted(evidence), sorted(c for c in COLUMNS if c != "late"))
        for column, entry in evidence.items():
            self.assertEqual(entry["status"], "assumed")
            self.assertTrue(entry["source"] and entry["availability"])
        self.assertEqual(quality["evaluation_contract"]["access"], "chronological")
        self.assertEqual(quality["evaluation_contract"]["use"], "retrospective_research")
        self.assertEqual(quality["timing"]["observations"], [])
        self.assertEqual(quality["expected_duplicate_ids"], 0)

    def test_calendar_order_not_encounter_order(self):
        # Re-write train rows in reverse encounter order; the boundary must stay
        # the same calendar month.
        rows = list(_rows(_months((2023, 1), 24)))
        with (self.input / "train.csv").open(newline="", encoding="utf-8") as handle:
            fieldnames = next(csv.reader(handle))
        with (self.input / "train.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reversed(rows))
        result = smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        self.assertEqual(result["boundary_month"], "2024-07")

    def test_refuses_source_without_truthful_declarations(self):
        quality = json.loads((self.input / "quality.json").read_text())
        del quality["label_source_columns"]
        (self.input / "quality.json").write_text(json.dumps(quality))
        with self.assertRaises(ValueError) as ctx:
            smoke_artifact.build_derivative(self.input, self.output, SMOKE)
        self.assertIn("label_source_columns", str(ctx.exception))


class GateAcceptanceTests(unittest.TestCase):
    """THE integration proof: the real gate, two-phase, on a built fixture.

    qualify --report must pass (report ok), --accept must succeed, and a
    mutated CSV after the report must be refused by --accept.
    """

    @classmethod
    def setUpClass(cls):
        if not GATE.is_file():
            raise unittest.SkipTest("gate script not present")
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.input = base / "input"
        cls.input.mkdir()
        _fixture_input(cls.input)
        cls.derivative = base / "derivative"
        cls.derivative.mkdir()
        (cls.derivative / ".smoke-owned").write_text("owned\n")
        cls.result = smoke_artifact.build_derivative(cls.input, cls.derivative, SMOKE)
        cls.report = base / "report.json"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_01_qualification_report_passes(self):
        completed = subprocess.run(
            [sys.executable, str(GATE), str(self.derivative),
             "--report", str(self.report)],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(completed.returncode, 0, completed.stdout[-2000:])
        payload = json.loads(self.report.read_text())
        self.assertTrue(payload["ok"],
                        f"failed checks: {payload.get('failed_checks')}")
        self.assertEqual(payload["gate_version"], "1.5.0")
        self.assertEqual(payload["failed_checks"], [])

    def test_02_accept_succeeds_on_qualified_bytes(self):
        self.assertTrue(self.report.is_file(), "report must exist from test_01")
        completed = subprocess.run(
            [sys.executable, str(GATE), "--accept", str(self.report),
             str(self.derivative)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stdout[-2000:])
        self.assertIn("ACCEPTED", completed.stdout)

    def test_03_accept_refuses_mutated_csv(self):
        with (self.derivative / "public" / "train.csv").open("a", newline="",
                                                           encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writerow({**dict.fromkeys(COLUMNS, "0"),
                             "incident_number": "MUTANT",
                             "response_datetime": "2023-06-01T00:00:00.000",
                             "late": "1"})
        completed = subprocess.run(
            [sys.executable, str(GATE), "--accept", str(self.report),
             str(self.derivative)],
            capture_output=True, text=True, timeout=120)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ACCEPT FAILED", completed.stdout)
        self.assertIn("has changed since qualification", completed.stdout)


class AssemblerTests(unittest.TestCase):
    """Real assembly from the read-only pinned harness; exact runtime schema."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        if not HARNESS.is_dir():
            raise unittest.SkipTest("pinned harness checkout not present")
        head = subprocess.run(["git", "-C", str(HARNESS), "rev-parse", f"{HARNESS_COMMIT}^{{commit}}"],
                              capture_output=True, text=True, timeout=60)
        if head.stdout.strip() != HARNESS_COMMIT:
            raise unittest.SkipTest(f"harness commit unavailable: {HARNESS_COMMIT[:12]}")
        job = json.loads((ROOT / "ops" / "smoke" /
                          "austin-adapter-smoke-001.job.json").read_text())
        # CI clones are shallow: cross-branch commit pins (the runtime owner's
        # adapter @commit) resolve only where that object is fetched. The tests
        # de-ref them to the working tree; the @ref machinery itself is proven
        # by the dedicated @HEAD test below.
        for path, spec in job["smoke"]["bundle_files"].items():
            if spec.startswith("repo:") and "@" in spec:
                job["smoke"]["bundle_files"][path] = spec.rsplit("@", 1)[0]
        self.job_path = self.base / "job.json"
        self.job_path.write_text(json.dumps(job, indent=2) + "\n")
        self.out_path = self.base / "pinned.json"

    def _assemble(self, verify=False):
        return subprocess.run(
            [sys.executable, str(ASSEMBLER), str(self.job_path),
             "--harness", str(HARNESS), "--out", str(self.out_path)]
            + ([] if verify else ["--no-gh-verify"]),
            capture_output=True, text=True, timeout=300)

    def test_assembles_real_bundle_with_runtime_schema(self):
        completed = self._assemble()
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        bundle = json.loads(self.out_path.read_text())
        # Exactly the runtime's source/pinned.json schema.
        self.assertEqual(sorted(bundle), ["files", "harness_commit"])
        self.assertEqual(bundle["harness_commit"], HARNESS_COMMIT)
        for path, entry in bundle["files"].items():
            self.assertEqual(sorted(entry), ["base64", "sha256"], path)
            content = base64.b64decode(entry["base64"])
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"],
                             f"digest mismatch for {path}")
        self.assertLess(self.out_path.stat().st_size, 2 * 1024 * 1024)
        for required in ("image/Dockerfile", "image/.dockerignore",
                        "image/uv.lock", "image/pyproject.toml",
                        "image/task_template/train.py",
                        "image/bench/score_holdout.py",
                        "adapter/score_holdout.py", "gate/qualify_dataset.py",
                        "workers/smoke_artifact.py"):
            self.assertIn(required, bundle["files"])
        job = json.loads(self.job_path.read_text())
        smoke = job["smoke"]
        # set(files) == set(pinned_sources): the runtime's materializer requires
        # exactly this equality, and every digest must match.
        self.assertEqual(set(smoke["pinned_sources"]), set(bundle["files"]))
        for path, digest in smoke["pinned_sources"].items():
            self.assertEqual(digest, bundle["files"][path]["sha256"])
        # expected_sha256 is keyed by LOGICAL names — the runtime fetches each
        # under its REAL asset name from smoke.asset_names.
        self.assertEqual(sorted(smoke["expected_sha256"]),
                         ["meta.json", "public/eval.csv", "public/train.csv",
                          "quality.json"])
        self.assertEqual(smoke["asset_names"],
                         {"public/train.csv": "train.csv",
                          "public/eval.csv": "eval.csv",
                          "meta.json": "meta.json",
                          "quality.json": "quality.json"})
        manifest = json.loads((ROOT / "release" / "austin-911-response" /
                               "MANIFEST.json").read_text())
        self.assertEqual(smoke["expected_sha256"]["public/train.csv"],
                         manifest["assets"]["public/train.csv"]["sha256"])
        # artifact_version is copied programmatically from the frozen manifest,
        # never transcribed.
        self.assertEqual(smoke["artifact_version"], manifest["artifact_version"])
        self.assertEqual(smoke["source_bundle"]["sha256"],
                         hashlib.sha256(self.out_path.read_bytes()).hexdigest())
        self.assertTrue(smoke["source_provenance"]["image/Dockerfile"]
                        .startswith(f"harness@{HARNESS_COMMIT}:"))
        self.assertIn("repo@", smoke["source_provenance"]["gate/qualify_dataset.py"])

    def test_ref_source_resolves_commit(self):
        job = json.loads(self.job_path.read_text())
        job["smoke"]["bundle_files"]["adapter/score_holdout.py"] = \
            "repo:adapters/score_holdout.py@HEAD"
        self.job_path.write_text(json.dumps(job))
        completed = self._assemble()
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=60).stdout.strip()
        job = json.loads(self.job_path.read_text())
        self.assertEqual(job["smoke"]["source_provenance"]["adapter/score_holdout.py"],
                         f"repo@{head}:adapters/score_holdout.py")
        expected = subprocess.run(["git", "-C", str(ROOT), "show",
                                   "HEAD:adapters/score_holdout.py"],
                                  capture_output=True, timeout=60).stdout
        bundle = json.loads(self.out_path.read_text())
        entry = bundle["files"]["adapter/score_holdout.py"]
        self.assertEqual(hashlib.sha256(expected).hexdigest(), entry["sha256"])

    def test_refuses_unresolvable_ref(self):
        job = json.loads(self.job_path.read_text())
        job["smoke"]["bundle_files"]["adapter/score_holdout.py"] = \
            "repo:adapters/score_holdout.py@" + "0" * 40
        self.job_path.write_text(json.dumps(job))
        completed = self._assemble()
        self.assertEqual(completed.returncode, 1)

    def test_refuses_nonexistent_harness_source(self):
        job = json.loads(self.job_path.read_text())
        job["smoke"]["bundle_files"]["image/ghost.py"] = "harness:does/not/exist.py"
        self.job_path.write_text(json.dumps(job))
        completed = self._assemble()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("has no", completed.stderr)

    def test_refuses_forbidden_bundle_path(self):
        job = json.loads(self.job_path.read_text())
        job["smoke"]["bundle_files"]["image/.git/config"] = "harness:README.md"
        self.job_path.write_text(json.dumps(job))
        completed = self._assemble()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("forbidden", completed.stderr)

    def test_refuses_bulk_csv_source(self):
        job = json.loads(self.job_path.read_text())
        job["smoke"]["bundle_files"]["rows/train.csv"] = "harness:README.md"
        self.job_path.write_text(json.dumps(job))
        completed = self._assemble()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("refuses bulk", completed.stderr)

    def test_refuses_wrong_harness_commit(self):
        job = json.loads(self.job_path.read_text())
        job["smoke"]["harness_commit"] = "0" * 40
        self.job_path.write_text(json.dumps(job))
        completed = self._assemble()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("pins", completed.stderr)


if __name__ == "__main__":
    unittest.main()
