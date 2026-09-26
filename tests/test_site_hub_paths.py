"""The website's Hub link check must use the paths the dataset actually has.

The site model computed Hub paths itself (`data/<asset>.csv`), which holds only for a flat,
single-level release. For a level-structured dataset the check could never pass, and satisfying it
by writing names that do not exist on the Hub would have produced a page linking to 404s.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "release" / "noaa-tide-flooding"


class DeclaredHubPathsTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((PACKAGE / "MANIFEST.json").read_text())
        self.destinations = json.loads((PACKAGE / "DESTINATIONS.json").read_text())

    def test_a_level_structured_dataset_declares_its_hub_paths(self):
        self.assertTrue(self.manifest.get("hub_paths"), "the manifest must declare the Hub paths")
        self.assertEqual(set(self.manifest["assets"]), set(self.manifest["hub_paths"]))

    def test_every_declared_path_is_the_one_verified_on_the_hub(self):
        verified = self.destinations["destinations"]["huggingface"]["files_verified"]
        for logical, path in self.manifest["hub_paths"].items():
            self.assertIn(path, verified, logical)
        for path in self.manifest["hub_paths"].values():
            self.assertFalse(path.startswith("data/"), "the flat rule is not this dataset's layout")

    def test_the_flat_rule_is_still_the_default_for_a_single_level_release(self):
        austin = json.loads((ROOT / "release" / "austin-911-response" / "MANIFEST.json").read_text())
        self.assertNotIn("hub_paths", austin, "a single-level release must be unchanged")


if __name__ == "__main__":
    unittest.main()
