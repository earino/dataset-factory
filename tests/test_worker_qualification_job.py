"""The worker job that builds and qualifies the Austin extract.

Qualification has to run on the worker, over the full artifact, before anything is scored.
That means the job bundle must be self-contained - the worker cannot read this repository -
and the entrypoint must fail the job when the gate fails while still leaving the gate's
diagnostics in `/output` for collection.

These tests exercise the assembly step and the bundle rules that `factory.worker` enforces,
without launching anything or touching the network.
"""
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factory import worker  # noqa: E402


def load_assemble_module():
    path = ROOT / "scripts" / "assemble-job.py"
    spec = importlib.util.spec_from_file_location("assemble_job", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["assemble_job"] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


assemble_job = load_assemble_module()


class AssembledBundle(unittest.TestCase):
    def setUp(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(assemble_job.main(["austin-001"]), 0)
        self.report = json.loads(captured.getvalue())
        self.directory = ROOT / self.report["job_directory"]
        self.job = json.loads((self.directory / "job.json").read_text())

    def test_the_bundle_is_self_contained(self):
        names = {entry["bundled_as"] for entry in self.report["files"]}
        self.assertEqual(names, {"build.py", "run.sh", "qualify_dataset.py"})
        self.assertTrue((self.directory / "build.py").is_file())
        self.assertTrue((self.directory / "run.sh").is_file())
        # The gate inside the bundle is the repository's gate, byte for byte.
        canonical = ROOT / "skills" / "dataset-qualification" / "scripts" / "qualify_dataset.py"
        self.assertEqual((self.directory / "qualify_dataset.py").read_bytes(),
                         canonical.read_bytes())

    def test_the_bundle_passes_the_worker_source_rules(self):
        bundle = worker.source_bundle(self.directory / "job.json", self.job)
        self.assertTrue(bundle)
        self.assertLessEqual(len(bundle), 2 * 1024 * 1024)
        # The bundle carries the worker's own executor, not just the job's files.
        self.assertIn(b"source/build.py", bundle)
        self.assertIn(b"source/run.sh", bundle)
        self.assertIn(b"source/qualify_dataset.py", bundle)

    def test_the_entrypoint_builds_then_qualifies_and_fails_the_job(self):
        script = (self.directory / "run.sh").read_text()
        self.assertIn("build.py --out", script)
        self.assertIn("qualify_dataset.py", script)
        self.assertIn("--report /output/qualification.json", script)
        # Diagnostics survive a failure, and a failed gate is a non-zero exit.
        self.assertIn("exit \"$qual_status\"", script)
        self.assertIn("cp \"$OUT/summary.json\" /output/summary.json", script)

    def test_the_job_fits_the_configured_allowance(self):
        policy_path = ROOT / "config" / "local.json"
        if not policy_path.is_file():
            self.skipTest("no local policy on this machine")
        policy = json.loads(policy_path.read_text())
        self.assertIn(self.job["server_type"], policy["server_types"])
        self.assertIn(self.job["location"], policy["allowed_locations"])
        self.assertLessEqual(self.job["lifetime_minutes"], policy["max_lifetime_minutes"])

    def test_plan_is_offline_and_reports_the_reservation(self):
        result = subprocess.run(
            ["sh", "scripts/scout-factory", "worker", "plan",
             f"{self.report['job_directory']}/job.json"],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["cloud_calls"], 0)
        self.assertFalse(plan["enabled"], "launches stay disabled until cleanup is verified")
        self.assertEqual(plan["reserved_hours"], 3)
        self.assertEqual(plan["reservation_eur"], "0.24")


if __name__ == "__main__":
    unittest.main()
