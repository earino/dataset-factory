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


class ChicagoHubSchemaTests(unittest.TestCase):
    """Regression guards for the food release: food-hf-001 uploaded all 201 assets, then the
    loading check died casting 'Canvass' to int64 because `inspection_type` was missing from
    hub-schema.json and silently defaulted to int64."""

    ROOT = Path(__file__).resolve().parent.parent
    PACKAGE = ROOT / "release" / "chicago-food-inspections"
    SCHEMA = ROOT / "candidates" / "chicago-food-inspections" / "hub-schema.json"

    def test_inspection_type_is_declared_as_a_string(self):
        infos = json.loads((self.PACKAGE / "dataset_infos.json").read_text())
        schema = json.loads(self.SCHEMA.read_text())
        self.assertIn("inspection_type", schema["string"],
                      "inspection_type holds values like 'Canvass' and must be declared string")
        for name, info in infos.items():
            self.assertEqual(info["features"]["inspection_type"]["dtype"], "string",
                             f"{name}: inspection_type must not be coerced to a number")

    def test_every_feature_column_is_declared_exactly_once(self):
        infos = json.loads((self.PACKAGE / "dataset_infos.json").read_text())
        schema = json.loads(self.SCHEMA.read_text())
        sets = {dtype: set(schema[dtype]) for dtype in ("string", "float64", "int64")}
        self.assertFalse(set(sets["string"]) & (set(sets["float64"]) | set(sets["int64"])),
                         "a column declared under two dtypes is ambiguous")
        for name, info in infos.items():
            for column, spec in info["features"].items():
                if column == name:  # the label column defaults to int64
                    self.assertEqual(spec["dtype"], "int64")
                    continue
                self.assertIn(column, sets[spec["dtype"]],
                               f"{name}: '{column}' is typed {spec['dtype']} in the schema "
                               "file but is not declared there")

    def test_generator_rejects_undeclared_feature_columns(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hf_dataset_infos", self.ROOT / "scripts" / "hf-dataset-infos.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        types = {"string": ["a"], "float64": [], "int64": ["b"]}
        self.assertEqual(module.dtype_for("a", "label", types), "string")
        self.assertEqual(module.dtype_for("b", "label", types), "int64")
        with self.assertRaises(SystemExit) as caught:
            module.dtype_for("c", "label", types)
        self.assertIn("undeclared", str(caught.exception))
        # the label column keeps its int64 default
        self.assertEqual(module.dtype_for("label", "label", types), "int64")
        # a column under two sets is refused outright
        with self.assertRaises(SystemExit):
            module.dtype_for("a", "label", {**types, "float64": ["a"]})


if __name__ == "__main__":
    unittest.main()
