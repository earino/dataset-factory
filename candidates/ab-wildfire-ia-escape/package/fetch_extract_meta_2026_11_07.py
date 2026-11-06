#!/usr/bin/env python3
"""Fetch the abwildfire-build-001 extract's compact metadata (meta.json,
quality.json) from the private staging release 437132110, verifying each
digest against the collected job ledger. Bulk data never passes through the
coordinator; these two files are 1,217 B and 21,089 B.

Never sends the token to a redirect target on another host."""
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "earino/dataset-factory-staging"
RELEASE = 437132110
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")
OUT = Path("/opt/data/dataset-factory/.factory/abwildfire-build-001/reports")

WANTED = {
    718800868: ("meta.json", 1217,
                "aeb2ef927fc0d8565a86a6901afe5ee29359787bb39693342d18ce6850a9bcfb"),
    718801140: ("quality.json", 21089,
                "331a4ceb0944d33b80b0a6519c0148603b19b4fff1ae5136571ae3126cff3ec1"),
}


class NoAuthOnHostChange(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            old_host = urllib.parse.urlsplit(req.full_url).netloc
            new_host = urllib.parse.urlsplit(newurl).netloc
            if new_host != old_host:
                new.remove_header("Authorization")
        return new


def main() -> int:
    token = TOKEN_FILE.read_text().strip()
    opener = urllib.request.build_opener(NoAuthOnHostChange())
    ledger = json.loads(Path("/opt/data/dataset-factory/jobs/abwildfire-build-001.json").read_text())
    by_id = {a["id"]: a for a in ledger["result"]["assets"]}
    OUT.mkdir(parents=True, exist_ok=True)
    for asset_id, (name, size, digest) in sorted(WANTED.items()):
        entry = by_id.get(asset_id)
        if entry is None or entry["sha256"] != digest or entry["size"] != size:
            raise SystemExit(f"ledger disagrees about asset {asset_id} ({name})")
        url = f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}"
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/octet-stream",
            "User-Agent": "dataset-factory-packaging",
        })
        with opener.open(req, timeout=120) as response:
            body = response.read()
        if len(body) != size or hashlib.sha256(body).hexdigest() != digest:
            raise SystemExit(f"{name}: digest/size mismatch on fetch")
        (OUT / name).write_bytes(body)
        print(f"{name}: {len(body)} B sha256 {digest[:16]}... verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
