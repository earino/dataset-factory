"""The dataset card must describe the release that exists.

Two defects shipped in the published card and both are checked here:

* the card asserted "private. Public visibility requires explicit human approval" as a literal, so
  it stayed wrong after the operator approved publication;
* the repository id was written as `{{repo_id}}`, which an f-string renders to `{repo_id}`, so the
  replacement never matched and the literal placeholder shipped - the documented loading command
  was not runnable as printed.

The card is built inside a module that needs `huggingface_hub`, so these are source checks rather
than an import of the builder.
"""

import unittest
from pathlib import Path

PUBLISH_SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "hf-publish.py"


class CardTests(unittest.TestCase):
    def setUp(self):
        self.source = PUBLISH_SOURCE.read_text()

    def test_the_repository_id_placeholder_survives_the_f_string(self):
        self.assertNotIn("{{repo_id}}", self.source,
                         "an f-string renders this to '{repo_id}', which the replacement cannot match")
        self.assertIn('REPO_PLACEHOLDER = "__REPO_ID__"', self.source)
        self.assertIn("REPO_PLACEHOLDER, repo_id", self.source)

    def test_the_status_line_follows_the_recorded_publication_state(self):
        self.assertIn('manifest_data.get("published")', self.source)
        self.assertNotIn("**Status: private. Public visibility requires explicit human approval.**",
                         self.source)

    def test_the_loading_note_follows_the_recorded_publication_state(self):
        self.assertIn("loading_note", self.source)
        self.assertNotIn("For a private repository, pass a token that has access to it (the "
                         "inference credential does not):", self.source.split("def card(")[1].split("def ")[0])

    def test_the_public_loading_example_does_not_demand_a_token(self):
        self.assertIn("{', token=True' if not published else ''}", self.source)


if __name__ == "__main__":
    unittest.main()
