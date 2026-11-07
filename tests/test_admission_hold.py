"""Admission refuses before side effects, without disabling recovery."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from factory import admission, candidates
from factory.common import FactoryError, write_json
from tests.test_research_session_wrapper import load, ROOT

session = load("hold_session_test", ROOT / "scripts/scout_research_session.py")
capture = load("hold_capture_test", ROOT / "scripts/standing-capture.py")
manifest = load("hold_manifest_test", ROOT / "scripts/release-manifest.py")


class AdmissionHoldTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "config/admission.json"
        self.value = dict(version=1, hold=True, reason="acceptance pending",
                          allowed_worker_bundles={})
        write_json(self.path, self.value)

    def test_missing_malformed_duplicate_and_wrong_type_fail_closed(self):
        for body in ('{}', '{', '{"hold":true,"hold":false}',
                     json.dumps({**self.value, "hold": "false"})):
            self.path.write_text(body)
            with self.assertRaisesRegex(FactoryError, "missing or invalid"):
                admission.require(self.root, "discovery")
        self.path.unlink()
        with self.assertRaises(FactoryError):
            admission.require(self.root, "discovery")

    def test_operator_can_lift_hold_with_one_field(self):
        with self.assertRaisesRegex(FactoryError, "remediation hold"):
            candidates.create(self.root, "test")
        self.assertFalse((self.root / "candidates").exists())
        self.value["hold"] = False
        write_json(self.path, self.value)
        self.assertEqual("test", candidates.create(self.root, "test")["id"])

    def test_only_exact_reviewed_worker_bundle_is_admitted(self):
        self.value["allowed_worker_bundles"] = {"audit-001": "a" * 64}
        write_json(self.path, self.value)
        admission.require(self.root, "worker", job_id="audit-001", bundle_sha256="a" * 64)
        for job, digest in (("audit-002", "a" * 64), ("audit-001", "b" * 64)):
            with self.assertRaises(FactoryError):
                admission.require(self.root, "worker", job_id=job, bundle_sha256=digest)

    def test_session_holds_before_budget_or_model_and_reports_held_slot(self):
        events = []
        with patch.object(session, "REPO", self.root), \
                patch.object(session, "note"), patch.object(session, "run_gate") as budget, \
                patch.object(session, "run_agent") as agent:
            self.assertEqual(0, session.run_session(session.parse_args([]), -1,
                observe=lambda *args: events.append(args)))
        self.assertEqual("held", events[0][0])
        budget.assert_not_called()
        agent.assert_not_called()

    def test_followup_still_uses_budget_and_cannot_be_enabled_by_prompt_name(self):
        with patch.object(session, "REPO", self.root), patch.object(session, "note"), \
                patch.object(session, "run_gate", return_value=(False, "", "budget held")) as gate:
            args = session.parse_args(["--prompt-file", "docs/worker-watch-prompt.md"])
            session.run_session(args, -1)
            gate.assert_not_called()
            session.run_session(args, -1, worker_followup=True)
            gate.assert_called_once()

    def test_source_capture_refuses_before_fetch_or_ledger_write(self):
        with patch.object(capture, "ROOT", self.root), patch.object(capture, "fetch") as fetch, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, capture.main(["--all"]))
        fetch.assert_not_called()
        self.assertFalse((self.root / "candidates").exists())

    def test_new_manifest_refuses_before_descriptor_or_write(self):
        with patch.object(manifest, "ROOT", self.root), \
                patch.object(manifest.sys, "argv", ["release-manifest.py", "test"]), \
                patch.object(manifest, "descriptor") as descriptor:
            with self.assertRaisesRegex(FactoryError, "package construction"):
                manifest.main()
        descriptor.assert_not_called()
        self.assertFalse((self.root / "release").exists())
