#!/usr/bin/env python3
"""Fetch bounded diagnostics (container.log, manifest.json) for a failed job
from the private staging release, verifying each digest against the job ledger.
Never sends the token to a redirect target on another host."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

REPO = "earino/dataset-factory-staging"
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")


class NoAuthOnHostChange(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            old_host = urllib.parse.urlsplit(req.full_url).netloc
            new_host = urllib.parse.urlsplit(newurl).netloc
            if new_host != old_host:
                new.remove_header("Authorization")
        return new


import urllib.parse  # noqa: E402  (used by the handler above)

def fetch(asset_id: int, dest: Path) -> None:
    token = TOKEN_FILE.read_text().strip()
    url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}"
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/octet-stream",
        "User-Agent": "dataset-factory-diagnostics",
    })
    opener = urllib.request.build_opener(NoAuthOnHostChange())
    with opener.open(req, timeout=120) as response:
        body = response.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    print(f"{dest.name}: {len(body)} B sha256={hashlib.sha256(body).hexdigest()}")


def main() -> int:
    job_id = sys.argv[1]
    base = Path(__file__).resolve().parent
    ledger = json.loads((base.parent.parent / "jobs" / f"{job_id}.json").read_text())
    result = ledger.get("result") or {}
    wanted = {}
    for asset in result.get("assets", []):
        if asset.get("size") == 143 or asset.get("size", 0) < 20000:
            wanted[asset["id"]] = asset
    out_dir = base.parent.parent / ".factory" / job_id / "reports"
    for asset_id, asset in wanted.items():
        dest = out_dir / ("container.log" if asset["size"] == 143 else f"asset-{asset_id}.bin")
        fetch(asset_id, dest)
        body = dest.read_bytes()
        assert hashlib.sha256(body).hexdigest() == asset["sha256"], "digest mismatch"
    log = out_dir / "container.log"
    if log.is_file():
        print("--- container.log ---")
        print(log.read_text(errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
