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



class DescriptorTests(unittest.TestCase):
    """The generator is data-driven: adding a dataset needs a descriptor, not a new generator."""

    def test_a_dataset_without_a_descriptor_is_refused_not_guessed(self):
        with self.assertRaises(SystemExit) as caught:
            release_manifest.descriptor("no-such-dataset")
        self.assertIn("release.json is missing", str(caught.exception))

    def test_a_descriptor_missing_a_required_key_is_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "candidates" / "thing").mkdir(parents=True)
            (root / "candidates" / "thing" / "release.json").write_text(
                json.dumps({"release_version": "2026.09"}))
            original = release_manifest.ROOT
            release_manifest.ROOT = root
            try:
                with self.assertRaises(SystemExit) as caught:
                    release_manifest.descriptor("thing")
            finally:
                release_manifest.ROOT = original
        self.assertIn("release_tag", str(caught.exception))

    def test_combined_version_is_order_independent(self):
        a = {"temporal": {"artifact_version": "aa"}, "station_disjoint": {"artifact_version": "bb"}}
        b = {"station_disjoint": {"artifact_version": "bb"}, "temporal": {"artifact_version": "aa"}}
        self.assertEqual(release_manifest.combined_artifact_version(a),
                         release_manifest.combined_artifact_version(b))
        self.assertNotEqual(release_manifest.combined_artifact_version(a),
                            release_manifest.combined_artifact_version(
                                {"temporal": {"artifact_version": "bb"},
                                 "station_disjoint": {"artifact_version": "aa"}}))


class PublishedPackageInvariants(unittest.TestCase):
    """Invariants over the real package, because these are the defects a reviewer would hit."""

    def setUp(self):
        self.release = ROOT / "release" / "noaa-tide-flooding"
        self.manifest = json.loads((self.release / "MANIFEST.json").read_text())

    def test_no_release_asset_name_contains_a_slash(self):
        """GitHub rejects `/` in asset names; the download helper restores the layout instead."""
        for relative, info in self.manifest["assets"].items():
            self.assertNotIn("/", info["asset_name"], relative)

    def test_every_asset_appears_in_the_layout_the_helper_restores(self):
        self.assertEqual(set(self.manifest["assets"]), set(self.manifest["layout"].values()))

    def test_each_level_carries_its_own_gate_version(self):
        levels = self.manifest["levels"]
        self.assertEqual(["station_disjoint", "temporal"], sorted(levels))
        for name, data in levels.items():
            self.assertEqual("1.3.0", data["gate_version"], name)
            self.assertEqual(32, data["checks"], name)
            self.assertRegex(data["artifact_version"], r"^[0-9a-f]{64}$")

    def test_the_derived_version_is_labelled_as_derived(self):
        """A reader must not mistake the combined label for a gate output."""
        self.assertIn("derived", self.manifest["artifact_version_note"])
        self.assertEqual(64, len(self.manifest["artifact_version"]))

    def test_the_card_claims_publication_only_when_the_package_is_published(self):
        """The README's status line is a claim about the package, so it has to match the record.

        This test asserted the opposite until 2026-09-26 - that the card said "Status: private" -
        which was true while the package was unpublished. Once it went public that assertion
        obstructed the truth it was written to protect. It now reads the state from the manifest and
        checks the claim against it in both directions, so it still fails a card that overstates
        (claims public while unpublished) and one that understates.
        """
        card = (self.release / "README.md").read_text()
        if self.manifest["published"]:
            self.assertEqual("public", self.manifest["visibility"])
            self.assertIn("Status: public", card)
            self.assertNotIn("Status: private", card)
        else:
            self.assertNotEqual("public", self.manifest["visibility"])
            self.assertIn("Status: private", card)



if __name__ == "__main__":
    unittest.main()
