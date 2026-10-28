#!/usr/bin/env python3
"""Download this dataset's release assets, verify them, and lay them out for the runner.

GitHub release asset names cannot contain `/`, so the five assets are flat
(`public-train.csv`, ...) and this script restores the layout the benchmark expects:

    <dest>/public/train.csv
    <dest>/public/eval.csv
    <dest>/private/holdout.csv
    <dest>/meta.json
    <dest>/quality.json

Every file is checked against the release's own recorded size and against `SHA256SUMS`,
so a download that does not match is refused rather than silently used.

While the repository is private (under review) the script needs `GITHUB_TOKEN` or an
authenticated `gh` CLI and downloads through the API's asset path; once the release is
public no credential is needed and the plain download URL works.

    python3 get_dataset.py --dest ./task

The equivalent by hand:

    gh release download v2026.10 --repo earino/ec-merger-phase2-opening --dir ./flat
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "earino/ec-merger-phase2-opening"
TAG = "v2026.10"
# flat asset name -> destination relative to --dest
LAYOUT = {
    "public-train.csv": "public/train.csv",
    "public-eval.csv": "public/eval.csv",
    "private-holdout.csv": "private/holdout.csv",
    "meta.json": "meta.json",
    "quality.json": "quality.json",
}
# Recorded at packaging time from the gate's artifact block; the manifest is the authority.
EXPECTED = {
    "public-train.csv": {"bytes": 429048,
                         "sha256": "1619b6f4ad4a7dab0f437335c231f727f6f5c5f0ea02b3454366f5a71ab90a44"},
    "public-eval.csv": {"bytes": 155077,
                         "sha256": "4fb28c0908e4c79ccf194de3b27f2996c05efc0f01ec4074c953a7eb697f24f6"},
    "private-holdout.csv": {"bytes": 253649,
                         "sha256": "5867e34f3ebf714b9ec0ef307989cb4296438148390a6a5ea2bcf88795f703fd"},
    "meta.json": {"bytes": 1342,
                         "sha256": "b139620d5f469c17faa974574220878f8c1f70accf6d975243a018049fae5ef9"},
    "quality.json": {"bytes": 21855,
                         "sha256": "0203fdf934a0564fdb8d2910372986424547f25448fd603a79e95d4ac02fb7ec"},
}
URL = "https://github.com/{repo}/releases/download/{tag}/{name}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _stream(url: str, target: Path, headers: dict | None = None) -> None:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)


def _asset_id(name: str, token: str) -> int:
    """Resolve a release asset id through the API.

    The `github.com/<repo>/releases/download/...` URL does not serve assets of a **private**
    repository to a token-authenticated client - it answers 404 - so a private download has to go
    through the API's asset endpoint, which returns the bytes with
    `Accept: application/octet-stream`. Measured 2026-10-21 on the who-flunet release; the same
    applies here while this repository is private.
    """
    meta = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"
    request = urllib.request.Request(meta, headers={"Authorization": f"Bearer {token}",
                                                    "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.loads(response.read().decode())
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset["id"]
    raise SystemExit(f"{name}: not present in release {TAG} of {REPO}")


def fetch(name: str, target: Path, token: str | None) -> None:
    try:
        if token:
            asset_id = _asset_id(name, token)
            _stream(f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}", target,
                    {"Authorization": f"Bearer {token}",
                     "Accept": "application/octet-stream"})
        else:
            _stream(URL.format(repo=REPO, tag=TAG, name=name), target)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{name}: HTTP {exc.code} - the release may be private; set GITHUB_TOKEN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", default="./task", help="dataset directory to create")
    parser.add_argument("--tag", default=TAG, help="release tag (default: the published one)")
    args = parser.parse_args()

    dest = Path(args.dest)
    token = os.environ.get("GITHUB_TOKEN")
    total = 0
    for name, relative in sorted(LAYOUT.items()):
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = EXPECTED[name]
        if target.is_file() and target.stat().st_size == expected["bytes"] \
                and sha256_of(target) == expected["sha256"]:
            print(f"  {relative}: already present and matching")
            total += expected["bytes"]
            continue
        print(f"  {relative}: downloading {name}")
        fetch(name, target, token)
        size, digest = target.stat().st_size, sha256_of(target)
        if size != expected["bytes"] or digest != expected["sha256"]:
            raise SystemExit(
                f"{relative}: got {size} B sha256 {digest[:16]}..., "
                f"expected {expected['bytes']} B {expected['sha256'][:16]}...")
        total += size
    print(f"downloaded and verified {len(LAYOUT)} files, {total} bytes, into {dest}")
    manifest = dest / "meta.json"
    if manifest.is_file():
        meta = json.loads(manifest.read_text())
        print(f"task: {meta['name']} target={meta['target']} rows={meta['rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
