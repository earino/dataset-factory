#!/usr/bin/env python3
"""Development fetch of the EA bathing-water classification source (coordinator probe).

Not shipped to the worker: build.py does its own fetching. This exists to inspect the
real payload locally before writing the construction, and to keep the measurements
in the candidate record reproducible.
"""
import gzip
import json
import pathlib
import sys
import urllib.request

OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".factory/eab-probe/data")
OUT.mkdir(parents=True, exist_ok=True)
SEASONS = list(range(2015, 2026))
BASE = "https://environment.data.gov.uk"


def fetch(url, timeout=90, accept="application/json"):
    req = urllib.request.Request(url, headers={"Accept": accept,
                                               "User-Agent": "dataset-factory-probe/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


for season in SEASONS:
    url = f"{BASE}/data/bathing-water-quality/compliance-rBWD/slice/year/{season}?_format=json"
    try:
        body = fetch(url)
    except Exception as exc:
        print(season, "MISSING", exc)
        continue
    (OUT / f"season-{season}.json.gz").write_bytes(gzip.compress(body))
    obs = json.loads(body)["result"]["primaryTopic"]["observation"]
    print(season, len(body), len(obs))

# water metadata for every point seen in the newest season
newest = json.loads(gzip.decompress((OUT / "season-2025.json.gz").read_bytes()))
points = {}
for o in newest["result"]["primaryTopic"]["observation"]:
    about = o["bwq_bathingWater"]["_about"]
    points[about.rsplit("/", 1)[-1]] = about
print("points", len(points))
meta = {}
for i, (bwspid, about) in enumerate(sorted(points.items())):
    try:
        doc = json.loads(fetch(about, accept="application/json"))
    except Exception as exc:
        print(bwspid, "META-MISSING", exc)
        continue
    meta[bwspid] = doc["result"]["primaryTopic"]
    if i == 0:
        print("META KEYS", sorted(meta[bwspid].keys()))
(OUT / "metadata.json.gz").write_bytes(gzip.compress(json.dumps(meta).encode()))
print("metadata rows", len(meta))
first = meta[sorted(meta)[0]]
print(json.dumps({k: v for k, v in first.items()
                  if k in ("district", "type", "bathingWaterType", "name",
                           "appointedSewerageUndertaker", "latestComplianceAssessment")},
                 indent=1)[:1200])
