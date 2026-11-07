#!/usr/bin/env python3
"""Generate the fresh-consumer job.json for ab-wildfire-ia-escape.

Digests are copied programmatically from the frozen MANIFEST.json (never
hand-typed: cpcb-aqi-consumer-001 died pre-container on a one-character
digest transcription error at position 36 of public/eval.csv). The release
asset ids are resolved live from the GitHub API by name AND digest match, so
the fetch spec can only name assets that are server-side digest-equal to the
frozen manifest. Asserts the destination stays private before writing.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
REL = ROOT / "release" / "ab-wildfire-ia-escape"
REPO = "earino/ab-wildfire-ia-escape"
RELEASE_ID = 437179999
TAG = "v2026.11"
DEST = ROOT / "candidates" / "ab-wildfire-ia-escape" / "consumer" / "source" / "job.json"


def gh(path):
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"gh api {path} failed: {done.stderr[:300]}")
    return json.loads(done.stdout)


def main() -> int:
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    assets_block = manifest["assets"]          # logical path -> {asset_name, bytes, sha256}

    repo = gh(f"repos/{REPO}")
    assert repo["private"] is True, "the destination repository must be private"
    release = gh(f"repos/{REPO}/releases/{RELEASE_ID}")
    assert release["tag_name"] == TAG and release["draft"] is False
    listed = {a["name"]: a for a in release["assets"]}
    assert set(listed) == {info["asset_name"] for info in assets_block.values()}, \
        f"live assets {sorted(listed)} do not match the manifest"

    fetch_assets = []
    for logical in sorted(assets_block):
        info = assets_block[logical]
        asset = listed[info["asset_name"]]
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        assert asset["size"] == info["bytes"], f"{logical}: live size {asset['size']} != manifest {info['bytes']}"
        assert digest == info["sha256"], f"{logical}: live digest != manifest digest"
        fetch_assets.append({"asset_id": asset["id"],
                             "dest": logical,
                             "size": info["bytes"],
                             "sha256": info["sha256"]})

    job = {
        "id": "abwildfire-consumer-001",
        "candidate": "ab-wildfire-ia-escape",
        "release": True,
        "image": "python:3.13-slim",
        "server_type": "cx23",
        "location": "hel1",
        "cpus": 2,
        "memory_mb": 4096,
        "timeout_minutes": 40,
        "lifetime_minutes": 60,
        "max_disk_mb": 8000,
        "max_artifact_mb": 8,
        "what": ("Fresh-consumer verification of the ab-wildfire-ia-escape v2026.11 private "
                 "release (artifact "
                 "c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2): the worker "
                 "host fetches the five released assets from earino/ab-wildfire-ia-escape "
                 "release 437179999 with digest verification (the container holds no "
                 "credential), then the container runs every published REPRODUCE.md step "
                 "against the released bytes - package-vs-MANIFEST check, get_dataset.py "
                 "verification, sha256sum -c, gate 1.5.0 re-run on the full artifact, "
                 "exact-byte --accept against the shipped qualification.json, declared "
                 "dependency imports, baseline reproduce (both AUC prints 0.9554, CONTRACT "
                 "OK, holdout never copied into a workdir), score.py references recomputed "
                 "equal to measurements.json (fixed-seed CIs reproduce exactly) - and "
                 "additionally recomputes the pre-registered deciding check measurements.json "
                 "records (model-minus-persistence [0.0154, 0.0871], model-minus-calendar "
                 "[0.1911, 0.2998], model AUC CI [0.9382, 0.9686] entirely above 0.5, verdict "
                 "headroom_demonstrated) from the released bytes through the shipped "
                 "baseline/train.py and code/score.py, never reimplemented. The optional "
                 "rebuild-from-source step is not run: it needs the pinned 10.4 MB publisher "
                 "CSV, code/build.py refuses any other source, and REPRODUCE.md documents it "
                 "as optional. Bytes never pass through the coordinator."),
        "stopping_condition": ("any digest mismatch at fetch fails the job before the "
                               "container starts; a gate failure, acceptance failure, baseline "
                               "mismatch, reference mismatch or deciding-check mismatch fails "
                               "at that step with diagnostics uploaded - none of them is a "
                               "retry trigger and no figure may be quoted from a failed stage; "
                               "the target repository must stay private and the flip remains "
                               "the operator's single approval"),
        "fetch": {
            "repo": REPO,
            "release": RELEASE_ID,
            "assets": fetch_assets,
        },
    }
    DEST.write_text(json.dumps(job, indent=1) + "\n")
    print(f"wrote {DEST}")
    for asset in fetch_assets:
        print(f"  {asset['dest']}: asset_id {asset['asset_id']} "
              f"{asset['size']} B sha256 {asset['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
