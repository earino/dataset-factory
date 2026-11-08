UCMR publish-1 failure pinpoint + pause record (2026-11-08T20:52Z).

PAUSE: scout-factory-tick paused 20:50:48Z at a safe boundary (no
in-flight model/worker children; source-15 build-2 repair result
preserved on disk unvalidated; cleanup sweep cron remains active).
No new publication attempts will launch; no retries burned.

FAILURE PINPOINT (read-only code + state inspection):
- Failing operation: hub_control action='publish' - the Hugging Face
  Hub control helper subprocess, workers/release_publish.py:110-121,
  invoked at publication_stage='publish' (line 203-204) AFTER verified
  GH + HF file transfers (transfer.failures=[], hf_publish.failures=[]).
- Helper sequence inside the subprocess: verify Hub main commit ->
  create version tag if absent -> update_repo_settings(repo_id,
  repo_type='dataset', private=False) -> repo_info verification.
- Suppression point: subprocess.run(capture_output=True) at line 115;
  on nonzero return, line 118 raises UploadError('Hub publish failed;
  remote state will be reconciled on retry') and DISCARDS
  result.stderr - the exact helper exception and any HTTP status are
  lost. No log survives; the worker is deleted.
- State readbacks bracketing the failure: GitHub repo
  earino/factory-ucmr5-first-sample-pfas exists and REMAINS PRIVATE
  (the PATCH private=false at line 206 never ran); Hugging Face
  dataset repo earino/factory-ucmr5-first-sample-pfas EXISTS and is
  STILL PRIVATE (unauthenticated API GET -> HTTP 401). Therefore the
  helper failed before the visibility flip took effect: at main-commit
  verification, tag creation, or update_repo_settings itself.
- Error class recorded in the manifest: UploadError; failure_stage
  release_publish; exit 1; elapsed 199 s. HTTP status: unknown (lost
  with the discarded stderr).
- operator note: upstream HfApi.update_repo_settings(private=False,
  repo_type=dataset) signature is valid; no API-change assumption.

NEXT: the operator's structured error receipt for the existing helper
(capturing operation/error class/HTTP status from the same subprocess)
makes the next attempt diagnosable; the designed retry then reconciles
destination files and tags safely. No manual visibility flip, no
acceptance-gate change.

ADDENDUM 21:02Z: publish-2 (launched by the in-flight tick seconds
before the 20:50:48Z pause; preserved per operator instruction) FAILED
IDENTICALLY at 21:00:06Z - UploadError, failure_stage release_publish,
publication_stage publish, elapsed 119.6 s, staging release 438514274.
Repeatability CONFIRMED with real evidence; its job bundle predated the
fix, so no structured receipt. The create_tag keyword-only fix
(948e3ce) deployed 20:59:39Z; tick resumed 21:00Z. Next retry
(publish-3) assembles from fixed code with structured error receipts.
Job record exported alongside publish-1's.
