#!/usr/bin/env python3
"""Fetch the small report assets of the camara-001 staging release into
.factory/camara-001/reports/ (bulk CSVs skipped), verifying each sha256
against the release's own manifest. Read-only against the private staging
release; no bulk data touches the coordinator.
"""
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO = "earino/dataset-factory-staging"
RELEASE = 421522080
DEST = Path(__file__).resolve().parents[2] / ".factory" / "camara-001" / "reports"
LIMIT = 256 * 1024  # 256 KiB report ceiling


def token():
    path = os.environ.get("FACTORY_GITHUB_TOKEN_FILE") or "/opt/data/.secrets/github-staging.token"
    return Path(path).read_text().strip()


def api(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}",
                                 headers={"Authorization": f"Bearer {token()}",
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "dataset-factory/collect"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # surface the 302 so the caller can fetch it without auth


def download(asset_id, dest: Path):
    """Two-step download: ask the API for the asset (auth header), read the
    302 Location, then fetch the signed URL with NO auth header (the token
    never reaches the storage host)."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}",
        headers={"Authorization": f"Bearer {token()}",
                 "Accept": "application/octet-stream",
                 "User-Agent": "dataset-factory/collect"})
    try:
        with opener.open(req, timeout=120) as resp:
            dest.write_bytes(resp.read())
            return
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        location = error.headers.get("Location")
    if not location:
        raise SystemExit(f"no redirect Location for asset {asset_id}")
    bare = urllib.request.Request(location,
                                  headers={"User-Agent": "dataset-factory/collect"})
    with urllib.request.urlopen(bare, timeout=180) as resp:
        dest.write_bytes(resp.read())


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    release = api(f"releases/{RELEASE}")
    manifest_asset = None
    for asset in release["assets"]:
        if asset["name"] == "manifest.json":
            manifest_asset = asset
    if manifest_asset is None:
        raise SystemExit("release manifest.json not found")
    download(manifest_asset["id"], DEST / "manifest.json")
    manifest = json.loads((DEST / "manifest.json").read_text())
    entries = manifest.get("files") or manifest.get("assets") or []
    index = {entry.get("path") or entry.get("name"): entry for entry in entries}
    fetched, skipped = [], []
    for name, entry in sorted(index.items()):
        size = entry.get("size") or 0
        if size > LIMIT:
            skipped.append((name, size))
            continue
        asset = next((a for a in release["assets"]
                      if a["name"] == entry.get("name") or a["name"] == name), None)
        if asset is None:
            skipped.append((name, "no asset"))
            continue
        target = DEST / Path(str(name)).name
        download(asset["id"], target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        expected = entry.get("sha256")
        status = "OK" if digest == expected else f"MISMATCH {digest[:12]}"
        fetched.append((str(name), len(target.read_bytes()), status))
    print(json.dumps({"fetched": fetched, "skipped_bulk": skipped}, indent=1))


if __name__ == "__main__":
    main()
