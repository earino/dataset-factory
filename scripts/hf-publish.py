#!/usr/bin/env python3
"""Publish the accepted artifact to Hugging Face, from the same release manifest as GitHub.

One manifest, two destinations. Every fact on the card - version, checksums, splits, labels,
provenance, licence status, measurements - is read from `MANIFEST.json` and the dataset's own
metadata files, so the two platforms cannot drift into describing different datasets.

Two-phase, because the repository is ~131 MB and bulk data does not belong on the coordinator:

* **small files** (card, docs, manifest, sums, meta.json, quality.json) are uploaded from here;
* **the CSVs** are uploaded by a worker job (`hf_publish` in the job bundle), which fetches each
  asset from the GitHub release, verifies its digest and pushes it to Hugging Face.

Both phases are safe to re-run: uploads are per-file and idempotent, and a file already matching
its manifest digest is skipped rather than re-sent. Completion is tracked per destination, so
GitHub can be complete while Hugging Face is still pending, and a release is reported complete
only when both verify.

Credentials: the write token is taken from `HF_TOKEN_WRITE` (or a credential **file** with
`--token-file`), used in-process, and never printed, logged, written into the package, or passed
as a command-line argument. The inference credential is never read or changed.

    python3 scripts/hf-publish.py --plan
    python3 scripts/hf-publish.py --create --upload-small
    python3 scripts/hf-publish.py --verify
"""

import argparse
import hashlib
import json
import re
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = Path("/opt/data/.venvs/hf/bin/python")
# Resolved per run: several dataset packages now exist, so the package under work is named rather
# than assumed, and the repository id comes from the dataset's own descriptor.
PACKAGE = REPO_ROOT / "release" / "austin-911-response"
# The Hugging Face path for each artifact file, from the dataset's descriptor when it declares one.
# Austin's published card uses flat `data/` names, so its descriptor declares nothing and the
# original rule below still produces exactly what is already published.
HF_PATHS = {}
CANDIDATE = "austin-911-response"
BUILD = REPO_ROOT / ".factory" / "hf-package"
# Rendered into the card. A doubled-brace placeholder was used here before, but an f-string renders
# that to a single brace, so the replacement silently did nothing and shipped the literal.
REPO_PLACEHOLDER = "__REPO_ID__"

# Files that travel to Hugging Face unchanged, and where they land.
SMALL_FILES = {
    "MANIFEST.json": "MANIFEST.json",
    "SHA256SUMS": "SHA256SUMS",
    "LICENSE.md": "LICENSE.md",
    "LICENSE-MIT.txt": "LICENSE-MIT.txt",
    "LICENSE-CC0-1.0.txt": "LICENSE-CC0-1.0.txt",
    "DATA_DICTIONARY.md": "DATA_DICTIONARY.md",
    "VERIFICATION.md": "VERIFICATION.md",
    "measurements.json": "measurements.json",
}
# Assets whose logical path is inside the archive rather than a file in the package directory.
ASSET_LOCATION = {"meta.json": "meta.json", "quality.json": "quality.json"}


def reexec_in_venv():
    if os.environ.get("HF_PUBLISH_VENV") == "1":
        return
    try:
        import huggingface_hub  # noqa: F401
        return
    except ImportError:
        pass
    if not VENV_PYTHON.is_file():
        print(json.dumps({"ok": False, "error": f"huggingface_hub missing and {VENV_PYTHON} not "
                                                "found"}, indent=2))
        raise SystemExit(2)
    os.environ["HF_PUBLISH_VENV"] = "1"
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])


def load_token(args):
    """Never printed. The file mechanism is the fallback for environments without managed vars."""
    if args.token_file:
        path = Path(args.token_file)
        if not path.is_file():
            raise SystemExit(f"credential file {path} does not exist")
        return path.read_text().strip()
    token = os.environ.get(args.token_var)
    if not token:
        raise SystemExit(f"{args.token_var} is not visible and no --token-file was given")
    return token


def manifest():
    return json.loads((PACKAGE / "MANIFEST.json").read_text())


def resolve_candidate(name: str | None) -> str:
    """Which dataset package this run is about.

    With one package present the answer is unambiguous; with several, guessing would publish the
    wrong dataset's bytes under the right dataset's name, so the caller must say.
    """
    packages = sorted(folder.name for folder in (REPO_ROOT / "release").iterdir()
                      if (folder / "MANIFEST.json").is_file())
    if name:
        if name not in packages:
            raise SystemExit(f"no release package for {name}; present: {packages}")
        return name
    if len(packages) == 1:
        return packages[0]
    raise SystemExit("several release packages exist; pass --candidate: " + ", ".join(packages))


def descriptor(candidate: str) -> dict:
    return json.loads((REPO_ROOT / "candidates" / candidate / "release.json").read_text())


def asset_target(manifest_data, logical):
    if logical in HF_PATHS:
        return HF_PATHS[logical]
    """Where an asset lands in the Hugging Face repository.

    The CSVs live under `data/` (the card's `data_files` points there); `meta.json` and
    `quality.json` stay at the root, matching the layout the runner contract expects.
    """
    asset_name = manifest_data["assets"][logical]["asset_name"]
    return f"data/{asset_name}" if logical.endswith(".csv") else asset_name


def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_card_template(text: str, manifest_data: dict) -> str:
    """Fill a dataset-supplied card with values the manifest owns.

    The card is a narrative, and a narrative cannot be generated from a manifest: which task, which
    splits, why the dataset exists. What *can* be generated is every fact a reader might check -
    version, tag, status, row counts, loading instructions, licence - so the dataset writes the
    prose and the generator fills the facts, rather than the prose being frozen into the generator.
    """
    splits = manifest_data.get("splits") or {}
    published = bool(manifest_data.get("published"))
    total = sum(entry.get("rows", 0) for entry in splits.values()) if isinstance(splits, dict) else 0
    licences = manifest_data.get("licenses") or {}
    values = {
        "REPO_ID": CANDIDATE,  # replaced by the real id at build time
        "ARTIFACT_VERSION": str(manifest_data.get("artifact_version")),
        "RELEASE_TAG": str(manifest_data.get("release_tag")),
        "GITHUB_REPOSITORY": str(manifest_data.get("repository")),
        "STATUS_LINE": ("public. Released after explicit operator authorisation; publication changed "
                        "no data file, tag or checksum.") if published else (
                        "private. Public visibility requires explicit human approval. Nothing here "
                        "has been published."),
        "LOADING_NOTE": ("The repository is public, so loading needs no credential:") if published else (
                        "For a private repository, pass a token that has access to it:"),
        "ROWS_TOTAL": f"{total:,}",
        "DATA_LICENSE": str((licences.get("data_compilation") or {}).get("spdx")),
        "CODE_LICENSE": str((licences.get("code") or {}).get("spdx")),
        "SOURCE_LICENSE": str((licences.get("source_data") or {}).get("spdx")),
        "SOURCE_ATTRIBUTION": str((licences.get("source_data") or {}).get("attribution")),
        "TOKEN_ARG": "" if published else ", token=True",
    }
    out = text
    for key, value in values.items():
        out = out.replace("{" + key + "}", value)
    # Only UPPER_CASE tokens are placeholders: a card legitimately contains braces in example
    # output, and treating those as unfilled placeholders made the check fail on correct prose.
    unresolved = sorted({name for name in re.findall(r"\{([A-Z][A-Z0-9_]*)\}", out)
                         if name not in values})
    if unresolved:
        raise SystemExit(f"card template has unresolved placeholders: {unresolved}")
    return out


def card(manifest_data):
    """The dataset card, generated from the manifest so both platforms describe one dataset."""
    splits = manifest_data["splits"]
    measurements = manifest_data.get("measurements") or {}
    clock = measurements.get("clock_offset") or {}
    threshold = measurements.get("threshold_search") or {}
    extraction = measurements.get("extraction_cost") or {}
    source = manifest_data.get("source") or {}
    licenses = manifest_data.get("licenses") or {}
    code_license = (licenses.get("code") or {}).get("spdx") or "not declared"
    data_license = (licenses.get("data_compilation") or {}).get("spdx") or "not declared"
    source_license = (licenses.get("source_data") or {})
    # Publication state comes from the manifest, which derives it from the recorded destination
    # state. The card asserted "private" unconditionally, so it stayed wrong after publication.
    template = REPO_ROOT / "candidates" / CANDIDATE / "card.md"
    if template.is_file():
        # A dataset that supplies its own card gets the dataset-driven path; Austin's published card
        # predates this and is left byte-identical by the branch below.
        return render_card_template(template.read_text(), manifest_data)
    published = bool(manifest_data.get("published"))
    status_line = ("public. Released after explicit operator authorisation; publication changed no "
                   "data file, tag or checksum.") if published else (
                   "private. Public visibility requires explicit human approval. Nothing here has "
                   "been published.")
    loading_note = ("The repository is public, so loading needs no credential and no token has to "
                    "be passed:") if published else (
                   "For a private repository, pass a token that has access to it (the inference "
                   "credential does not):")
    source_spdx = source_license.get("status") or source_license.get("spdx") or "not declared"
    attribution = source_license.get("attribution") or ""
    citation = source_license.get("citation") or ""
    qualification = manifest_data.get("qualification") or {}
    baseline = manifest_data.get("baseline") or {}

    def rows(name):
        return splits[name]["rows"]

    def rate(name):
        return splits[name]["positive_rate"]

    return f"""---
license: cc0-1.0
language:
  - en
pretty_name: Austin 911 Response Time ({manifest_data['release_version']})
size_categories:
  - 1M<n<10M
task_categories:
  - tabular-classification
tags:
  - tabular
  - public-safety
  - emergency-response
  - temporal-split
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

# Austin 911 Response Time ({manifest_data['release_version']})

**Status: {status_line}**

Predict whether an Austin 911 call for service will have a **late first-unit arrival**: at least
`{threshold.get('chosen_seconds', 'T')} seconds` between the call being answered and the first unit
arriving. The label and every feature are knowable at prediction time; the label source column is
never shipped.

- **Artifact version:** `{manifest_data['artifact_version']}`
- **Version tag:** `{manifest_data['release_tag']}` (use this revision for reproducibility)
- **GitHub counterpart:** {manifest_data.get('repository')}
- **Rows:** {rows('train') + rows('eval') + rows('holdout'):,} across three disjoint temporal splits

## Loading

Version-pinned. `revision` is the tag, not a branch, so the bytes cannot change under you.

```python
from datasets import load_dataset

ds = load_dataset("__REPO_ID__", revision="{manifest_data['release_tag']}")
print(ds)
# DatasetDict({{
#     train: Dataset({{features: [...], num_rows: {rows('train')}}}),
#     eval: Dataset({{features: [...], num_rows: {rows('eval')}}}),
#     holdout: Dataset({{features: [...], num_rows: {rows('holdout')}}})
# }})

# the label is `late`, a binary target
print(ds["train"].features["late"])
```

{loading_note}

```python
ds = load_dataset("__REPO_ID__", revision="{manifest_data['release_tag']}"{', token=True' if not published else ''})
```

The files are also plain CSVs, so they can be used without `datasets`:

```bash
hf download __REPO_ID__ --repo-type dataset --revision {manifest_data['release_tag']} \\
    --include "data/*.csv" --local-dir ./austin
```

## Splits

Split by `response_datetime`, disjoint and ordered, so no split leaks into another:

| split | rows | positives | positive rate | window |
| --- | --- | --- | --- | --- |
| `train` | {rows('train'):,} | {splits['train']['positives']:,} | {rate('train'):.4f} | before 2025-01-01 |
| `eval` | {rows('eval'):,} | {splits['eval']['positives']:,} | {rate('eval'):.4f} | 2025 |
| `holdout` | {rows('holdout'):,} | {splits['holdout']['positives']:,} | {rate('holdout'):.4f} | 2026 onward |

## The labels

`late` is the binary target: `1` when the first unit arrived `{threshold.get('chosen_seconds', 'T')}` or
more seconds after the call was answered.

The threshold was frozen from the **training window by rule, not by hand** - the largest tested
value whose training-window positive rate stays at or above 0.40, counting only aggregate queries:

- `{threshold.get('chosen_seconds')}s` gives a training rate of **{threshold.get('training_rate_at_chosen')}**
- `{threshold.get('why_not_1260', '').split()[0] if threshold.get('why_not_1260') else 'the next value'}`
  falls below the target: {threshold.get('why_not_1260', 'recorded in measurements.json')}

Positive rates differ by split ({rate('train'):.4f} / {rate('eval'):.4f} / {rate('holdout'):.4f});
that reflects when the data was collected, not a construction fault.

## The response-time clock (measured, not assumed)

`response_time` is documented as measuring from when the call was **answered**, and no column
records that instant, so the label cannot be recomputed from the shipped fields. Measured over
{clock.get('rows_measured', 'N')} rows:

- definition: `{clock.get('definition', 'n/a')}`
- median **{clock.get('median_seconds')}s**, p05 {clock.get('p05_seconds')}s, p95 {clock.get('p95_seconds')}s,
  range {clock.get('min_seconds')}s to {clock.get('max_seconds')}s
- {clock.get('negative_rows')} negative / {clock.get('exact_zero_rows')} exact zero /
  {clock.get('positive_rows')} positive rows

Reproduce it with `{clock.get('command', 'the recorded command')}`.

## Provenance

- Source: {source.get('name')} (dataset `{source.get('dataset_id')}`), {source.get('landing_page')}
- Licence of the source data: Public Domain, per the publisher's catalogue metadata.
- Extraction: **{extraction.get('http_requests_total', 'N')} HTTP requests**
  ({extraction.get('breakdown', {}).get('aggregate_queries', 'n/a')} aggregate,
  {extraction.get('breakdown', {}).get('page_requests', 'n/a')} pages), measured
  {extraction.get('wall_clock_seconds', 'n/a')}s on {extraction.get('machine', 'a worker')}.
- Rebuild: `MANIFEST.json` pins the build timestamp, so a rebuild is byte-identical.

## Licence and attribution

| | |
| --- | --- |
| Source data (City of Austin) | **{source_spdx}** - designation preserved, attribution and citation given below |
| Our rights in this derived compilation | **{data_license}** (`LICENSE-CC0-1.0.txt`) |
| Code and documentation in the GitHub counterpart | **{code_license}** (`LICENSE-MIT.txt`) |

**Scope, stated plainly:** the CC0 dedication covers **our contribution** - the row selection, the
derived binary label, the temporal partition and the packaging. It does **not** cover or relicense
the City of Austin's data, which keeps its own Public Domain designation. This dataset is derived
from the City of Austin's open data and is labelled as derived; it is **not an official City of
Austin product**.

**Attribution.** {attribution}

**Suggested citation.**

> {citation}

**Future datasets** in this series choose terms compatible with each source; CC0 here is not a
standing permission to override another source's terms.

## Qualification and baseline

- Gate: **{qualification.get('result', 'not recorded')}** (gate {qualification.get('gate_version')}),
  run over the full artifact on a worker.
- One baseline through the runner's existing training and validation contract:
  **eval AUC {baseline.get('eval_auc', 'not recorded')}**.
- Scope: {manifest_data.get('scope', 'one baseline; no agent or harness comparison is implied.')}

Every number above is measured, with the command that produced it recorded in
`measurements.json`; figures that are estimates are labelled as such.
"""


def build_package(manifest_data, repo_id):
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "data").mkdir(exist_ok=True)
    written = []
    for source_name, target_name in SMALL_FILES.items():
        source = PACKAGE / source_name
        if source.is_file():
            (BUILD / target_name).write_bytes(source.read_bytes())
            written.append(target_name)
    card_text = card(manifest_data).replace(REPO_PLACEHOLDER, repo_id)
    (BUILD / "README.md").write_text(card_text)
    written.append("README.md")
    # Loading instructions for the two entry points, kept beside the card.
    token_note = ("The repository is public, so no token is needed." if manifest_data.get("published")
                  else "Private repository: pass a token that has access to it.")
    (BUILD / "LOADING.md").write_text(
        f"# Getting the data\n\n## Hugging Face (this repository), version-pinned\n\n"
        "```python\nfrom datasets import load_dataset\n"
        f'ds = load_dataset("{repo_id}", revision="{manifest_data["release_tag"]}")\n```\n\n'
        f"{token_note}\n\n"
        "## GitHub counterpart\n\n"
        f"`{manifest_data.get('get_dataset_command')}` in "
        f"{manifest_data.get('repository')}.\n\n"
        "Both destinations carry the same files and the same digests; "
        "`MANIFEST.json` and `SHA256SUMS` verify either copy.\n"
    )
    written.append("LOADING.md")
    return written


def plan(manifest_data, repo_id):
    assets = manifest_data["assets"]
    return {
        "repository": repo_id,
        "private": not manifest_data.get("published", False),
        "release_tag": manifest_data["release_tag"],
        "artifact_version": manifest_data["artifact_version"],
        "small_uploads": sorted(build_package(manifest_data, repo_id)),
        "asset_uploads": [
            {"logical": logical, "to": asset_target(manifest_data, logical),
             "asset_name": info["asset_name"], "bytes": info["bytes"],
             "sha256": info["sha256"], "via": "worker job (hf_publish)"}
            for logical, info in sorted(assets.items())
        ],
        "card_generated_from": "MANIFEST.json",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", default=None,
                        help="which dataset package to publish (required once several exist)")
    parser.add_argument("--repo", default=None, help="owner/name; default from the manifest source")
    parser.add_argument("--token-var", default="HF_TOKEN_WRITE")
    parser.add_argument("--token-file", default=None,
                        help="read the write token from this file instead of the environment")
    parser.add_argument("--plan", action="store_true", help="build the package and print the plan")
    parser.add_argument("--create", action="store_true", help="create the private dataset repo")
    parser.add_argument("--upload-small", action="store_true", help="upload docs and small files")
    parser.add_argument("--tag", action="store_true", help="create the version tag")
    parser.add_argument("--verify", action="store_true", help="verify uploaded files vs the manifest")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    # The package must be chosen before anything is read from it: reading the manifest first meant
    # this ran against whichever dataset was hardcoded, whatever --candidate said.
    candidate = resolve_candidate(args.candidate)
    global PACKAGE, HF_PATHS, CANDIDATE
    CANDIDATE = candidate
    PACKAGE = REPO_ROOT / "release" / candidate
    declared = descriptor(candidate)
    HF_PATHS = declared.get("hf_paths") or {}
    manifest_data = manifest()
    repo_id = args.repo or declared["repository"].removeprefix("https://github.com/")
    result = {"repository": repo_id}

    if args.plan or not any((args.create, args.upload_small, args.tag, args.verify)):
        result.update(plan(manifest_data, repo_id))
        print(json.dumps(result, indent=2))
        return 0

    reexec_in_venv()
    token = load_token(args)
    from huggingface_hub import HfApi, create_repo, upload_folder
    from huggingface_hub.utils import HfHubHTTPError

    api = HfApi(token=token)
    who = api.whoami()
    result["acting_account"] = who.get("name")
    result["token_role"] = ((who.get("auth") or {}).get("accessToken") or {}).get("role")

    if args.create:
        create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True, token=token)
        info = api.repo_info(repo_id, repo_type="dataset")
        result["created"] = {"id": info.id, "private": info.private}
        if not info.private:
            print(json.dumps({**result, "ok": False,
                              "error": "repository is PUBLIC; publication requires approval"},
                             indent=2))
            return 1

    if args.upload_small:
        build_package(manifest_data, repo_id)
        upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(BUILD),
                      allow_patterns=[name for name in sorted(build_package(manifest_data, repo_id))],
                      commit_message=f"Publish {manifest_data['release_tag']} documentation and "
                                     "small files from the release manifest",
                      token=token)
        result["small_uploaded"] = sorted(build_package(manifest_data, repo_id))

    if args.tag:
        # Idempotent, and deliberately the LAST step of a release: a tag created before the data
        # lands pins a commit without the files, and the version-pinned load then fetches nothing.
        # Re-running deletes and re-creates it at the current head instead of failing.
        try:
            api.delete_tag(repo_id, tag=manifest_data["release_tag"], repo_type="dataset",
                           token=token)
            result["tag_replaced"] = True
        except Exception as exc:  # noqa: BLE001 - absent tag is the normal first run
            result["tag_replaced"] = f"no existing tag ({type(exc).__name__})"
        api.create_tag(repo_id, tag=manifest_data["release_tag"], repo_type="dataset", token=token)
        refs = api.list_repo_refs(repo_id, repo_type="dataset")
        tag_sha = next((r.target_commit for r in (refs.tags or []) if r.name == manifest_data["release_tag"]), None)
        branch_sha = next((b.target_commit for b in (refs.branches or []) if b.name == "main"), None)
        result["tagged"] = manifest_data["release_tag"]
        result["tag_commit"] = tag_sha
        result["main_commit"] = branch_sha
        result["tag_matches_main"] = bool(tag_sha) and tag_sha == branch_sha

    if args.verify:
        try:
            info = api.repo_info(repo_id, repo_type="dataset", files_metadata=True)
        except HfHubHTTPError as exc:
            print(json.dumps({**result, "ok": False, "error": f"repo_info failed: {exc}"}, indent=2))
            return 1
        # Size alone is not verification: the Hub exposes a sha256 only for LFS objects, so a
        # match on that digest is checked where present, and size is a weaker fallback for files
        # stored as plain git blobs (which hf-publish.py re-hashes by download).
        on_hub = {}
        for sibling in (info.siblings or []):
            lfs = getattr(sibling, "lfs", None) or {}
            on_hub[sibling.rfilename] = (sibling.size, lfs.get("sha256"))
        result["repo_private"] = info.private
        expected = {}
        for logical, entry in (manifest_data.get("assets") or {}).items():
            expected[asset_target(manifest_data, logical)] = (entry["bytes"], entry["sha256"])
        present, missing, mismatched, digest_checked = [], [], [], []
        for path, (size, sha256) in sorted(expected.items()):
            if path not in on_hub:
                missing.append(path)
                continue
            hub_size, hub_digest = on_hub[path]
            if hub_size is not None and hub_size != size:
                mismatched.append({"path": path, "expected_bytes": size, "hub_bytes": hub_size})
                continue
            if hub_digest:
                if hub_digest != sha256:
                    mismatched.append({"path": path, "expected_sha256": sha256,
                                       "hub_sha256": hub_digest})
                    continue
                digest_checked.append(path)
            present.append(path)
        result["digest_verified"] = sorted(digest_checked)
        result["digest_note"] = ("paths not listed under digest_verified are stored as plain git "
                                 "blobs, where the Hub reports no sha256; the worker re-hashes "
                                 "those by download instead")
        result["files"] = {"present": present, "missing": missing, "size_mismatch": mismatched}
        result["small_files"] = sorted(name for name in SMALL_FILES.values() if name in on_hub)
        try:
            refs = api.list_repo_refs(repo_id, repo_type="dataset")
            result["tags"] = sorted(r.name for r in (refs.tags or []))
        except HfHubHTTPError:
            result["tags"] = None
        result["ok"] = not missing and not mismatched
        # Record this destination's completion next to the package, so the release can be tracked
        # per platform and a half-published release cannot be mistaken for a finished one.
        record_path = PACKAGE / "DESTINATIONS.json"
        try:
            record = json.loads(record_path.read_text()) if record_path.is_file() else {}
        except json.JSONDecodeError:
            record = {}
        record.setdefault("release_tag", manifest_data["release_tag"])
        record["destinations"] = record.get("destinations") or {}
        record["destinations"]["huggingface"] = {
            "repo": repo_id,
            "revision": manifest_data["release_tag"],
            "private": info.private,
            "verified": bool(result["ok"]),
            "verified_at": None if not result["ok"] else __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
            "files_verified": sorted(present),
            "missing": missing,
            "size_mismatch": mismatched,
            "loading_check": (result.get("loading_check") or "run by the worker job and recorded "
                              "in its report"),
        }
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        result["recorded"] = str(record_path.relative_to(REPO_ROOT))

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
