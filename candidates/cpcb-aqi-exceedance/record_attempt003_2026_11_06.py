"""Record attempt -003 preflight + launch for cpcb-aqi-exceedance (2026-11-06).

Appends the jobs[] launch receipt and the
measurements.attempt_003_preflight_and_launch_2026_11_06 entry, and rewrites
next_action to the collection ladder. Run from the repository root:

    python3 candidates/cpcb-aqi-exceedance/record_attempt003_2026_11_06.py
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REC = Path("candidates/cpcb-aqi-exceedance/record.json")


def main() -> int:
    record = json.loads(REC.read_text())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # --- jobs[]: launch receipt (do not duplicate if re-run) -------------------
    jobs = record.setdefault("jobs", [])
    if any(j.get("job_id") == "cpcb-aqi-build-003" for j in jobs):
        print("launch receipt already present; nothing to do")
        return 0
    jobs.append({
        "job_id": "cpcb-aqi-build-003",
        "candidate": "cpcb-aqi-exceedance",
        "server_id": 174749145,
        "server_type": "cpx32",
        "location": "hel1",
        "status": "running",
        "launched_at": "2026-11-06T06:05:10.237943+00:00",
        "expires_at": "2026-11-06T08:25:10+00:00",
        "timeout_minutes": 100,
        "lifetime_minutes": 140,
        "reservation_eur": 0.32,
        "provider_hourly_eur": 0.06924,
        "source_sha256": "467bab9c411b9656d20a94885a841f2db223d76d3d547c6c16a89c7cff766782",
        "bundled_gate_sha256": "4fab8a34fe4f3357b7cd911087bfa243c56a96d8720e40d0d4cb2169100404d1",
        "staging_repo": "earino/dataset-factory-staging",
        "what": ("repair attempt per measurements.attempt_002_refusal_2026_11_06"
                 ".repair_for_attempt_003"),
    })

    # --- measurements ----------------------------------------------------------
    m = record.setdefault("measurements", {})
    m["attempt_003_preflight_and_launch_2026_11_06"] = {
        "recorded_at": now,
        "repair_applied": (
            "source/build.py per repair_for_attempt_003: HARD anchors kept "
            "(vintage pin exported_at 2026-09-30T11:25:11+00:00 + 196,521,834 rows; "
            "549 stations; UNKNOWN_STATE sentinel for the 62 null-state stations; "
            "2025 hole months asserted empty; Delhi 2024-11-18 fixture 38/36/36; "
            "monsoon 2023-08-15 bound >=300 complete / <=4 exceed). The exact "
            "panel-total and per-window station-day/positive assertions against the "
            "2026-11-05 probe were DROPPED: the probe's values move to a "
            "non-asserting PROBE_REFERENCE, the build records its own measured "
            "counts in summary.json (with probe deltas reported, never asserted) "
            "and asserts internal consistency: windows partition the panel exactly "
            "(sum of per-window station-days == panel total) and an independent "
            "second pass with the label-rule operands (n>=18, mean>90) reproduces "
            "the per-window positives. Descriptive texts (meta.split_description, "
            "quality row_selection basis) now derive the 2025 tail counts from the "
            "build's own measurement instead of the probe's 47,566/829 literals. "
            "score.py's state-season climatology O(n^2) fix (rate table built once) "
            "was already in source and is carried unchanged. Population, label, "
            "threshold, splits, features, exclusions and timing block unchanged."
        ),
        "dry_run_2026_11_06": {
            "note": ("synthetic bytes only; exercises the machinery, says nothing "
                     "about the real task's headroom"),
            "build_rc": 0,
            "synthetic_counts": {"train": {"rows": 6597, "positives": 650},
                                "eval": {"rows": 1643, "positives": 180},
                                "holdout": {"rows": 1670, "positives": 181}},
            "gate_version": "1.5.0", "gate_ok": True, "failed_checks": [],
            "accept": "ACCEPTED synthetic artifact f5c72b1c25fde180f7f33d5ca771a5c27b930cbefbfaa6c2ee5c522788f0d194",
            "score_rc": 0,
            "score_machinery_figures_synthetic_only": {
                "station_persistence_auc": 0.9522,
                "state_season_climatology_auc": 0.8425,
                "station_train_rate_auc": 0.7241,
                "majority_accuracy": 0.8904,
            },
        },
        "launch": {
            "job_id": "cpcb-aqi-build-003",
            "server_id": 174749145,
            "launched_at": "2026-11-06T06:05:10.237943+00:00",
            "reservation_eur": 0.32,
            "command": "sh scripts/scout-factory worker launch .factory/jobs/cpcb-aqi-build-003/job.json",
        },
        "no_score_exists": ("no real-data performance metric exists; the previous "
                           "attempts' refusals happened before any gate, acceptance "
                           "or score"),
    }

    record["next_action"] = (
        "COLLECT cpcb-aqi-build-003 (`sh scripts/scout-factory worker collect "
        "cpcb-aqi-build-003`) and verify the ladder in the collected bytes: build rc=0 "
        "with the measured counts recorded in summary.json (probe deltas reported), "
        "gate 1.5.0 ok=true failed_checks=[], exact-byte --accept ACCEPTED, then "
        "score.py's pre-registered triad on eval rows only. A failed hard anchor, "
        "internal-consistency check, gate or accept is a recorded finding: diagnose "
        "first; a second refusal of the same count class is a new finding, not "
        "another retry. Then destroy the worker with provider read-back. ADOPT the "
        "measured counts into split_strategy/positive_events BEFORE reporting any "
        "figure. Then the baseline job (prepare_baseline_from_002.py generalises to "
        "the -003 staging release: fetch artifact, re-accept exact bytes before any "
        "score, harness runner verbatim, pre-registered deciding check, "
        "cluster = station_id). Holdout (2024) stays sealed."
    )
    record["updated_at"] = now
    REC.write_text(json.dumps(record, indent=1) + "\n")
    print("record updated:", now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
