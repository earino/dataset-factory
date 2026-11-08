FINAL CUTOFF SNAPSHOT 2026-11-08 19:08:46Z (wind-down began 19:06:21Z)

Deployed SHA: 6ac5f833ce6a517db1ea15f56776b4f387aab8de (final
implementation target; includes f33b6af repair-contract fix; consumes
build-7's existing quality.task.features corrected-meanings format;
944 tests/13 skips; exact CI green; deployed 19:00:03Z).

Cutoff result: pipeline_enabled=false applied 19:06:21Z via the exact
cutoff script; scheduled backstop cron f0852e8c6392 fired 19:07
idempotently. Verified: config pipeline_enabled=false; last tick status
"waiting" with no new admissions; no live hermes/tick/model processes at
19:08:46Z. In-flight work at cutoff (UCMR build-8 construction child,
evaluate-3) completed and its artifacts remain in
.factory/model-tasks/; nothing was killed.

Queue (post-cutoff): sources 1-12 terminal (deferred at attempt limits or
rejected on terms evidence); source-13 UCMR at build attempt
rw-2ce60e8ae8f7-build-8 behind the standing factory remediation hold
("reopen only after R1-R4 acceptance and recorded reruns of the four
blocked packages"); source-14 ClinicalTrials REJECTED (not repaired:
access/renderability failure); source-15 at discover, unadmitted.

Workers: none. Jobs ledger fully reconciled - every job record deleted,
no pending collection. Provider: 0 servers, 0 primary IPs.

UCMR build-7 staged release 438449041: manifest still carries ORIGINAL
descriptions; needs a fresh corrected bundle before release. NOT
approved, NOT published (operator instruction; full qualification +
fresh semantic acceptance/publication remain unproven).

RESUME STEPS (in order):
1. Operator completes R1-R4 acceptance and the recorded reruns of the
   four blocked packages to clear the remediation hold.
2. Set pipeline_enabled=true in /opt/data/dataset-factory/config/local.json
   (single flag; the 6ac5f83+ tick resumes admissions automatically).
3. UCMR source-13 build-8 proceeds: fresh corrected bundle writing the
   corrected meanings in quality.task.features (existing format consumed
   by 6ac5f83), then full qualification, fresh semantic review, and
   publication gates - no manual approval shortcut.
4. source-15+ resume discovery under the 7b77595 ordering (admitted
   attempts first, then publication > review > construction >
   discovery, oldest-first). Deferred sources 1-12 require operator
   reopen decisions; rejected sources (5,7,8,10,14) stay closed.
5. Cleanup sweep and budget accounting continue unchanged.
