"""Record the -004 SUCCESS (full ladder green) for cpcb-aqi-exceedance.

Adopts the measured counts into split_strategy BEFORE any figure is reported, marks
the job succeeded+deleted, records the triad figures with their commands, and sets
next_action to the baseline job. Run from the repository root:

    python3 candidates/cpcb-aqi-exceedance/record_attempt004_success_2026_11_06.py
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

    # --- jobs[]: -004 succeeded ------------------------------------------------
    for j in record.setdefault("jobs", []):
        if j.get("job_id") == "cpcb-aqi-build-004":
            j["status"] = "succeeded"
            j["exit_code"] = 0
            j["staging_release_id"] = 436180445
            j["destroyed_at"] = "2026-11-06T06:41:44+00:00"
            j["provider_read_back"] = "GET /v1/servers/174751006 -> 404 not_found (2026-11-06)"
            j["outcome"] = ("full ladder green on the real artifact: build rc=0, "
                            "gate 1.5.0 45/45 ok failed_checks=[], exact-byte "
                            "--accept ACCEPTED a749f0df2f9dd010..., score.py triad "
                            "rc=0 on eval 2023")

    # --- measurements: the accepted artifact and its triad ---------------------
    m["attempt_004_accepted_artifact_2026_11_06"] = {
        "recorded_at": now,
        "job": "cpcb-aqi-build-004",
        "commands": [
            "sh scripts/scout-factory worker launch .factory/jobs/cpcb-aqi-build-004/job.json",
            "sh scripts/scout-factory worker collect cpcb-aqi-build-004",
            "sh scripts/scout-factory worker destroy cpcb-aqi-build-004",
            "verify: .factory/cpcb-aqi-build-004/reports/ (6 assets fetched from staging "
            "release 436180445, every sha256 equal to the release manifest and the ledger)",
        ],
        "ladder": {
            "build_rc": 0,
            "gate": {"version": "1.5.0", "ok": True, "checks": "45/45",
                     "failed_checks": []},
            "accept": "ACCEPTED /output/extract matches the qualified artifact "
                      "a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959",
            "score_rc": 0,
            "artifact_files": {
                "train.csv": {"bytes": 45_644_743,
                              "sha256": "24b03a701c34d91834a7c5285d1c928ec33cda9282a2085405b06d541faa9c73"},
                "eval.csv": {"bytes": 20_210_392,
                             "sha256": "e187f645445e135e092898a280e74a2ecba6e75cb25ed9c5470d6f96f779c478"},
                "holdout.csv": {"bytes": 22_967_353,
                                "sha256": "2dae0040cdc2c80fa4adc9cc3b48f26882a6a20f451a252ac3a72f10da8f460f"},
                "meta.json": {"bytes": 1_197,
                              "sha256": "1f59e74e4d6003f03371c4514ee9edda7e79e8ecfa3f995723b1520bac6e2fd7"},
                "quality.json": {"bytes": 22_603,
                                 "sha256": "98250e9d2731f89da021aec360f5d5535fc374241a98db14f185397f9126849a"},
            },
        },
        "measured_counts_adopted": {
            "note": ("measured by this build's own single-pass fetch (168 requests, "
                     "0 truncated, 0 unparseable, 54,138,890 B); they reproduce the "
                     "-003 fetch exactly, and supersede the defective 2026-11-05 "
                     "probe totals (deltas reported in summary.json, never asserted)"),
            "panel_rows_total": 717_429,
            "panel_stations_with_rows": 546,
            "panel_stations_registered": 549,
            "window_station_days": {"train_2019_2022": 339_756, "eval_2023": 154_003,
                                    "holdout_2024": 176_104, "tail_2025_04_09": 47_566},
            "window_valid_day_positives": {"train_2019_2022": 63_748, "eval_2023": 20_773,
                                           "holdout_2024": 19_277, "tail_2025_04_09": 829},
            "shipped_rows": {"train": {"rows": 288_754, "positives": 61_075,
                                       "positive_rate": 0.211512,
                                       "distinct_positive_days": 1_248},
                             "eval": {"rows": 126_570, "positives": 19_819,
                                      "positive_rate": 0.156585,
                                      "distinct_positive_days": 351},
                             "holdout": {"rows": 145_124, "positives": 18_222,
                                         "positive_rate": 0.125562,
                                         "distinct_positive_days": 352}},
            "excluded": {"thin_day": {"train": 33_586, "eval": 18_065,
                                      "holdout": 20_101},
                         "unlabelable_next_day": {"train": 17_416, "eval": 9_368,
                                                  "holdout": 10_879},
                         "outside_windows": 42_638},
            "fixtures": {"delhi_2024_11_18": {"station_days": 39, "complete_n18": 36,
                                              "pos_n18": 36},
                         "monsoon_2023_08_15": {"complete_n18": 389, "pos_n18": 1},
                         "hole_2025_rows": 0},
        },
        "prevalence_shift": {
            "train_2019_2022": 0.211512, "eval_2023": 0.156585,
            "holdout_2024": 0.125562,
            "note": ("declining exceedance prevalence across the temporal split - an "
                     "out-of-distribution property of the split, reported rather "
                     "than adjusted (score.py prevalence_shift records the same)"),
        },
        "reference_triad_eval_2023": {
            "command": "python3 /workspace/score.py --data /output/extract --accepted-report /output/qualification-cpcb-aqi-exceedance.json --report /output/references-cpcb-aqi-exceedance.json (run.sh stage 4, post-acceptance)",
            "rows": 126_570, "positives": 19_819, "distinct_positive_days": 351,
            "station_persistence": {"auc": 0.9689109528605426,
                                   "brier": 0.2830447212174809,
                                   "binary_agreement_accuracy": 0.9350161965710674},
            "state_season_climatology": {"auc": 0.861668549124152,
                                         "brier": 0.09678794864992082,
                                         "unseen_cell_rows": 144},
            "global_rate": {"auc": None, "brier": 0.13508330404901164,
                            "note": "degenerate constant member, no ranking information"},
            "station_train_rate_supplementary": {"auc": 0.7616362039606324},
            "majority_class": {"accuracy": 0.843414711226989},
            "clustered_paired_bootstrap": {
                "station_persistence_vs_state_season_climatology": {
                    "resamples": 1000, "clusters": 509, "mean": 0.107316,
                    "ci95": [0.095881, 0.120774]},
                "vs_global_rate": "degenerate resamples (constant score has no "
                                  "ranking information); recorded, not inferred",
            },
            "per_season_persistence_auc": {"DJF": 0.9541, "JJAS": 0.9522,
                                           "MAM": 0.9359, "ON": "see references json"},
            "interpretation": ("persistence dominates: the next-day exceedance label "
                              "is largely carried by day-D PM2.5. Per the "
                              "pre-registered deciding rule the FULL MODEL (baseline "
                              "job) must beat EVERY member - station_persistence at "
                              "0.9689 is the bar; the deciding comparison runs in "
                              "cpcb-aqi-baseline-001, never by re-tuning here"),
            "holdout": "sealed; no reference reads private/holdout.csv",
        },
        "defects_recorded": {
            "summary_job_label": ("summary.json's 'job' field reads 'cpcb-aqi-build-003' "
                                  "(the literal was bumped for -003 and not re-bumped "
                                  "when job.json moved to -004). Auxiliary diagnostics "
                                  "file only: summary.json is not part of the runner "
                                  "layout, the gate does not read it, and the ledger, "
                                  "staging manifest and container.log all identify -004 "
                                  "correctly. To fix in any future rebuild; not an "
                                  "artifact defect."),
        },
    }

    # --- split_strategy: adopt the measured counts ------------------------------
    record["split_strategy"] = (
        "Temporal by day on the cpcb_caaqm stream only (5 us_embassy DS* stations "
        "excluded; one instrumentation stream). MEASURED 2026-11-06 by the accepted "
        "build cpcb-aqi-build-004 (single-pass fetch of the pinned XKDR export; the "
        "2026-11-05 probe totals it replaces were defective - see "
        "measurements.attempt_002_refusal_2026_11_06): panel 717,429 station-days "
        "across 546 reporting stations (549 registered); windows train 2019-2022 "
        "339,756 / eval 2023 154,003 / holdout 2024 176,104 station-days; the "
        "2025-04..09 partial tail 47,566 station-days / 829 valid-day positives is "
        "excluded and counted; the 2025-01..03 and 2025-10..12 hole months are "
        "asserted empty (0 rows). SHIPPED rows after eligibility (complete day D, "
        "labelable D+1): train 288,754 rows / 61,075 positives (21.15%) / 1,248 "
        "distinct positive days; eval 126,570 / 19,819 (15.66%) / 351; holdout "
        "145,124 / 18,222 (12.56%) / 352. Excluded and counted per split: thin day D "
        "(33,586 / 18,065 / 20,101), unlabelable D+1 (17,416 / 9,368 / 10,879). "
        "Prevalence declines across the split (21.2% -> 15.7% -> 12.6%): an "
        "out-of-distribution property of the temporal split, reported rather than "
        "adjusted. Positives are winter-clustered (per-season eval prevalence DJF "
        "33.0% vs JJAS 1.0%); construction evaluates with station-clustered "
        "intervals (cluster = station_id; 509 eval clusters). Both classes present "
        "in every window; eval/holdout clear the gate minimums with large margin."
    )

    record["next_action"] = (
        "LAUNCH cpcb-aqi-baseline-001 (fetch block already filled from staging "
        "release 436180445 by prepare_baseline_from_002.py cpcb-aqi-build-004; "
        "baseline/qualification.json copied and digest-verified; "
        "expected_artifact.json written): `python3 scripts/assemble-job.py "
        "cpcb-aqi-baseline` (or the cpcb-aqi-baseline bundle), plan, launch; then "
        "collect and verify: re-accept ACCEPTED for a749f0df2f9dd010... BEFORE any "
        "score, harness runner (train.py + validate.sh verbatim) eval AUC, then "
        "report.py's PRE-REGISTERED deciding check on identical eval rows "
        "(126,570 rows; every triad member: station_persistence 0.9689, "
        "state_season_climatology 0.8617, degenerate global_rate; "
        "station-clustered paired bootstrap, cluster = station_id). Headroom ONLY "
        "if the model beats EVERY member with a CI excluding zero in its favour (and "
        "its own AUC CI entirely above 0.5 for the degenerate member); triad "
        "dominance -> recorded defect, drop or re-target per the rule written before "
        "any score. Destroy the worker with provider read-back. Holdout (2024) "
        "stays sealed; no re-tuning of threshold, window, label or features after "
        "any score."
    )
    record["updated_at"] = now
    REC.write_text(json.dumps(record, indent=1) + "\n")
    print("record updated:", now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
