"""Record the cpcb-aqi-baseline-001 HEADROOM verdict (2026-11-06)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REC = Path("candidates/cpcb-aqi-exceedance/record.json")


def main() -> int:
    record = json.loads(REC.read_text())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    m = record.setdefault("measurements", {})

    for j in record.setdefault("jobs", []):
        if j.get("job_id") == "cpcb-aqi-baseline-001":
            j["status"] = "succeeded"
            j["exit_code"] = 0
            j["staging_release_id"] = 436196921
            j["destroyed_at"] = "2026-11-06T07:04:55+00:00"
            j["provider_read_back"] = "GET /v1/servers/174753994 -> 404 not_found (2026-11-06)"
            j["outcome"] = ("runner contract OK (train.py 0.9734 == validate.py "
                            "0.9734, runner files digest-identical to the read-only "
                            "clone) and the pre-registered deciding check returns "
                            "headroom_demonstrated")

    m["baseline_deciding_check_2026_11_06"] = {
        "recorded_at": now,
        "job": "cpcb-aqi-baseline-001",
        "commands": [
            "python3 candidates/cpcb-aqi-exceedance/prepare_baseline_from_002.py cpcb-aqi-build-004",
            "sh scripts/scout-factory worker launch .factory/jobs/cpcb-aqi-baseline-001/job.json",
            "sh scripts/scout-factory worker collect cpcb-aqi-baseline-001",
            "sh scripts/scout-factory worker destroy cpcb-aqi-baseline-001",
            "verify: .factory/cpcb-aqi-baseline-001/reports/ (10 assets fetched from "
            "staging release 436196921, every sha256 equal to the ledger digests)",
        ],
        "ladder": {
            "reaccept_before_any_score": "ACCEPTED /data/extract matches the qualified "
                                         "artifact a749f0df2f9dd010 (72 B acceptance log)",
            "runner_contract": {"contract_ok": True,
                                "eval_auc_train_py": 0.9734,
                                "eval_auc_validate_py": 0.9734,
                                "runner_files_unmodified": True},
            "holdout": "never copied into the workdir (materialize log); no holdout "
                       "figure exists or is implied",
        },
        "deciding_check": {
            "rule": "headroom ONLY if the model beats EVERY member with a "
                    "station-clustered paired bootstrap 95% CI excluding zero in "
                    "its favour (degenerate constant member: model AUC CI entirely "
                    "above 0.5); written before any score",
            "eval_rows": 126_570, "clusters": 509,
            "model_eval_auc": 0.9734021284395283,
            "vs_station_persistence": {"member_auc": 0.9689109528605426,
                                       "mean_diff": 0.004487,
                                       "ci95": [0.003777, 0.005159],
                                       "beaten": True},
            "vs_state_season_climatology": {"member_auc": 0.861668549124152,
                                            "mean_diff": 0.111802,
                                            "ci95": [0.10015, 0.125189],
                                            "beaten": True},
            "vs_global_rate_degenerate": {"model_auc_ci95": [0.971304, 0.975297],
                                          "entirely_above_0_5": True,
                                          "beaten": True},
            "verdict": "headroom_demonstrated",
            "scope": ("eval split only (2023 station-days); the +0.0045 gap over "
                      "persistence is small but its station-clustered CI excludes "
                      "zero decisively; prevalence decline and winter clustering are "
                      "reported beside the number; the sealed holdout (2024) was "
                      "not evaluated"),
            "reporting_defects_recorded": ("agreement:false in the report is the "
                                           "afdb-precedent tolerance artifact "
                                           "(validate.py logs 4 decimals; the two "
                                           "AUCs agree to 7 significant figures)"),
        },
    }

    record["next_action"] = (
        "HEADROOM DEMONSTRATED (baseline_deciding_check_2026_11_06, pre-registered "
        "rule): package cpcb-aqi-exceedance per the dataset-release skill from the "
        "accepted artifact a749f0df2f9dd010... (staging release 436180445 holds the "
        "five runner-layout files + reports; digests in "
        "measurements.attempt_004_accepted_artifact_2026_11_06): assemble the "
        "package (README/card, data dictionary, licence from license_evidence - "
        "GODL-India attribution + XKDR CC BY 4.0, derived-data label), "
        "release-manifest.py, check-package.py, VERIFICATION.md with what was NOT "
        "covered (holdout sealed; current-vintage assumption; intraday latency "
        "unmeasured), then private staging and the review handoff. The holdout "
        "stays sealed until the design is frozen; no re-tuning of threshold, "
        "window, label or features after any score. The dvsa-mot-build-002 repair "
        "remains the next construction item on the actionable list."
    )
    record["updated_at"] = now
    REC.write_text(json.dumps(record, indent=1) + "\n")
    print("record updated:", now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
