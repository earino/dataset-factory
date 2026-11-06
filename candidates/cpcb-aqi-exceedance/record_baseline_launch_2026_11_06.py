"""Record the cpcb-aqi-baseline-001 launch receipt (2026-11-06)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REC = Path("candidates/cpcb-aqi-exceedance/record.json")


def main() -> int:
    record = json.loads(REC.read_text())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = record.setdefault("jobs", [])
    if not any(j.get("job_id") == "cpcb-aqi-baseline-001" for j in jobs):
        jobs.append({
            "job_id": "cpcb-aqi-baseline-001",
            "candidate": "cpcb-aqi-exceedance",
            "server_id": 174753994,
            "server_type": "cpx32",
            "location": "hel1",
            "status": "running",
            "launched_at": "2026-11-06T06:43:41.610409+00:00",
            "expires_at": "2026-11-06T08:53:41+00:00",
            "timeout_minutes": 100,
            "lifetime_minutes": 140,
            "reservation_eur": 0.32,
            "provider_hourly_eur": 0.06924,
            "source_sha256": "fd50589b7a87d469c18c4c4b42b8d865aef86385db7622f40fe770186e4c1760",
            "staging_repo": "earino/dataset-factory-staging",
            "what": ("runner-contract baseline + pre-registered deciding check on "
                     "the accepted artifact a749f0df2f9dd010... (fetched from "
                     "staging release 436180445, re-accept before any score)"),
        })
    record["next_action"] = (
        "COLLECT cpcb-aqi-baseline-001 (`sh scripts/scout-factory worker collect "
        "cpcb-aqi-baseline-001`) and verify IN THE COLLECTED BYTES, in order: "
        "(1) re-accept ACCEPTED for a749f0df2f9dd010... before any score; (2) the "
        "harness runner's eval AUC (train.py vs validate.sh agreement); (3) "
        "report.py's PRE-REGISTERED deciding check on the identical 126,570 eval "
        "rows - the model must beat EVERY triad member (station_persistence 0.9689, "
        "state_season_climatology 0.8617, degenerate global_rate) with the "
        "station-clustered paired bootstrap 95% CI excluding zero in its favour "
        "(and its own cluster-bootstrap AUC CI entirely above 0.5 for the degenerate "
        "member). Record the verdict EITHER WAY as a measured finding - headroom or "
        "triad dominance (drop/re-target per the rule written before any score); an "
        "interval containing zero is inconclusive, not parity. Destroy the worker "
        "with provider read-back. Holdout (2024) stays sealed; no re-tuning after "
        "any score. After the verdict: if headroom, package per dataset-release; if "
        "dominance/inconclusive, record and stop (the wb-loan/unhcr precedent)."
    )
    record["updated_at"] = now
    REC.write_text(json.dumps(record, indent=1) + "\n")
    print("record updated:", now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
