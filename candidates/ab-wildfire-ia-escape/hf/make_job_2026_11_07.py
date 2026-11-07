#!/usr/bin/env python3
"""Generate the hf_publish worker job for ab-wildfire-ia-escape.

Asset ids and digests are resolved programmatically: digests come from the
frozen MANIFEST.json, ids from the live GitHub release API by name AND
digest match (the cpcb-aqi-hf-001 lesson: a one-character hand-typed digest
kills the job at the fetch, on a paid worker). The verify_loading block is
derived from the release package's own recorded facts - split row/positive
counts from MANIFEST.json, the shipped columns and the label from
measurements.json - never restated by hand.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
REL = ROOT / "release" / "ab-wildfire-ia-escape"
SOURCE_REPO = "earino/ab-wildfire-ia-escape"
RELEASE_ID = 437179999
TAG = "v2026.11"
DEST = ROOT / "candidates" / "ab-wildfire-ia-escape" / "hf" / "job.json"


def gh(path):
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"gh api {path} failed: {done.stderr[:300]}")
    return json.loads(done.stdout)


def main() -> int:
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    measurements = json.loads((REL / "measurements.json").read_text())
    assets_block = manifest["assets"]

    repo = gh(f"repos/{SOURCE_REPO}")
    assert repo["private"] is True, "the source repository must be private"
    release = gh(f"repos/{SOURCE_REPO}/releases/{RELEASE_ID}")
    assert release["tag_name"] == TAG and release["draft"] is False
    listed = {a["name"]: a for a in release["assets"]}
    assert set(listed) == {info["asset_name"] for info in assets_block.values()}, \
        f"live assets {sorted(listed)} do not match the manifest"

    hf_assets = []
    for logical in sorted(assets_block):
        info = assets_block[logical]
        asset = listed[info["asset_name"]]
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        assert asset["size"] == info["bytes"], f"{logical}: live size != manifest"
        assert digest == info["sha256"], f"{logical}: live digest != manifest digest"
        target = f"data/{info['asset_name']}" if logical.endswith(".csv") else info["asset_name"]
        hf_assets.append({"asset_id": asset["id"],
                          "dest": info["asset_name"],
                          "target": target,
                          "size": info["bytes"],
                          "sha256": info["sha256"]})

    splits_manifest = manifest["splits"]
    columns = measurements["column_policy"]["shipped"]
    label = manifest["dataset"]["target"] if isinstance(manifest.get("dataset"), dict) else None
    if not label:
        label = json.loads((REL / "meta.json").read_text())["target"]
    verify_loading = {
        "splits": {name: {"rows": splits_manifest[name]["rows"],
                          "positives": splits_manifest[name]["positives"]}
                   for name in ("train", "eval", "holdout")},
        "columns": columns,
        "label": label,
        "label_values": [0, 1],
    }

    job = {
        "id": "abwildfire-hf-001",
        "candidate": "ab-wildfire-ia-escape",
        "release": True,
        "server_type": "cx23",
        "location": "hel1",
        "cpus": 2,
        "memory_mb": 4096,
        "timeout_minutes": 40,
        "lifetime_minutes": 60,
        "max_disk_mb": 4000,
        "max_artifact_mb": 8,
        "what": ("Complete pinned verification of the ab-wildfire-ia-escape artifact "
                 "c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2 on the "
                 "private Hugging Face repo earino/ab-wildfire-ia-escape: fetch all five "
                 "released files from the private GitHub release 437179999 at their recorded "
                 "asset ids (digests equal to the package MANIFEST.json, resolved by digest "
                 "match through the live release API), verify each sha256 on arrival, upload "
                 "each with the Hub-reported digest verified after upload, delete the local "
                 "copy, and run the documented load_dataset path against the uploaded bytes "
                 "(splits, columns, label values as recorded in the manifest). The bytes "
                 "never pass through the coordinator; peak worker disk is one asset "
                 "(4.1 MB total)."),
        "stopping_condition": ("a digest mismatch at fetch or after upload fails the job with "
                              "diagnostics uploaded; a partial upload is reconciled by digest "
                              "in the next deliberately planned attempt, never by re-running "
                              "blind; the Hub repository must be created private and the flip "
                              "remains the operator's single approval"),
        "hf_publish": {
            "repo": "earino/ab-wildfire-ia-escape",
            "revision": "main",
            "source_repo": SOURCE_REPO,
            "assets": hf_assets,
            "verify_loading": verify_loading,
        },
    }
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(job, indent=1) + "\n")
    print(f"wrote {DEST}")
    for asset in hf_assets:
        print(f"  {asset['dest']} -> {asset['target']}: asset_id {asset['asset_id']} "
              f"{asset['size']} B sha256 {asset['sha256'][:16]}...")
    print(f"  verify_loading: {json.dumps(verify_loading['splits'])}")
    print(f"  label: {label}; {len(columns)} shipped columns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
