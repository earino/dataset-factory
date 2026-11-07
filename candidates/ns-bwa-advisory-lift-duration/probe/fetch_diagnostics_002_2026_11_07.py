#!/usr/bin/env python3
"""Fetch ns-bwa-002 staging manifest + small diagnostic assets (bounded).

Same bounded rules as the dvsa-mot fetch probes. Run from the repo root
AFTER `sh scripts/scout-factory worker collect ns-bwa-002`. Never fetches
the extract CSVs or source.tar: only the manifest and the small report
files (summary, qualification, acceptance, references, container.log),
each asserted <= 2 MB before download. The bulk extract stays in staging
for the baseline job to fetch worker-side.
"""
import hashlib
import json
import subprocess
from pathlib import Path

GH = "/opt/data/.local/bin/gh"
OUT = Path("/opt/data/dataset-factory/.factory/ns-bwa-002")
MAX_BYTES = 2 * 1024 * 1024
WANT_PREFIX = ("summary.json", "qualification-", "acceptance-",
               "references-", "container.log")
SKIP = ("source.tar",)

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
    stripped = logical.removeprefix("output/")
    if logical in SKIP or stripped.startswith("extract/"):
        continue
    if not any(stripped.startswith(p) for p in WANT_PREFIX):
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

# also print the extract asset identities the baseline job will fetch
print("extract assets for the baseline fetch block:")
for entry in manifest["assets"]:
    if entry["file"].startswith("output/extract/"):
        print(f"  {entry['file']}: asset_id={by_name[entry['name']]['id']} "
              f"size={entry['size']} sha256={entry['sha256']}")
