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


STUB_HUGGINGFACE = '''\
"""Stand-in for huggingface_hub: records the commits the upload helper asks for."""
import json
import os


class CommitOperationAdd:
    def __init__(self, path_or_fileobj, path_in_repo):
        self.path_or_fileobj = path_or_fileobj
        self.path_in_repo = path_in_repo


class HfApi:
    def __init__(self, token=None):
        self.token = token

    def create_commit(self, repo_id=None, repo_type=None, revision=None, operations=None,
                      commit_message=None):
        with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"repo_id": repo_id, "operations": len(operations),
                                     "targets": [op.path_in_repo for op in operations]}) + "\\n")
        return type("CommitInfo", (), {"oid": "stub-oid"})()

    def upload_file(self, **kwargs):
        raise AssertionError("the uploader must batch files into one commit, not one per file")
'''


class UploadBatchingTests(unittest.TestCase):
    """One commit per file hits the Hub's per-repository commit limit.

    It did: 99 of 226 MSHA assets failed with HTTP 429 after ~127 single-file commits, and the
    job had to be re-run. These tests run the real helper source against a stub client.
    """

    def test_the_helper_commits_the_whole_plan_in_one_commit(self):
        import json as jsonlib
        import os
        import subprocess
        import sys
        import tempfile

        body = dict(helpers())["UPLOAD_HELPER"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "huggingface_hub.py").write_text(STUB_HUGGINGFACE)
            (root / "helper.py").write_text(body)
            files = []
            for index in range(3):
                path = root / f"asset-{index}.bin"
                path.write_bytes(b"payload")
                files.append({"path": str(path), "target": f"data/asset-{index}.csv"})
            (root / "plan.json").write_text(jsonlib.dumps(files))
            log = root / "calls.log"
            env = dict(os.environ, PYTHONPATH=tmp, HF_WRITE_TOKEN="stub-token",
                       STUB_LOG=str(log))
            finished = subprocess.run([sys.executable, str(root / "helper.py"), "owner/repo",
                                       str(root / "plan.json"), "main"],
                                      capture_output=True, text=True, cwd=tmp, env=env,
                                      timeout=120)
            self.assertEqual(finished.returncode, 0, finished.stderr)
            calls = [jsonlib.loads(line) for line in log.read_text().splitlines() if line]
        self.assertEqual(1, len(calls), calls)
        self.assertEqual(3, calls[0]["operations"], calls)
        self.assertEqual(["data/asset-0.csv", "data/asset-1.csv", "data/asset-2.csv"],
                         calls[0]["targets"])

    def test_the_batch_size_stays_inside_a_sane_commit(self):
        text = HELPER_SOURCE.read_text()
        match = re.search(r"^BATCH_SIZE = (\d+)$", text, re.M)
        self.assertIsNotNone(match, "no batch size is defined")
        size = int(match.group(1))
        self.assertGreater(size, 1, "one commit per file exceeds the Hub commit limit")
        self.assertLessEqual(size, 16)


if __name__ == "__main__":
    unittest.main()
