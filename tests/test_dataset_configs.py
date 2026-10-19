"""A per-target manifest keeps one flat split map; the config rule must still find its configs.

`config_names()`/`config_splits()` read the `splits` map, which for a per-target dataset is the
shared pool (split -> {rows, ...}), not split -> protocol. Running that rule on the MSHA release
reported "no configs", and the page and Hub card would then have documented a load command that
named no config - or, worse, the wrong splits. These tests pin the corrected rule against the real
packaged manifest and pin the old rule's failure so the bug cannot return silently.
"""

import json
import unittest
from pathlib import Path

from factory import site_model

ROOT = Path(__file__).resolve().parents[1]
MSHA = ROOT / "release" / "msha-enforcement-citations" / "MANIFEST.json"


class PerTargetConfigsTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MSHA.read_text())

    def test_every_section_is_a_config(self):
        self.assertEqual(site_model.dataset_config_names(self.manifest),
                         sorted(self.manifest["levels"]))
        self.assertEqual(len(site_model.dataset_config_names(self.manifest)), 45)

    def test_every_config_carries_the_three_shared_splits(self):
        splits = site_model.dataset_config_splits(self.manifest)
        self.assertEqual(set(splits), set(self.manifest["levels"]))
        for config, names in splits.items():
            self.assertEqual(names, ["eval", "holdout", "train"], config)
            rows = {name: self.manifest["splits"][name]["rows"] for name in names}
            self.assertEqual(rows, {"eval": 49233, "holdout": 33576, "train": 415088}, config)

    def test_the_old_split_map_rule_cannot_see_them(self):
        # The guard: on the pre-fix input the split-map-only rule yields no configs at all, so a
        # regression to it fails above rather than shipping a page that documents nothing.
        self.assertEqual(site_model.config_names(self.manifest.get("splits") or {}), [],
                         "the pre-fix rule reports no configs, which is the bug being pinned")

    def test_nested_protocol_manifests_still_resolve_per_protocol(self):
        noaa = json.loads((ROOT / "release" / "noaa-tide-flooding" / "MANIFEST.json").read_text())
        self.assertEqual(site_model.dataset_config_names(noaa), sorted(noaa["splits"]))
        splits = site_model.dataset_config_splits(noaa)
        self.assertEqual(splits["temporal"], ["eval", "holdout", "train"])


if __name__ == "__main__":
    unittest.main()
