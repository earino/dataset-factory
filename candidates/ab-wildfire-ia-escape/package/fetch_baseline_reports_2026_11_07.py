#!/usr/bin/env python3
"""Fetch the abwildfire-baseline-002 bounded reports from the private staging
release 437168266 through the worker-written manifest.json (which maps numbered
parts to logical paths), verifying every digest against the collected job
ledger. Bulk data never passes through the coordinator (fetched files are all
< 256 KiB).

Never sends the token to a redirect target on another host."""
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "earino/dataset-factory-staging"
RELEASE = 437168266
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")
OUT = Path("/opt/data/dataset-factory/.factory/abwildfire-baseline-002/output")
MAX_BYTES = 262144

WANTED = ("baseline_result.json", "references-ab-wildfire-ia-escape.json",
          "summary.json", "accept.log", "train.log", "validate.log",
          "references.log", "materialize.log", "container.log")


class NoAuthOnHostChange(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            if urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
                new.remove_header("Authorization")
        return new


def main() -> int:
    token = TOKEN_FILE.read_text().strip()
    opener = urllib.request.build_opener(NoAuthOnHostChange())

    def get(path, accept):
        req = urllib.request.Request(f"https://api.github.com{path}", headers={
            "Authorization": "Bearer " + token, "Accept": accept,
            "User-Agent": "dataset-factory-packaging"})
        with opener.open(req, timeout=120) as response:
            return response.read()

    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/{RELEASE}/assets?per_page=100",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "dataset-factory-packaging"})
    with opener.open(req, timeout=60) as response:
        assets = {a["name"]: a for a in json.loads(response.read().decode())}

    manifest = json.loads(get(
        f"/repos/{REPO}/releases/assets/{assets['manifest.json']['id']}",
        "application/octet-stream"))
    ledger = json.loads(Path("/opt/data/dataset-factory/jobs/abwildfire-baseline-002.json").read_text())
    by_id = {a["id"]: a for a in ledger["result"]["assets"]}
    OUT.mkdir(parents=True, exist_ok=True)

    for entry in manifest.get("assets", []):
        logical = entry.get("file") or entry.get("path") or ""
        if not any(logical == w or logical.endswith("/" + w) for w in WANTED):
            continue
        part = entry["name"]
        asset = assets[part]
        recorded = by_id.get(asset["id"])
        if recorded is None or asset["size"] != recorded["size"] or asset["size"] > MAX_BYTES:
            raise SystemExit(f"{part}: ledger disagrees about size")
        body = get(f"/repos/{REPO}/releases/assets/{asset['id']}",
                   "application/octet-stream")
        if len(body) != entry["size"] or hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise SystemExit(f"{part}: digest mismatch vs the staging manifest")
        if hashlib.sha256(body).hexdigest() != recorded["sha256"]:
            raise SystemExit(f"{part}: digest mismatch vs the job ledger")
        dest = OUT / logical.replace("/", "-")
        dest.write_bytes(body)
        print(f"{logical}: {len(body)} B sha256 {entry['sha256'][:16]}... verified")
    if not (OUT / "baseline_result.json").is_file():
        raise SystemExit("baseline_result.json was not fetched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
