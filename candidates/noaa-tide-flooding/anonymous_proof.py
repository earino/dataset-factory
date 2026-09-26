#!/usr/bin/env python3
"""Prove both destinations are readable with no credential at all.

Every request in this file goes out with no Authorization header, no token, and no cookie jar.
For each destination it checks the metadata endpoint, then actually retrieves bytes: one file in
full so its digest can be compared with the release's own SHA256SUMS, and a ranged read of a
larger file so the check covers more than metadata.

NOAA ships two configurations, so the checks name the configuration each file belongs to rather
than assuming a single flat `data/` directory: the GitHub release names assets with dashes
(`temporal-public-eval.csv`) while the release index and the Hub both use the nested path
(`temporal/public/eval.csv`).
"""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = ROOT / "release" / "noaa-tide-flooding"
GH_REPO = "earino/noaa-tide-flooding"
GH_TAG = "v2026.09"
HF_REPO = "earino/noaa-tide-flooding"
OUT = ROOT / ".factory" / "noaa-anonymous-proof.json"

FULL = "temporal/public/eval.csv"          # 12.5 MB: small enough to fetch and hash
RANGED = "temporal/public/train.csv"       # 97.9 MB: fetched as a range only


def get(url, headers=None, limit=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=180) as r:
        body = r.read(limit) if limit else r.read()
        return r.status, dict(r.headers), body


def expected_digest(rel):
    for line in (RELEASE_DIR / "SHA256SUMS").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == rel:
            return parts[0]
    raise SystemExit("no digest for %s" % rel)


def main():
    ev = {"method": "no Authorization header, no token, no cookie jar"}

    status, headers, body = get("https://api.github.com/repos/%s" % GH_REPO)
    meta = json.loads(body)
    ev["github_metadata"] = {"status": status, "private": meta["private"],
                             "visibility": meta.get("visibility"),
                             "anonymous_rate_remaining": headers.get("X-RateLimit-Remaining")}

    status, headers, body = get("https://api.github.com/repos/%s/releases/tags/%s" % (GH_REPO, GH_TAG))
    rel = json.loads(body)
    ev["github_release"] = {"status": status, "release_id": rel["id"], "tag": rel["tag_name"],
                            "assets": [{"name": a["name"], "size": a["size"]} for a in rel["assets"]]}

    # full anonymous download of one data file, digest-checked against SHA256SUMS
    asset = FULL.replace("/", "-")
    url = "https://github.com/%s/releases/download/%s/%s" % (GH_REPO, GH_TAG, asset)
    status, headers, body = get(url)
    ev["github_full_download"] = {
        "url": url, "release_path": FULL, "status": status, "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "matches_sha256sums": hashlib.sha256(body).hexdigest() == expected_digest(FULL),
    }

    # ranged anonymous read of the largest file, to show size is really served
    url = "https://github.com/%s/releases/download/%s/%s" % (GH_REPO, GH_TAG, RANGED.replace("/", "-"))
    status, headers, body = get(url, headers={"Range": "bytes=0-199"})
    ev["github_ranged_read"] = {"url": url, "release_path": RANGED, "status": status,
                                "bytes": len(body), "content_range": headers.get("Content-Range"),
                                "content_length": headers.get("Content-Length")}

    status, headers, body = get("https://huggingface.co/api/datasets/%s" % HF_REPO)
    info = json.loads(body)
    ev["hf_metadata"] = {"status": status, "private": info.get("private"),
                         "gated": info.get("gated"), "sha": info.get("sha"),
                         "siblings_count": len(info.get("siblings") or [])}

    url = "https://huggingface.co/datasets/%s/resolve/%s/%s" % (HF_REPO, GH_TAG, FULL)
    status, headers, body = get(url)
    ev["hf_full_download"] = {
        "url": url, "status": status, "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "matches_sha256sums": hashlib.sha256(body).hexdigest() == expected_digest(FULL),
        "x_repo_commit": headers.get("X-Repo-Commit"),
    }

    url = "https://huggingface.co/datasets/%s/resolve/%s/%s" % (HF_REPO, GH_TAG, RANGED)
    status, headers, body = get(url, headers={"Range": "bytes=0-199"})
    ev["hf_ranged_read"] = {"url": url, "status": status, "bytes": len(body),
                            "content_range": headers.get("Content-Range")}

    ev["all_public"] = all([
        ev["github_metadata"]["private"] is False,
        ev["github_full_download"]["matches_sha256sums"],
        ev["hf_metadata"]["private"] is False,
        ev["hf_full_download"]["matches_sha256sums"],
    ])

    OUT.write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps(ev, indent=1))


if __name__ == "__main__":
    main()
