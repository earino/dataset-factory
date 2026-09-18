#!/usr/bin/env python3
"""Verify the qualification report refers to the exact bytes preserved in staging.

`--accept` re-hashes an extract directory on disk, which is the right check when the extract is
local. On the coordinator the extract is deliberately not on disk - bulk data stays in staging -
so the equivalent chain is verified here instead, using only the small manifest and report:

  release assets  ->  manifest.json digests  ->  qualification.json artifact digests

`collect` has already checked every uploaded asset's size and digest against the worker's own
manifest, so if the report's digests equal the manifest's for the same files, the report
describes the bytes that were uploaded, not some earlier or different build.
"""
import json
import subprocess
import sys

RELEASE = int(sys.argv[1])
REPO = "earino/dataset-factory-staging"


def asset(asset_id):
    done = subprocess.run(["gh", "api", f"repos/{REPO}/releases/assets/{asset_id}",
                           "-H", "Accept: application/octet-stream"],
                          capture_output=True, check=True)
    return json.loads(done.stdout)


listing = json.loads(subprocess.run(
    ["gh", "api", f"repos/{REPO}/releases/{RELEASE}/assets?per_page=100"], capture_output=True,
    check=True).stdout)
ids = {item["name"]: item["id"] for item in listing}
manifest = asset(ids["manifest.json"])
qualification = asset(ids["file-0008-part-0000"])

by_path = {entry["file"]: entry for entry in manifest["assets"]}
# The report records the exact files the gate read, under the names it saw them.
assert qualification["gate_version"], "report has no gate version"
components = qualification["artifact"]["artifact_version"]["components"]
report_hashes = {name: qualification["artifact"][name]["sha256"] for name in components
                 if isinstance(qualification["artifact"].get(name), dict)}

def find_uploaded(path):
    """Manifest paths carry the container prefix (`output/extract/public/train.csv`)."""
    for entry in manifest["assets"]:
        if entry["file"] == path or entry["file"].endswith("/" + path):
            return entry
    return None


print(f"release {RELEASE}: {'PASSED' if qualification['ok'] else 'FAILED'} "
      f"(gate {qualification['gate_version']}), "
      f"artifact_version {qualification['artifact']['artifact_version']['digest'][:16]}...")
print()
mismatches = []
for name, digest in sorted(report_hashes.items()):
    path = qualification["artifact"][name]["file"]
    uploaded = find_uploaded(path)
    if uploaded is None:
        mismatches.append(f"{path} is not in the manifest")
        continue
    same = uploaded["sha256"] == digest
    print(f"  {'match' if same else 'DIFFER'}  {path:22} {digest[:16]}... uploaded {uploaded['size']}B")
    if not same:
        mismatches.append(f"{path}: report {digest[:16]} != uploaded {uploaded['sha256'][:16]}")

print()
if mismatches:
    print("ACCEPT FAILED:")
    for item in mismatches:
        print(" -", item)
    sys.exit(1)
print("ACCEPTED: the passing report describes the exact bytes preserved in staging.")