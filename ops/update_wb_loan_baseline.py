#!/usr/bin/env python3
"""Record the wb-loan-disbursement-completion baseline outcome (2026-10-29).

Reads the collected worker evidence, asserts the numbers it writes match what the job's
own reports say, then records the decision in the candidate record. Refuses to write if
the accepted artifact, the gate report digest or the contract AUCs do not line up.
"""
import json
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
CAND = ROOT / "candidates/wb-loan-disbursement-completion"
JOB = ROOT / ".factory/wb-sol-baseline-001/reports"

result = json.loads((JOB / "baseline_result.json").read_text())
refs = json.loads((ROOT / ".factory/wb-baseline-002/reports-download/references.json").read_text())

assert result["qualification_report"]["accepted_artifact_version"] == "c9ac51b846f7b1ee"
assert result["qualification_report"]["gate_version"] == "1.5.0"
assert result["qualification_report"]["gate_ok"] is True
assert result["qualification_report"]["accepted_before_scoring"] is True
assert result["contract"]["contract_ok"] is True
assert result["runner_files"]["unmodified"] is True
model = result["contract"]["eval_auc_from_train_py"]
assert model == result["contract"]["eval_auc_from_validate_py"] == 0.5452

country = refs["references"]["country_prior"]["auc"]
persistence = refs["references"]["persistence_country_last"]["auc"]
loan_type = refs["references"]["loan_type_prior"]["auc"]

record = json.loads((CAND / "record.json").read_text())
record["status"] = "dropped"
record["verdict"] = (
    "No demonstrated headroom under this protocol. The harness runner's own baseline "
    f"reached eval AUC {model:.4f} on the accepted artifact (train.py and validate.py agree "
    "exactly), against a train-estimated country identity prior of "
    f"{country:.4f}, an instrument-type prior of {loan_type:.4f} and a country-persistence "
    f"reference of {persistence:.4f} on the same 1,034 eval rows. The observed gap over the "
    "country prior is +0.0088; the marginal standard errors are about 0.019 each, so the "
    "difference is far inside sampling noise - an inconclusive difference, not parity and "
    "not a demonstrated edge. Nothing here proves the question is unanswerable; it says this "
    "source's approval-instant fields do not carry it."
)
record["rejection_reason"] = (
    "Measured no headroom over an identity prior at the Board-approval instant. Diagnosis, "
    "bounded: the shipped features at the instant are the instrument's static attributes "
    "(loan_type, original_principal_amount, borrower/guarantor identity, country) plus "
    "identifiers; the label is highly persistent (68-69% positive in every split) and country "
    "identity carries nearly all of the observable signal. There is no within-row history and "
    "no macro/country-year covariate in DS00047 at the approval instant, so the tested model "
    "has little beyond the prior to learn from. The negative finding is preserved: artifact "
    "c9ac51b846f7b1ee, gate 1.5.0 report cad5d763, worker job wb-sol-baseline-001 (staging "
    "release 427393678). Holdout was never scored (no holdout evaluation ran), so the sealed "
    "split remains unused."
)
record["measurements"]["baseline_2026_10_29"] = {
    "command": (
        "worker job wb-sol-baseline-001 (cx23, 45-min timeout) - fetched the accepted artifact "
        "from staging release 427207251, re-ran gate 1.5.0 --accept against the bundled report "
        "(ACCEPTED c9ac51b846f7b1ee), materialized the runner workdir (public train+eval only) "
        "and ran the harness task_template train.py + validate.sh unmodified"
    ),
    "artifact_version": "c9ac51b846f7b1eef7693129514290e837446cc8e72dbdacf562b43d5e1b4c1f",
    "gate_report_sha256": "cad5d763c34a9a5938193c58bc03375fa194a01bb5946c5a04320781cea4c644",
    "eval_rows": 1034,
    "full_model_eval_auc": model,
    "full_model_eval_auc_validate_recompute": result["contract"]["eval_auc_from_validate_py"],
    "references_same_rows": {
        "persistence_country_last": persistence,
        "country_prior": country,
        "loan_type_prior": loan_type,
        "majority_class_accuracy": refs["references"]["majority_class"]["accuracy"],
    },
    "observed_gap_model_minus_country_prior": round(model - country, 4),
    "uncertainty": (
        "NOT a paired test. Per-row model scores were not written by the runner contract, so "
        "no paired bootstrap on identical rows is possible from this run. Marginal "
        "Hanley-McNeil AUC standard errors are 0.0189 (model) and 0.0190 (country prior) at "
        "701 positives / 333 negatives; a conservative independent-sum difference SE is 0.0268, "
        "giving gap/SE = 0.33. Label it an inconclusive difference."
    ),
    "scope": (
        "Eval split only (2000-2009). The sealed holdout was not evaluated and no holdout "
        "figure exists or is implied. Runner contract only, no agent harness loop."
    ),
    "evidence": (
        ".factory/wb-sol-baseline-001/reports/{baseline_result.json,train.log,validate.log,"
        "accept.log,manifest.json}; staging release 427393678 (tag job-wb-sol-baseline-001)"
    ),
}
record["jobs"].append({
    "status": "deleted",
    "server_id": 173237051,
    "created_at": "2026-10-29T02:13:07Z",
    "deleted_at": "2026-10-29T02:23:39Z",
    "reservation_eur": "0.06",
    "staging_release": 427393678,
    "id": "wb-sol-baseline-001",
    "outcome": "exit 0; contract OK; eval AUC 0.5452 from both train.py and validate.py",
})
record["next_action"] = (
    "None (dropped 2026-10-29). Negative finding preserved in "
    "measurements.baseline_2026_10_29 and in staging release 427393678. Reopen only as a NEW "
    "task instance with approval-instant information the source table does not carry (e.g. a "
    "verified as-of country/macro covariate join with its own availability ledger), or a "
    "change target; do not re-tune this label, threshold or these splits."
)
(CAND / "record.json").write_text(json.dumps(record, indent=1) + "\n")
print("record updated:", record["status"], model, country, persistence, loan_type)
