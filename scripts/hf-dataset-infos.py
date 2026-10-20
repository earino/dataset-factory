#!/usr/bin/env python3
"""Write the Hub `dataset_infos.json` that pins column types for a per-target release.

Why this file exists: the Hub infers CSV column types from a sample of each file. In this
artifact `mine_id` and `event_no` are mostly digits but occasionally alphanumeric
(`F015FC6`), so pyarrow inferred `int64` from one block and then failed to cast a later
block - `load_dataset` raised ArrowInvalid on the eval split. A declared schema makes the
loader parse every column as the type the artifact actually uses, instead of guessing.

Identifiers are declared `string` on purpose: `mine_id` is zero-padded (`0100003`) and must
not be read back as `100003`.

Column typing is per candidate. Without `--types-file` the built-in MSHA sets apply, so the
documented MSHA invocation is unchanged; with `--types-file candidates/<id>/hub-schema.json`
the declared sets win ({"string": [...], "float64": [...], "int64": [...]}).

The metas come from the Hub by default (`--meta-source hub`, the MSHA path: the files are on
the Hub by the time the schema is regenerated). `--meta-source github` reads each config's
`meta.json` from the dataset's own GitHub release instead - digest-verified against the
package manifest - so the schema can be generated BEFORE the first Hub upload and ship with
the first one; that is the order that avoids a loading check failing on inferred types.

    python3 scripts/hf-dataset-infos.py --candidate msha-enforcement-citations \
        --token-file /opt/data/.secrets/huggingface-write.token --out /tmp/dataset_infos.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

STRING_COLUMNS = {
    "event_no", "mine_id", "inspection_date", "coal_metal_ind", "mine_type", "state",
    "fips_cnty_cd", "primary_canvass", "company_type", "portable_operation", "activity_code",
    "program_area", "inspect_office_cd",
}
FLOAT_COLUMNS = {"prior_mean_citations"}


def load_types(path):
    """Per-candidate column typing; None keeps the built-in (MSHA) sets."""
    if not path:
        return None
    declared = json.loads(Path(path).read_text())
    for key in ("string", "float64", "int64"):
        if key not in declared or not isinstance(declared[key], list):
            raise SystemExit(f"types file {path} needs a list under '{key}'")
    seen = {}
    for key in ("string", "float64", "int64"):
        for column in declared[key]:
            if column in seen:
                raise SystemExit(f"types file {path} declares '{column}' under both "
                                 f"'{seen[column]}' and '{key}'")
            seen[column] = key
    return declared


def dtype_for(column, label, types=None):
    """dtype for one column.

    With a types file, every feature column must be declared under exactly one of
    string/float64/int64; only the label column may fall through to the int64 default. An
    undeclared feature column once fell through silently to int64, so the Hub `dataset_infos`
    typed the string column `inspection_type` as int64 and `load_dataset` raised ArrowInvalid
    casting 'Canvass' - a whole worker job failed on a schema nobody wrote. Declaring nothing
    is an error, not a guess. Without a types file the built-in (MSHA) sets keep their
    historical default: unlisted columns are int64.
    """
    string_set = (types or {}).get("string", STRING_COLUMNS)
    float_set = (types or {}).get("float64", FLOAT_COLUMNS)
    int_set = (types or {}).get("int64", ())
    matches = [name for name, members in (("string", string_set), ("float64", float_set),
                                          ("int64", int_set)) if column in members]
    if len(matches) > 1:
        raise SystemExit(f"'{column}' is declared under multiple dtype sets: {matches}")
    if matches:
        return matches[0]
    if types is not None and column != label:
        raise SystemExit(f"the types file leaves '{column}' undeclared: every feature column "
                         "must appear under exactly one of string/float64/int64 - undeclared "
                         "columns must not be guessed")
    return "int64"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--package", default=None)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--meta-source", choices=("hub", "github"), default="hub",
                        help="where each config's meta.json is read from")
    parser.add_argument("--github-token-file", default=None,
                        help="publish credential for --meta-source github (never printed)")
    parser.add_argument("--types-file", default=None,
                        help="candidates/<id>/hub-schema.json declaring string/float64/int64 sets")
    args = parser.parse_args()

    package = Path(args.package) if args.package else REPO_ROOT / "release" / args.candidate
    manifest = json.loads((package / "MANIFEST.json").read_text())
    # The manifest records the GitHub URL; the Hub repository is the same owner/name.
    repo = manifest["repository"].rstrip("/").split("github.com/", 1)[-1]
    token = Path(args.token_file).read_text().strip()

    def github_meta(config):
        """Read <config>-meta.json from the dataset's own GitHub release, verified against the
        package manifest's recorded digest - the same bytes the Hub will receive, read where they
        already live so the schema can be generated before the first upload."""
        gh_token = Path(args.github_token_file).read_text().strip() if args.github_token_file \
            else (_ for _ in ()).throw(SystemExit(
                "--meta-source github needs --github-token-file (the publish credential)"))
        tag = manifest["release_tag"]

        def call(url, accept="application/vnd.github+json"):
            request = urllib.request.Request(url, headers={
                "Accept": accept,
                "Authorization": f"Bearer {gh_token}",
                "X-GitHub-Api-Version": "2022-11-28"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()

        release = json.loads(call(f"https://api.github.com/repos/{repo}/releases/tags/{tag}"))
        wanted = f"{config}-meta.json"
        asset = next((a for a in release.get("assets", []) if a["name"] == wanted), None)
        if asset is None:
            raise SystemExit(f"{wanted} is not an asset of release {tag} in {repo}")
        data = call(
            f"https://api.github.com/repos/{repo}/releases/assets/{asset['id']}",
            accept="application/octet-stream")
        expected = (manifest["levels"][config].get("files") or {}).get(f"{config}/meta.json", {})
        if expected.get("sha256") and hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise SystemExit(f"{wanted}: GitHub bytes do not match the manifest digest")
        return json.loads(data)

    metas, features = {}, None
    for config in sorted(manifest["levels"]):
        if args.meta_source == "github":
            meta = github_meta(config)
        else:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(repo, f"{config}-meta.json", repo_type="dataset", token=token)
            meta = json.loads(Path(path).read_text())
        names = [c for c in meta["columns"] if c != meta["target"]]
        if features is None:
            features = names
        elif names != features:
            raise SystemExit(f"{config}: feature list differs from the first config")
        metas[config] = meta
    if not features:
        raise SystemExit("no configs in the manifest")

    types = load_types(args.types_file)
    infos = {}
    for config in sorted(manifest["levels"]):
        label = metas[config]["target"]
        columns = list(features) + [label]
        declared = {column: {"dtype": dtype_for(column, label, types), "_type": "Value"}
                    for column in columns}
        splits = {}
        for split, want in sorted(manifest["levels"][config].get("splits", {}).items()
                                  if isinstance(manifest["levels"][config].get("splits"), dict)
                                  else manifest["splits"].items()):
            if isinstance(want, dict) and "rows" in want:
                splits[split] = {"name": split, "num_examples": want["rows"]}
        infos[config] = {
            "description": metas[config].get("description", ""),
            "citation": metas[config].get("attribution", ""),
            "homepage": "https://earino.github.io/" + repo.split("/")[-1],
            "license": metas[config].get("license", ""),
            "features": declared,
            "post_processed": None,
            "supervised_keys": None,
            "task_templates": None,
            "builder_name": "csv",
            "config_name": config,
            "version": {"version_str": "0.0.1", "major": 0, "minor": 0, "patch": 1},
            "splits": splits,
        }
    Path(args.out).write_text(json.dumps(infos, indent=2) + "\n")
    print(json.dumps({"configs": len(infos), "columns": len(columns), "out": args.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
