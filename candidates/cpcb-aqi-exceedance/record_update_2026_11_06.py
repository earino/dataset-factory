#!/usr/bin/env python3
"""Record the 2026-11-06 pre-launch dry run + the two review fixes into the
cpcb-aqi-exceedance record. Asserts every value it writes came from the run."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
record_path = BASE / "record.json"
record = json.loads(record_path.read_text())

DRY = Path("/opt/data/cache/scratch/cpcb-dryrun-2026-11-06")
refs = json.loads((DRY / "references.json").read_text())
gate = json.loads((DRY / "qualification.json").read_text())
build_log = (DRY / "build.log").read_text()
accept_log = (DRY / "accept.out").read_text()

assert gate["ok"] is True and gate["failed_checks"] == [], "synthetic gate did not pass"
assert "ACCEPTED" in accept_log, "synthetic --accept did not accept"
artifact = gate["artifact"]["artifact_version"]["digest"]
assert artifact.startswith("858ef86535986d7c"), artifact
assert refs["rows"]["eval"] == 1643 and refs["references"]["station_persistence"]["auc"] > 0.9
assert '"thin_day": {"train": 2181, "eval": 556, "holdout": 548}' in build_log, \
    "thin_day counter is not populated; the fix did not take effect"

record.setdefault("measurements", {})["construction_preflight_2026_11_06"] = {
    "recorded_at": "2026-11-06T00:00:00+00:00",
    "purpose": ("pre-launch review + the MANDATORY local dry run (synthetic build -> "
                "the REAL gate 1.5.0 -> exact-byte --accept -> score.py) before any "
                "worker cycle. No real-data artifact, score, gate or acceptance exists "
                "yet; nothing measured here is quotable about the real task"),
    "review_fixes_before_dry_run": [
        "trailing-window membership (construction semantics): window.append((day, mean)) "
        "moved above the split/labelability exclusions, so every VALID day feeds later "
        "rows' 7d/30d/90d means, days_since_gt90 and exceed_count_30d. Before the fix a "
        "valid day whose D+1 was missing or thin vanished from D+2..D+91 aggregates, "
        "contradicting the declared feature frame ('mean of the station's valid-day "
        "means') and over-triggering the -1.0 sentinels",
        "excluded['thin_day'] was initialised but never incremented (the earlier smoke's "
        "thin_day 0 while thin days existed); now counted per split from the panel",
        "summary.json per_split_per_month.excluded_unlabelable was hard-wired to 0 by a "
        "dead 'TOTAL' branch; now carries the measured per-month unlabelable count",
    ],
    "dry_run": {
        "build": "python3 candidates/cpcb-aqi-exceedance/source/build.py --synthetic "
                 "--out <scratch>/extract --work-dir <scratch>/work -> rc=0",
        "synthetic_counts": {"train": "6597 rows / 650 pos", "eval": "1643 / 180",
                             "holdout": "1670 / 181"},
        "synthetic_exclusions": {"thin_day": {"train": 2181, "eval": 556, "holdout": 548},
                                 "unlabelable_next_day": {"train": 2192, "eval": 545,
                                                          "holdout": 545}},
        "gate": "gate 1.5.0 ok=true failed_checks=[] on the synthetic extract",
        "accept": "ACCEPTED, synthetic artifact 858ef86535986d7c",
        "score_py_first_real_execution": {
            "station_persistence": {"auc": refs["references"]["station_persistence"]["auc"]},
            "state_season_climatology": {"auc": refs["references"]["state_season_climatology"]["auc"]},
            "global_rate": {"auc": None, "rate": refs["references"]["global_rate"]["rate"]},
            "station_train_rate": {"auc": refs["references"]["station_train_rate"]["auc"]},
            "majority_class_accuracy": refs["references"]["majority_class"]["accuracy"],
            "note": "synthetic bytes only - exercises the machinery; says nothing about "
                    "the real task's headroom, and the persistence number is inflated by "
                    "the generator's deliberate autocorrelation",
        },
        "files_added": ["source/score.py", "source/run.sh", "source/job.json",
                        "source/bundle.json"],
    },
    "pre_registered_deciding_rule": {
        "written_before_any_score": True,
        "members": ["station_persistence", "state_season_climatology", "global_rate"],
        "rule": ("headroom ONLY if the full model beats EVERY member with a "
                 "station-clustered (station_id) paired bootstrap 95% CI excluding zero "
                 "in the model's favour AND the model's own cluster-bootstrap AUC CI lies "
                 "entirely above 0.5 (the degenerate constant member); triad dominance -> "
                 "recorded defect, drop or re-target; no re-tuning of threshold, window, "
                 "label or features after any score"),
    },
}

record["construction_script"] = "candidates/cpcb-aqi-exceedance/source/build.py"
record["next_action"] = (
    "cpcb-aqi-build-001 assembled from source/bundle.json and launched on a cpx32/hel1 "
    "worker (timeout 100 min, lifetime 140, max_artifact_mb 300). Collect when terminal; "
    "require in the collected bytes, IN ORDER: build rc=0 with every panel anchor exact "
    "(716,750 rows; 339,557/154,003/175,624/47,566 per window; 63,735/20,773/19,254/829 "
    "valid-day positives; 549 stations; Delhi 2024-11-18 fixture; monsoon trough bound), "
    "gate 1.5.0 ok=true failed_checks=[], exact-byte --accept ACCEPTED, then score.py's "
    "reference triad. Destroy the worker with provider read-back. Then assemble + launch "
    "the baseline bundle (baseline/: fetch the artifact from the staging release, re-accept "
    "BEFORE any score, run the harness train.py/validate.sh verbatim, and apply the "
    "pre-registered deciding check; cluster = station_id). The holdout stays sealed. A "
    "failed anchor/gate/accept is a recorded finding: diagnose first, at most one rebuild "
    "per structural defect, never edit the declaration to pass."
)
record["updated_at"] = "2026-11-06T00:00:00+00:00"

record_path.write_text(json.dumps(record, indent=1) + "\n")
print("record updated; checks:", json.dumps({
    "dry_run_gate_ok": gate["ok"],
    "artifact": artifact[:16],
    "eval_rows": refs["rows"]["eval"],
    "persistence_auc_synthetic": round(refs["references"]["station_persistence"]["auc"], 4),
}))
