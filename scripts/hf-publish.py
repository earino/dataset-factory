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
import uuid
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = Path("/opt/data/.venvs/hf/bin/python")
# Resolved per run: several dataset packages now exist, so the package under work is named rather
# than assumed, and the repository id comes from the dataset's own descriptor.
# Set per run by main() from --candidate. There is deliberately no dataset name here: a default
# published whichever dataset was named last, which is how --plan for one dataset printed another's
# files. Reading it before it is set is a programming error, not a fallback.
PACKAGE = None
# Set per run by main(). No dataset is named here: a default is how one dataset's files were
# published under another's card.
CANDIDATE = None
BUILD = REPO_ROOT / ".factory" / "hf-package"


sys.path.insert(0, str(REPO_ROOT))
from factory.release_schema import as_release, load_release, record_destination, atomic_write, UNKNOWN
from factory.hub_integrity import HubIntegrityError, refs, verify_revision, tag_verified_commit, load_worker_receipt

def _config_names(splits):
    """The config names a split map is grouped by, through the rule the dataset page also uses.

    Defined once in factory.site_model so a card and a page cannot disagree about whether the
    documented loading command needs a config named.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from factory.site_model import config_names
    return config_names(splits)


def _manifest_configs(manifest_data):
    """{config: [split names]} for every config the manifest declares.

    The split-map-only rule returned nothing for MSHA, whose 45 per-section configs live under
    `levels` while `splits` describes the shared pool - so the card would have declared one config
    over one arbitrary CSV pair and the load would have produced the wrong splits.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from factory.site_model import dataset_config_splits
    return dataset_config_splits(manifest_data)


def hub_path(manifest_data, config, split):
    """Where a config's split CSV lives on the Hub, from the manifest alone."""
    release = as_release(manifest_data)
    m = release.metadata
    prefix = "" if config in ("default", "") else config + "/"
    for logical, artifact in (m.get("layout") or {}).items():
        if artifact.startswith(prefix) and artifact.rsplit("/", 1)[-1] == f"{split}.csv":
            declared = (m.get("hub_paths") or {})
            for key in (artifact, logical):
                if declared.get(key):
                    return declared[key]
            info = (m.get("assets") or {}).get(artifact) or {}
            if info.get("asset_name"):
                return f"data/{info['asset_name']}"
    raise SystemExit(f"no Hub path for config {config!r} split {split!r}")


def configs_block(manifest_data):
    """The card's `configs:` frontmatter, generated from the manifest rather than typed."""
    lines = []
    for config, splits in sorted(_manifest_configs(manifest_data).items()):
        lines.append(f"  - config_name: {config}")
        lines.append("    data_files:")
        for split in splits:
            lines.append(f"      - split: {split}")
            lines.append(f"        path: {hub_path(manifest_data, config, split)}")
    return "\n".join(lines)
# Rendered into the card. A doubled-brace placeholder was used here before, but an f-string renders
# that to a single brace, so the replacement silently did nothing and shipped the literal.
REPO_PLACEHOLDER = "__REPO_ID__"

# Files that travel to Hugging Face unchanged, and where they land.
SMALL_FILES = {
    "MANIFEST.json": "MANIFEST.json",
    # Declares every config's column types. Without it the loader infers types from a sample of
    # each CSV, and `event_no` (mostly digits, occasionally `F015FC6`) was inferred as int64 and
    # then failed to cast, so the documented `load_dataset` call raised on the holdout split.
    "dataset_infos.json": "dataset_infos.json",
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
    if PACKAGE is None:
        raise SystemExit("no candidate resolved; main() must set PACKAGE from --candidate first")
    return load_release(PACKAGE)


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
    """Resolve the declared Hub path, retaining flat names for historical releases."""
    release = as_release(manifest_data)
    paths = release.metadata.get("hub_paths") or {}
    if logical in paths:
        return paths[logical]
    asset_name = release.metadata["assets"][logical]["asset_name"]
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
    release = as_release(manifest_data)
    m = release.metadata
    published = release.published
    total = release.rows
    configs = sorted(n for n in release.configs if n != "default")
    licences = release.licences
    values = {
        # The template's loading example has to name the repository the way the Hub does. Filling
        # this with the bare candidate name produced a card whose documented command raised
        # DatasetNotFoundError, while the guard that watched for the literal placeholder passed.
        "REPO_ID": REPO_PLACEHOLDER,  # replaced by the real owner-qualified id at build time
        "CONFIGS": ", ".join(configs),
        "CONFIGS_BLOCK": configs_block(manifest_data),
        "N_CONFIGS": f"{len(configs):,}",
        "ARTIFACT_VERSION": release.artifact_id or UNKNOWN,
        "RELEASE_TAG": release.tag or UNKNOWN,
        "GITHUB_REPOSITORY": str(m.get("repository")),
        "STATUS_LINE": ("public. Released after explicit operator authorisation; publication changed "
                        "no data file, tag or checksum.") if published else (
                        "private. Public visibility requires explicit human approval. Nothing here "
                        "has been published."),
        "LOADING_NOTE": ("The repository is public, so loading needs no credential:") if published else (
                        "For a private repository, pass a token that has access to it:"),
        "ROWS_TOTAL": f"{total:,}" if total is not None else UNKNOWN,
        "BASELINE_AUC": release.baseline_display,
        "DATA_LICENSE": str((licences.get("data_compilation") or {}).get("spdx")),
        "CODE_LICENSE": str((licences.get("code") or {}).get("spdx")),
        "SOURCE_LICENSE": str((licences.get("source_data") or {}).get("spdx")),
        "SOURCE_ATTRIBUTION": str((licences.get("source_data") or {}).get("attribution")),
        "TOKEN_ARG": "" if published else ", token=True",
    }
    out = text
    for key, value in values.items():
        # str() because a value can legitimately be None before a candidate is resolved, and
        # a TypeError there would read as a template bug rather than a missing input.
        out = out.replace("{" + key + "}", str(value))
    # Only UPPER_CASE tokens are placeholders: a card legitimately contains braces in example
    # output, and treating those as unfilled placeholders made the check fail on correct prose.
    unresolved = sorted({name for name in re.findall(r"\{([A-Z][A-Z0-9_]*)\}", out)
                         if name not in values})
    if unresolved:
        raise SystemExit(f"card template has unresolved placeholders: {unresolved}")
    return out


def card(manifest_data):
    """The dataset card, generated from the manifest so both platforms describe one dataset."""
    template = REPO_ROOT / "candidates" / CANDIDATE / "card.md"
    if template.is_file():
        # A dataset that supplies its own card gets the dataset-driven path; Austin's published card
        # predates this and is left byte-identical by the branch below.
        return render_card_template(template.read_text(), manifest_data)
    # Refuse rather than fall back to another dataset's prose. This used to fall through to one
    # dataset's card hardcoded here, which would have shipped its description under another's name.
    raise SystemExit(f"candidates/{CANDIDATE}/card.md is missing: every dataset supplies its own card")

def navigation_record():
    """The record the managed navigation block is built from, once this release has a live site.

    None until DESTINATIONS.json records a verified site, so a staged package never advertises a
    page that does not exist yet.
    """
    record_path = PACKAGE / "DESTINATIONS.json"
    if not record_path.is_file():
        # No destinations recorded at all: the same state as "no verified site", which is the
        # staged-package case this function exists for. A first-ever --plan must not crash on it.
        return None
    release = load_release(PACKAGE)
    site = release.destinations.get("site")
    if site is None or not site.verified:
        return None
    sys.path.insert(0, str(REPO_ROOT))
    from factory.site_model import project
    editorial = json.loads((REPO_ROOT / "sites" / f"{CANDIDATE}.json").read_text())
    config = json.loads((REPO_ROOT / "config" / "sites.json").read_text())
    return project(PACKAGE, editorial, config)


def loading_text(manifest_data, repo_id):
    """The loading instructions, generated so the printed command is the one that works.

    A dataset with more than one config (NOAA: one per level) needs the config named, or the
    documented command raises "Config name is missing"; the owner-qualified id is needed too, since
    a bare name raises DatasetNotFoundError for an anonymous reader. Both defects shipped, so both
    are generated here from the manifest rather than written by hand.
    """
    release = as_release(manifest_data)
    m = release.metadata
    token_note = ("The repository is public, so no token is needed." if release.published
                  else "Private repository: pass a token that has access to it.")
    config_map = _manifest_configs(manifest_data)
    configs = sorted(n for n in release.configs if n != "default")
    tag = as_release(manifest_data).tag
    if configs:
        loading = "\n".join(f'ds = load_dataset("{repo_id}", "{name}", revision="{tag}")'
                            for name in configs)
        config_note = (f"This dataset has {len(configs)} configs - {', '.join(configs)} - one per "
                       "target; the config has to be named, and each is a complete binary task "
                       "instance with its own train/eval/holdout files:\n\n")
    else:
        loading = f'ds = load_dataset("{repo_id}", revision="{tag}")'
        config_note = ""
    return (
        f"# Getting the data\n\n## Hugging Face (this repository), version-pinned\n\n"
        f"{config_note}"
        "```python\nfrom datasets import load_dataset\n"
        f"{loading}\n```\n\n"
        f"{token_note}\n\n"
        "## GitHub counterpart\n\n"
        f"`{m.get('get_dataset_command')}` in "
        f"{m.get('repository')}.\n\n"
        "Both destinations carry the same files and the same digests; "
        "`MANIFEST.json` and `SHA256SUMS` verify either copy.\n"
    )


def build_package(manifest_data, repo_id):
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "data").mkdir(exist_ok=True)
    written = []
    # Licence files are dataset-specific: a dataset may ship terms of its own that are not one of
    # the standard texts hardcoded above (Chicago ships the City's Data Terms of Use), so every
    # LICENSE* file in the package travels, not only the names in SMALL_FILES.
    extra_licenses = [p.name for p in sorted(PACKAGE.glob("LICENSE*"))
                      if p.is_file() and p.name not in SMALL_FILES]
    for source_name in list(SMALL_FILES) + extra_licenses:
        target_name = SMALL_FILES.get(source_name, source_name)
        source = PACKAGE / source_name
        if source.is_file():
            (BUILD / target_name).write_bytes(source.read_bytes())
            written.append(target_name)
    card_text = card(manifest_data).replace(REPO_PLACEHOLDER, repo_id)
    # A live site is linked from the card, and the block is derived here rather than written once by
    # the publication pipeline: a later card re-upload without it stripped the only link a reader
    # had to the dataset's own page, and verification then failed with "Destination navigation
    # is missing".
    record = navigation_record()
    if record is not None:
        from factory.site_model import linked_readme
        card_text = linked_readme(card_text, record)
    (BUILD / "README.md").write_text(card_text)
    written.append("README.md")
    (BUILD / "LOADING.md").write_text(loading_text(manifest_data, repo_id))
    written.append("LOADING.md")
    return written


def plan(manifest_data, repo_id):
    release = as_release(manifest_data)
    m = release.metadata
    assets = m["assets"]
    return {
        "repository": repo_id,
        "private": not release.published,
        "release_tag": release.tag,
        "artifact_version": release.artifact_id,
        "small_uploads": sorted(build_package(manifest_data, repo_id)),
        "asset_uploads": [
            {"logical": logical, "to": asset_target(manifest_data, logical),
             "asset_name": info["asset_name"], "bytes": info["bytes"],
             "sha256": info["sha256"], "via": "worker job (hf_publish)"}
            for logical, info in sorted(assets.items())
        ],
        "card_generated_from": "MANIFEST.json",
    }


class _SafeHubRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https':
            raise HubIntegrityError('refusing non-HTTPS Hub redirect')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and target.netloc != urlsplit(req.full_url).netloc:
            redirected.remove_header('Authorization')
        return redirected


def small_reader(repo_id, token, endpoint):
    """Stream only declared small metadata, pinned to a commit; no persistent cache."""
    from huggingface_hub import hf_hub_url
    opener = build_opener(_SafeHubRedirect())

    def read(path, commit, limit):
        url = hf_hub_url(repo_id, path, repo_type='dataset', revision=commit, endpoint=endpoint)
        if urlsplit(url).scheme != 'https':
            raise HubIntegrityError('refusing non-HTTPS Hub download')
        request = Request(url, headers={'Authorization': f'Bearer {token}'})
        with opener.open(request, timeout=30) as response:
            return response.read(limit + 1)
    return read


def record_attempt(candidate, result):
    """Keep failed/incomplete attempts distinct from the last complete release receipt."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', candidate):
        raise HubIntegrityError('invalid candidate identifier for verification attempt')
    folder = REPO_ROOT / '.factory' / 'hub-verification' / candidate
    for entry in (folder, *folder.parents):
        if entry == REPO_ROOT:
            break
        if entry.is_symlink():
            raise HubIntegrityError('verification attempt path contains a symlink')
    folder.mkdir(parents=True, exist_ok=True)
    # One current diagnostic per candidate, bounded by the release's metadata size. Historical
    # successful evidence stays in DESTINATIONS; don't consume the compact-report allowance
    # with an unbounded poll history.
    path = folder / 'latest.json'
    result['attempt_id'] = uuid.uuid4().hex
    result['attempted_at'] = __import__('datetime').datetime.now(
        __import__('datetime').timezone.utc).isoformat(timespec='seconds')
    result['attempt_recorded'] = str(path.relative_to(REPO_ROOT))
    encoded = json.dumps(result, indent=2) + '\n'
    if len(encoded.encode()) > 256 * 1024:
        raise HubIntegrityError('verification attempt exceeds compact-report limit')
    atomic_write(path, encoded)


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
    parser.add_argument("--tag", action="store_true", help="verify assets, then create an immutable version tag at the verified main commit")
    parser.add_argument("--verify", action="store_true", help="verify uploaded files and record evidence in DESTINATIONS.json (writes locally)")
    parser.add_argument("--worker-job", help="collected successful hf_publish job supplying pinned bulk-digest evidence")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    # The package must be chosen before anything is read from it: reading the manifest first meant
    # this ran against whichever dataset was hardcoded, whatever --candidate said.
    candidate = resolve_candidate(args.candidate)
    global PACKAGE, CANDIDATE
    CANDIDATE = candidate
    PACKAGE = REPO_ROOT / "release" / candidate
    declared = descriptor(candidate)
    manifest_data = manifest()
    m = manifest_data.metadata
    repo_id = args.repo or declared["repository"].removeprefix("https://github.com/")
    result = {"repository": repo_id}

    if args.plan or not any((args.create, args.upload_small, args.tag, args.verify)):
        result.update(plan(manifest_data, repo_id))
        print(json.dumps(result, indent=2))
        return 0

    reexec_in_venv()
    token = load_token(args)
    from huggingface_hub import HfApi, create_repo, upload_folder

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
                      commit_message=f"Publish {as_release(manifest_data).tag} documentation and "
                                     "small files from the release manifest",
                      token=token)
        result["small_uploaded"] = sorted(build_package(manifest_data, repo_id))

    if args.tag or args.verify:
        try:
            main_commit, tags = refs(api, repo_id)
            tag = manifest_data.tag
            if args.tag and tag in tags and tags[tag] != main_commit:
                raise HubIntegrityError('existing release tag names another commit; preserve it and use a new reviewed version')
            # A verification-only repeat checks the immutable release tag, even after editorial
            # commits advance main. Before first tagging, verify main without claiming a tag exists.
            revision = main_commit if args.tag else tags.get(tag, main_commit)
            expected = {}
            for logical, entry in (m.get("assets") or {}).items():
                target = asset_target(manifest_data, logical)
                if target in expected:
                    raise HubIntegrityError('manifest maps more than one asset to a Hub path')
                expected[target] = (entry["bytes"], entry["sha256"])
            receipt = load_worker_receipt(REPO_ROOT, args.worker_job, repo_id, expected) if args.worker_job else None
            result.update(verify_revision(api, repo_id, expected, revision,
                                          small_reader(repo_id, token, api.endpoint), receipt))
            if args.worker_job:
                result["worker_job"] = args.worker_job
            if args.tag:
                result.update(tag_verified_commit(api, repo_id, tag, result))
            _, current_tags = refs(api, repo_id)
            tag_matches = current_tags.get(tag) == result['commit']
            if (args.tag or tag in tags) and not tag_matches:
                raise HubIntegrityError('release tag changed during verification; preserve remote state and inspect')
            # Files can pass before tagging, but the destination is not complete until its
            # promised revision resolves to those exact verified bytes.
            result['release_revision_verified'] = result['ok'] and tag_matches
            result['tags'] = sorted(current_tags)
            result['digest_note'] = 'All accepted assets have SHA-256 evidence at the recorded commit.'
            fields = {
                'repo': repo_id, 'revision': tag, 'commit': result['commit'],
                'private': result['repo_private'],
                'verified': result['release_revision_verified'],
                'verified_at': (__import__('datetime').datetime.now(
                    __import__('datetime').timezone.utc).isoformat(timespec='seconds')
                    if result['release_revision_verified'] else None),
                'files_verified': result['digest_verified'],
                **{k: v for k, v in result['files'].items() if k != 'present'},
                'loading_check': (f'verified by collected worker job {args.worker_job}' if args.worker_job
                                  else 'not checked by this command; require the worker loading report'),
            }
            if args.worker_job:
                fields['worker_job'] = args.worker_job
            record_path = PACKAGE / 'DESTINATIONS.json'
            if result['release_revision_verified']:
                record_destination(record_path, 'huggingface', fields, release_tag=tag)
                result['recorded'] = str(record_path.relative_to(REPO_ROOT))
        except Exception as exc:
            # API/download exception strings can contain signed URLs or credential context.
            # Preserve the existing receipt on errors; emit only our own safe refusal messages.
            result['ok'] = False
            if result.get('status') != 'incomplete':
                result['status'] = 'failed'
            result['error'] = str(exc) if isinstance(exc, HubIntegrityError) else type(exc).__name__
            result['next_action'] = 'inspect the remote revision; preserve existing tags; verify again before tagging'
        if result.get('status') == 'incomplete':
            result['next_action'] = 'use --worker-job with a collected publishing job that produced a pinned verification receipt'
        record_attempt(candidate, result)

    print(json.dumps(result, indent=2))
    return 2 if result.get("status") == "incomplete" else (0 if result.get("ok", True) else 1)


if __name__ == "__main__":
    sys.exit(main())
