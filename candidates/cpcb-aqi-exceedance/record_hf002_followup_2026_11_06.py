#!/usr/bin/env python3
"""Record the cpcb-aqi-hf-002 outcome (worker-status follow-up, 2026-11-06).

Updates jobs[] in the candidate record to succeeded_and_deleted with the
verified evidence, rewrites next_action to the remaining release-sequence
steps (run-time ceiling stopped this session before hf-publish --verify),
and prepends the STATE.md entry. Asserts every field it reads first."""
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
REC = BASE / "candidates" / "cpcb-aqi-exceedance" / "record.json"
STATE = BASE / "STATE.md"
LEDGER = BASE / "jobs" / "cpcb-aqi-hf-002.json"

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
ledger = json.loads(LEDGER.read_text())
assert ledger["status"] == "deleted", ledger["status"]
assert ledger["result"]["status"] == "succeeded"
record = json.loads(REC.read_text())

job = None
for entry in record["jobs"]:
    if entry.get("id") == "cpcb-aqi-hf-002":
        job = entry
        break
assert job is not None
assert job["status"] == "running", job["status"]
assert job["parent_job"] == "cpcb-aqi-hf-001"
assert job["server_id"] == 174835948

job["kind"] = "hf_publish"
job["status"] = "succeeded_and_deleted"
job["collected_at"] = "2026-11-06T15:58:47Z"
job["deleted_at"] = "2026-11-06T16:11:10Z"
job["elapsed_seconds"] = 104.0
job["staging_release"] = 436695608
job["provider_read_back"] = ("GET /v1/servers/174835948 -> 404 not_found "
                             "(2026-11-06T16:11Z); project servers 0, primary_ips 0")
job["outcome"] = (
    "SUCCEEDED: the single changed retry closed the HF bulk upload of private release "
    "436366305 to the private Hub repo earino/cpcb-aqi-exceedance. Four assets skipped "
    "'already at the manifest digest' (meta.json, data/private-holdout.csv, "
    "data/public-train.csv, quality.json); public-eval.csv fetched at the manifest digest "
    "(20210392 B e187f645445e135e092898a280e74a2ecba6e75cb25ed9c5470d6f96f779c478) and "
    "uploaded with the Hub-reported digest verified. Hub-side read-back: all five files at "
    "manifest digests, ok true, errors [], main commit 2535150e7f9301416d7b24d1627738b265789a35. "
    "Documented load_dataset check green and equal to hf/job.json verify_loading "
    "(train 288754 rows/61075 pos, eval 126570/19819, holdout 145124/18222, 23 columns, "
    "labels {0,1}, problems []). ALL 53 RECORDED ACCEPTANCE CHECKS PASS "
    "(verify_hf002_outcome_2026_11_06.py: collected result vs hf/job.json vs frozen "
    "MANIFEST.json). Evidence: staging release 436695608 manifest (9021 B sha 02cddeb34ea87"
    "14e08010518cf35b6a312875842e540b74c3041b73d950a6e66) fetched digest-verified to "
    ".factory/cpcb-aqi-hf-002/reports/; host_cleanup_complete true (no unique bytes on the "
    "worker); no bulk CSV ever reached the coordinator."
)

old_na = record["next_action"]
assert "cpcb-aqi-hf-002 RUNNING" in old_na, old_na[:120]
record["next_action"] = (
    "PRIVATE STAGING; BOTH DESTINATIONS' BYTES NOW LANDED AND VERIFIED; RELEASE-SEQUENCE "
    "CLOSE-OUT REMAINING (run-time ceiling stopped the 16:12Z follow-up after collection, "
    "acceptance verification and provider-confirmed worker deletion). CLOSED: consumer-002 "
    "green; cpcb-aqi-hf-002 SUCCEEDED (53 acceptance checks green, Hub holds all five "
    "assets at manifest digests on main commit 2535150e7f9301416d7b24d1627738b265789a35, "
    "load_dataset green). REMAINING, in order: (a) python3 scripts/hf-publish.py --verify "
    "--candidate cpcb-aqi-exceedance --worker-job cpcb-aqi-hf-002 --token-file "
    "/opt/data/.secrets/huggingface-write.token (exit 0 required; writes the huggingface "
    "block of release/cpcb-aqi-exceedance/DESTINATIONS.json); (b) --tag LAST (tag v2026.11 "
    "== verified main commit, idempotent); (c) DESTINATIONS.json github block (write "
    "programmatically, same shape as eutl): repo earino/cpcb-aqi-exceedance, release_id "
    "436366305, tag v2026.11, target_commit cb3b251faa9e3cac37231746474585cc77f6f9c9 re-read "
    "from the API, private true, verified true + timestamp, files_verified = the five logical "
    "manifest paths (public/train.csv, public/eval.csv, private/holdout.csv, meta.json, "
    "quality.json), checks citing the transfer job cpcb-aqi-publish-001 (5/5, failures []), "
    "the live server-side read-back and the consumer-002 evidence; top-level artifact_version "
    "a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959; (d) record -> packaged: "
    "packaged_at + artifacts[0] structured release identity, generate the pre-flip adversarial "
    "audit prompt from skills/dataset-release/templates/pre-flip-audit-prompt.md with digests "
    "filled programmatically from the frozen manifest, then awaiting_operator TRUE; (e) read "
    "the CI run for the 16:12Z push commit first, then checks: check-candidate --all, "
    "check-package release/cpcb-aqi-exceedance, check-suitability, full suite; commit/push and "
    "read CI for that exact commit. The flip stays the operator's single approval and waits for "
    "the independent auditor's verdict unless waived. Holdout sealed; no re-tuning after any "
    "score."
)
record["updated_at"] = now

# jobs[]-order sanity: the -002 entry must still follow -001
ids = [e.get("id") for e in record["jobs"]]
assert ids.index("cpcb-aqi-hf-002") == ids.index("cpcb-aqi-hf-001") + 1, ids
REC.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")

state_entry = f"""## 2026-11-06 ({now}) - follow-up (worker-status runner): cpcb-aqi-hf-002 SUCCEEDED - HF bulk upload complete and verified (eval at the manifest digest, Hub read-back 5/5 manifest digests at commit 2535150e, load_dataset green); 53 recorded acceptance checks pass; worker 174835948 destroyed with provider 404 read-back (0 servers, 0 IPs); remaining: hf-publish --verify, --tag, DESTINATIONS github block, packaged + pre-flip audit prompt + awaiting_operator; nothing public, holdout sealed

Watcher follow-up for cpcb-aqi-hf-002 (the single changed retry for the hf-001 eval-digest
spec defect; that recovery is spent and it succeeded). The shared research mutex was this
runner's for the whole invocation. Unrelated untracked work (candidates/fenz-incident-data/)
inspected and left untouched, not committed.

- COLLECTED (ledger collected_at 15:58:47Z, result.json present): succeeded, elapsed
  104.0 s. Four assets skipped 'already at the manifest digest' (meta.json,
  data/private-holdout.csv, data/public-train.csv, quality.json); public-eval.csv fetched
  at the manifest digest (20210392 B e187f645445e135e092898a280e74a2ecba6e75cb25ed9c5470d6f96f779c478)
  and uploaded with the Hub-reported digest verified; Hub-side read-back: all five files
  at manifest digests, ok true, errors [], main commit
  2535150e7f9301416d7b24d1627738b265789a35; load_dataset check green and equal to
  hf/job.json verify_loading (train 288754/61075, eval 126570/19819, holdout 145124/18222,
  23 columns, labels {{0,1}}, problems []). ALL 53 RECORDED ACCEPTANCE CHECKS PASS
  (verify_hf002_outcome_2026_11_06.py: collected result vs hf/job.json vs the frozen
  release MANIFEST.json).
- CLEANUP (deletion confirmed by the provider): worker 174835948 destroyed 16:11:10Z;
  GET /v1/servers/174835948 -> 404 not_found; project servers 0, primary_ips 0.
  Preservation accounted before teardown: all five assets durable on the Hub at manifest
  digests (Hub read-back in the job result) and on GitHub release 436366305 (verified
  server-side 15:45Z); host_cleanup_complete true. Staging evidence fetched
  digest-verified: release 436695608 manifest (9021 B sha 02cddeb34ea8714e08010518cf35b6a312875842e540b74c3041b73d950a6e66)
  to .factory/cpcb-aqi-hf-002/reports/. No bulk CSV ever reached the coordinator.
- NOT DONE THIS SESSION (wall-clock ceiling; precise handoff in record.next_action):
  hf-publish.py --verify (writes the huggingface block of DESTINATIONS.json), --tag LAST,
  the DESTINATIONS.json github block, packaged_at + pre-flip audit prompt + awaiting_operator
  TRUE, the full local suite, and the exact-commit CI read for this push (unread at close;
  the next session reads the run for this commit FIRST). The flip remains the operator's
  single approval and waits for the independent auditor's verdict unless waived. Holdout
  sealed; no figure newly quotable beyond the already-recorded qualified references.

Next action (also in record.next_action): steps (a)-(e) above, starting with the CI read
for this commit, then hf-publish.py --verify and --tag.

"""
old_state = STATE.read_text()
assert old_state.startswith("## 2026-11-06 (15:52Z) - follow-up"), old_state[:60]
STATE.write_text(state_entry + old_state)
print(f"record + STATE updated at {now}; job outcome recorded, next_action rewritten")
