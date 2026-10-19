"""Guards for the Hub schema declaration (`dataset_infos.json`).

The documented load command is `load_dataset(repo, "<config>")`. Without a declared schema the
loader infers each CSV column's type from a sample, and `event_no` - mostly digits, but `F015FC6`
in 19,502 rows - was inferred as int64 and then failed to cast, so the *holdout* split raised
ArrowInvalid and the documented path did not reproduce the artifact.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "release" / "msha-enforcement-citations"
INFOS = PACKAGE / "dataset_infos.json"
IDENTIFIERS = ("event_no", "mine_id", "fips_cnty_cd", "inspection_date", "activity_code")


class DatasetInfosTests(unittest.TestCase):
    def test_every_config_declares_its_columns(self):
        infos = json.loads(INFOS.read_text())
        manifest = json.loads((PACKAGE / "MANIFEST.json").read_text())
        self.assertEqual(sorted(infos), sorted(manifest["levels"]))
        for name, info in infos.items():
            self.assertEqual(info["config_name"], name)
            self.assertIn(name, info["features"], "the label column is missing from the schema")
            self.assertEqual(sorted(info["splits"]), ["eval", "holdout", "train"])

    def test_identifiers_are_declared_as_strings(self):
        infos = json.loads(INFOS.read_text())
        for name, info in infos.items():
            for column in IDENTIFIERS:
                self.assertEqual(info["features"][column]["dtype"], "string",
                                 f"{name}: {column} must not be coerced to a number")

    def test_label_and_continuous_columns_have_their_declared_types(self):
        infos = json.loads(INFOS.read_text())
        for name, info in infos.items():
            self.assertEqual(info["features"][name]["dtype"], "int64")
            self.assertEqual(info["features"]["prior_mean_citations"]["dtype"], "float64")

    def test_the_schema_travels_to_the_hub(self):
        source = (ROOT / "scripts" / "hf-publish.py").read_text()
        match = re.search(r"^SMALL_FILES = \{(.*?)^\}", source, re.S | re.M)
        self.assertIsNotNone(match)
        self.assertIn('"dataset_infos.json"', match.group(1),
                      "the schema file must be uploaded with the card and docs")

    def test_the_generator_treats_identifiers_as_strings(self):
        source = (ROOT / "scripts" / "hf-dataset-infos.py").read_text()
        block = re.search(r"^STRING_COLUMNS = \{(.*?)^\}", source, re.S | re.M)
        self.assertIsNotNone(block)
        for column in IDENTIFIERS:
            self.assertIn(f'"{column}"', block.group(1),
                          f"{column} is an identifier and must be declared as a string")


if __name__ == "__main__":
    unittest.main()
