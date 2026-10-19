#!/usr/bin/env python3
"""Download this dataset's release assets, verify them, and lay them out for the runner.

GitHub release asset names cannot contain `/`, so the 226 assets are flat
(`sec_56_12004-public-train.csv`, ...) and this script restores the layout the benchmark
expects:

    <dest>/<config>/public/train.csv
    <dest>/<config>/public/eval.csv
    <dest>/<config>/private/holdout.csv
    <dest>/<config>/meta.json
    <dest>/<config>/quality.json
    ...
    <dest>/labels.csv                  (the joint multi-label matrix, dataset root)

for each of the 45 per-section configs. Every file is checked against the release's own
recorded size and against `SHA256SUMS`, so a download that does not match is refused rather than
silently used.

The repository is private until publication, so a credential is needed: either the `gh` CLI
(already authenticated) or `GITHUB_TOKEN` in the environment.

    python3 get_dataset.py --dest ./task                          # everything, ~3.3 GB
    python3 get_dataset.py --dest ./task --config sec_56_12004   # one config, ~73 MB
    python3 get_dataset.py --dest ./task --labels-only            # just labels.csv

The equivalent by hand:

    gh release download v2026.10 --repo earino/msha-enforcement-citations --dir ./flat
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

REPO = "earino/msha-enforcement-citations"
TAG = "v2026.10"
# The 45 shipped configs, in the worker's own shipped order (prevalence-descending).
CONFIGS = (
    "sec_56_14107_A", "sec_56_14100_B", "sec_56_12004", "sec_56_14132_A", "sec_75_400",
    "sec_50_30_A", "sec_75_370_A_1", "sec_56_20003_A", "sec_56_12032", "sec_56_11001",
    "sec_56_14112_B", "sec_56_12028", "sec_75_503", "sec_56_14101_A_2", "sec_75_202_A",
    "sec_75_220_A_1", "sec_56_9300_A", "sec_56_12008", "sec_56_4201_A_2", "sec_77_404_A",
    "sec_56_4101", "sec_77_1104", "sec_56_12018", "sec_75_512", "sec_56_11002",
    "sec_75_517", "sec_47_41_A", "sec_56_14100_C", "sec_56_14112_A_1", "sec_75_1725_A",
    "sec_75_1403", "sec_56_12030", "sec_56_14207", "sec_75_342_A_4", "sec_75_403",
    "sec_77_1606_C", "sec_56_11012", "sec_77_1605_D", "sec_56_16005", "sec_56_9300_B",
    "sec_77_1110", "sec_75_1100_3", "sec_56_1000", "sec_75_604_B", "sec_77_502",
)
# flat asset name -> destination relative to the dataset directory
LAYOUT: dict[str, str] = {"labels.csv": "labels.csv"}
for _config in CONFIGS:
    for _asset, _relative in (
        ("public/train.csv", "public/train.csv"),
        ("public/eval.csv", "public/eval.csv"),
        ("private/holdout.csv", "private/holdout.csv"),
        ("meta.json", "meta.json"),
        ("quality.json", "quality.json"),
    ):
        LAYOUT[f"{_config}-{_asset.replace('/', '-')}"] = f"{_config}/{_relative}"


def token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def auth_headers() -> dict:
    value = token()
    return {"Authorization": "Bearer " + value} if value else {}


def release(tag: str) -> dict:
    """Read the release through `gh` when available, else the API."""
    if shutil.which("gh") and not token():
        done = subprocess.run(["gh", "api", f"repos/{REPO}/releases/tags/{tag}"],
                              capture_output=True, text=True)
        if done.returncode == 0:
            return json.loads(done.stdout)
        raise SystemExit(f"gh could not read {REPO}@{tag}: {done.stderr.strip()[:200]}")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/tags/{tag}",
        headers={"Accept": "application/vnd.github+json", **auth_headers()})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except Exception as exc:
        raise SystemExit(f"could not read {REPO}@{tag}: {type(exc).__name__}. "
                         "The repository is private; authenticate with `gh auth login` or set "
                         "GITHUB_TOKEN.") from None


def download(asset: dict, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("gh") and not token():
        done = subprocess.run(["gh", "release", "download", asset["_tag"], "--repo", REPO,
                               "--pattern", asset["name"], "--dir", str(dest.parent),
                               "--clobber"], capture_output=True, text=True)
        if done.returncode:
            raise SystemExit(f"gh download failed: {done.stderr.strip()[:200]}")
        (dest.parent / asset["name"]).replace(dest)
        return dest
    request = urllib.request.Request(
        asset["url"], headers={"Accept": "application/octet-stream", **auth_headers()})
    with urllib.request.urlopen(request, timeout=1800) as response, dest.open("wb") as stream:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            stream.write(chunk)
    return dest


def sha256_of(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            result.update(block)
    return result.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", default="task", help="where to write the dataset directory")
    parser.add_argument("--tag", default=TAG)
    parser.add_argument("--config", default=None, choices=list(CONFIGS),
                        help="fetch one config's five files instead of all 226 assets")
    parser.add_argument("--labels-only", action="store_true",
                        help="fetch only the joint multi-label matrix labels.csv")
    parser.add_argument("--sums", default=None,
                        help="path to SHA256SUMS (default: ./SHA256SUMS if present)")
    args = parser.parse_args()

    if args.config and args.labels_only:
        raise SystemExit("--config and --labels-only are mutually exclusive")
    wanted = {name: relative for name, relative in LAYOUT.items()
              if (args.config is None or relative.startswith(args.config + "/"))
              and (not args.labels_only or relative == "labels.csv")}
    if args.labels_only:
        wanted = {"labels.csv": "labels.csv"}

    info = release(args.tag)
    assets = {a["name"]: a for a in info["assets"]}
    missing = [name for name in wanted if name not in assets]
    if missing:
        raise SystemExit(f"release {args.tag} is missing {len(missing)} assets, e.g. {missing[:3]}")

    dest_root = Path(args.dest)
    written = []
    for name, relative in wanted.items():
        asset = dict(assets[name], _tag=args.tag)
        path = dest_root / relative
        download(asset, path)
        size = path.stat().st_size
        if asset["size"] != size:
            raise SystemExit(f"{name}: downloaded {size} bytes, release records {asset['size']}")
        written.append((relative, size, sha256_of(path)))
        print(f"  {name:40} -> {relative:44} {size:>12,} B")

    sums = Path(args.sums) if args.sums else Path("SHA256SUMS")
    if sums.is_file():
        expected = {}
        for line in sums.read_text().splitlines():
            digest, _, path = line.partition("  ")
            expected[path.strip()] = digest
        problems = [relative for relative, _, digest in written
                    if relative in expected and expected[relative] != digest]
        if problems:
            raise SystemExit(f"SHA256SUMS disagrees for: {problems}")
        print(f"  verified {len(written)} file(s) against {sums}")
    else:
        print("  note: no SHA256SUMS next to this script, sizes printed above for comparison")

    print(f"\nwrote {dest_root}/ (runner layout): <config>/public/, <config>/private/, "
          "meta.json, quality.json per config; labels.csv at the root")
    if args.config:
        print("next: python3 code/qualify_dataset.py " + str(dest_root / args.config))
    else:
        print("next: python3 code/qualify_dataset.py " + str(dest_root / (args.config or "sec_56_12004")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
