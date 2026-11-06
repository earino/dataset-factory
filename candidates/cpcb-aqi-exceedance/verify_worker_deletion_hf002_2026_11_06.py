#!/usr/bin/env python3
"""Provider read-back: cpcb-aqi-hf-002's server and primary IP must be gone.
Token read in-process from its 0600 file; never printed or exported."""
import json
import urllib.error
import urllib.request
from pathlib import Path

TOKEN = Path("/opt/data/.secrets/hetzner.token").read_text().strip()
SERVER_ID = 174835948


def call(path: str):
    req = urllib.request.Request("https://api.hetzner.cloud/v1" + path,
                                 headers={"Authorization": "Bearer " + TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, None


status, _ = call(f"/servers/{SERVER_ID}")
assert status == 404, f"server {SERVER_ID} still answers HTTP {status}"
status, listing = call("/servers")
assert status == 200
ids = [s["id"] for s in listing["servers"]]
assert SERVER_ID not in ids, ids
status, ips = call("/primary_ips")
assert status == 200
ledger = json.loads(Path("/opt/data/dataset-factory/jobs/cpcb-aqi-hf-002.json").read_text())
print(json.dumps({"server": SERVER_ID, "get_status": 404,
                  "servers_in_project": len(ids),
                  "primary_ips": len(ips.get("primary_ips", [])),
                  "deleted_at": ledger.get("deleted_at")}))
