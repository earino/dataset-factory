"""Static checks on the worker's Hugging Face helpers.

The helpers are source strings written to disk and run as separate processes on the worker, so a
missing import is not caught by importing this module - it is caught three minutes into a paid
job. That is exactly what happened: the verify helper used `os.environ` without importing `os`,
and the job failed after the (correct) upload had already been verified.

So the imports of every helper are checked here, against the modules the body actually uses.
"""
import ast
import re
import unittest
from pathlib import Path

HELPER_SOURCE = Path(__file__).resolve().parents[1] / "workers" / "hf_publish.py"
STDLIB_LOOKALIKES = ("os", "sys", "json", "hashlib", "subprocess", "pathlib", "urllib")


def helpers():
    text = HELPER_SOURCE.read_text()
    pattern = re.compile(r"^([A-Z_]*HELPER) = '''(.*?)'''", re.S | re.M)
    return pattern.findall(text)


class HelperImportTests(unittest.TestCase):
    def test_at_least_the_upload_and_verify_helpers_are_checked(self):
        names = [name for name, _ in helpers()]
        self.assertIn("UPLOAD_HELPER", names)
        self.assertIn("VERIFY_HELPER", names)

    def test_every_helper_parses(self):
        for name, body in helpers():
            with self.subTest(helper=name):
                ast.parse(body)

    def test_every_helper_imports_every_module_it_uses(self):
        for name, body in helpers():
            with self.subTest(helper=name):
                imported = set(re.findall(r"^import (\w+)", body, re.M))
                imported |= {match.split()[0] for match in
                             re.findall(r"^from (\w+) import", body, re.M)}
                used = {module for module in STDLIB_LOOKALIKES if f"{module}." in body}
                self.assertEqual(set(), used - imported,
                                 f"{name} uses {sorted(used - imported)} without importing it")

    def test_the_verify_helper_passes_the_credential_explicitly(self):
        """A private dataset cannot be read without it, and HF_TOKEN is absent from that child."""
        body = dict(helpers())["VERIFY_HELPER"]
        self.assertIn("token=os.environ", body)

    def test_the_helpers_never_take_a_credential_as_an_argument(self):
        for name, body in helpers():
            with self.subTest(helper=name):
                self.assertNotIn("sys.argv[5]", body)
                self.assertNotIn("--token", body)


if __name__ == "__main__":
    unittest.main()
