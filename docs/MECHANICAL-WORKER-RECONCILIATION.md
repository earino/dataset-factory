# Repeated worker close-out without a model

The watcher already collects results deterministically. The remaining gap was that
every terminal notification started another Hermes session, even when the outcome
had been collected, deleted and committed by an earlier session. The follow-up
runner now tries `sh scripts/scout-factory worker bookkeep <job>` while holding the
existing research mutex. Successful mechanical verification marks the notification
handled; a missing record, new outcome, mismatch or interrupted check reaches the
existing bounded model follow-up. Model and worker allowances are unchanged.

This path requires an exact committed job ledger with a terminal container result,
collection time and deletion time. It reuses the same staging verifier as collection:
job release tag, asset membership, sizes and server-reported SHA256 digests. It also
checks the exact server ID, job-labelled servers and primary IPs, including an
unassigned recorded address whose labels changed. It never calls delete or launch.
An old address recycled onto a different server is not old-job cleanup residue.

If a local collected report exists it must agree with the ledger. The ledger is
checked again after network observations. The compact local receipt binds ledger
and implementation hashes; repeat checks preserve the original receipt and manual
handled note while still making fresh staging/provider calls. No dataset rows are
downloaded and no candidate, qualification, release or publication state advances.
New results still need their ordinary first interpretation and durable handoff.
Host-operation jobs without a container exit code conservatively remain with the
model; no success value is invented for them.

Worker reconciliation now preserves the original deletion timestamp. Previously
each `status` call wrote a new `deleted_at`, which made ordinary rereads look like
another actor's cleanup. A ledger marked deleted while its owned server still
exists now refuses rather than letting `destroy` return a false completed state.

## Recorded-week replay

`scripts/replay-worker-followups.py` examines actual Scout follow-up commits with
STATE edits and reads each referenced ledger from the **parent** commit. It cannot
use a record that the follow-up itself was about to create. Any substantive file
change, new/incomplete outcome or ambiguous job context retains the model.

The preserved October 31–November 7 replay at `528154a` contains 30 recorded
follow-up commits. Five are bookkeeping-only sessions whose referenced parent
ledgers satisfy the mechanical prerequisite. They could skip the model only if
all mandatory live staging/provider checks also pass. The report names every
commit, parent, ledger hash and decision. This is a conservative conditional
replay, not a complete scheduler event archive or a claim of five sessions actually
saved; historical provider state has not been reconstructed. Runtime tests prove
that missing checks and mismatches cannot mark a job handled.

Before deployment, run the normal clean-clone suite and exact-commit CI. Scout can
then exercise one already completed job with the supported command and retain the
bounded receipt. No watcher schedule, token allowance, worker budget or expiry
changes are needed. The independent sweeper remains separate and active.
