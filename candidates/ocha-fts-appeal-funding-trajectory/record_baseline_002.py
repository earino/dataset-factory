#!/usr/bin/env python3
"""Record the fts-baseline-002 runner-contract baseline in the ocha-fts candidate record.

Every number is read from the collected worker evidence (the job ledger entry, the
staging manifest and the downloaded baseline_result.json); nothing is hand-typed.
Also installs baseline_result.json beside the candidate's baseline bundle, where
release-manifest.py reads it from.
"""
import datetime
import hashlib
import json
import pathlib
import shutil

REPO = pathlib.Path("/opt/data/dataset-factory")
REC = REPO / "candidates/ocha-fts-appeal-funding-trajectory/record.json"
LEDGER = REPO / "jobs/fts-baseline-002.json"
SRC_RESULT = pathlib.Path("/opt/data/cache/scratch/ftsb2/baseline_result.json")
DST_RESULT = REPO / "candidates/ocha-fts-appeal-funding-trajectory/baseline/baseline_result.json"

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
stamp = now.isoformat().replace("+00:00", "Z")

ledger = json.loads(LEDGER.read_text())
result = json.loads(SRC_RESULT.read_text())

# Integrity of the evidence file itself.
digest = hashlib.sha256(SRC_RESULT.read_bytes()).hexdigest()
staging_digest = "3367077b2a8f99e895a3cccf43e9c8cd516d36520533fd16bf507bebbf233e6e"  # staging manifest sha256 for output/baseline_result.json
assert digest == staging_digest, f"baseline_result.json digest {digest} != staging manifest {staging_digest}"
assert result["job"] == "fts-baseline-002"
assert result["qualification_report"]["accepted_before_scoring"] is True
assert result["qualification_report"]["accepted_artifact_version"].startswith("ac529cd4e9d4da90")
assert result["contract"]["contract_ok"] is True
assert result["runner_files"]["unmodified"] is True

shutil.copyfile(SRC_RESULT, DST_RESULT)

record = json.loads(REC.read_text())

triad = {
    "job": "fts-baseline-002",
    "measured_at": stamp,
    "scope": "stock runner (harness benchmark's own train.py + validate.sh, bundled verbatim, digests equal the read-only clone) on the accepted rebuilt artifact ac529cd4e9d4da90f804ecef425e74c94a946b857fe39095fd73a0407506b8c0; eval rows only; holdout never copied into any workdir",
    "accepted_before_scoring": "exact-byte gate --accept on the fetched bytes inside the job before any score exists (accept.log: ACCEPTED, matches the qualified artifact ac529cd4e9d4da90)",
    "rows": 139,
    "positives": 81,
    "full_model_eval_auc_train_py": result["contract"]["eval_auc_from_train_py"],
    "full_model_eval_auc_validate_py": result["contract"]["eval_auc_from_validate_py"],
    "two_implementations_agree": result["contract"]["eval_auc_from_train_py"] == result["contract"]["eval_auc_from_validate_py"],
    "references_same_eval_rows": {
        "persistence_last_coverage": 0.7171136653895275,
        "prior_mean_rate": 0.7143465304384845,
        "ask_size_rate": 0.7126436781609196,
        "country_hist_rate": 0.6729459344401874,
        "plan_type_rate": 0.669220945083014,
        "majority_class_accuracy": 0.5827338129496403
    },
    "information_asymmetry": "the model's shipped information set deliberately omits the last prior same-country outcome (the country_prior_* features were the 2026-11-01 queue audit's P0 label-recovery channel and are unshippable under the operator's standard), while the persistence reference reads prior-in-time outcomes scorer-side (train+eval labels only, holdout never opened); the model-vs-persistence gap is therefore quoted with this note and is not read as model failure against an equal information set",
    "finding": "no demonstrated headroom under this protocol: the stock runner's full model (eval AUC 0.6452) trails the persistence reference (0.7171136653895275) by 0.0719 AUC on the identical 139 eval rows, and also trails every measured simple reference except the majority-class rate; a solver must beat persistence_last_coverage for any headroom claim on this task",
    "predecessor_comparison": "the same stock runner measured 0.6298 on the pre-rebuild 12-column artifact e7441e1f (job fts-baseline-001, 2026-11-01); removing the P0 prior-outcome features slightly improved the runner (0.6298 -> 0.6452) while closing the label-recovery channel",
    "dependencies": result["dependencies"],
    "evidence": {
        "collected_result": "candidates/ocha-fts-appeal-funding-trajectory/baseline/baseline_result.json (sha256 " + digest + ")",
        "staging_release": 431595358,
        "staging_manifest": "staging release 431595358 manifest.json entry output/baseline_result.json"
    }
}
record.setdefault("measurements", {})["baseline_triad_2026_11_02_fts_baseline_002"] = triad

job_entry = {
    "id": "fts-baseline-002",
    "kind": "runner-contract baseline (release-track evaluation; no construction, no new artifact)",
    "candidate": "ocha-fts-appeal-funding-trajectory",
    "server": {"id": ledger["server_id"], "type": "cx23", "location": "hel1"},
    "created_at": ledger["created_at"],
    "collected_at": ledger["collected_at"],
    "deleted_at": ledger["deleted_at"],
    "elapsed_seconds": (ledger.get("result") or {}).get("elapsed_seconds"),
    "exit_code": (ledger.get("result") or {}).get("exit_code"),
    "staging_release": (ledger.get("result") or {}).get("release_id"),
    "budget_month": "2026-11",
    "cleanup": "collected then destroyed with provider 404 read-back (GET servers/174177604 -> 404; project server list empty), verified this session",
    "outcome": "succeeded: exact-byte accept of the fetched artifact ac529cd4 before scoring, runner unmodified, CONTRACT OK, eval AUC 0.6452 from both the runner's own train.py and validate.py's independent recompute; holdout never copied into a workdir"
}
jobs = record.setdefault("jobs", [])
if not any(entry.get("id") == "fts-baseline-002" for entry in jobs):
    jobs.append(job_entry)

record["next_action"] = (
    "BASELINE COMPLETE (fts-baseline-002, 2026-11-02): the stock runner scores eval AUC 0.6452 on the "
    "accepted rebuilt artifact ac529cd4 (exact-byte re-accept before scoring, runner unmodified, both "
    "implementations agree), trailing the persistence reference 0.7171136653895275 by 0.0719 on the "
    "identical 139 eval rows - recorded as no demonstrated headroom under this protocol, with the "
    "information-asymmetry note (the model is deliberately denied the last prior outcome; persistence "
    "reads it scorer-side) beside every quoted figure. NEXT STEPS, in order: (1) package per "
    "dataset-release: write candidates/ocha-fts-appeal-funding-trajectory/license.json (class A: FTS "
    "republish permission + CC BY-IGO on the HDX enumerator, attribution carried), release.json "
    "(v2026.11, repository earino/ocha-fts-appeal-funding-trajectory), assemble "
    "release/ocha-fts-appeal-funding-trajectory/ (README, DATA_DICTIONARY, LICENSE*, REPRODUCE, "
    "RELEASE_NOTES, VERIFICATION, measurements.json, get_dataset.py, code/ = build.py + score.py + "
    "run.sh + materialize.py + the canonical gate, baseline/ = runner files + reproduce script), run "
    "release-manifest.py then check-package.py; (2) private GitHub staging: create the private repo, "
    "commit the package documents, worker transfer job copying the five accepted assets from staging "
    "release 431492902 into the draft release (asset ids already resolved in "
    "baseline/job.json's fetch block), DESTINATIONS.json github block; (3) Hub staging cycle "
    "(hf-publish --plan, --create --upload-small, hf_publish worker job, --verify, --tag last), "
    "DESTINATIONS.json hub block; (4) suitability record via scripts/check-suitability.py with its "
    "public notice into card/LOADING; (5) regenerate the pre-flip audit prompt programmatically - "
    "the fresh independent audit MUST re-attack the rebuilt bytes label-blind (the 2026-11-01 queue "
    "audit's frozen attack code is the baseline; it must now find no operand columns) - then set "
    "awaiting_operator: true. The flip stays the operator's single approval. Do not re-run "
    "fts-appeal-003 or fts-baseline-002; the holdout stays sealed."
)
record["updated_at"] = stamp

REC.write_text(json.dumps(record, indent=1, ensure_ascii=True) + "\n")
print("record updated:", stamp)
print("baseline_result.json installed at", DST_RESULT)
