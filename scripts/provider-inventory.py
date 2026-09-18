#!/usr/bin/env python3
"""Read-only provider inventory for the smoke cycle.

Talks to the Hetzner API directly, with the token read from the _FILE path, so the
before/after comparison does not depend on this project's own bookkeeping claiming success.
Usage: python3 .factory/smoke_inventory.py
"""
import json
import os
import urllib.request

PROJECT = "earino-dataset-factory"
TOKEN_FILE = os.environ.get("HCLOUD_TOKEN_FILE", "/opt/data/.secrets/hetzner.token")


def token():
    for key in ("HCLOUD_TOKEN", "HCLOUD_TOKEN_FILE", "HETZNER_TOKEN"):
        value = os.environ.get(key)
        if value and not key.endswith("_FILE"):
            return value.strip()
        if key.endswith("_FILE") and value and os.path.isfile(value):
            with open(value) as handle:
                return handle.read().strip()
    with open(TOKEN_FILE) as handle:
        return handle.read().strip()


def get(path):
    request = urllib.request.Request(
        "https://api.hetzner.cloud/v1" + path,
        headers={"Authorization": "Bearer " + token(),
                 "User-Agent": "dataset-factory-smoke-inventory"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    out = {}
    for resource, key in (("servers", "servers"), ("primary_ips", "primary_ips")):
        data = get(f"/{resource}?label_selector=factory={PROJECT}")
        items = data.get(key, [])
        out[resource] = [
            {"id": item["id"], "name": item.get("name"),
             "labels": item.get("labels", {}),
             "created": item.get("created"),
             "ip": (item.get("ipv4") or {}).get("ip")
                   or ((item.get("public_net") or {}).get("ipv4") or {}).get("ip")
                   or item.get("ip")}
            for item in items
        ]
        out[resource + "_count"] = len(items)
        out[resource + "_total_in_account"] = len(get(f"/{resource}").get(key, []))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
