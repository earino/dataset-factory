# Hugging Face datasets: concrete notes

## Layout that loads

The repository is a git repo; the consumer sees a tree. Put the tabular files where the card's
`data_files` points and keep the artifact's own metadata files at the root, mirroring the other
destination's layout.

A card's YAML front matter is what defines the splits, so generate it from the manifest's own split
names and counts rather than writing it by hand:

```yaml
---
license: other
license_name: <state the real status, e.g. source-public-domain-compilation-pending-review>
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train.csv
      - split: eval
        path: data/eval.csv
      - split: holdout
        path: data/holdout.csv
---
```

Split names do not have to be the conventional `train`/`validation`/`test`; use the artifact's own
vocabulary so the destination and the manifest agree, and assert those names back when verifying.

## What the card claims about itself

The card is the artifact's most-read description, and it is generated - so its claims about state
are programmatic inputs, not prose.

- **Derive the status line and the loading instructions from the manifest's publication state.** If
the card is built from the manifest, it already knows whether the release is public; a hardcoded
"Status: private..." or "for a private repository, pass a token" stays wrong forever after the
visibility changes, and the regeneration step meant to fix it re-emits the same literal.
- **Substitute the repository id with a sentinel, and assert the built card.** A doubled-brace token
inside an f-string renders to a single-brace string, so the replacement silently matches nothing and
the card ships `load_dataset("{repo_id}")`. Check the built text for zero placeholders and the real
id present - the check belongs in the test suite, next to the other static checks on the generator.
- **The loading example must run under the current visibility.** `token=True` in a public dataset's
documented command fails for the reader it was written for. Emit the credential argument only while
the repository is private.
- **Name a configuration in the example when the card declares more than one.** A config-less
invocation of a multi-config dataset never loads, so the example has to print the config name, and
that name comes from the card's own `configs:` block rather than from the generator's prose.
- **Re-read the live card, not the local build.** Fetch `README.md` from the repository after
uploading and confirm the state claims and the substitution by reading what a visitor reads.
- Uploading the regenerated card overwrites the navigation block that a website pipeline may manage
in the same document. Re-run that pipeline's link step afterwards (it is written to be idempotent
and to preserve the rest of the document), then verify the links are present again.

## Changing visibility

- Flip it through the client, not a hand-built endpoint: `HfApi.update_repo_settings(repo_id,
repo_type="dataset", private=False)`. The repository path is not the settings path, so a `PATCH`
constructed from the repository URL answers 404 and reads like a missing repository.
- Read `dataset_info().private` **and** `gated` back afterwards, then confirm anonymously: the
dataset API reached with no token reports `private: false`, and the revision-pinned files answer a
bounded range request.
- Do **not** route the flip through a tool whose create path asserts `private=True`. A create with
`exist_ok=True` is the documented way to make a repository, so re-running that same command to
refresh documentation can re-privatise a published dataset. Use the upload-only path and read the
visibility back before and after.
- After a visibility change, every destination's prose still describes the pre-publication state:
treat publication itself as a documentation-change event, and fix the status claims on each platform
in the same pass.

## Version-pinned loading, and proving it

```python
from datasets import load_dataset

ds = load_dataset("<owner>/<name>", "<config>", revision="<tag>")                  # public
ds = load_dataset("<owner>/<name>", "<config>", revision="<tag>", token=True)      # private
```

- **Name a configuration whenever the repository defines one.** The configs are declared in the
  card's front matter, and a call without one against such a repository is refused by name:
  `ValueError: Config name is missing. Please pick one among the available configs: ['<a>', '<b>']`.
  That refusal is the *functioning* case, not a broken release - the same revision loads once the
  argument is added - so check whether the card declares `configs:` before writing or verifying an
  example, and load every documented config at the pinned revision, comparing each one's split counts
  against the manifest.
- Never let the documentation choose the config for the reader: a silent default hands them a
  configuration they did not pick, with different splits and a different grain. Which config exists
  is the artifact's structure, not a formatting detail.
- The card and any landing page must print the **same** call from one shared helper. The site reads
  the config names off the same manifest; two hand-written examples drift, and the reader copies
  whichever one they happened to open.

- `revision` must be the **tag**, not a branch, and the tag must point at the commit that contains
  the data - a tag created before the upload pins an empty revision and the load returns nothing.
- For a private repository the credential must be passed. `datasets` looks for its own environment
  variable, so a child process whose environment was deliberately stripped needs `token=<value>`
  passed explicitly - otherwise the failure is `DatasetNotFoundError`, which reads like a
  permissions problem rather than a missing argument.
- `DatasetNotFoundError` from an uncredentialed call against a private repo is the **evidence of
  privacy**; pair it with the credentialed call succeeding as one observation.
- The `hf download` CLI with `--revision` and `--include` is the non-`datasets` path to document for
  consumers who only want the files.
- When the library is not installed where you are checking (it lives with the consumer/worker, not
  necessarily in the publishing venv), verify the same path at HTTP level instead: fetch the
  revision-pinned files and the revision metadata anonymously, and say plainly which level you
  checked rather than implying the library call was run.
- **Tag immutability after a documentation fix**: prose edits go to the default branch, never to the
tag. Confirm afterwards that the tag still resolves to the data commit and that the revision still
lists the artifact files.

## Uploading from a worker

- Create the repository first (`create_repo(..., repo_type="dataset", private=True)`), then read
  `repo_info().private` back and stop if it is not private.
- Keep the client in a virtualenv beside the job, not in a container, so the token never reaches an
  image or a mount. A stock worker image may have no `uv` and may create a venv with no `pip` -
  install what provides pip, or bootstrap it, and assert the import before uploading.
- Upload per file with `path_or_fileobj`, then re-read the file's record from the service and compare
  digests. Do this in the same unit of work that downloaded and hashed the file, then delete the local
  copy - the worker should hold one asset at a time, not the whole artifact.
- Passing the branch head as the upload revision and tagging afterwards is the correct order; an
  upload addressed to a tag that does not yet include the content will not appear in the pinned
  revision.

## Verification quirks that cause false failures

- `repo_info(..., files_metadata=True)` exposes a content `sha256` **only for files stored as LFS
  objects**. A small file stored as a regular git blob exposes a blob id, which is a SHA-1 over
  different bytes: comparing it to the manifest's sha256 reports a mismatch on a correct upload.
  For files below a few MB, download and hash them instead.
- A CSV loaded by `datasets` yields an integer column for a 0/1 label with no class names, so a check
  written against a labelled feature type always reports a mismatch. Compare the data's distinct
  values and the positive count per split.
- Split names in `data_files` become the keys of the returned `DatasetDict`; assert them against the
  manifest rather than assuming `train`/`test`.
- Row counts from a full load are cheap to compare and catch a truncated upload that a size check
  can miss; do both.

## API and CLI notes

- Client signatures vary by version: a `create_tag` may reject a `message` keyword. Check the
  installed client rather than assuming, and make the tagging step delete-then-create so it can be
  re-run.
- `whoami()` reports the authenticated account, its type and the token's role - enough to fix the
  namespace and to confirm a write role without ever printing the credential. A fine-grained token
  may report no scopes at all; the role is the usable signal.
- A 404 from `repo_info` is ambiguous between "absent" and "not visible to this token" - it means the
  repository must be created (or fetched with the right credential), not that the name is wrong.
- The API's dataset view and the settings view are different surfaces: `dataset_info()` is the
  read path for name, private, gated, sha and the file list, and it is the one to quote when
  reporting what the destination currently is.
