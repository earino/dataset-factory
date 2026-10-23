#!/usr/bin/env python3
"""Record camara-002's failed gate attempt (clustered positives) and hand the
task-design decision to advancement. Run once after collection."""
import json
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "record.json"
record = json.loads(RECORD.read_text())

jobs = record.get("jobs", [])
entry = next((j for j in jobs if j.get("id") == "camara-002"), None)
if entry is None:
    raise SystemExit("camara-002 job entry missing from record")
if "gate 1.4.0" in entry.get("outcome", ""):
    raise SystemExit("camara-002 follow-up already recorded")

entry["outcome"] = (
    "failed (exit 1, 389.4 s): the re-anchored rebuild ran the full 70-file "
    "union cleanly (build_status=0; 642,067 in-window bills, splits identical "
    "to camara-001's full-union measurement - train 160,559 rows / 14,323 "
    "positives, eval 37,885 / 1,397, holdout 36,892 / 1,793; PL 4188/2021 "
    "fixture positive in holdout; portal PL-only cross-check within its "
    "11,640 bound) and uploaded all 12 assets to staging release "
    "job-camara-002 (id 421533646), then qualification gate 1.4.0 FAILED "
    "exactly one of 38 checks: splits.enough_clustered_positives - with "
    "event_key_column=apresentacao_year the positives cluster into only 4 "
    "distinct events in eval (1,397 positives over 2015-2018) and 4 in "
    "holdout (1,793 over 2019-2022) against the gate minimum of 30 positives "
    "AND 20 distinct events. Scientific/task-design failure, not "
    "infrastructure and not a code defect: 4-year cohort windows can never "
    "carry 20 year-clusters. The other 37 checks passed, including every "
    "leakage, timing, split-window/disjointness and runner-contract check. "
    "Reports collected into .factory/camara-002/reports/ (8 small assets + "
    "the staging manifest, each sha256-verified; the 3 bulk CSV digests "
    "agree across the gate artifact block, the staging manifest and the "
    "collect result, and each answered a ranged GET at its full size). "
    "Worker destroyed 07:12:22Z via the lifecycle CLI; provider deletion "
    "read back (GET /servers/171989986 = 404 server not found; project "
    "primary_ips list is empty). No figure from this attempt is quotable: "
    "the gate did not pass, so the in-build naive references and the "
    "8.92% -> 3.69% -> 4.86% prevalence shift remain unqualified."
)
entry["server_id"] = 171989986

record.setdefault("measurements", {})["camara_002_gate_result_2026_10_23"] = (
    "Gate 1.4.0 over the full staged artifact (artifact_version digest "
    "013f0b0696696a03cd0e0bcaad176936e7cd96b8c2e02358d0a67257af799fa9; "
    "train/eval/holdout/meta/quality): 37 of 38 checks passed; the only "
    "failure is splits.enough_clustered_positives, recomputed by the gate "
    "from the rows as eval 1,397 positives / 4 distinct apresentacao_year "
    "events and holdout 1,793 / 4, against minimums of 30 positives and 20 "
    "distinct events (train has 24 distinct positive years). The full "
    "artifact and the gate report are preserved at the private staging "
    "release job-camara-002 (id 421533646, 12 assets, digests verified at "
    "collection); the gate report is also at "
    ".factory/camara-002/reports/qualification-camara-bill-advancement.json "
    "(gitignored local copy)."
)

record["next_action"] = (
    "HANDED TO ADVANCEMENT (task-design decision, not a code patch). "
    "camara-002's only gate failure, splits.enough_clustered_positives, is "
    "structural under the current design: event_key_column=apresentacao_year "
    "with 4-year eval/holdout cohort windows caps independent positive "
    "events at 4, far below the gate's 20-event minimum, so no rebuild of "
    "the same design can pass. Cheapest discriminating next check: decide "
    "the independence claim. (a) If year-level clustering is the honest "
    "claim for Brazilian bill enactment, the design cannot pass - record "
    "the negative finding and re-target (e.g. an onset/change target with "
    "denser event grain) or drop; (b) if bill-level (or "
    "legislature-session-level) independence is defensible on domain "
    "grounds, re-declare event_key_column in quality.json and re-run the "
    "gate over the SAME staged artifact (release job-camara-002, id "
    "421533646) as a bounded re-gate job - do not launch a third full "
    "build; the one-rebuild budget for this defect class is already spent "
    "(camara-001 guard re-anchor -> camara-002 gate fail). Inflating the "
    "clustered count without a defensible independence claim is exactly "
    "what the gate refuses. No number from either attempt is quotable until "
    "a gate passes and --accept verifies the exact bytes on a worker."
)

RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("record updated: camara-002 failed-gate outcome, "
      "measurements.camara_002_gate_result_2026_10_23, next_action -> "
      "advancement handoff")
