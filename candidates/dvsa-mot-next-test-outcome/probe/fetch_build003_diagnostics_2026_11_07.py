#!/usr/bin/env python3
"""Fetch dvsa-mot-build-003's small diagnostic assets (bounded, one-off).

build-003 failed at 2018 before writing summary.json, and its diagnostics
were diagnosed directly from the staging release; the local .factory dir kept
only result.json. The deterministic cross-check for build-004 needs build-003's
container.log as the chain source for the 2017 receipt (38,056,161 /
35,983,938 / 35,975 - the first zip-era year ever parsed), so this script
fetches the small diagnostic assets of staging release 437475493,
digest-verifying each against the collected result.json (never hand-typed).

Staging assets are flat numbered parts, so logical names come from the staging
manifest.json asset itself. Only assets under SMALL_CAP (100 KB) are fetched:
container.log (3,344 B) and manifest.json (4,412 B) qualify; source.tar
(235,520 B, part file-0000-part-0000) is never downloaded. Classification is
by content with a refuse-to-guess rule.
"""
import hashlib
import json
import subprocess
from pathlib import Path

GH = "/opt/data/.local/bin/gh"
OUT = Path("/opt/data/dataset-factory/.factory/dvsa-mot-build-003")
SMALL_CAP = 100 * 1024

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


saved = {}
for meta in result["assets"]:
    if meta["size"] > SMALL_CAP:
        print(f"skip asset {meta['id']} ({meta['size']} B > small cap)")
        continue
    blob = api(f"repos/{repo}/releases/assets/{meta['id']}",
               accept="application/octet-stream").encode()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != meta["sha256"] or len(blob) != meta["size"]:
        raise SystemExit(f"asset {meta['id']}: fetched bytes disagree with "
                         f"the collected result.json digest")
    stripped = blob.lstrip()
    if stripped.startswith(b"{"):
        parsed = json.loads(blob)
        if "assets" in parsed and "job" in parsed:
            dest = OUT / "staged-manifest.json"
        else:
            raise SystemExit(f"asset {meta['id']}: unexpected JSON, refusing")
    elif b"rows_seen=" in blob:
        dest = OUT / "staged-container.log"
    else:
        raise SystemExit(f"asset {meta['id']}: unexpected content, refusing")
    dest.write_bytes(blob)
    saved[dest.name] = len(blob)
    print("saved", dest.name, len(blob), "bytes (digest OK)")

assert "staged-container.log" in saved, "container.log asset not found"
assert "staged-manifest.json" in saved, "staging manifest asset not found"

manifest = json.loads((OUT / "staged-manifest.json").read_text())
parts = {e["name"]: e["file"] for e in manifest["assets"]}
if parts.get("file-0000-part-0000") != "source.tar":
    raise SystemExit(f"unexpected part map: {parts}")
log = (OUT / "staged-container.log").read_text()
years = [ln[:4] for ln in log.splitlines()
         if ln[:4].isdigit() and ln[4:6] == ": " and "rows_seen=" in ln]
print("container.log receipt years:", years)
if "2017" not in years:
    raise SystemExit("2017 receipt missing from build-003 container.log")
print("bounded build-003 diagnostics fetch complete")
