"""The dataset card must describe the release that exists.

Three defects shipped in a published card and all of them are checked here:

* the card asserted "private. Public visibility requires explicit human approval" as a literal, so
  it stayed wrong after the operator approved publication;
* the repository id was written as `{{repo_id}}`, which an f-string renders to `{repo_id}`, so the
  replacement never matched and the literal placeholder shipped - the documented loading command
  was not runnable as printed;
* the card's `configs:` block and its loading example are hand-written in the template, so nothing
  tied them to the manifest. The published Chicago card's load returned splits `train`/`test` and
  reported `eval` and `holdout` missing, because no configs block declared them; the worker's own
  loading check caught it only after publication, and no test would have. Every declared split must
  now exist in the manifest, every manifest split must be declared, and any numeric row count in the
  loading example must equal the manifest's.

The card is built inside a module that needs `huggingface_hub`, so these are source checks rather
than an import of the builder.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH_SOURCE = ROOT / "scripts" / "hf-publish.py"


def declared_configs(card_text):
    """Every (config_name, split, path) triple the card's frontmatter `configs:` block declares.

    Deliberately a small parser rather than a YAML import: the block is three keys deep and the test
    should fail loudly on a card that is malformed rather than silently see no configs.
    """
    frontmatter = card_text.split("---", 2)[1] if card_text.startswith("---") else ""
    triples, config, in_data_files = [], None, False
    split = None
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:]          # list items: "- config_name: default"
        if stripped.startswith("config_name:"):
            config = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("data_files:"):
            in_data_files = True
            continue
        elif in_data_files and stripped.startswith("split:"):
            split = stripped.split(":", 1)[1].strip()
        elif in_data_files and stripped.startswith("path:"):
            path = stripped.split(":", 1)[1].strip()
            if split is not None:
                triples.append((config, split, path))
            split = None
    return triples


def expected_configs(manifest):
    """The card's configs, expressed from the manifest alone.

    A single-split-protocol dataset keeps a flat `splits` map and one card config named `default`;
    a dataset with more than one protocol (NOAA's temporal and station-disjoint) nests the splits
    under the protocol name and the card carries one config per protocol. Both shapes are real, so
    the expectation is derived rather than assumed.
    """
    splits = manifest.get("splits") or {}
    nested = bool(splits) and all(isinstance(v, dict) and "rows" not in v for v in splits.values())
    if nested:
        return {protocol: {split: body.get("rows") for split, body in group.items()}
                for protocol, group in splits.items()}
    return {"default": {split: body.get("rows") for split, body in splits.items()}}


def declared_row_counts(card_text):
    """Numeric split row counts in the loading example; `...` placeholders are skipped."""
    counts = {}
    for match in re.finditer(r"#\s+(\w+): Dataset\(\{features: \[\.\.\.\], num_rows: ([0-9]+)\}\)",
                             card_text):
        counts[match.group(1)] = int(match.group(2))
    return counts


def superseded_values(node):
    """Every figure and artifact digest the manifest records as superseded.

    A card and a README are prose, and prose is where a retired value survives: the NOAA card kept
    quoting the superseded artifact's AUC pair, and the package README went on advertising the
    superseded artifact's own version digest (`8896c442…`) as the artifact the release carried. Each
    was retired by a `superseded` block or a `previous_measurement` entry in the manifest, so both
    kinds of value are harvested from the record rather than from a list maintained by hand.

    Digests are harvested as their 16-hex-character prefixes, which is how documents quote them.
    """
    numbers, digests = set(), set()

    def harvest(value):
        if isinstance(value, dict):
            for item in value.values():
                harvest(item)
        elif isinstance(value, list):
            for item in value:
                harvest(item)
        elif isinstance(value, bool):
            return
        elif isinstance(value, (int, float)):
            numbers.add(round(float(value), 4))
        elif isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32,64}", value):
            digests.add(value[:16])

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, (dict, list)) and ("superseded" in str(key).lower()
                                                       or "previous_measurement" in str(key).lower()):
                    harvest(item)
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(node)
    return numbers, digests


class CardTests(unittest.TestCase):
    def setUp(self):
        self.source = PUBLISH_SOURCE.read_text()

    def test_the_repository_id_placeholder_survives_the_f_string(self):
        self.assertNotIn("{{repo_id}}", self.source,
                         "an f-string renders this to '{repo_id}', which the replacement cannot match")
        self.assertIn('REPO_PLACEHOLDER = "__REPO_ID__"', self.source)
        self.assertIn("REPO_PLACEHOLDER, repo_id", self.source)

    def _renderer(self):
        """The card is generated by a dataset-agnostic renderer now, so it can be exercised directly.

        These were source-text checks because the card was an f-string inside a module that needed
        huggingface_hub. The renderer takes a template and a manifest and touches nothing else, so the
        behaviour is asserted on its output instead - which is what actually matters and what the
        source checks could not see.
        """
        import importlib.util
        import sys
        sys.path.insert(0, str(ROOT))
        spec = importlib.util.spec_from_file_location("hf_publish_module", PUBLISH_SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_a_public_release_loads_without_a_token(self):
        module = self._renderer()
        template = "status: {STATUS_LINE}\n{LOADING_NOTE}\nload_dataset('x'{TOKEN_ARG})\n"
        public = module.render_card_template(template, {"published": True, "release_tag": "v1",
                                                        "artifact_version": "a" * 64, "splits": {}})
        private = module.render_card_template(template, {"published": False, "release_tag": "v1",
                                                         "artifact_version": "a" * 64, "splits": {}})
        self.assertIn("no credential", public)
        self.assertNotIn("token=True", public)
        self.assertIn("token=True", private)
        self.assertIn("requires explicit human approval", private)

    def test_an_unresolved_placeholder_is_refused(self):
        module = self._renderer()
        with self.assertRaises(SystemExit):
            module.render_card_template("value: {NOT_A_KNOWN_FIELD}", {"published": False})

    def _candidates(self):
        for manifest_path in sorted((ROOT / "release").glob("*/MANIFEST.json")):
            candidate = manifest_path.parent.name
            card_path = ROOT / "candidates" / candidate / "card.md"
            if card_path.is_file():
                yield candidate, json.loads(manifest_path.read_text()), card_path.read_text()

    def test_every_declared_split_exists_in_the_manifest(self):
        seen = 0
        for candidate, manifest, card_text in self._candidates():
            expected = expected_configs(manifest)
            triples = declared_configs(card_text)
            self.assertTrue(triples, f"{candidate}: card declares no configs, so load_dataset would "
                                     f"not produce the manifest's splits")
            by_config = {}
            for config, split, path in triples:
                by_config.setdefault(config, {})[split] = path
            self.assertEqual(set(by_config), set(expected),
                             f"{candidate}: card configs {sorted(by_config)} do not match the "
                             f"manifest's {sorted(expected)}")
            for config, declared in sorted(by_config.items()):
                self.assertEqual(set(declared), set(expected[config]),
                                 f"{candidate}/{config}: card declares {sorted(declared)}, manifest "
                                 f"has {sorted(expected[config])}")
                for split, path in sorted(declared.items()):
                    self.assertEqual(Path(path).name, f"{split}.csv",
                                     f"{candidate}/{config}: split {split} points at {path}")
            seen += 1
        self.assertEqual(seen, 3, "expected a card for every released candidate")

    def test_any_row_count_in_the_loading_example_matches_the_manifest(self):
        for candidate, manifest, card_text in self._candidates():
            expected = expected_configs(manifest)
            # The loading example is one block, so it can only be checked when the card has a single
            # config; a multi-protocol card shows placeholders instead.
            if list(expected) != ["default"]:
                continue
            rows_by_split = expected["default"]
            for split, rows in declared_row_counts(card_text).items():
                with self.subTest(candidate=candidate, split=split):
                    self.assertIn(split, rows_by_split,
                                  f"{candidate}: the loading example shows a split the manifest lacks")
                    self.assertEqual(rows, rows_by_split[split],
                                     f"{candidate}: the loading example promises {rows} rows for "
                                     f"{split}, the manifest has {rows_by_split[split]}")

    def test_the_documented_commands_are_the_ones_that_run(self):
        """The card and LOADING.md must print a command an anonymous reader can actually run.

        Two published defects lived in the rendered text, not in the template source: the NOAA card
        named the bare candidate ("noaa-tide-flooding"), which raises DatasetNotFoundError for a
        reader without a token, and its summary line read "Rows: 0 across two levels" because the
        row total was summed over a nested split map as if it were flat. The third is the config: a
        repository with two configs refuses load_dataset unless one is named. So this asserts on the
        generated output, which is what a reader copies.
        """
        module = self._renderer()
        seen = 0
        for candidate, manifest, _card_text in self._candidates():
            # card() reads the candidate from a module global the CLI sets; the test drives it.
            module.CANDIDATE = candidate
            repo_id = str(manifest["repository"]).removeprefix("https://github.com/")
            rendered = module.card(manifest).replace(module.REPO_PLACEHOLDER, repo_id)
            loading = module.loading_text(manifest, repo_id)
            expected = expected_configs(manifest)
            with self.subTest(candidate=candidate):
                self.assertNotIn("__REPO_ID__", rendered, f"{candidate}: card holds the build token")
                self.assertNotIn("__REPO_ID__", loading, f"{candidate}: LOADING.md holds the token")
                self.assertIn("/", repo_id, f"{candidate}: the repository id has no owner")
                shown = re.findall(r'load_dataset\(\s*"([^"]+)"', rendered + loading)
                self.assertTrue(shown, f"{candidate}: no loading command is documented")
                for name in shown:
                    self.assertEqual(name, repo_id,
                                     f"{candidate}: the documented command names {name!r}, which is "
                                     f"not the repository id {repo_id!r}")
                if len(expected) > 1:
                    for config in sorted(expected):
                        self.assertIn(f'"{config}"', loading,
                                      f"{candidate}: LOADING.md does not name config {config!r}, so "
                                      f"its command raises 'Config name is missing'")
                else:
                    self.assertIn(f'ds = load_dataset("{repo_id}"',
                                  loading.replace("|", "").replace("\n", " ").replace("  ", " "),
                                  f"{candidate}: a single-config repository needs no config argument")
                total = sum(rows for splits in expected.values() for rows in splits.values())
                if manifest.get("published"):
                    # Austin's template still carried the private-era sentence while its manifest
                    # said published: a rebuild would have shipped a card denying its own release.
                    self.assertIn("**Status: public", rendered,
                                  f"{candidate}: the manifest says published, the card does not")
                    self.assertNotIn("Status: private", rendered,
                                     f"{candidate}: the card claims a private release")
                match = re.search(r"\*\*Rows:\*\* ([\d,]+)", rendered)
                if match is None:
                    self.fail(f"{candidate}: the card states no row total")
                self.assertEqual(int(match.group(1).replace(",", "")), total,
                                 f"{candidate}: the card states {match.group(1)} rows; the manifest's "
                                 f"splits hold {total:,}")
            seen += 1
        self.assertEqual(seen, 3, "expected a card for every released candidate")

    RETIREMENT_MARKERS = ("superseded", "supersedes", "earlier", "previous", "retired", "no longer")

    def _documents(self, candidate, manifest, card_text):
        """Everything a reader is handed: the generated card and the package's own prose.

        The card is what the Hub shows; the package markdown is what the GitHub tree and the website
        publish. A retired figure that survives in either is the same defect, and the README shipped
        the superseded artifact digest for longer than the card did.
        """
        yield f"candidates/{candidate}/card.md", card_text
        release = ROOT / "release" / candidate
        for path in sorted(release.rglob("*.md")):
            if "eval_cache" in path.parts:
                continue
            yield str(path.relative_to(ROOT)), path.read_text()

    def test_no_document_states_a_superseded_figure_or_artifact(self):
        """A retired value may be named as history, never stated as the current one.

        The distinction matters because both uses look identical to a grep: the NOAA card quoted the
        superseded artifact's pair in its results table (a reader takes that as the released result)
        and, after the fix, names the same pair in a sentence saying it was the earlier pass. Only
        the first is a defect, so a retirement marker has to be near the value.
        """
        checked = 0
        for candidate, manifest, card_text in self._candidates():
            retired_numbers, retired_digests = superseded_values(manifest)
            if not retired_numbers and not retired_digests:
                continue
            for name, document in self._documents(candidate, manifest, card_text):
                lines = document.splitlines()
                unmarked = []
                for index, line in enumerate(lines):
                    quoted = {round(float(token), 4) for token in re.findall(r"\b0\.\d{3,4}\b", line)}
                    quoted &= retired_numbers
                    quoted.update(digest for digest in retired_digests if digest in line)
                    if not quoted:
                        continue
                    window = " ".join(lines[max(0, index - 1):index + 2]).lower()
                    if any(marker in window for marker in self.RETIREMENT_MARKERS):
                        continue
                    unmarked.extend(sorted(map(str, quoted)))
                with self.subTest(document=name):
                    self.assertEqual(
                        unmarked, [],
                        f"{name}: states {sorted(set(unmarked))} as current; the manifest records "
                        f"it as superseded")
                checked += 1
        self.assertGreater(checked, 0, "no document was checked, so this test proves nothing")


if __name__ == "__main__":
    unittest.main()
