#!/usr/bin/env python3
"""Record the afdb-project-cancellation construction outcome (2026-11-05).

Applies the pre-registered deciding rule to the measured evidence from jobs
afdb-build-001 and afdb-baseline-001, corrects two measured-number slips in the
record's own prose (with evidence), and moves the candidate to dropped.

Every number written here is read from the collected worker reports under
.factory/afdb-build-001 and .factory/afdb-baseline-001 - nothing is restated
from memory.
"""
import json
from pathlib import Path

RECORD = Path("candidates/afdb-project-cancellation/record.json")
BUILD = Path(".factory/afdb-build-001")
BASE = Path(".factory/afdb-baseline-001")

record = json.loads(RECORD.read_text())
qual = json.loads((BUILD / "output_qualification-afdb-project-cancellation.json").read_text())
refs = json.loads((BUILD / "output_references-afdb-project-cancellation.json").read_text())
baseline = json.loads((BASE / "output_baseline_result.json").read_text())
build_summary = json.loads((BUILD / "output_extract_summary.json").read_text())

assert qual["ok"] and not qual["failed_checks"], "gate must have passed"
art_digest = qual["artifact"]["artifact_version"]["digest"]
assert baseline["qualification_report"]["accepted_before_scoring"]
assert baseline["qualification_report"]["accepted_artifact_version"] == art_digest[:16]

deciding = baseline["deciding_check"]
members = deciding["members"]
verdict = deciding["verdict"]
assert verdict == "triad_not_beaten"

# ---- corrections of the record's own prose, with evidence ---------------------
old_split = record["split_strategy"]
corrected_split = old_split.replace(
    "holdout 2012-2023 (1,118 / 38 / 31-33 cells / 3.40%)",
    "holdout 2012-2023 (1,087 / 38 / 31 cells / 3.50% - CORRECTED 2026-11-05 "
    "from the pinned-vintage per-year table and confirmed by the build: the "
    "original 1,118/3.40% subtracted 2012's 110 rows instead of 2011's 141; the "
    "pre-registered windows and the 38 positives were always correct)")
assert corrected_split != old_split, "split_strategy correction anchor not found"
record["split_strategy"] = corrected_split

# ---- status -------------------------------------------------------------------
record["status"] = "dropped"
record["rejected_at"] = "2026-11-05T17:24:03Z"
record["rejection_reason"] = (
    "Measured no headroom over the identity prior at the board-approval instant, "
    "under the pre-registered deciding check. The full model (harness runner "
    "baseline, xgboost, eval AUC 0.6394 on the identical 1,126 eval rows) beats "
    "the trailing sector-x-decade rate (0.4697) with a cluster-aware paired "
    "bootstrap CI of [+0.0124, +0.3231] and the degenerate global rate (model "
    "AUC CI [0.5354, 0.7480] entirely above 0.5), but does NOT beat the "
    "strongest member, the trailing country rate (0.5491): model-minus-prior CI "
    "[-0.0765, +0.2546] contains zero, so the observed +0.0903 gap is "
    "inconclusive, not a demonstrated margin. Per the rule written before any "
    "score ('headroom is demonstrated ONLY if the full model beats EVERY triad "
    "member with a cluster-aware bootstrap 95% CI excluding zero in the model's "
    "favour'), headroom is NOT demonstrated and the candidate drops with the "
    "evidence preserved - the third measured instance of the WB at-approval "
    "family defect (after wb-ieg-project-outcome and wb-loan-disbursement-"
    "completion). The negative finding does not prove every competent model "
    "must lose: eval carries only 29 independent positive event cells "
    "(country-or-region x approval year), and the cluster-aware interval is "
    "wide precisely because the positives are that clustered.")
record["construction_script"] = (
    "candidates/afdb-project-cancellation/source/build.py (worker job "
    "afdb-build-001, construct-only, no performance metric computed anywhere in "
    "the build; source vintage pinned by the 57 sha256 digests measured by "
    "afdb-panel-probe-001, any mismatch refuses; run.sh order construct -> "
    "qualify -> exact-byte --accept -> score.py references)")
record["next_action"] = (
    "None (dropped 2026-11-05 by the pre-registered deciding check). Negative "
    "finding preserved in measurements.construction_2026_11_05, "
    "measurements.references_2026_11_05_eval_rows, measurements."
    "baseline_2026_11_05 and in the private staging releases 435481585 "
    "(build) and 435496906 (baseline). Reopen only as a NEW task instance with "
    "approval-instant information the IATI at-approval attributes do not "
    "carry (e.g. a verified as-of country-year macro/covariate join with its "
    "own availability ledger, or a change/onset label that is not a level "
    "prediction); do not re-tune this label, threshold, these splits or these "
    "features to chase a score.")

# ---- measurements --------------------------------------------------------------
record["measurements"]["construction_2026_11_05"] = {
    "command": ("worker job afdb-build-001 (cx23/hel1, server 174648468, 30.4 s, "
                "EUR 0.04 reserved): fetched all 57 pinned afdb.org IATI XML "
                "files (172,488,241 B), every sha256 matched the "
                "afdb-panel-probe-001 vintage pin, built the terminal panel "
                "(statuses 3+5, approvals 1967-2023) and wrote the runner "
                "layout; gate 1.5.0 passed 44/44 on the full artifact and "
                "exact-byte --accept ACCEPTED"),
    "artifact_version": art_digest,
    "gate_report_sha256": "4f62a55ff4f7b23aa75542e15911b4a915e1ab50c4e6804bb51591a9432d154e",
    "layout": ("public/train.csv (144,157 B, sha256 4132bc2e03bc5e02...), "
               "public/eval.csv (87,036 B, 15d38c19f7bba8ce...), "
               "private/holdout.csv (83,914 B, 518f10ae708d55dd...), meta.json "
               "(878 B, b05caf826073...), quality.json (11,576 B, 067348010f5a...)"),
    "split_stats": build_summary["splits"],
    "population": {
        "activities_total": 5188,
        "status_histogram": {"3": 3897, "5": 191, "2": 819, "1": 281},
        "terminal_rows": 4088,
        "censored_excluded": 1100,
        "excluded_2024plus": build_summary["population"]["excluded_2024plus"],
    },
    "feature_diagnostics": build_summary["feature_diagnostics"],
    "corrections_recorded": {
        "holdout_row_count": ("the record's split_strategy prose wrote "
                              "holdout 1,118 rows / 3.40%; the pinned-vintage "
                              "per-year table and the build both measure 1,087 "
                              "rows / 3.50% (38 positives unchanged); the slip "
                              "subtracted 2012's 110 rows instead of 2011's "
                              "141 when re-cutting the eval boundary"),
        "no_country_positives": ("notes.md wrote '13 positive rows carry no "
                                 "recipient-country'; the exact count on the "
                                 "pinned vintage is 17 (564 terminal rows "
                                 "carry no recipient-country, ALL 564 carry a "
                                 "recipient-region instead, so zero rows fall "
                                 "to the MULTINATIONAL bucket and the event "
                                 "key resolves them by region code)"),
    },
    "staging_release": 435481585,
    "evidence": (".factory/afdb-build-001/{staging-manifest.json, "
                 "output_qualification-afdb-project-cancellation.json, "
                 "output_references-afdb-project-cancellation.json, "
                 "output_extract_summary.json, output_extract_meta.json, "
                 "output_acceptance-afdb-project-cancellation.txt}"),
}
record["measurements"]["references_2026_11_05_eval_rows"] = {
    "command": ("afdb-build-001 run.sh stage 4 (score.py, post-acceptance only) "
                "on the identical 1,126 eval rows; every rate table estimated "
                "ONLY from the 1,871 train rows"),
    "train_positive_rate": refs["train_positive_rate"],
    "eval_positive_rate": refs["eval_positive_rate"],
    "references": refs["references"],
    "clustered_paired_differences": refs["clustered_paired_differences"],
    "per_approval_year": refs["per_approval_year"],
    "prevalence_shift": refs["prevalence_shift"],
    "structural_note": ("eval years 2007 and 2008 carry ZERO positives among "
                        "scored rows (80 and 92 rows): the outcome-observability "
                        "selection bites exactly as declared - 2007+ approvals "
                        "are the censored backlog's era, so those years score "
                        "only operations that resolved by the snapshot"),
}
record["measurements"]["baseline_2026_11_05"] = {
    "command": ("worker job afdb-baseline-001 (cx23/hel1, server 174650265, "
                "69.1 s, EUR 0.04 reserved): fetched the accepted artifact from "
                "private staging release 435481585, re-ran gate 1.5.0 --accept "
                "against the bundled report (ACCEPTED " + art_digest[:16] + "), "
                "materialized the runner workdir (public train+eval only) and "
                "ran the harness task_template train.py + validate.sh unmodified "
                "(bundled sha256s match the read-only clone, "
                "runner_files.unmodified true), then computed the pre-registered "
                "deciding check with per-row model scores from the same code "
                "path validate.py uses"),
    "artifact_version": art_digest,
    "eval_rows": deciding["eval_rows"],
    "full_model_eval_auc": deciding["model_eval_auc"],
    "full_model_eval_auc_validate_recompute": deciding["model_eval_auc_recomputed_by_validate"],
    "agreement_defect": ("report.py's agreement flag reads false only because "
                         "its 1e-9 tolerance is stricter than validate.py's "
                         "4-decimal log rounding; the two AUCs agree to "
                         "3.3e-6. Reporting defect in the flag, not in the "
                         "scores; recorded, not silently ignored."),
    "triad_same_rows": {
        "global_rate": None,
        "trailing_country_rate": members["trailing_country_rate"]["member_auc"],
        "trailing_sector_decade_rate": members["trailing_sector_decade_rate"]["member_auc"],
    },
    "deciding_check": {
        "rule": deciding["rule"],
        "global_rate_treatment": members["global_rate"]["model_auc_ci"],
        "global_rate_beaten": members["global_rate"]["beaten"],
        "model_minus_country_prior_ci": members["trailing_country_rate"]["model_minus_member_ci"],
        "country_prior_beaten": members["trailing_country_rate"]["beaten"],
        "model_minus_sector_decade_ci": members["trailing_sector_decade_rate"]["model_minus_member_ci"],
        "sector_decade_beaten": members["trailing_sector_decade_rate"]["beaten"],
        "verdict": verdict,
    },
    "observed_gap_model_minus_country_prior": round(
        deciding["model_eval_auc"] - members["trailing_country_rate"]["member_auc"], 4),
    "uncertainty": ("cluster-aware paired bootstrap, 1000 resamples, clusters = "
                    "the 404 declared event_key cells in eval; the "
                    "model-vs-country-prior interval [-0.0765, +0.2546] contains "
                    "zero: an inconclusive difference, not parity and not a "
                    "demonstrated margin"),
    "scope": deciding["scope"],
    "dependencies": baseline["dependencies"],
    "staging_release": 435496906,
    "evidence": (".factory/afdb-baseline-001/{staging-manifest.json, "
                 "output_baseline_result.json, output_train.log, "
                 "output_validate.log, output_accept.log, container.log}"),
}

# ---- artifacts -----------------------------------------------------------------
record["artifacts"].append({
    "artifact_version": art_digest,
    "gate_version": qual["gate_version"],
    "built_by_job": "afdb-build-001",
    "layout": "public/train.csv, public/eval.csv, private/holdout.csv, meta.json, quality.json",
    "split_stats": build_summary["splits"],
    "qualified": True,
    "accepted_exact_bytes": True,
    "staging_release": 435481585,
    "note": ("evidence artifact for the dropped negative finding; no release "
             "package was prepared (the pre-registered deciding check failed "
             "before packaging); bytes preserved in the private staging release"),
})

# ---- jobs ----------------------------------------------------------------------
record["jobs"].extend([
    {
        "id": "afdb-build-001",
        "kind": "construction + full-artifact qualification + exact-byte accept + reference triad",
        "server_id": 174648468,
        "server_type": "cx23/hel1",
        "status": "succeeded",
        "exit_code": 0,
        "elapsed_s": 30.4,
        "reserved_eur": "0.04",
        "staging_release": 435481585,
        "deleted_at": "2026-11-05T17:14:43Z",
        "provider_readback": "GET /servers/174648468 -> 404 not_found",
    },
    {
        "id": "afdb-baseline-001",
        "kind": "runner-contract baseline + pre-registered deciding check",
        "server_id": 174650265,
        "server_type": "cx23/hel1",
        "status": "succeeded",
        "exit_code": 0,
        "elapsed_s": 69.1,
        "reserved_eur": "0.04",
        "staging_release": 435496906,
        "deleted_at": "2026-11-05T17:23:38Z",
        "provider_readback": "GET /servers/174650265 -> 404 not_found",
    },
])

RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record updated: status=dropped, corrections applied, evidence recorded")
