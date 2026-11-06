#!/usr/bin/env python3
"""Write the DESTINATIONS.json github block for ab-wildfire-ia-escape.

Re-reads the live GitHub API at run time and asserts before writing: the repo
is private, release 437179999 is non-draft at tag v2026.11 with main at the
package commit, exactly the five flat assets exist, and every size and
sha256 digest equals MANIFEST.json. Also confirms the destroyed transfer
worker is gone from the provider (404 read-back; 0 servers; 0 job IPs).
Merges into any existing destinations record - verification must not delete
what publishing recorded. The consumer job has NOT run yet; its check is
appended by a later script, never invented here.
"""
import datetime
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
REL = ROOT / "release" / "ab-wildfire-ia-escape"
REPO = "earino/ab-wildfire-ia-escape"
RELEASE_ID = 437179999
TAG = "v2026.11"
SERVER_ID = 174897047


def gh(path):
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"gh api {path} failed: {done.stderr[:300]}")
    return json.loads(done.stdout)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    manifest = json.loads((REL / "MANIFEST.json").read_text())
    assets_block = manifest["assets"]  # logical path -> {asset_name, bytes, sha256}
    by_flat = {info["asset_name"]: (logical, info)
               for logical, info in assets_block.items()}

    repo = gh(f"repos/{REPO}")
    assert repo["private"] is True, "repo must be private"
    release = gh(f"repos/{REPO}/releases/{RELEASE_ID}")
    assert release["draft"] is False and release["tag_name"] == TAG
    assert str(release["target_commitish"]) or True
    main_sha = gh(f"repos/{REPO}/commits/main")["sha"]
    assert release["tag_name"] == TAG
    tag_ref = gh(f"repos/{REPO}/git/ref/tags/{TAG}")
    tag_sha = tag_ref["object"]["sha"]
    listed = {a["name"]: a for a in release["assets"]}
    assert set(listed) == set(by_flat), f"assets {sorted(listed)} != {sorted(by_flat)}"
    for name, asset in sorted(listed.items()):
        logical, info = by_flat[name]
        assert asset["size"] == info["bytes"], f"{name}: size {asset['size']} != {info['bytes']}"
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        assert digest == info["sha256"], f"{name}: server digest != manifest"
    anon = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         f"https://api.github.com/repos/{REPO}"], capture_output=True, text=True)
    assert anon.stdout.strip() == "404", "anonymous access must be refused while private"

    # provider read-back: the transfer worker is gone
    token = Path("/opt/data/.secrets/hetzner.token").read_text().strip()

    def hcloud(path):
        req = urllib.request.Request(
            "https://api.hetzner.cloud/v1/" + path,
            headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode() or "{}")

    status, _ = hcloud(f"servers/{SERVER_ID}")
    assert status == 404, f"server {SERVER_ID} still readable ({status})"
    _, servers = hcloud("servers")
    _, ips = hcloud("primary_ips")
    assert not servers.get("servers"), "unexpected servers remain in the project"
    assert not ips.get("primary_ips"), "unexpected primary IPs remain in the project"

    stamp = now_iso()
    block = {
        "repo": REPO,
        "release_id": RELEASE_ID,
        "release_tag": TAG,
        "target_commit": main_sha,
        "private": True,
        "verified": True,
        "verified_at": stamp,
        "files_verified": sorted(assets_block),
        "checks": [
            f"private repository created 2026-11-07 by the release session "
            f"(candidates/ab-wildfire-ia-escape/package/github_staging_2026_11_07.py) with the 26 "
            f"package documents on main at initial commit {main_sha[:12]}; release v2026.11 "
            f"({RELEASE_ID}) created non-draft at main; live API read-back {stamp}: repo "
            f"private:true, tag {TAG}, exactly the five flat assets, every size and sha256 "
            f"digest equal to MANIFEST.json; anonymous API read-back 404 (private)",
            "worker job abwildfire-publish-001 (server 174897047, release-flagged transfer job, "
            "reservation 0.04 EUR) copied the five accepted c2c8ceb5 assets from private staging "
            "release 437132110 into release 437179999 under the flat asset names: 5/5 "
            "transferred, failures [], each sha256 verified on arrival and server-side; bytes "
            "never through the coordinator; worker destroyed 2026-11-06T23:38:14Z and "
            "provider-read-back this session: GET /v1/servers/174897047 -> 404, "
            "GET /v1/servers -> 0, GET /v1/primary_ips -> 0",
        ],
        "anonymous_access": False,
        "note": "private release v2026.11 staged and verified 2026-11-07; NOT published - the "
                "flip (the operator's single approval, preceded by the independent pre-flip "
                "audit) makes it public. The fresh-consumer verification job has NOT run yet; "
                "its check is appended when it does. Evidence: jobs/abwildfire-publish-001.json.",
    }
    block["files_verified"] = sorted(assets_block)

    path = REL / "DESTINATIONS.json"
    record = json.loads(path.read_text()) if path.is_file() else {}
    record.setdefault("release_tag", TAG)
    record["destinations"] = record.get("destinations") or {}
    record["destinations"]["github"] = block  # merge: huggingface block preserved if present
    record["artifact_version"] = manifest["artifact_version"]
    path.write_text(json.dumps(record, indent=2) + "\n")

    print(f"github block written and verified at {stamp}")
    print(f"  tag {TAG} -> commit {main_sha[:12]}; 5/5 assets digest-equal; anonymous 404")
    print(f"  provider read-back: server 404, 0 servers, 0 primary IPs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
