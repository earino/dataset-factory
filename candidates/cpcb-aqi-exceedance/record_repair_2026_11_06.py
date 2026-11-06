#!/usr/bin/env python3
"""Record the cpcb-aqi-build-001 refusal, the measured cause, the repair, and
the cpcb-aqi-build-002 relaunch. Asserts the ledger/diagnostic facts it writes."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
record_path = BASE / "record.json"
record = json.loads(record_path.read_text())

bad = json.loads((ROOT / "jobs" / "cpcb-aqi-build-001.json").read_text())
good = json.loads((ROOT / "jobs" / "cpcb-aqi-build-002.json").read_text())
log = (ROOT / ".factory" / "cpcb-aqi-build-001" / "reports" / "container.log").read_text()
missing = json.loads((BASE / "probe" / "out" / "cpcb_missing_state_2026_11_06.json").read_text())

assert bad["status"] == "deleted" and bad["result"]["status"] == "failed" \
    and bad["result"]["exit_code"] == 1
assert bad["deleted_at"], "worker deletion is not recorded"
assert "carries no state_name" in log
assert len(missing) == 62, len(missing)
assert all(s["station_id"] for s in missing)
assert good["status"] == "running"
assert good["source_sha256"] != bad["source_sha256"]

record["measurements"]["construction_refusal_2026_11_06"] = {
    "recorded_at": "2026-11-06T02:35:00+00:00",
    "job": "cpcb-aqi-build-001",
    "server_id": bad["server_id"],
    "outcome": ("FAILED exit 1 after 10.1 s (no OOM), 0 rows fetched beyond /v1/meta and "
                "/v1/stations: the build's fail-loud station-registry assertion refused "
                "the pinned export"),
    "diagnostic": "BUILD REFUSED: station site_5405 carries no state_name",
    "measured_cause": {
        "method": ("one anonymous GET /v1/stations with the publisher's front-page demo key, "
                   "2026-11-06; script + JSON retained at "
                   "probe/out/cpcb_missing_state_2026_11_06.json"),
        "cpcb_pm25_stations": 549,
        "stations_without_state_name": 62,
        "also_null": ["city_name", "latitude", "longitude"],
        "shape": ("newer stations (first_seen 2017-2024) across Karnataka, Tamil Nadu, "
                  "Kerala, Maharashtra, Manipur, Meghalaya, Tripura, Bihar, Jharkhand, "
                  "Odisha, Madhya Pradesh, Gujarat, Uttar Pradesh, Andhra Pradesh"),
        "significance": ("the discovery probe counted 549 stations but did not check "
                         "attribute coverage; 11.3% of the population carries no state "
                         "identity in the export"),
    },
    "decision": ("declared sentinel convention: those stations ship state_name="
                 "'UNKNOWN_STATE' (recorded in quality.json station_registry and in the "
                 "state_name feature_evidence), NOT station dropping (which would invalidate "
                 "the measured 549-station anchors: 716,750 rows and every per-window count) "
                 "and NOT state inference from station names (invented data). Population, "
                 "rows, labels, splits and thresholds are unchanged; only the missing-"
                 "categorical convention is added"),
    "staging_release": bad["result"]["release_id"],
    "worker_cleanup": "destroyed 2026-11-06T02:33:50Z (ledger deleted_at; provider read-back pending recording)",
}

record["jobs"] = [
    {"id": "cpcb-aqi-build-002", "server_id": good["server_id"], "server_type": "cpx32",
     "location": "hel1", "status": "running_at_launch", "launched_at": good["created_at"],
     "reservation_eur": "0.32", "provider_hourly_eur": good["provider_hourly_eur"],
     "source_sha256": good["source_sha256"], "attempt": 2,
     "repair_of": "cpcb-aqi-build-001",
     "what": "repair relaunch (state sentinel); full construct -> gate -> accept -> triad",
     "stopping_condition": "same as -001; a second refusal of the same class is a new finding"},
    {"id": "cpcb-aqi-build-001", "server_id": bad["server_id"], "status": "failed",
     "launched_at": bad["created_at"], "exit_code": 1, "elapsed_seconds": 10.1,
     "staging_release": bad["result"]["release_id"],
     "reason": "station registry assertion: 62 of 549 stations carry no state_name"},
]
record["updated_at"] = "2026-11-06T02:35:00+00:00"
record_path.write_text(json.dumps(record, indent=1) + "\n")
print(json.dumps({"build_001": "failed/refused", "missing_state": len(missing),
                  "build_002": good["server_id"], "source_changed": True}))
