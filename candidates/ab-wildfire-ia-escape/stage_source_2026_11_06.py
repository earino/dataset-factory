#!/usr/bin/env python3
"""Stage the pinned Alberta wildfire source CSV in the private staging repo.

The publisher (open.alberta.ca) sits behind a Cloudflare managed challenge for
plain HTTP clients (curl 403, measured 2026-11-06), so a worker cannot fetch
the CSV itself. Precedent: source-nhsae-001. This coordinator-side helper
creates a private draft release in earino/dataset-factory-staging and uploads
the sha256-pinned CSV the discovery session fetched through the cleared
browser context. The build job fetches it through the executor's verified
`fetch` mechanism; the container never holds a credential.

Prints the release id, asset id, size and sha256 for job.json. Never prints
the token. One-shot: an existing tag is a refusal, not an overwrite.
"""
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "earino/dataset-factory-staging"
TAG = "source-abwildfire-001"
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")
CSV = Path("/opt/data/cache/scratch/ab-wildfire/fp-historical-wildfire-data-2006-2025.csv")
SHA256 = "8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72"
ASSET_NAME = CSV.name


class NoAuthOnHostChange(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
                new.remove_header("Authorization")
        return new


def api(method: str, url: str, token: str, body: bytes | None = None, data: bytes | None = None,
        content_type: str = "application/json"):
    payload = data if data is not None else body
    request = urllib.request.Request(url, method=method, data=payload, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "dataset-factory-source-staging",
        "Content-Type": content_type,
    })
    with urllib.request.build_opener(NoAuthOnHostChange()).open(request, timeout=300) as response:
        payload = response.read()
    return json.loads(payload) if payload else {}


def main() -> int:
    if not TOKEN_FILE.is_file():
        print(json.dumps({"ok": False, "error": "staging token file missing"}))
        return 1
    token = TOKEN_FILE.read_text().strip()
    if not CSV.is_file():
        print(json.dumps({"ok": False, "error": f"pinned CSV missing at {CSV}"}))
        return 1
    digest = hashlib.sha256(CSV.read_bytes()).hexdigest()
    if digest != SHA256:
        print(json.dumps({"ok": False, "error": f"pinned CSV digest changed: {digest}"}))
        return 1
    size = CSV.stat().st_size
    if size != 10400030:
        print(json.dumps({"ok": False, "error": f"unexpected size {size}"}))
        return 1

    # Refuse to overwrite: a release on this tag means a previous run staged it.
    try:
        existing = api("GET", f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}", token)
        if existing.get("id"):
            print(json.dumps({"ok": False, "error": f"release {TAG} already exists (id {existing['id']}); "
                            "record its asset instead of re-staging"}))
            return 1
    except urllib.error.HTTPError as exc:  # 404 is the expected absence
        if exc.code != 404:
            raise

    release = api("POST", f"https://api.github.com/repos/{REPO}/releases", token,
                  body=json.dumps({
                      "tag_name": TAG,
                      "name": "ab-wildfire-ia-escape pinned source CSV",
                      "body": "fp-historical-wildfire-data-2006-2025.csv, sha256 " + SHA256 + ". "
                              "The pinned publisher fetch measured on the coordinator 2026-11-06 "
                              "(browser channel; open.alberta.ca challenges plain HTTP clients). "
                              "Consumed by the abwildfire-build-001 worker job through the "
                              "executor's verified fetch.",
                      "draft": True, "private": True,
                  }).encode())
    release_id = release["id"]
    upload = api("POST",
                 f"https://uploads.github.com/repos/{REPO}/releases/{release_id}/assets"
                 f"?name={urllib.parse.quote(ASSET_NAME)}",
                 token, data=CSV.read_bytes(),
                 content_type="application/octet-stream")
    asset_id = upload["id"]

    # Read the asset back and re-verify the stored bytes before reporting success.
    check = api("GET", f"https://api.github.com/repos/{REPO}/releases/{release_id}/assets", token)
    entry = next(a for a in check if a["id"] == asset_id)
    redownload = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/assets/{asset_id}",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/octet-stream",
                 "User-Agent": "dataset-factory-source-staging"})
    with urllib.request.build_opener(NoAuthOnHostChange()).open(redownload, timeout=300) as response:
        stored = response.read()
    stored_digest = hashlib.sha256(stored).hexdigest()
    ok = stored_digest == SHA256 and entry["size"] == size and entry["state"] == "uploaded"
    print(json.dumps({
        "ok": ok,
        "release_id": release_id, "tag": TAG, "asset_id": asset_id,
        "asset_name": entry["name"], "size": entry["size"], "state": entry["state"],
        "sha256_verified_on_redownload": stored_digest,
        "expected_sha256": SHA256,
    }, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
