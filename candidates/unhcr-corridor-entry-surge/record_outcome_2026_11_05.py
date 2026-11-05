"""Record the unhcr-corridor-003 completed ladder and apply the pre-registered
deciding check: identity priors dominate both momentum references on identical
eval rows, so per the rule written before any score existed the candidate DROPS
for no demonstrated headroom (wb-loan precedent). Run from the repo root:
python3 candidates/unhcr-corridor-entry-surge/record_outcome_2026_11_05.py
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "candidates" / "unhcr-corridor-entry-surge" / "record.json"
RESULT = ROOT / ".factory" / "unhcr-corridor-003" / "result.json"


def utc_now() -> str:
    out = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True,
                         text=True, check=True)
    return out.stdout.strip()


def main() -> int:
    record = json.loads(RECORD.read_text())
    result = json.loads(RESULT.read_text())
    now = utc_now()

    for job in record["jobs"]:
        if job["id"] == "unhcr-corridor-003":
            job["status"] = (
                "succeeded-collected-then-deleted (ledger jobs/unhcr-corridor-003.json; "
                "server 174550077 destroyed with provider 404 read-back, 0 servers / "
                "0 primary IPs)"
            )
            job["outcome"] = (
                "COMPLETED LADDER, all stages green, in order (container.log lines 1-810): "
                "(1) construct: fresh HDX worker fetch 8,669,567 B in 2.5 s, sha256 "
                "d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950 = the "
                "discovery pin EXACTLY (the repaired fetch); every hard anchor reproduced "
                "exactly - train 363/127/106, eval 202/98/80, holdout 159/72/64 "
                "rows/positives/events, full-population cross-check 653/214/153, "
                "230/103/83, 170/73/64; all six known-event fixtures green; cross-row "
                "label-operand recovery ZERO in every split; 724 rows written. "
                "(2) gate 1.5.0 on the FULL artifact: ok=true, failed_checks=[]. "
                "(3) exact-byte --accept: ACCEPTED, qualified artifact 0473275c81266071. "
                "(4) score.py references, its FIRST real execution, strictly after "
                "acceptance, eval rows only, holdout never opened. The pre-registered "
                "deciding check returned identity_prior_dominates_no_headroom -> per the "
                "rule written before any score, the candidate DROPS for no demonstrated "
                "headroom (the wb-loan precedent). No re-tuning of threshold, "
                "eligibility, label or windows after the score."
            )
            job["evidence"] = (
                "staging release 434717809 (assets verified by collect; container.log + "
                "qualification + references + the 5 extract files); local "
                ".factory/unhcr-corridor-003/result.json; worker destroyed "
                "2026-11-05T02:51:55Z, provider read-back 0/0"
            )

    record["measurements"]["construction_outcome_unhcr_corridor_003"] = {
        "measured_at": now,
        "artifact_version": "0473275c81266071 (gate 1.5.0, exact-byte ACCEPTED on the worker)",
        "rows": "train 363 (35.0% pos, 106 clusters) / eval 202 (48.5% pos, 80 clusters) / "
                "holdout 159 (45.3% pos, 64 clusters); 724 shipped rows",
        "prevalence_shift": "train 35.0% -> eval 48.5% positives (out-of-distribution as "
                            "well as temporal); holdout 45.3%",
        "references_on_identical_eval_rows": {
            "identity_combined": "AUC 0.5515, Brier 0.2745",
            "identity_only_host": "AUC 0.5528, Brier 0.2900",
            "identity_only_origin": "AUC 0.5024, Brier 0.3421",
            "momentum_bucket_rate": "AUC 0.5346, Brier 0.2671",
            "momentum_raw": "AUC 0.4496, Brier 2.76",
            "persistence_state_rate": "AUC 0.5286, Brier 0.2676",
            "persistence_last_value": "AUC 0.4447, Brier 7,215,238",
            "global_rate": "degenerate constant, no ranking information",
            "majority_class": "accuracy 0.5149 on this split (fitted on train)",
        },
        "deciding_check_measured": {
            "momentum_raw_vs_identity_combined":
                "observed difference -0.1019, cluster-bootstrap 95% CI "
                "[-0.2159, +0.0075], 150 resamples over 155 surge_cluster keys",
            "momentum_bucket_rate_vs_identity_combined":
                "observed difference -0.0169, cluster-bootstrap 95% CI "
                "[-0.1562, +0.1095], 150 resamples",
            "identity_dominates": True,
            "verdict": "identity_prior_dominates_no_headroom",
        },
        "per_eval_entry_year_note": (
            "2015 identity 0.423 / bucket 0.528; 2016 0.481/0.626; 2017 0.539/0.568; "
            "2018 0.491/0.433; 2019 identity 0.829 (the largest eval year); 2020 (6 rows) "
            "bucket 1.0 vs identity 0.4 - single-year reversals in both directions, no "
            "stable momentum advantage in any year"
        ),
        "interpretation": (
            "Under this pre-registered protocol (annual grain, one row per corridor at "
            "first >=500-application year, momentum-eligible, eval entry years "
            "2015-2020) no momentum-family reference beats the identity-only prior: "
            "identity_combined AUC 0.5515 tops every reference measured, and both "
            "deciding pairs have observed differences in identity's favor with intervals "
            "containing zero. momentum_raw at 0.4496 and persistence_last_value at "
            "0.4447 sit below 0.5 - the mean-reversion property the discovery "
            "association measured, not a defect. identity_combined itself is barely "
            "above chance: there is no demonstrated useful signal for this task shape. "
            "This is a measured negative finding under one protocol; it does not prove "
            "every competent model must fail, and the rule pre-registered its "
            "consequence before any score existed: drop, like the wb-loan precedent. "
            "The full model / runner baseline job was never warranted (headroom was the "
            "precondition) and the holdout remains sealed."
        ),
    }

    record["status"] = "dropped"
    record["rejection_reason"] = (
        "No demonstrated headroom over identity-only priors, measured on the accepted "
        "artifact by the pre-registered deciding check: identity_combined (AUC 0.5515) "
        "dominates both momentum references (momentum_raw 0.4496, momentum_bucket_rate "
        "0.5346) on identical eval rows; both deciding pairs' observed differences favor "
        "identity (cluster-bootstrap 95% CIs contain zero). Per the rule written into "
        "the record before any score existed, this is the DROP branch (the "
        "wb-loan-disbursement-completion precedent). Construction, gate 1.5.0, exact-byte "
        "acceptance and scoring all succeeded - this is a task-utility verdict, not an "
        "infrastructure or qualification failure. The next1_g25 fallback stays behind a "
        "fresh operator decision only."
    )
    record["next_action"] = (
        "None pending. The candidate is DROPPED on the pre-registered rule with the "
        "negative finding preserved in measurements.construction_outcome_unhcr_corridor_"
        "003. The staged evidence (staging release 434717809: extract, qualification "
        "report 0473275c81266071, references, container.log) and the local report "
        ".factory/unhcr-corridor-003/result.json remain readable; the holdout was never "
        "opened by any stage. The parent record (unhcr-refugee-data-finder) keeps its "
        "reopen condition; any new task instance from this source (e.g. the next1_g25 "
        "change/onset shape) requires a fresh operator decision and a fresh "
        "construct->qualify->accept->score cycle with its own pre-registered deciding "
        "check. A one-shot corridor design without demonstrated momentum headroom must "
        "not be re-tuned to chase a score."
    )
    record["updated_at"] = now
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print("record updated at", now, "- status: dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
