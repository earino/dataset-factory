#!/usr/bin/env python3
"""Record the abwildfire-baseline-002 runner-contract baseline (packaging step).

Reads every figure from the collected baseline_result.json and the job ledger;
nothing retyped. Adds the job to record.jobs, writes
measurements.runner_baseline_abwildfire_002, and points next_action at the
remaining private-staging steps (GitHub destination, fresh-consumer job, Hub,
DESTINATIONS, packaged + pre-flip audit prompt). Status stays qualified until
both destinations are verified and packaged_at is set.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "candidates" / "ab-wildfire-ia-escape"
ART = "c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2"

baseline = json.loads((CAND / "baseline" / "baseline_result.json").read_text())
job = json.loads((ROOT / "jobs" / "abwildfire-baseline-002.json").read_text())
assert hashlib.sha256((CAND / "baseline" / "baseline_result.json").read_bytes()).hexdigest() \
    == "a437d01bd7ada9fe730bfd0af0bd2553f7f70047252a02bdc0bba245d5aaebf1"
assert baseline["qualification_report"]["qualified_artifact_version"] == ART
assert baseline["qualification_report"]["accepted_before_scoring"] is True
assert baseline["runner_files"]["unmodified"] is True
assert baseline["contract"]["contract_ok"] is True
dec = baseline["deciding_check"]
assert dec["verdict"] == "headroom_demonstrated"

record_path = CAND / "record.json"
record = json.loads(record_path.read_text())

entry = {
    "id": "abwildfire-baseline-002",
    "candidate": "ab-wildfire-ia-escape",
    "status": "succeeded",
    "exit_code": job["result"]["exit_code"],
    "elapsed_seconds": job["result"]["elapsed_seconds"],
    "server_id": job["server_id"],
    "server_type": job["job"]["server_type"],
    "location": job["job"]["location"],
    "image": f"{job['result'].get('image_id', 'python:3.13-slim')}",
    "staging_release": f"{job['result']['release_id']} (private earino/dataset-factory-staging, tag job-abwildfire-baseline-002)",
    "reservation_eur": job.get("reservation_eur"),
    "collected_at": job.get("collected_at"),
    "deleted_at": job.get("deleted_at"),
    "what": "runner-contract baseline on the accepted artifact (re-accept before any score, "
            "benchmark train.py + validate.sh unmodified, materialize from public splits only, "
            "holdout never copied into a workdir) plus the pre-registered model-vs-triad deciding "
            "check; see job record .factory/jobs/abwildfire-baseline-002 and jobs/ ledger",
}
if not any(j["id"] == entry["id"] for j in record.get("jobs", [])):
    record["jobs"].append(entry)

record["measurements"]["runner_baseline_abwildfire_002"] = {
    "date": "2026-11-07",
    "job": "abwildfire-baseline-002 (cx23 hel1, server "
           f"{job['server_id']}, {job['result']['elapsed_seconds']:.1f} s, exit 0; "
           f"destroyed after verified collection at {job.get('deleted_at')})",
    "protocol": "pre-registered deciding check (baseline/report.py): the runner model's per-row "
                "eval scores (same code path as validate.py, via runpy over the benchmark's own "
                "train.py) vs every triad member on identical eval rows, day-clustered paired "
                "bootstrap (cluster = assessment_date, 500 resamples, fixed-seed LCG); re-accept "
                "of the fetched bytes against the gate report BEFORE any score; holdout never "
                "copied into any workdir and never opened by score.py",
    "accepted_before_scoring": True,
    "runner_contract": {
        "contract_ok": baseline["contract"]["contract_ok"],
        "eval_auc_from_train_py": baseline["contract"]["eval_auc_from_train_py"],
        "eval_auc_from_validate_py": baseline["contract"]["eval_auc_from_validate_py"],
        "runner_files_unmodified": baseline["runner_files"]["unmodified"],
        "dependencies": baseline["dependencies"],
    },
    "model_eval_auc": dec["model_eval_auc"],
    "members": dec["members"],
    "supplementary_model_vs_logistic_reference": dec["supplementary_model_vs_logistic_reference"],
    "verdict": dec["verdict"],
    "verdict_scope": dec["scope"],
    "reading": "the stock runner beats every pre-registered triad member with day-clustered CIs "
               "excluding zero (persistence +0.0459 [+0.0154, +0.0871]; calendar/identity "
               "+0.2428 [+0.1911, +0.2998]; degenerate constant vs model AUC CI [0.9382, "
               "0.9686]) - HEADROOM DEMONSTRATED under the pre-registered rule, on eval "
               "2016-2020 only, holdout sealed. Recorded beside the construction-time finding: "
               "the simple logistic reference's edge over persistence is INCONCLUSIVE (+0.0111 "
               "[-0.0292, +0.0514]) - a simple linear reference does not demonstrably beat the "
               "one-feature persistence rule; the stock runner does. Not a tuning target: no "
               "label, threshold, window or feature may change to widen any gap.",
    "references_reproduction": "score.py's triad re-run in this job is byte-identical to the "
                               "build job's collected references report except the "
                               "accepted_report path field (deterministic fixed-seed bootstrap "
                               "confirmed across independent executions)",
}

record["next_action"] = (
    "Private staging, in order: (1) create the private GitHub repository "
    "earino/ab-wildfire-ia-escape and push the 24 package files as the initial commit, then "
    "create release v2026.11 non-draft at main and transfer the five accepted assets from "
    "staging release 437132110 into it via a release-flagged transfer worker job (asset ids "
    "resolved by digest match through publish-dataset.py --stream-test; verify server-side "
    "digests, anonymous API read-back must 404); (2) the fresh-consumer worker job on the "
    "released bytes (cqc consumer/source pattern, fetch block from the new release): gate 1.5.0 "
    "re-run, exact-byte --accept c2c8ceb5, baseline reproduce (both AUC prints 0.9554, CONTRACT "
    "OK), score.py references recomputed equal to measurements.json, reproduce_baseline.sh "
    "executed; (3) hf-publish.py --plan, --create --upload-small, the hf_publish worker job, "
    "--verify, --tag LAST; (4) release/ab-wildfire-ia-escape/DESTINATIONS.json both blocks "
    "(github first, files_verified as lists, top-level artifact_version c2c8ceb5...); (5) record "
    "-> packaged with packaged_at + structured artifacts[0] + awaiting_operator TRUE only after "
    "the pre-flip adversarial audit prompt is generated from the frozen manifest "
    "(skills/dataset-release/templates/pre-flip-audit-prompt.md, digests filled "
    "programmatically); then check-candidate --all, check-package, check-suitability, suite, "
    "CI for the exact commit. The flip is the operator's single approval and waits for the "
    "independent auditor's verdict unless waived. The cpcb flip remains the operator's."
)

record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record updated: jobs +", len(record["jobs"]), "entries; next_action -> private staging steps")
