"""Tests for the deployment export.

The export is configuration and state that will be committed, so the checks that matter are the
negative ones: that a secret-shaped string stops the write, that only allowlisted configuration
fields can appear, and that no excluded file type reaches the directory.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scout-snapshot.py"
EXPORT = ROOT / "deployment" / "scout"

spec = importlib.util.spec_from_file_location("scout_snapshot", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
snapshot = importlib.util.module_from_spec(spec)
sys.modules["scout_snapshot"] = snapshot
exec(compile(SCRIPT.read_bytes(), str(SCRIPT), "exec"), snapshot.__dict__)


class SecretScanTests(unittest.TestCase):
    def test_github_tokens_are_detected(self):
        for sample in ("ghp_" + "a" * 24, "github_pat_" + "b" * 24):
            with self.subTest(sample=sample[:10]):
                self.assertTrue(snapshot.scan(f"token: {sample}", "test"))

    def test_hugging_face_and_openai_shaped_keys_are_detected(self):
        for sample in ("hf_" + "c" * 30, "sk-" + "d" * 30, "AKIA" + "E" * 14):
            with self.subTest(sample=sample[:6]):
                self.assertTrue(snapshot.scan(sample, "test"))

    def test_private_keys_and_bearer_headers_are_detected(self):
        self.assertTrue(snapshot.scan("-----BEGIN OPENSSH PRIVATE KEY-----", "test"))
        self.assertTrue(snapshot.scan("Authorization: Bearer " + "e" * 30, "test"))

    def test_ordinary_content_is_not_flagged(self):
        text = ("allowance 5.0 USD; tag v2026.09; artifact e4598317e406984f; "
                "servers 0; primary IPs 0")
        self.assertEqual([], snapshot.scan(text, "test"))

    def test_allowlist_entries_that_name_a_credential_are_rejected(self):
        """A field name that smells like a credential is refused even if someone allowlists it."""
        for name in ("hf_token", "github.secret", "worker.credentials", "notify.chat_id"):
            with self.subTest(field=name):
                self.assertIsNotNone(snapshot.FORBIDDEN_KEYS.search(name))


class ExportedFilesTests(unittest.TestCase):
    def test_the_committed_exports_exist(self):
        for name in ("versions.json", "config-export.json", "STATE-SNAPSHOT.md", "README.md",
                     "IDENTITY.md"):
            with self.subTest(file=name):
                self.assertTrue((EXPORT / name).is_file(), f"{name} is missing from the export")

    def test_no_committed_export_contains_a_secret_shape(self):
        for path in EXPORT.rglob("*"):
            if not path.is_file():
                continue
            with self.subTest(file=path.name):
                self.assertEqual([], snapshot.scan(path.read_text(errors="replace"), path.name))

    def test_only_allowlisted_configuration_fields_are_exported(self):
        exported = json.loads((EXPORT / "config-export.json").read_text())
        self.assertEqual(sorted(snapshot.CONFIG_ALLOWLIST), sorted(exported["allowlist"]))
        for key in exported["fields"]:
            with self.subTest(field=key):
                self.assertIn(key, snapshot.CONFIG_ALLOWLIST)
                self.assertIsNone(snapshot.FORBIDDEN_KEYS.search(key),
                                  f"{key} looks like a credential and must not be exported")

    def test_no_excluded_file_type_is_committed(self):
        self.assertEqual([], snapshot.forbidden_files())

    def test_the_snapshot_records_its_sources_and_observation_time(self):
        text = (EXPORT / "STATE-SNAPSHOT.md").read_text()
        self.assertIn("Observed ", text)
        self.assertIn("Source:", text)
        versions = json.loads((EXPORT / "versions.json").read_text())
        self.assertTrue(versions.get("observed_at"))

    def test_the_snapshot_does_not_name_a_delivery_chat(self):
        """Private messaging identifiers stay out of the export."""
        text = (EXPORT / "STATE-SNAPSHOT.md").read_text()
        self.assertNotIn("telegram:", text)
        self.assertNotIn("chat_id", text)

    def test_the_check_mode_passes_on_the_committed_export(self):
        self.assertEqual(0, snapshot.main(["--check"]))


if __name__ == "__main__":
    unittest.main()
