#!/usr/bin/env python3
"""List the abwildfire-baseline-002 staging release assets with names and ids."""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "earino/dataset-factory-staging"
RELEASE = 437168266
TOKEN_FILE = Path("/opt/data/.secrets/github-staging.token")


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
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/{RELEASE}/assets?per_page=100",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "dataset-factory-packaging"})
    with opener.open(req, timeout=60) as response:
        assets = json.loads(response.read().decode())
    for a in assets:
        print(a["id"], a["size"], a["name"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
