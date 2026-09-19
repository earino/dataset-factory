"""The manifest must describe the release that exists, not a fixed claim about it.

`visibility`, `published` and `publication_note` were literals, so the documented post-publication
regeneration re-asserted "private" after the release had gone public. They are now derived from
`DESTINATIONS.json`, which records what was actually checked per destination.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("release_manifest", ROOT / "scripts/release-manifest.py")
release_manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_manifest)


def destinations(private, verified):
    return {"release_tag": "v2026.09",
            "destinations": {"github": {"private": private, "verified": verified,
                                        "verified_at": "2026-09-19T00:00:00+00:00"},
                             "huggingface": {"private": private, "verified": verified,
                                             "verified_at": "2026-09-19T00:00:00+00:00"}}}


class PublicationStateTests(unittest.TestCase):
    def state(self, payload):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "DESTINATIONS.json"
            if payload is not None:
                path.write_text(json.dumps(payload))
            return release_manifest.publication_state(Path(folder))

    def test_public_destinations_report_published(self):
        published, visibility, note = self.state(destinations(private=False, verified=True))
        self.assertTrue(published)
        self.assertEqual("public", visibility)
        self.assertIn("operator authorisation", note)

    def test_private_destinations_stay_private(self):
        published, visibility, note = self.state(destinations(private=True, verified=True))
        self.assertFalse(published)
        self.assertIn("private", visibility)
        self.assertIn("Nothing here has been published", note)

    def test_an_unverified_destination_is_not_reported_as_published(self):
        published, visibility, _ = self.state(destinations(private=False, verified=False))
        self.assertFalse(published)
        self.assertIn("private", visibility)

    def test_no_recorded_destinations_stays_private(self):
        published, visibility, _ = self.state(None)
        self.assertFalse(published)
        self.assertIn("private", visibility)


if __name__ == "__main__":
    unittest.main()
