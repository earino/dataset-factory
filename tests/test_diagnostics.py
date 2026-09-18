import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from factory.__main__ import main
from factory.common import FactoryError
from factory.diagnostics import benchmark_status, memory_status
from factory.http import credential_status, secret


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "private.token"
        self.path.write_text("fixture-secret-never-print\n")
        self.path.chmod(0o600)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_doctor_checks_files_without_disclosing_values_or_paths(self):
        for name in ("HCLOUD_TOKEN_FILE", "FACTORY_GITHUB_TOKEN_FILE"):
            os.environ[name] = str(self.path)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(["--root", str(self.root), "doctor", "--require-worker-credentials"])
        self.assertEqual(status, 0)
        raw = output.getvalue()
        self.assertNotIn("fixture-secret-never-print", raw)
        self.assertNotIn("private.token", raw)
        report = json.loads(raw)
        self.assertEqual(report["worker_credentials"]["HCLOUD_TOKEN"]["source"], "file")
        self.assertFalse(report["github_cli_environment"]["GH_TOKEN"])

    def test_missing_credentials_only_fail_explicit_preflight(self):
        # A Hermes dashboard .env is deliberately not executed or parsed.
        (self.root / ".env").write_text("HCLOUD_TOKEN=fixture-secret-never-print\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root), "doctor"]), 0)
            self.assertEqual(main(["--root", str(self.root), "doctor", "--require-worker-credentials"]), 1)
        with self.assertRaises(FactoryError):
            secret("HCLOUD_TOKEN")

    def test_launcher_works_outside_repo_without_shell_startup(self):
        import sys
        launcher = Path(__file__).resolve().parents[1] / "scripts/scout-factory"
        # Keep only the Python binary search path and explicit token-file paths.
        environment = {"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
                       "HCLOUD_TOKEN_FILE": str(self.path), "FACTORY_GITHUB_TOKEN_FILE": str(self.path)}
        result = subprocess.run(["/bin/sh", str(launcher), "doctor", "--require-worker-credentials"],
                                cwd=self.root, env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("fixture-secret-never-print", result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(all(state["ready"] for state in report["worker_credentials"].values()))
        self.assertEqual(report["project_root"], str(launcher.parent.parent))

    def test_environment_precedence_matches_runtime(self):
        os.environ.update(HCLOUD_TOKEN="environment-fixture", HCLOUD_TOKEN_FILE=str(self.root / "missing"))
        report = credential_status("HCLOUD_TOKEN")
        self.assertEqual(report["source"], "environment")
        self.assertEqual(report["file_status"], "missing")
        self.assertEqual(secret("HCLOUD_TOKEN"), "environment-fixture")

    def test_bad_files_rejected_by_doctor_and_runtime(self):
        os.environ["HCLOUD_TOKEN_FILE"] = str(self.path)
        for state, contents, mode in (("insecure_permissions", "token", 0o644),
                                      ("empty", " \n", 0o600), ("too_large", "x" * 4097, 0o600)):
            with self.subTest(state=state):
                self.path.write_text(contents)
                self.path.chmod(mode)
                self.assertEqual(credential_status("HCLOUD_TOKEN")["file_status"], state)
                with self.assertRaisesRegex(FactoryError, state):
                    secret("HCLOUD_TOKEN")
        os.environ["HCLOUD_TOKEN_FILE"] = str(self.root)
        self.assertEqual(credential_status("HCLOUD_TOKEN")["file_status"], "not_regular")


class ResourceTests(unittest.TestCase):
    def test_available_memory_respects_visible_container_headroom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "meminfo"
            proc.write_text("MemTotal: 2097152 kB\nMemAvailable: 916480 kB\nSwapTotal: 1048576 kB\n")
            (root / "memory.max").write_text(str(1024**3))
            (root / "memory.current").write_text(str(768 * 1024**2))
            report = memory_status(proc, root)
            self.assertEqual(report["available_mib"], 895)
            self.assertEqual(report["effective_available_mib"], 256)
            self.assertEqual(report["swap_total_mib"], 1024)
            (root / "memory.max").write_text("max")
            self.assertEqual(memory_status(proc, root)["effective_available_mib"], 895)

    def test_unavailable_memory_is_unknown_not_hardcoded_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(memory_status(root / "missing", root)["effective_available_mib"])

    def test_benchmark_source_does_not_imply_prepared_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "dataset-factory"
            benchmark = root / "harness_benchmark"
            (benchmark / "bench").mkdir(parents=True)
            (benchmark / "datasets").mkdir()
            (benchmark / "datasets/prepare_credit.py").touch()
            report = benchmark_status(project)
            self.assertTrue(report["source_present"])
            self.assertTrue(report["preparation_scripts"]["credit"])
            self.assertFalse(any(report["prepared_tasks"].values()))
            for file in ("meta.json", "public/train.csv", "public/eval.csv", "private/holdout.csv"):
                path = benchmark / "data/prepared/airline" / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            report = benchmark_status(project)
            self.assertTrue(report["prepared_tasks"]["airline"])
            self.assertFalse(report["prepared_tasks"]["fraud"])


if __name__ == "__main__":
    unittest.main()
