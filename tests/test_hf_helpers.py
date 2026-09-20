"""Static checks on the worker's Hugging Face helpers.

The helpers are source strings written to disk and run as separate processes on the worker, so a
missing import is not caught by importing this module - it is caught three minutes into a paid
job. That is exactly what happened: the verify helper used `os.environ` without importing `os`,
and the job failed after the (correct) upload had already been verified.

So the imports of every helper are checked here, against the modules the body actually uses.
"""
import ast
import json
import re
import unittest
from pathlib import Path

HELPER_SOURCE = Path(__file__).resolve().parents[1] / "workers" / "hf_publish.py"
STDLIB_LOOKALIKES = ("os", "sys", "json", "hashlib", "subprocess", "pathlib", "urllib")


def helpers():
    text = HELPER_SOURCE.read_text()
    pattern = re.compile(r"^([A-Z_]*HELPER) = '''(.*?)'''", re.S | re.M)
    return pattern.findall(text)


class HelperImportTests(unittest.TestCase):
    def test_at_least_the_upload_and_verify_helpers_are_checked(self):
        names = [name for name, _ in helpers()]
        self.assertIn("UPLOAD_HELPER", names)
        self.assertIn("VERIFY_HELPER", names)

    def test_every_helper_parses(self):
        for name, body in helpers():
            with self.subTest(helper=name):
                ast.parse(body)

    def test_every_helper_imports_every_module_it_uses(self):
        for name, body in helpers():
            with self.subTest(helper=name):
                imported = set(re.findall(r"^import (\w+)", body, re.M))
                imported |= {match.split()[0] for match in
                             re.findall(r"^from (\w+) import", body, re.M)}
                used = {module for module in STDLIB_LOOKALIKES if f"{module}." in body}
                self.assertEqual(set(), used - imported,
                                 f"{name} uses {sorted(used - imported)} without importing it")

    def test_the_verify_helper_passes_the_credential_explicitly(self):
        """A private dataset cannot be read without it, and HF_TOKEN is absent from that child."""
        body = dict(helpers())["VERIFY_HELPER"]
        self.assertIn("token=os.environ", body)

    def test_the_helpers_never_take_a_credential_as_an_argument(self):
        for name, body in helpers():
            with self.subTest(helper=name):
                self.assertNotIn("sys.argv[5]", body)
                self.assertNotIn("--token", body)


STUB_DATASETS = """\
\"\"\"Stand-in for the `datasets` package so the helper's own branches can be run for real.\"\"\"
import json
import os


class Frame:
    def __init__(self):
        self.num_rows = 10
        self.column_names = ["row_id", "late"]

    def __len__(self):
        return self.num_rows

    def __getitem__(self, key):
        return [1, 1, 1] + [0] * 7

    def unique(self, column):
        return [0, 1]


def load_dataset(repo_id, name=None, revision=None, token=None):
    assert token == "stub-token", token
    return {split: Frame() for split in ("train", "eval", "holdout")}
"""


def run_verify_helper(expected):
    """Run the real VERIFY_HELPER source against a stub `datasets`, as the worker does."""
    import json
    import os
    import subprocess
    import sys
    import tempfile

    body = dict(helpers())["VERIFY_HELPER"]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "datasets.py").write_text(STUB_DATASETS)
        (root / "helper.py").write_text(body)
        (root / "expected.json").write_text(json.dumps(expected))
        env = dict(os.environ, PYTHONPATH=tmp, HF_WRITE_TOKEN="stub-token")
        finished = subprocess.run([sys.executable, str(root / "helper.py"),
                                   "owner/repo", "main", str(root / "expected.json")],
                                  capture_output=True, text=True, cwd=tmp, env=env, timeout=120)
    return finished


def frames(rows=10, positives=3):
    return {split: {"rows": rows, "positives": positives}
            for split in ("train", "eval", "holdout")}


class VerifyHelperBranchTests(unittest.TestCase):
    """The helper is written to disk and run as its own process, so both of its branches are run.

    The multi-config branch used to fall through into the single-config code, which read
    `expected["splits"]` for a job that declares `configs`: the crash happened after the upload had
    already been verified, and it cost a paid worker run to find. Running the source is the only
    check that would have caught it.
    """

    def test_multi_config_jobs_are_checked_per_config(self):
        expected = {"configs": {name: {"splits": frames(), "columns": ["row_id", "late"],
                                       "label": "late"}
                                for name in ("station_disjoint", "temporal")}}
        finished = run_verify_helper(expected)
        self.assertEqual(finished.returncode, 0, finished.stderr)
        report = json.loads(finished.stdout)
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual([], report["problems"])
        self.assertEqual(["train", "eval", "holdout"], report["configs"]["temporal"]["splits"])
        self.assertEqual(3, report["checked"]["temporal/train"]["positives"])
        self.assertNotIn("splits", report, "the single-config branch must not run for a configs job")

    def test_multi_config_jobs_compare_rather_than_just_load(self):
        expected = {"configs": {"temporal": {"splits": frames(positives=4),
                                             "columns": ["row_id", "late"], "label": "late"}}}
        finished = run_verify_helper(expected)
        report = json.loads(finished.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(any("positives" in problem for problem in report["problems"]),
                        report["problems"])

    def test_single_config_jobs_still_run_the_original_path(self):
        expected = {"splits": frames(), "columns": ["row_id", "late"], "label": "late",
                    "label_values": [0, 1]}
        finished = run_verify_helper(expected)
        self.assertEqual(finished.returncode, 0, finished.stderr)
        report = json.loads(finished.stdout)
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(["train", "eval", "holdout"], report["splits"])
        self.assertEqual(10, report["checked"]["train"]["rows"])


if __name__ == "__main__":
    unittest.main()
