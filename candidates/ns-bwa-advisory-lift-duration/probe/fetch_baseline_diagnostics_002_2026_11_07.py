#!/usr/bin/env python3
"""Fetch ns-bwa-baseline-002 staging manifest + small report assets (bounded).

Same bounded rules as fetch_diagnostics_002_2026_11_07.py. Run from the repo
root. The worker is already destroyed, so collection happens from the recorded
private staging release 437536802 instead of `worker collect`. Fetches only
the manifest and the small report files the baseline job uploaded (all
asserted <= 256 KiB before download, the largest is ~190 KB); never fetches
a bulk CSV. Every fetched asset is digest-verified against the manifest.
"""
import hashlib
import json
import subprocess
from pathlib import Path

GH = "/opt/data/.local/bin/gh"
OUT = Path("/opt/data/dataset-factory/.factory/ns-bwa-baseline-002")
MAX_BYTES = 256 * 1024
SKIP_LOGICAL = ("source.tar",)

result = json.loads((OUT / "result.json").read_text())
repo = result["repo"]
release = result["release_id"]


def api(path, accept=None):
    cmd = [GH, "api", path]
    if accept:
        cmd += ["-H", f"Accept: {accept}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"api failed {path}: {res.stderr[:300]}")
    return res.stdout


assets = json.loads(api(f"repos/{repo}/releases/{release}/assets?per_page=100"))
by_name = {a["name"]: a for a in assets}
manifest_asset = by_name.get("manifest.json")
if not manifest_asset:
    raise SystemExit("no manifest.json asset in the staging release")
data = api(f"repos/{repo}/releases/assets/{manifest_asset['id']}",
           accept="application/octet-stream")
(OUT / "staged-manifest.json").write_text(data)
manifest = json.loads(data)
print(f"release {release}: {len(assets)} assets; manifest lists "
      f"{len(manifest['assets'])} files")

fetched = []
for entry in manifest["assets"]:
    logical = entry["file"]
    if logical in SKIP_LOGICAL:
        continue
    if entry["size"] > MAX_BYTES:
        raise SystemExit(f"{logical}: {entry['size']} bytes exceeds the "
                         f"{MAX_BYTES} bounded-fetch cap; refusing")
    asset = by_name.get(entry["name"])
    if asset is None:
        raise SystemExit(f"{logical}: asset {entry['name']} missing")
    blob = api(f"repos/{repo}/releases/assets/{asset['id']}",
               accept="application/octet-stream")
    digest = hashlib.sha256(blob.encode()).hexdigest()
    if digest != entry["sha256"]:
        raise SystemExit(f"{logical}: digest mismatch {digest} vs "
                         f"{entry['sha256']}")
    (OUT / entry["name"]).write_text(blob)
    fetched.append((logical, entry["size"], digest[:16]))

print("fetched (digest-verified):")
for logical, size, digest in sorted(fetched):
    print(f"  {logical}: {size} bytes {digest}...")
