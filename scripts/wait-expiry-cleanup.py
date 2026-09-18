#!/usr/bin/env python3
"""Watch for the expiry path to delete an uncollected worker.

Polls the provider directly (not our ledger) until the named server disappears, then
reports how long after expiry that happened and which cron tick was due. Exits 0 on
deletion, 3 on timeout.
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request

PROJECT = "earino-dataset-factory"
SERVER_ID = int(sys.argv[1])
EXPIRES = int(sys.argv[2])
BUDGET_SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 3000


def token():
    path = os.environ.get("HCLOUD_TOKEN_FILE", "/opt/data/.secrets/hetzner.token")
    token = os.environ.get("HCLOUD_TOKEN")
    if token:
        return token.strip()
    with open(path) as handle:
        return handle.read().strip()


def servers():
    request = urllib.request.Request(
        "https://api.hetzner.cloud/v1/servers?label_selector=factory=" + PROJECT,
        headers={"Authorization": "Bearer " + token()})
    with urllib.request.urlopen(request, timeout=30) as response:
        return [s["id"] for s in json.load(response).get("servers", [])]


def ips():
    request = urllib.request.Request(
        "https://api.hetzner.cloud/v1/primary_ips?label_selector=factory=" + PROJECT,
        headers={"Authorization": "Bearer " + token()})
    with urllib.request.urlopen(request, timeout=30) as response:
        return [i["id"] for i in json.load(response).get("primary_ips", [])]


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%SZ")


started = time.monotonic()
deadline = started + BUDGET_SECONDS
print(f"{stamp()} watching server {SERVER_ID}, expires "
      f"{datetime.datetime.fromtimestamp(EXPIRES, datetime.timezone.utc):%H:%M:%SZ}")
while time.monotonic() < deadline:
    try:
        present = SERVER_ID in servers()
    except Exception as exc:                                    # network hiccup: keep watching
        print(f"{stamp()} provider query failed: {type(exc).__name__}")
        present = True
    if not present:
        late = (time.time() - EXPIRES) / 60
        print(f"{stamp()} DELETED: server {SERVER_ID} is gone from the provider "
              f"({late:.1f} min after expiry)")
        print(f"{stamp()} remaining project servers: {servers()}")
        print(f"{stamp()} remaining project primary IPs: {ips()}")
        sys.exit(0)
    print(f"{stamp()} still present; {(EXPIRES - time.time())/60:+.0f} min vs expiry")
    time.sleep(60)

print(f"{stamp()} TIMEOUT after {BUDGET_SECONDS}s: server {SERVER_ID} still present")
print(f"{stamp()} servers now: {servers()}  ips now: {ips()}")
sys.exit(3)