"""A live website must be recorded as a destination, or the dashboard denies it exists.

Nine datasets had live pages and only two showed the pill: `DESTINATIONS.json` is what the dashboard
reads, and the publisher wrote only a receipt. These tests pin the recording step.
"""
import json
import tempfile
import unittest
from pathlib import Path

from factory import site_pipeline


class RecordSiteDestinationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="site-dest-"))
        (self.root / "release" / "fixture").mkdir(parents=True)
        (self.root / "release" / "fixture" / "DESTINATIONS.json").write_text(
            json.dumps({"destinations": {"github": {"verified": True}}}))
        self.original = site_pipeline.ROOT
        site_pipeline.ROOT = self.root

    def tearDown(self):
        site_pipeline.ROOT = self.original

    def _record(self, stamp="2026-10-22T00:00:00+00:00"):
        site_pipeline.record_site_destination(
            {"dataset": "fixture", "urls": {"version": "https://example.org/fixture/"}}, stamp)
        return json.loads((self.root / "release" / "fixture" / "DESTINATIONS.json").read_text())

    def test_the_site_is_added_without_disturbing_the_others(self):
        body = self._record()
        self.assertEqual({"github", "site"}, set(body["destinations"]))
        self.assertTrue(body["destinations"]["site"]["verified"])
        self.assertEqual("https://example.org/fixture/", body["destinations"]["site"]["url"])

    def test_recording_twice_keeps_one_entry(self):
        self._record()
        body = self._record("2026-10-22T01:00:00+00:00")
        self.assertEqual(1, len([k for k in body["destinations"] if k == "site"]))
        self.assertEqual("2026-10-22T01:00:00+00:00", body["destinations"]["site"]["verified_at"])

    def test_a_missing_destinations_file_is_not_created(self):
        site_pipeline.record_site_destination(
            {"dataset": "absent", "urls": {"version": "https://example.org/x/"}}, "2026-10-22T00:00:00+00:00")
        self.assertFalse((self.root / "release" / "absent" / "DESTINATIONS.json").exists())


if __name__ == "__main__":
    unittest.main()
