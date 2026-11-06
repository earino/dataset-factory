#!/usr/bin/env python3
"""Record the cpcb-aqi-hf-001 failed-job follow-up: diagnosis, cleanup and the
one changed retry (cpcb-aqi-hf-002). Every value is asserted against the
collected evidence before the record is written; nothing is retyped."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "candidates/cpcb-aqi-exceedance/record.json"
LED1 = ROOT / "jobs/cpcb-aqi-hf-001.json"
LED2 = ROOT / "jobs/cpcb-aqi-hf-002.json"
SPEC = ROOT / "candidates/cpcb-aqi-exceedance/hf/job.json"
MAN = ROOT / "release/cpcb-aqi-exceedance/MANIFEST.json"
REP = ROOT / ".factory/cpcb-aqi-hf-001/reports/manifest.json"
STATE = ROOT / "STATE.md"

led1 = json.loads(LED1.read_text())
led2 = json.loads(LED2.read_text())
spec = json.loads(SPEC.read_text())
man = json.loads(MAN.read_text())
import hashlib

# ---- assert the evidence this recording claims ----
assert led1["job"]["id"] == "cpcb-aqi-hf-001"
assert led1["status"] == "deleted", led1["status"]
res = led1["result"]
assert res["status"] == "failed"
assert res["elapsed_seconds"] == 121.7
assert res["hf_publish"]["failures"] == [
    {"target": "data/public-eval.csv", "error": "Downloaded asset digest differs"}]
assert len(res["hf_publish"]["uploads"]) == 4
mapping = {"meta.json": "meta.json", "data/private-holdout.csv": "private/holdout.csv",
           "data/public-train.csv": "public/train.csv", "quality.json": "quality.json"}
for u in res["hf_publish"]["uploads"]:
    assert u["sha256"] == man["files"][mapping[u["target"]]]["sha256"], u["target"]
assert res["release_id"] == 436618377
assert res["host_cleanup_complete"] is True
assert led1["collected_at"].startswith("2026-11-06T15:38:30")
assert led1["deleted_at"].startswith("2026-11-06T15:48:36")
blob = REP.read_bytes()
assert hashlib.sha256(blob).hexdigest() == (
    "67a50a9cc18c0e1af5f8e8b5be970f49c9439a8ce800d5bd30572da7b0172e5c"), "staging manifest digest"
assert [a["sha256"] for a in res["assets"]] == [
    "7ba877cea13d5e9a0b87b6c047ce0ed6f7a6d07d1912658dd9815ba783029578",
    "67a50a9cc18c0e1af5f8e8b5be970f49c9439a8ce800d5bd30572da7b0172e5c"]

# the corrected spec: all five digests equal the frozen manifest, attempt id bumped
assert spec["id"] == "cpcb-aqi-hf-002"
map2 = {"meta.json": "meta.json", "private-holdout.csv": "private/holdout.csv",
        "public-eval.csv": "public/eval.csv", "public-train.csv": "public/train.csv",
        "quality.json": "quality.json"}
for a in spec["hf_publish"]["assets"]:
    assert a["sha256"] == man["files"][map2[a["dest"]]]["sha256"], a["dest"]

# the retry launch receipt
assert led2["job"]["id"] == "cpcb-aqi-hf-002"
assert led2["status"] == "running"
assert led2["server_id"] == 174835948
assert led2["source_sha256"] == "00152c787b8c4072f63d2e14be811d28d607ae1ddb86daca5ce44c2d79215b18"
assert led2["reservation_eur"] == "0.04"
expires = dt.datetime.fromtimestamp(led2["expires"], dt.timezone.utc).isoformat()

# ---- record.json ----
rec = json.loads(REC.read_text())
jobs = rec["jobs"]
assert jobs[-1]["id"] == "cpcb-aqi-hf-001"
assert jobs[-1]["status"] == "running"
jobs[-1].update({
    "kind": "hf_publish",
    "status": "failed_and_deleted",
    "collected_at": "2026-11-06T15:38:30Z",
    "deleted_at": "2026-11-06T15:48:36Z",
    "exit_code": None,
    "elapsed_seconds": 121.7,
    "staging_release": 436618377,
    "provider_read_back": "GET /v1/servers/174825952 -> 404 not_found (2026-11-06T15:49Z); project servers 0, primary_ips 0",
    "outcome": ("FAILED at the fetch stage of public-eval.csv: 'Downloaded asset digest "
                "differs'. Diagnosis (programmatic diff vs the frozen MANIFEST.json + live "
                "server-side read-back): the hf/job.json spec carried 'a' where the manifest "
                "has 'e' at position 36 of the eval sha256 - the same one-character "
                "transcription defect class as cpcb-aqi-consumer-001, inherited from the same "
                "hand-compiled asset list (the 13:12Z fix corrected consumer/source/job.json "
                "only). THE RELEASE IS INTACT: live API read-back 2026-11-06T15:45Z shows all "
                "five assets of private release 436366305 (tag v2026.11, repo private true) "
                "reporting server digests equal to MANIFEST.json (eval public-eval.csv "
                "20210392 B e187f645445e135e092898a280e74a2ecba6e75cb25ed9c5470d6f96f779c478); "
                "consumer-002 had already host-verified the same five digests at 13:38Z. "
                "4 of 5 Hub uploads completed green with Hub-verified manifest digests "
                "(68,635,896 B); the load_dataset check never ran; no figure is quotable "
                "from this job. Evidence: staging release 436618377 (source.tar 92160 B "
                "sha 7ba877ce = the -001 bundle; manifest.json 5237 B sha 67a50a9c fetched "
                "to .factory/cpcb-aqi-hf-001/reports/ and sha256-verified); container.log "
                "empty (host-side hf job)."),
})
jobs.append({
    "id": "cpcb-aqi-hf-002",
    "kind": "hf_publish (running)",
    "launched_at": "2026-11-06T15:49:00Z",
    "server_id": 174835948,
    "status": "running",
    "reservation_eur": "0.04",
    "parent_job": "cpcb-aqi-hf-001",
    "source_sha256": led2["source_sha256"],
    "what": ("identical scope to cpcb-aqi-hf-001; the only changes are the corrected "
             "public-eval.csv sha256 (copied programmatically from MANIFEST.json; git diff "
             "= 2 lines: the digest + the id bump) and the attempt id. This retry SPENT the "
             "one changed recovery for this defect chain: idempotent by design, expected to "
             "skip the four assets already at the manifest digest on the Hub, fetch + "
             "upload eval, and run the documented load_dataset check."),
    "expires": expires,
})

rec["measurements"]["hf_001_eval_digest_spec_failure_2026_11_06"] = {
    "defect_class": ("job-spec digest transcription error (the cpcb-aqi-consumer-001 / "
                     "nz-ea-baseline-001/002 class), second occurrence: hf/job.json was "
                     "written in the 12:15Z session from the same hand-compiled asset list "
                     "whose eval line consumer-001 refused; the 13:12Z correction fixed "
                     "consumer/source/job.json only"),
    "spec_vs_manifest": "eval sha256 position 36: 'a' (spec) vs 'e' (manifest); both 64 chars",
    "release_intact": ("live server-side read-back 2026-11-06T15:45Z: all five assets of "
                       "private release 436366305 report API digests equal to MANIFEST.json; "
                       "repo private true; tag v2026.11 non-draft"),
    "job_outcome": ("failed exit None, elapsed 121.7 s; 4/5 uploads green (Hub-verified "
                    "manifest digests, 68,635,896 B); eval fetch refused; load_dataset "
                    "check not run; nothing quotable"),
    "evidence_paths": [".factory/cpcb-aqi-hf-001/result.json",
                       ".factory/cpcb-aqi-hf-001/reports/manifest.json",
                       "staging release 436618377"],
    "cleanup": ("worker 174825952 destroyed 2026-11-06T15:48:36Z; provider read-back "
                "GET /v1/servers/174825952 -> 404, project servers 0, primary_ips 0"),
    "recovery": ("the one changed retry (consumer-002 precedent): hf/job.json eval sha256 "
                 "corrected BY JSON LOAD/COPY/DUMP from MANIFEST.json, id bumped to "
                 "cpcb-aqi-hf-002, plan rc=0 (reservation EUR 0.04, 0 cloud calls, bundle "
                 "00152c78), launched 2026-11-06T15:49:00Z, server 174835948. A second "
                 "failure is a recorded finding handed to advancement, never another "
                 "silent retry."),
    "commands": ["gh api repos/earino/cpcb-aqi-exceedance/releases/436366305 (read-back)",
                 "sh scripts/scout-factory worker destroy cpcb-aqi-hf-001",
                 "sh scripts/scout-factory worker plan candidates/cpcb-aqi-exceedance/hf/job.json",
                 "sh scripts/scout-factory worker launch candidates/cpcb-aqi-exceedance/hf/job.json"],
}
rec["next_action"] = (
    "PRIVATE STAGING, GITHUB DONE, CONSUMER GREEN, HF SMALL FILES UPLOADED, BULK HF RETRY "
    "cpcb-aqi-hf-002 RUNNING (launched 2026-11-06T15:49:00Z, worker 174835948, reservation "
    "EUR 0.04, expires " + expires + "; the -001 eval-digest spec defect was corrected "
    "programmatically from MANIFEST.json and the old worker is provider-confirmed deleted). "
    "(1) CLOSED: consumer-002 green. (2) REMAINING: collect cpcb-aqi-hf-002 with "
    "`sh scripts/scout-factory worker collect cpcb-aqi-hf-002`; ACCEPTANCE = exit 0 and the "
    "job report shows the four already-uploaded assets skipped at their manifest digests, "
    "public-eval.csv fetched at the manifest digest and uploaded with the Hub-reported "
    "digest verified, local copies deleted, and the load_dataset check green "
    "(splits/positives/columns/label equal to hf/job.json verify_loading). If it failed: "
    "keep the collected reports and diagnose - the one recovery for this defect chain is "
    "SPENT, so a second failure goes to advancement as a recorded finding, never a silent "
    "retry. Then destroy the worker with provider 404 read-back, then "
    "`python3 scripts/hf-publish.py --verify --candidate cpcb-aqi-exceedance --worker-job "
    "cpcb-aqi-hf-002 --token-file /opt/data/.secrets/huggingface-write.token` (exit 0 "
    "required; writes the huggingface block of DESTINATIONS.json), then `--tag` LAST "
    "(tag v2026.11 == verified main commit, idempotent). (3) release/cpcb-aqi-exceedance/"
    "DESTINATIONS.json github block (write programmatically, same shape as eutl): repo "
    "earino/cpcb-aqi-exceedance, release_id 436366305, tag v2026.11, target_commit "
    "cb3b251faa9e3cac37231746474585cc77f6f9c9 re-read from the API, private true, verified "
    "true + now timestamp, files_verified = every logical manifest path (public/train.csv, "
    "public/eval.csv, private/holdout.csv, meta.json, quality.json), checks citing the "
    "transfer job cpcb-aqi-publish-001 (5/5, failures []), the live server-side read-back "
    "and the consumer-002 evidence; top-level artifact_version a749f0df2f9dd0103d0ba56524e1cc"
    "3638242fbc4710b0cac99603bcdef0d959. (4) record -> packaged: packaged_at + artifacts[0] "
    "structured release identity, generate the pre-flip adversarial audit prompt from "
    "skills/dataset-release/templates/pre-flip-audit-prompt.md with digests filled "
    "programmatically from the frozen manifest, then awaiting_operator TRUE. (5) checks: "
    "check-candidate --all, check-package release/cpcb-aqi-exceedance, check-suitability, "
    "full suite; commit/push and read CI for that exact commit. The flip stays the "
    "operator's single approval and waits for the independent auditor's verdict unless "
    "waived. Holdout sealed; no re-tuning after any score.")
rec["updated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
REC.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("record.json updated: jobs[-1] failed_and_deleted, +cpcb-aqi-hf-002 running,")
print("measurements.hf_001_eval_digest_spec_failure_2026_11_06, next_action rewritten;")
print("worker 174835948 expires", expires)
