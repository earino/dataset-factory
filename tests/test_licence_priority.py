"""Licence triage decides what gets built, so it is enforced in two places.

18 of 31 parked candidates were parked for licence or terms reasons, after the probing had already
been done. The fix is ordering: classify the licence first, sort the queue by it, and refuse to call
anything `ready` until it carries a class.

These tests pin both halves: the check that refuses a record without a class, and the ranker that
puts class A ahead of class C.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check = load("candidate_check_licence", ROOT / "scripts" / "check-candidate.py")


def record(**overrides):
    base = {
        "id": "fixture-candidate",
        "status": "ready",
        "domain": "testing",
        "prediction_question": "Will X happen?",
        "prediction_time": "at the publication of month M",
        "target_definition": "1 if X",
        "sources": [{"name": "fixture", "url": "https://example.org", "license": "CC BY 4.0"}],
        "license_evidence": [{"quote": "CC BY 4.0", "url": "https://example.org"}],
        "next_action": "build it",
        "jurisdiction": {"country": "CL"},
        "novelty": {"verdict": "novel", "checked_at": "2026-10-21", "against": []},
    }
    base.update(overrides)
    return base


class LicenceClassTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="licence-priority-"))
        (self.tmp / "candidates" / "fixture-candidate").mkdir(parents=True)

    def write(self, payload):
        (self.tmp / "candidates" / "fixture-candidate" / "record.json").write_text(
            json.dumps(payload))

    def problems(self):
        _, missing, _ = check.report(self.tmp, "fixture-candidate")
        return missing

    def test_a_ready_candidate_without_a_licence_class_is_refused(self):
        self.write(record())
        problems = self.problems()
        self.assertTrue(any(p.startswith("licence_class:") for p in problems), problems)

    def test_an_open_licence_class_passes(self):
        self.write(record(licence_class="A"))
        self.assertFalse([p for p in self.problems() if p.startswith("licence_class")])

    def test_a_prohibited_licence_cannot_be_packaged(self):
        self.write(record(status="packaged", licence_class="D"))
        problems = self.problems()
        self.assertTrue(any("cannot be published" in p for p in problems), problems)

    def test_an_investigating_candidate_may_stay_unclassified(self):
        self.write(record(status="investigating", novelty=None))
        self.assertFalse([p for p in self.problems() if p.startswith("licence_class")])


class RankOrderTests(unittest.TestCase):
    def test_class_a_sorts_ahead_of_c_in_the_queue(self):
        root = Path(tempfile.mkdtemp(prefix="licence-rank-"))
        for cid, cls in (("c-open", "C"), ("a-open", "A"), ("b-open", "B")):
            (root / "candidates" / cid).mkdir(parents=True)
            (root / "candidates" / cid / "record.json").write_text(json.dumps({
                "id": cid, "status": "ready", "licence_class": cls,
                "jurisdiction": {"country": "CL"}}))
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "licence-rank.py"),
                              "--root", str(root), "--json"],
                             capture_output=True, text=True, check=True).stdout
        payload = json.loads(out)
        self.assertEqual(["a-open", "b-open", "c-open"],
                         [row["id"] for row in payload["queue"]])


if __name__ == "__main__":
    unittest.main()
