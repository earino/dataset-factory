#!/usr/bin/env python3
"""Record attempt -002's actual refusal (panel count anchor) and the measured
reconciliation that shows the anchor - not the channel - was wrong."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
record_path = BASE / "record.json"
record = json.loads(record_path.read_text())
job = json.loads((ROOT / "jobs" / "cpcb-aqi-build-002.json").read_text())
log = (ROOT / ".factory" / "cpcb-aqi-build-002" / "reports" /
       "asset-715658052.bin").read_text()
rec = json.loads((BASE / "probe" / "out" / "reconcile_two_months_2026_11_06.json").read_text())

assert job["status"] == "deleted" and job["result"]["status"] == "failed"
assert job["result"]["exit_code"] == 1 and job["result"]["uploaded"] is True
assert "fetched panel rows 717429 != 716750" in log
assert '"requests": 168, "truncated_batches": 0, "unparseable_rows": 0' in log
for month in ("2019-01", "2025-08"):
    assert rec["months"][month]["delta"] == 0, month

record["measurements"]["attempt_002_refusal_2026_11_06"] = {
    "recorded_at": "2026-11-06T03:00:00+00:00",
    "job": "cpcb-aqi-build-002",
    "outcome": ("FAILED exit 1 after 524.2 s. The fetch completed cleanly - 168 requests, "
                "0 truncated responses, 0 unparseable rows, 54,138,890 B, 512.7 s - and the "
                "build then refused its own count anchor: 'BUILD REFUSED: fetched panel rows "
                "717429 != 716750'. Nothing was written, nothing gated, nothing scored."),
    "reconciliation": {
        "question": "is +679 a real change in the export, or a defect in the discovery probe's count?",
        "station_membership": ("identical: the live /v1/stations cpcb PM2.5 set and the "
                               "retained 2026-11-04 file both carry the same 549 ids (no "
                               "symmetric difference); retained at "
                               "probe/out/xkdr_cpcb_pm25_ids_2026_11_06.json"),
        "two_month_refetch": ("probe/probe_reconcile_two_months_2026_11_06.py re-issued the "
                              "exact request shape for 2019-01 and 2025-08 (2 batches each, "
                              "X-Truncated false) and deduped per (station, day): 4,282 and "
                              "9,462 - EXACTLY the 2026-11-05 probe's recorded per_month "
                              "values, delta 0 in both months"),
        "vintage": ("the pinned export is unchanged (exported_at 2026-09-30T11:25:11+00:00, "
                    "196,521,834 rows - asserted by the build before the fetch)"),
        "conclusion": ("the +679 is in the 2026-11-05 probe's RESUMED scratch aggregation, not "
                       "in the channel or the current fetch: that run appended rows to a "
                       "scratch file whose earlier content was deleted after the 401 window "
                       "while its resume MARK file kept those month-batches 'done', so some "
                       "rows were never re-fetched and the recorded total is low. The probe's "
                       "per-month values for the months re-measured are right; its 716,750 "
                       "total (and the per-window counts derived from the same file) cannot "
                       "be treated as an exact export fact."),
    },
    "repair_for_attempt_003": {
        "anchors_kept_hard": [
            "vintage pin: /v1/meta exported_at 2026-09-30T11:25:11+00:00 and 196,521,834 rows",
            "station count 549 cpcb PM2.5 (single-instrumentation population)",
            "Delhi 2024-11-18 fixture: 38 station-days, 36 complete, 36/36 mean > 90",
            "monsoon trough 2023-08-15: >= 300 complete station-days and <= 4 exceed",
            "the 2025 hole months (2025-01..03, 2025-10..12) carry zero cpcb rows",
        ],
        "anchors_changed": ("the exact panel-total and per-window station-day/positive counts "
                            "are no longer asserted against the probe; the build RECORDS the "
                            "counts it measures from its own single-pass fetch in summary.json "
                            "and asserts internal consistency (window counts sum to the panel "
                            "total; positives re-derived by the label rule). The record adopts "
                            "the measured counts before any figure is reported - the gate "
                            "recomputes counts from the rows regardless, so nothing the "
                            "qualification checks becomes weaker."),
        "unchanged": "population, label, threshold, splits, features, exclusions, timing block",
        "carries": "the post-launch score.py O(n^2) fix (already in source/score.py)",
    },
}
record["jobs"] = [j for j in record["jobs"] if j["id"] != "cpcb-aqi-build-002"] + [
    {"id": "cpcb-aqi-build-002", "server_id": job["server_id"], "status": "failed_and_deleted",
     "launched_at": job["created_at"], "exit_code": 1, "elapsed_seconds": 524.2,
     "deleted_at": job["deleted_at"], "staging_release": job["result"]["release_id"],
     "reason": ("count anchor: fetched panel rows 717,429 != probe total 716,750; fetch itself "
                "clean (168 requests, 0 truncated); +679 traced to the probe's resumed "
                "aggregation, not the channel"),
     "no_score": True},
]
record["next_action"] = (
    "ATTEMPT -003 (repair: count anchors restructured per "
    "measurements.attempt_002_refusal_2026_11_06.repair_for_attempt_003; score.py O(n^2) fix "
    "already in source). Steps: (1) edit source/build.py - keep the vintage pin, 549-station "
    "count, Delhi and monsoon fixtures and the 2025-hole assertion; drop the exact "
    "panel-total/per-window assertions against the probe, record the measured counts in "
    "summary.json and assert internal consistency; (2) re-run the synthetic dry run (build -> "
    "gate 1.5.0 -> --accept -> score.py); (3) bump source/job.json to cpcb-aqi-build-003, "
    "assemble, plan, launch (cpx32/hel1, timeout 100, lifetime 140, max_artifact_mb 300); "
    "(4) collect and require build rc=0 with the recorded counts, gate 1.5.0 ok=true "
    "failed_checks=[], exact-byte --accept ACCEPTED, then score.py's triad; (5) update "
    "split_strategy/positive_events with the measured counts BEFORE reporting any figure; "
    "(6) destroy the worker with provider read-back. Then the baseline job "
    "(prepare_baseline_from_002.py generalises to the -003 release: fetch, re-accept, triad, "
    "harness runner, pre-registered deciding check). Holdout stays sealed. A second refusal of "
    "the same count class is a new finding, not another retry."
)
record["updated_at"] = "2026-11-06T03:00:00+00:00"
record_path.write_text(json.dumps(record, indent=1) + "\n")
print(json.dumps({"recorded": "-002 refusal + reconciliation",
                  "two_month_delta": {m: rec["months"][m]["delta"] for m in rec["months"]},
                  "build_rows": 717429, "probe_total": 716750}))
