#!/usr/bin/env python3
"""Append the dvsa-mot-build-001 launch receipt to the candidate record."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "record.json"

receipt = {
    "id": "dvsa-mot-build-001",
    "launched_at": "2026-11-05T18:33:02Z",
    "server_id": 174661065,
    "server_type": "cpx32",
    "location": "hel1",
    "ipv4": "2.29.159.168",
    "provider_hourly_eur": "0.06924",
    "reservation_eur": "0.32",
    "bundle_sha256": "1e57d7ceee039a1932e2fd1c33288c26c68a0d3f71e30c2ebf9288f10b746c2a",
    "what": "construct -> gate 1.5.0 on the full artifact on the worker -> "
            "exact-byte --accept -> pre-registered reference triad; no performance "
            "metric before acceptance",
    "status": "running",
    "expected_reports": [
        "summary.json",
        "qualification-dvsa-mot-next-test-outcome.json",
        "acceptance-dvsa-mot-next-test-outcome.txt",
        "references-dvsa-mot-next-test-outcome.json",
    ],
}


def main() -> int:
    record = json.loads(RECORD.read_text())
    jobs = record.setdefault("jobs", [])
    if any(job.get("id") == receipt["id"] for job in jobs):
        print("job receipt already present; refusing to duplicate")
        return 1
    receipt["recorded_at"] = datetime.now(timezone.utc).isoformat()
    jobs.append(receipt)
    RECORD.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"recorded": receipt["id"], "at": receipt["recorded_at"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
