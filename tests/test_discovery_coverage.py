"""Tests for the discovery-coverage report.

The report exists because the bench drifted to 10 US sources and 1 Australian with 0 of 6 live
candidates non-US. A number that is computed wrongly is worse than no number: these cases pin the
count, the share, and the refusal to guess a missing jurisdiction from a URL.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "discovery-coverage.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


coverage = load(SCRIPT, "discovery_coverage")


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self._saved = coverage.CANDIDATES
        coverage.CANDIDATES = self.dir

    def tearDown(self):
        coverage.CANDIDATES = self._saved
        self._tmp.cleanup()

    def write(self, candidate_id, country, status="investigating", region="Europe"):
        path = self.dir / candidate_id
        path.mkdir()
        record = {"id": candidate_id, "status": status}
        if country:
            record["jurisdiction"] = {"country": country, "region": region, "publisher": "x"}
        (path / "record.json").write_text(json.dumps(record))

    def test_the_non_us_share_counts_live_candidates_only(self):
        self.write("de-one", "DE")
        self.write("fr-one", "FR", status="parked")
        self.write("us-one", "US")
        data = coverage.summarise()
        self.assertEqual(3, data["candidates"])
        self.assertEqual(2, data["live"])
        self.assertEqual(1, data["live_non_us"])
        self.assertEqual(0.5, data["live_non_us_share"])

    def test_a_missing_jurisdiction_is_reported_not_guessed(self):
        self.write("mystery", None)
        data = coverage.summarise()
        self.assertEqual(["mystery"], data["unknown_jurisdiction"])
        self.assertIn("UNKNOWN", data["by_country"])

    def test_the_command_fails_when_a_jurisdiction_is_unknown(self):
        self.write("mystery", None)
        self.assertEqual(1, coverage.main([]))

    def test_the_command_succeeds_when_every_record_states_one(self):
        self.write("de-one", "DE")
        self.assertEqual(0, coverage.main(["--json"]))


if __name__ == "__main__":
    unittest.main()
