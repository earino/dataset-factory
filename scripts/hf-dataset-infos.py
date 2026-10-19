#!/usr/bin/env python3
"""Write the Hub `dataset_infos.json` that pins column types for a per-target release.

Why this file exists: the Hub infers CSV column types from a sample of each file. In this
artifact `mine_id` and `event_no` are mostly digits but occasionally alphanumeric
(`F015FC6`), so pyarrow inferred `int64` from one block and then failed to cast a later
block - `load_dataset` raised ArrowInvalid on the eval split. A declared schema makes the
loader parse every column as the type the artifact actually uses, instead of guessing.

Identifiers are declared `string` on purpose: `mine_id` is zero-padded (`0100003`) and must
not be read back as `100003`.

    python3 scripts/hf-dataset-infos.py --candidate msha-enforcement-citations \
        --token-file /opt/data/.secrets/huggingface-write.token --out /tmp/dataset_infos.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

STRING_COLUMNS = {
    "event_no", "mine_id", "inspection_date", "coal_metal_ind", "mine_type", "state",
    "fips_cnty_cd", "primary_canvass", "company_type", "portable_operation", "activity_code",
    "program_area", "inspect_office_cd",
}
FLOAT_COLUMNS = {"prior_mean_citations"}


def dtype_for(column, label):
    if column == label or column in STRING_COLUMNS:
        return "string" if column in STRING_COLUMNS else "int64"
    if column in FLOAT_COLUMNS:
        return "float64"
    return "int64"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--package", default=None)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    from huggingface_hub import hf_hub_download

    package = Path(args.package) if args.package else REPO_ROOT / "release" / args.candidate
    manifest = json.loads((package / "MANIFEST.json").read_text())
    # The manifest records the GitHub URL; the Hub repository is the same owner/name.
    repo = manifest["repository"].rstrip("/").split("github.com/", 1)[-1]
    token = Path(args.token_file).read_text().strip()

    metas, features = {}, None
    for config in sorted(manifest["levels"]):
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

    infos = {}
    for config in sorted(manifest["levels"]):
        label = metas[config]["target"]
        columns = list(features) + [label]
        declared = {column: {"dtype": dtype_for(column, label), "_type": "Value"}
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
