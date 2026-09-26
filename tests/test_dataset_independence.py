"""The release machinery must not know any dataset's name or shape.

Every defect in the NOAA release was one class: a code path written for the first dataset that
silently assumed it was the only one - a flat split set, a flat Hub layout, Austin's clock-offset
script in the required-document list, a bundle table with per-dataset paths, a card fallback that
would have shipped one dataset described by another. These tests drive a *synthetic* dataset of a
deliberately different shape through the same code, so the class fails here instead of mid-release.
"""

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factory import site_model  # noqa: E402

CONFIG = {"schema_version": 1, "catalog_repository": "owner/catalog", "catalog_title": "Catalogue",
          "catalog_description": "d", "hosting": "github-project-pages"}
DOCS = ("README.md", "DATA_DICTIONARY.md", "LICENSE.md", "REPRODUCE.md", "RELEASE_NOTES.md",
        "VERIFICATION.md", "measurements.json", "get_dataset.py")


def synthetic_package(root: Path, levels=("alpha", "beta", "gamma"), hub_paths=False):
    """A package whose shape neither published dataset has: three levels, an extra split.

    Every document the projection requires is written exactly once and hashed afterwards, because it
    compares those hashes against the manifest - writing a file after hashing it is how a fixture
    fails for a reason that has nothing to do with the code under test.
    """
    package = root / "release" / "synthetic"
    package.mkdir(parents=True)
    for name in DOCS:
        body = "#!/usr/bin/env python3\n" if name.endswith(".py") else (
            "{}\n" if name.endswith(".json") else f"# {name}\n\nSynthetic.\n")
        (package / name).write_text(body)
    package_files = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in DOCS}

    if levels:
        splits = {name: {"train": {"rows": 30, "positives": 3}, "eval": {"rows": 20, "positives": 2},
                         "holdout": {"rows": 10, "positives": 1}, "extra": {"rows": 5, "positives": 0}}
                  for name in levels}
    else:
        splits = {"train": {"rows": 30, "positives": 3}, "eval": {"rows": 20, "positives": 2},
                  "holdout": {"rows": 10, "positives": 1}}
    files = {"alpha/public/train.csv": {"bytes": 10, "sha256": "a" * 64},
             "alpha/meta.json": {"bytes": 5, "sha256": "b" * 64}}
    assets = {relative: {"asset_name": relative.replace("/", "-"), **info}
              for relative, info in files.items()}
    layout = {f"task/{relative}": relative for relative in files}
    manifest = {
        "dataset": "synthetic", "release_tag": "v2099.01", "artifact_version": "c" * 64,
        "repository": "https://github.com/owner/synthetic", "splits": splits, "files": files,
        "assets": assets, "layout": layout, "package_files": package_files,
        "source": {"name": "s", "landing_page": "https://example.org"},
        "licenses": {"code": {"spdx": "MIT"},
                     "data_compilation": {"spdx": "CC0-1.0", "scope": "ours"},
                     "source_data": {"spdx": "LicenseRef-Public-Domain", "attribution": "a",
                                     "citation": "c"}},
        "qualification": {"gate_version": "1.3.0", "result": "PASSED - 32 checks",
                          "artifact_version": "c" * 64},
        "baseline": {},
    }
    if hub_paths:
        # A dataset that keeps its own layout on the Hub, as the level-structured one does.
        manifest["hub_paths"] = {relative: relative for relative in files}
    (package / "MANIFEST.json").write_text(json.dumps(manifest))

    if hub_paths:
        hub_files = sorted(manifest["hub_paths"].values())
    else:
        hub_files = sorted(f"data/{info['asset_name']}" if name.endswith(".csv")
                           else info["asset_name"] for name, info in assets.items())
    (package / "DESTINATIONS.json").write_text(json.dumps({
        "release_tag": "v2099.01", "artifact_version": "c" * 64,
        "destinations": {
            "github": {"repo": "owner/synthetic", "release_tag": "v2099.01", "verified": True,
                       "private": False, "files_verified": sorted(assets)},
            "huggingface": {"repo": "owner/synthetic", "revision": "v2099.01", "verified": True,
                            "private": False, "files_verified": hub_files}}}, indent=2))
    return package, manifest


def editorial():
    return {"schema_version": 1, "site_revision": 1, "title": "t", "summary": "s",
            "task_type": "binary-classification", "domain": "d", "release_date": "2099-01-01",
            "post": {"title": "p", "paragraphs": ["one"]}, "limitations": ["l"]}


class SyntheticDatasetTest(unittest.TestCase):
    def test_the_projection_handles_levels_it_has_never_seen(self):
        with tempfile.TemporaryDirectory() as folder:
            package, _ = synthetic_package(Path(folder))
            record = site_model.project(package, editorial(), CONFIG)
            self.assertEqual(12, len(record["splits"]), "every split of every level must be shown")
            self.assertIn("alpha-extra", record["splits"])

    def test_the_publish_check_agrees_with_the_record_by_construction(self):
        with tempfile.TemporaryDirectory() as folder:
            package, manifest = synthetic_package(Path(folder))
            record = site_model.project(package, editorial(), CONFIG)
            site_model.check_manifest(record, manifest)  # must not raise

    def test_a_flat_single_level_dataset_still_works(self):
        with tempfile.TemporaryDirectory() as folder:
            package, manifest = synthetic_package(Path(folder), levels=())
            record = site_model.project(package, editorial(), CONFIG)
            site_model.check_manifest(record, manifest)
            self.assertEqual(3, len(record["splits"]))

    def test_a_declared_hub_layout_is_honoured(self):
        with tempfile.TemporaryDirectory() as folder:
            package, manifest = synthetic_package(Path(folder), hub_paths=True)
            record = site_model.project(package, editorial(), CONFIG)
            site_model.check_manifest(record, manifest)
            self.assertEqual("alpha/public/train.csv", record["assets"]["alpha-public-train.csv"]["hf_path"])


class BundleDiscoveryTest(unittest.TestCase):
    def _module(self):
        spec = importlib.util.spec_from_file_location("assemble_job", ROOT / "scripts/assemble-job.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_bundles_are_discovered_not_tabulated(self):
        found = self._module().discover_bundles(ROOT)
        self.assertTrue(found)
        for name, entry in found.items():
            self.assertTrue((ROOT / entry["job_file"]).is_file(), name)

    def test_a_declaration_without_a_job_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            declared = root / "candidates" / "x" / "source"
            declared.mkdir(parents=True)
            (declared / "bundle.json").write_text(json.dumps({"name": "x"}))
            with self.assertRaises(SystemExit):
                self._module().discover_bundles(root)


if __name__ == "__main__":
    unittest.main()
