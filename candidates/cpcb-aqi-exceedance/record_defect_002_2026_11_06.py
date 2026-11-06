#!/usr/bin/env python3
"""Record the post-launch defect found in attempt -002's scoring stage and the
exact recovery handoff. Asserts the ledger/bundle facts it writes."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
record_path = BASE / "record.json"
record = json.loads(record_path.read_text())

job = json.loads((ROOT / "jobs" / "cpcb-aqi-build-002.json").read_text())
bundle_score = (ROOT / ".factory" / "jobs" / "cpcb-aqi-build-002" / "score.py").read_text()
source_score = (BASE / "source" / "score.py").read_text()

assert job["status"] == "running", job["status"]
assert "state_season_train" not in bundle_score, "the launched bundle is not the pre-fix code"
assert "state_season_train" in source_score, "source/score.py does not carry the fix"

record["measurements"]["attempt_002_scoring_defect_2026_11_06"] = {
    "recorded_at": "2026-11-06T02:45:00+00:00",
    "job": "cpcb-aqi-build-002",
    "defect": ("score.py's state_season_climatology 'unseen_cell_rows' rebuilt the whole "
               "train rate table INSIDE a per-eval-row generator expression: 154,003 eval "
               "rows x ~340,000 train rows = ~5.2e10 dictionary operations. Not a wrong "
               "number - a hang that would consume the container's 100-minute timeout"),
    "found_by": ("post-launch review of the bundled score.py while the job was running "
                 "(the launch-time review had checked the build and the gate contract, not "
                 "the reference table construction)"),
    "fix": ("the (state_name, target-season) train table is built ONCE in main() and the "
            "coverage counter reads it; verified on the synthetic extract (score.py runs in "
            "2.9 s end-to-end)"),
    "consequence_for_002": ("its bundle is immutable, so the run will pass the build, the "
                            "gate and --accept, then hang at the reference stage until the "
                            "100-minute container timeout (~04:14Z); the uploaded extract, "
                            "gate report and acceptance log are still valid evidence because "
                            "they are written before the reference stage, and no score exists"),
    "cannot_stop": ("worker destroy refuses a running job by design and the scheduler's "
                    "approval gate refused the container-lifecycle command, so the run was "
                    "left to its own timeout rather than bypassing either control"),
    "cost": "one further 0.32 EUR reservation (four reservations in November: 0.08 + 0.32 x3)",
}

record["jobs"] = [
    {"id": "cpcb-aqi-build-002", "server_id": job["server_id"], "server_type": "cpx32",
     "location": "hel1", "status": "running_at_session_end",
     "launched_at": job["created_at"], "reservation_eur": "0.32",
     "source_sha256": job["source_sha256"], "attempt": 2,
     "repair_of": "cpcb-aqi-build-001",
     "expected_outcome": ("build + gate 1.5.0 + exact-byte --accept succeed and are uploaded; "
                          "the reference stage hangs on the known O(n^2) defect and the "
                          "container is killed at the 100-minute timeout (~04:14Z), so the "
                          "job ends FAILED with valid construction/qualification evidence and "
                          "NO score"),
     "carries_defect": "score.py unseen_cell_rows O(n^2) (fixed in source/score.py after launch)"},
    {"id": "cpcb-aqi-build-001", "server_id": 174723039, "status": "failed_and_deleted",
     "launched_at": "2026-11-06T02:27:40.590444+00:00", "exit_code": 1,
     "elapsed_seconds": 10.1,
     "reason": "station registry assertion: 62 of 549 stations carry no state_name"},
]
record["next_action"] = (
    "RECOVERY AFTER ATTEMPT -002 (expected to fail at the reference stage ~04:14Z with the "
    "build/gate/accept evidence uploaded to its staging release): (1) collect "
    "cpcb-aqi-build-002; require the uploaded summary.json (panel anchors), the gate 1.5.0 "
    "report ok=true failed_checks=[] and the acceptance log ACCEPTED for the artifact digest; "
    "a failed gate or a missing acceptance log invalidates the artifact - diagnose before any "
    "relaunch. (2) Fetch the release's manifest.json and the gate report asset (small; the "
    "za-cct baseline/fill_from_collect.py is the cross-checking template: collected result, "
    "release manifest, live asset list must agree on every digest). (3) Copy the gate report "
    "to baseline/qualification.json and fill baseline/job.json's fetch block with the five "
    "extract assets (meta.json, quality.json, public/train.csv, public/eval.csv, "
    "private/holdout.csv; sizes + sha256 from the manifest). (4) assemble + plan + launch "
    "cpcb-aqi-baseline-001 (cpx32/hel1, timeout 100, lifetime 140): its run.sh re-accepts the "
    "fetched bytes BEFORE any score, then runs the fixed score.py reference triad, then the "
    "harness train.py/validate.sh verbatim, then the pre-registered deciding check (cluster = "
    "station_id). One worker cycle produces both the reference table and the full-model "
    "verdict. (5) Apply the pre-registered rule: headroom ONLY if the model beats EVERY triad "
    "member with a station-clustered 95% CI excluding zero in its favour AND its own AUC CI "
    "lies entirely above 0.5; triad dominance -> recorded defect, drop or re-target; no "
    "re-tuning after any score. Destroy the worker with provider read-back. The holdout "
    "(2024) stays sealed."
)
record["updated_at"] = "2026-11-06T02:45:00+00:00"
record_path.write_text(json.dumps(record, indent=1) + "\n")
print(json.dumps({"recorded": "attempt_002 scoring defect",
                  "bundle_pre_fix": True, "source_fixed": True,
                  "jobs": [j["id"] for j in record["jobs"]]}))
