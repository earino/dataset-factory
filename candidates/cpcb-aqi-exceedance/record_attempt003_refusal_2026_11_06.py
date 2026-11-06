"""Record the -003 refusal diagnosis, repair and -004 launch (cpcb-aqi-exceedance).

Run from the repository root:

    python3 candidates/cpcb-aqi-exceedance/record_attempt003_refusal_2026_11_06.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REC = Path("candidates/cpcb-aqi-exceedance/record.json")


def main() -> int:
    record = json.loads(REC.read_text())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    m = record.setdefault("measurements", {})

    # --- jobs[]: -003 outcome, -004 launch receipt ------------------------------
    jobs = record.setdefault("jobs", [])
    for j in jobs:
        if j.get("job_id") == "cpcb-aqi-build-003":
            j["status"] = "failed_and_deleted"
            j["exit_code"] = 1
            j["failed_at"] = "2026-11-06T06:15:06+00:00"
            j["staging_release_id"] = 436167238
            j["destroyed_at"] = "2026-11-06T06:18:36+00:00"
            j["provider_read_back"] = "GET /v1/servers/174749145 -> 404 not_found (2026-11-06)"
            j["outcome"] = ("BUILD REFUSED at the Delhi known-event fixture: "
                            "station_days 39 != 38 (complete_n18=36 and pos_n18=36 held); "
                            "the -002 count-anchor repair worked (no count refusal, "
                            "internal consistency passed, probe deltas reported)")
    if not any(j.get("job_id") == "cpcb-aqi-build-004" for j in jobs):
        jobs.append({
            "job_id": "cpcb-aqi-build-004",
            "candidate": "cpcb-aqi-exceedance",
            "server_id": 174751006,
            "server_type": "cpx32",
            "location": "hel1",
            "status": "running",
            "launched_at": "2026-11-06T06:20:37.757924+00:00",
            "expires_at": "2026-11-06T08:40:37+00:00",
            "timeout_minutes": 100,
            "lifetime_minutes": 140,
            "reservation_eur": 0.32,
            "provider_hourly_eur": 0.06924,
            "source_sha256": "90fd916354115b53910118e42df6c3aea91a41a10011b18bc5fc4d92b8612e25",
            "bundled_gate_sha256": "4fab8a34fe4f3357b7cd911087bfa243c56a96d8720e40d0d4cb2169100404d1",
            "staging_repo": "earino/dataset-factory-staging",
            "what": ("one rebuild for the Delhi-fixture operand defect: station_days "
                     "38 -> 39 (registry membership; the publisher's own bulletin "
                     "denominator is 36/39)"),
        })

    # --- measurements: the -003 refusal, diagnosis and repair ------------------
    m["attempt_003_refusal_2026_11_06"] = {
        "recorded_at": now,
        "job": "cpcb-aqi-build-003",
        "outcome": ("FAILED exit 1 at ~527 s, at the Delhi known-event fixture: "
                    "{'station_days': 39, 'complete_n18': 36, 'pos_n18': 36} != "
                    "{'station_days': 38, ...}. The fetch was clean (168 requests, "
                    "0 truncated, 0 unparseable, 54,138,890 B, 513.3 s) and the -002 "
                    "count-anchor repair behaved exactly as designed: no count "
                    "refusal, the internal-consistency checks passed, and the probe "
                    "deltas were reported. Nothing was written, gated, accepted or "
                    "scored."),
        "count_repair_confirmed": {
            "note": ("measured by the -003 fetch itself, single clean pass; these are "
                     "now the best available export facts (the 2026-11-05 probe "
                     "totals were defective). Preserved in the staging-release "
                     "container.log (release 436167238) and to be re-measured and "
                     "recorded in summary.json by -004."),
            "panel_rows_total": 717_429,
            "window_station_days": {"train_2019_2022": 339_756, "eval_2023": 154_003,
                                    "holdout_2024": 176_104, "tail_2025_04_09": 47_566},
            "window_positives_n18": {"train_2019_2022": 63_748, "eval_2023": 20_773,
                                     "holdout_2024": 19_277, "tail_2025_04_09": 829},
            "probe_deltas": {"total": 679, "train": 199, "eval": 0,
                             "holdout": 480, "tail": 0},
            "consistent_with": ("attempt_002_refusal_2026_11_06.reconciliation: the "
                               "+679 sits in the train/holdout windows where the "
                               "probe's resumed scratch aggregation lost rows; eval "
                               "and tail match the probe exactly"),
        },
        "diagnosis": {
            "defect_class": "known-event fixture operand mis-specification (first "
                            "occurrence; distinct from the -002 count-anchor class)",
            "evidence": [
                "the fixture's substantive claims held exactly: complete_n18=36, "
                "pos_n18=36 (36/36 complete Delhi station-days exceed 90)",
                "the 2026-11-05 preflight recorded station_days=38 from the PANEL "
                "(38 Delhi stations with rows on 2024-11-18; 2 thin n=11/n=9 -> 36 "
                "complete), but build.py counts REGISTRY MEMBERSHIP "
                "(fixture['station_days'] += 1 for every registry Delhi station)",
                "retained probe/out/xkdr_stations_2026_11_04.json: 39 cpcb_caaqm "
                "Delhi stations (558-station snapshot, 0 non-cpcb Delhi), unchanged "
                "in the live registry the -003 build fetched",
                "the publisher's own instrument: CPCB Daily AQI Bulletin 2024-11-18 "
                "says 'Delhi Severe 494, PM2.5, 36/39 stations' - denominator 39",
                "the fixture never executed on real data before -003: -001 refused "
                "at the station registry, -002 at the count anchor",
            ],
            "conclusion": ("the anchor was transcribed from the preflight's panel-row "
                           "count into a build that counts registry membership; the "
                           "registry-based 39/36/36 matches the bulletin's own "
                           "36/39 denominator, so the repair adopts registry "
                           "semantics rather than changing the build to count panel "
                           "rows"),
        },
        "repair_for_attempt_004": {
            "change": "ANCHORS['delhi_2024_11_18']['station_days']: 38 -> 39 "
                      "(complete_n18=36, pos_n18=36 unchanged); docstring updated to "
                      "state the registry-membership semantics and its evidence",
            "unchanged": ("vintage pin, 549-station count, UNKNOWN_STATE sentinel, "
                          "hole-month assertion, monsoon bound, internal-consistency "
                          "checks, probe-reference reporting, population, label, "
                          "threshold, splits, features, exclusions, timing block, "
                          "score.py"),
            "dry_run_2026_11_06": ("synthetic build rc=0 -> gate 1.5.0 ok=true "
                                   "failed_checks=[] -> --accept ACCEPTED (synthetic "
                                   "artifact f5c72b1c25fde180..., byte-identical to "
                                   "the -003 dry run) -> score.py rc=0; synthetic "
                                   "figures only, nothing about the real task"),
            "budget_rule": ("this is the one rebuild for the Delhi-fixture operand "
                            "defect; a refusal at the same fixture again is a new "
                            "finding requiring fresh diagnosis, not another retry"),
        },
        "no_score_exists": "no gate, acceptance or score ever ran on any cpcb artifact",
    }

    record["next_action"] = (
        "COLLECT cpcb-aqi-build-004 (`sh scripts/scout-factory worker collect "
        "cpcb-aqi-build-004`) and verify the ladder in the collected bytes: build rc=0 "
        "with the measured counts recorded in summary.json (expect ~717,429 panel rows "
        "per the -003 fetch; probe deltas reported), gate 1.5.0 ok=true "
        "failed_checks=[], exact-byte --accept ACCEPTED, then score.py's "
        "pre-registered triad on eval rows only. Then destroy the worker with provider "
        "read-back. ADOPT the measured counts into split_strategy/positive_events "
        "BEFORE reporting any figure. A refusal at the Delhi fixture again, or any new "
        "anchor/gate/accept failure, is a recorded finding: diagnose first (one rebuild "
        "per structural defect already spent for this class). Then the baseline job "
        "(prepare the fetch block from the -004 staging release, "
        "baseline/{run.sh,materialize.py,report.py,job.json,bundle.json}: fetch "
        "artifact, re-accept exact bytes before any score, harness runner verbatim, "
        "pre-registered deciding check, cluster = station_id). Holdout (2024) stays "
        "sealed."
    )
    record["updated_at"] = now
    REC.write_text(json.dumps(record, indent=1) + "\n")
    print("record updated:", now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
