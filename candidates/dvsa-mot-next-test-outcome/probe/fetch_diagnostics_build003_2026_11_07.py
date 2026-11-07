#!/usr/bin/env python3
"""Fetch dvsa-mot-build-003 staging manifest + small diagnostic assets (bounded).

Same bounded rules as fetch_diagnostics_2026_11_07.py (written for
build-002), pointed at the build-003 staging directory. Run from the repo
root AFTER `sh scripts/scout-factory worker collect dvsa-mot-build-003`.
Never fetches the extract CSVs or source.tar: only the manifest and the
small report files (summary, qualification, acceptance, references,
container.log), each asserted <= 2 MB before download. The bulk extract
stays in staging for the baseline job to fetch worker-side.
"""
import hashlib
import json
import subprocess
from pathlib import Path

GH = "/opt/data/.local/bin/gh"
OUT = Path("/opt/data/dataset-factory/.factory/dvsa-mot-build-003")
MAX_BYTES = 2 * 1024 * 1024
WANT_PREFIX = ("summary.json", "qualification-", "acceptance-", "references-",
               "container.log")
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
    if logical in SKIP or logical.startswith("extract/"):
        continue
    if not any(logical.startswith(p) for p in WANT_PREFIX):
        continue
    if entry["size"] > MAX_BYTES:
        raise SystemExit(f"{logical}: {entry['size']} bytes exceeds the "
                         f"{MAX_BYTES} bounded-fetch cap; refusing")
    asset = by_name[entry["name"]]
    if asset["size"] != entry["size"] or \
            asset.get("digest") != "sha256:" + entry["sha256"]:
        raise SystemExit(f"{logical}: live asset size/digest mismatch")
    blob = api(f"repos/{repo}/releases/assets/{asset['id']}",
               accept="application/octet-stream")
    dest = OUT / f"staged-{logical.replace('/', '__')}"
    dest.write_text(blob)
    fetched.append((logical, len(blob)))
    print("saved", dest.name, len(blob), "bytes")

for logical, size in fetched:
    entry = [e for e in manifest["assets"] if e["file"] == logical][0]
    blob = (OUT / f"staged-{logical.replace('/', '__')}").read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    ok = digest == entry["sha256"] and size == entry["size"]
    print(f"digest-check {logical}: {'OK' if ok else 'MISMATCH'}")
    if not ok:
        raise SystemExit(f"{logical}: fetched bytes do not hash to the manifest")
print("bounded diagnostics fetch complete")
