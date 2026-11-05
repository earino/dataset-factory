#!/usr/bin/env python3
"""Follow-up record update 2026-11-05 (watcher, job afdb-panel-probe-001): account
every staging asset with its exact name/path and observed digest, correct one asset
label, and record the CI result for the commit that recorded the probe outcome.

Evidence, all observed this session (2026-11-05, read-only):
- GitHub releases API, GET /repos/earino/dataset-factory-staging/releases/435425973
  (staging credential, read-only): 4 assets with name/size/digest fields.
- The release's manifest.json asset downloaded (63,190 B; hashed locally and compared
  to the API digest) and its files table read: it maps every part to its logical path.
- jobs/afdb-panel-probe-001.json source_sha256/source_bytes compared against the
  staged source.tar entry.
- Actions CI for commit fcffeed37b535021db44a519977e509f89086891 (HEAD == origin/main):
  one run, event push, completed/success, run 42063878395, via api.github.com (public
  repo, anonymous).
No other record field is touched; no number is invented - the script asserts every
observed value against the downloaded manifest before writing.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
CAND = ROOT / "candidates/afdb-project-cancellation"
SCRATCH = Path("/opt/data/cache/scratch/afdb_probe_manifest.json")

FOLLOWUP = "staging_asset_accounting_followup_2026_11_05"

# Observed 2026-11-05 via the releases API (asset name -> size, sha256 digest field).
API_ASSETS = {
    "file-0000-part-0000": (44298, "215c20d9e9727deb6dfcc3f98f072c77554ed6e8195e9f139b897aea1fbe0b0f"),
    "file-0001-part-0000": (112640, "b5fab84afbb607180e16fcdc52653f9914652d0ffd0bcaac521c1b73bd37c989"),
    "file-0002-part-0000": (4687, "56fc2b4b4b5c0b2c0403c5c62ddcc40b1cfcc58b1f99030fdadd22dfad5a35e6"),
    "manifest.json": (63190, "a324477c1df5b6b2a5aeb8fa361499be6d227ab04430c8a23769c5fc2da40f93"),
}

raw = SCRATCH.read_bytes()
assert len(raw) == API_ASSETS["manifest.json"][0], "manifest.json size drifted"
local_manifest_sha = hashlib.sha256(raw).hexdigest()
assert local_manifest_sha == API_ASSETS["manifest.json"][1], "manifest.json digest drifted"

man = json.loads(raw)
files = {e["file"]: e for e in man["assets"]}

ledger = json.loads((ROOT / "jobs/afdb-panel-probe-001.json").read_text())
assert files["source.tar"]["sha256"] == ledger["source_sha256"], "source.tar digest != ledger"
assert files["source.tar"]["size"] == ledger["source_bytes"], "source.tar size != ledger"

for logical in ("output/summary.json", "source.tar", "container.log"):
    entry = files[logical]
    size, sha = API_ASSETS[entry["name"]]
    assert (entry["size"], entry["sha256"]) == (size, sha), f"manifest/API mismatch on {logical}"

rec = json.loads((CAND / "record.json").read_text())
m = rec["measurements"]["worker_panel_probe_2026_11_05"]
assert FOLLOWUP not in m, "follow-up already applied"

m["staging_release"] = (
    "435425973 (private earino/dataset-factory-staging, tag job-afdb-panel-probe-001; "
    "staging manifest.json sha256 a324477c1df5b6b2a5aeb8fa361499be6d227ab04430c8a23769c5fc2da40f93, "
    "63,190 B, embeds the job result. Label corrected by the 2026-11-05 follow-up: this "
    "digest was first recorded as 'summary.json', but the worker's output/summary.json is "
    "a separate 44,298 B asset - see staging_asset_accounting_followup_2026_11_05)"
)

m[FOLLOWUP] = {
    "verified_by": (
        "2026-11-05 watcher follow-up (16:34Z), read-only: GitHub releases API "
        "GET /repos/earino/dataset-factory-staging/releases/435425973 - 4 assets "
        "present, each name/size/sha256 read back; manifest.json downloaded and its "
        "sha256 recomputed locally, equal to the API digest; its files table maps "
        "every part to a logical path; part digests equal the API digests"
    ),
    "assets": [
        {"logical_path": "output/summary.json", "asset": "file-0000-part-0000",
         "size": 44298, "sha256": "215c20d9e9727deb6dfcc3f98f072c77554ed6e8195e9f139b897aea1fbe0b0f"},
        {"logical_path": "source.tar (job input bundle)",
         "asset": "file-0001-part-0000", "size": 112640,
         "sha256": "b5fab84afbb607180e16fcdc52653f9914652d0ffd0bcaac521c1b73bd37c989",
         "matches": "jobs/afdb-panel-probe-001.json source_sha256/source_bytes (exact)"},
        {"logical_path": "container.log", "asset": "file-0002-part-0000",
         "size": 4687, "sha256": "56fc2b4b4b5c0b2c0403c5c62ddcc40b1cfcc58b1f99030fdadd22dfad5a35e6"},
        {"logical_path": "manifest.json (staging manifest; embeds the job result)",
         "asset": "manifest.json", "size": 63190,
         "sha256": "a324477c1df5b6b2a5aeb8fa361499be6d227ab04430c8a23769c5fc2da40f93"},
    ],
    "correction": (
        "the 2026-11-05 discovery session's staging_release string named the 63,190 B "
        "a324477c... asset 'summary.json'; that asset is the staging manifest.json. The "
        "worker's output/summary.json is file-0000-part-0000, 44,298 B, sha256 "
        "215c20d9e9727deb6dfcc3f98f072c77554ed6e8195e9f139b897aea1fbe0b0f. No recorded "
        "digest was wrong - the label was; corrected in the same field"
    ),
    "ci_on_recording_commit": (
        "fcffeed37b535021db44a519977e509f89086891 (the discovery tick that recorded this "
        "probe's outcome; HEAD == origin/main at verification): Actions run 42063878395, "
        "event push, completed/success, checked 2026-11-05 via "
        "api.github.com repos/earino/dataset-factory/actions/runs?head_sha= (anonymous, "
        "public repo)"
    ),
}

for j in rec.get("jobs", []):
    if j.get("id") == "afdb-panel-probe-001":
        j["followup_2026_11_05"] = (
            "staging release 435425973 accounted 4/4 assets (API digests + manifest.json "
            "mapping; source.tar matches the ledger source_sha256); asset label corrected; "
            "CI on fcffeed green (run 42063878395); handled by the 16:34Z watcher follow-up"
        )
        break
else:
    raise SystemExit("afdb-panel-probe-001 job entry not found")

(CAND / "record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
print("record follow-up applied: staging_release corrected,", FOLLOWUP, "added, jobs entry annotated")
