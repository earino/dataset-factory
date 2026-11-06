#!/usr/bin/env python3
"""Record the cpcb-aqi-build-001 launch receipt in the candidate record."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
record_path = BASE / "record.json"
record = json.loads(record_path.read_text())
ledger = json.loads((BASE.parent.parent / "jobs" / "cpcb-aqi-build-001.json").read_text())

assert ledger["status"] == "running", ledger.get("status")
entry = {
    "id": "cpcb-aqi-build-001",
    "server_id": ledger["server_id"],
    "server_type": "cpx32",
    "location": "hel1",
    "status": "running_at_launch",
    "launched_at": ledger["created_at"],
    "expires_epoch": ledger["expires"],
    "reservation_eur": "0.32",
    "provider_hourly_eur": ledger["provider_hourly_eur"],
    "source_sha256": ledger["source_sha256"],
    "staging_repo": ledger["staging_repo"],
    "what": ("full construction + gate 1.5.0 on the FULL artifact + exact-byte "
             "--accept + pre-registered reference triad; holdout sealed"),
    "stopping_condition": ("failed anchor/fixture assertion, truncated fetch, failed "
                           "gate or failed --accept stops the run with diagnostics "
                           "uploaded; the extract is never scored"),
}
record["jobs"] = [entry] + [j for j in record.get("jobs", []) if j.get("id") != entry["id"]]
record["updated_at"] = "2026-11-06T02:30:00+00:00"
record_path.write_text(json.dumps(record, indent=1) + "\n")
print(json.dumps({k: entry[k] for k in ("id", "server_id", "launched_at", "reservation_eur")}))
