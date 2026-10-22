# Testing every cleanup path

A worker system has more than one way for a paid resource to end, and only the normal path gets
exercised by accident. The others are the ones that strand machines: expiry when a coordinator is
gone, a lost artifact transfer, and a job that failed. Test each deliberately - one worker at a
time, provider-confirmed after each - and record which path acted, because "the worker is gone"
without "and this is what removed it" is not verification of the cleanup system.

Preconditions for all of them: the launch gate is open for the window, the account baseline is
taken, and the policy's cleanup flag is on.

## Normal path (the baseline the others are compared against)

Collect, verify each asset's digest against the producer's manifest, destroy, then read the
provider's inventory for zero of every resource type. Every other path below is a deviation from
this one, so establish it first.

## Expiry

Goal: prove the *scheduler*, not you, removes an expired machine.

1. Launch a job and deliberately **do not collect it**.
2. Read the refusal back from the normal teardown path. While the job is uncollected and
   unexpired, teardown must refuse it - that refusal is what leaves expiry as the only path that
   can remove the resource, so quote it as part of the evidence.
3. Size the lifetime so expiry lands shortly before the sweep's next tick. The launch path
   generally enforces a floor (`timeout_minutes + 15 <= lifetime_minutes`), so a small job timeout
   does **not** buy a small lifetime; compute the tick you are aiming at before launching.
4. Poll the provider directly on a fixed interval until the resource disappears. Record the lag
   after expiry and which tick acted, reading the scheduler's own run record rather than assuming
   it was the tick you expected.
5. Re-run the inventory probe: zero servers and zero secondary IPs.

An expired worker is exactly the case the sweep exists for, so its assets staying in staging is
correct: expiry reclaims compute, not artifacts.

## Upload recovery

Goal: prove the finished run is **reused rather than repeated**, and the artifacts are re-published.
This is the artifact-transfer path alone - the coordinator's own session being lost is a different
failure with a different test, below - so do not file it under "session recovery".

1. Let a job run cleanly and collect it once, keeping the report's execution identity fields.
2. Destroy the transfer target - delete the artifact release - then confirm the collect now fails.
   That failure *is* the recovery condition; do not simulate it with a flag when you can produce
   the real thing.
3. Run the project's documented recovery command, then collect again.
4. Prove reuse by comparing the execution identity fields before and after - exit code, elapsed
   time, resolved image digest. Identical values plus a **new** release id is the evidence: a
   rerun would move the elapsed time. This is the property that matters, because re-running a
   completed data job on recovery is silent double-billing and can double-emit side effects.

## Coordinator-session recovery

Goal: prove a **new coordinator session** can pick up persisted state and reconcile a live resource
without the conversation that created it. The transfer can be perfectly intact while the only
session that knows the worker exists is gone.

The mechanism that makes this necessary: a scheduled sweep deletes at the provider and touches
nothing in the coordinator's ledger. After an expiry sweep acts, the job record still reads
`running`, so the ledger's view of the world is corrected only when a session reconciles or closes
it. "The sweep cleans up" and "the record is accurate" are therefore two different claims.

1. Reconcile a resource whose recorded state is stale - the post-expiry record is the ideal case,
   because it is genuinely out of date rather than simulated to be.
2. Start a fresh agent session from outside the repository, with no prior context. Give it the
   project path, tell it to prefer the ledger and the operations document over the narrative state
   file, and require the record's fields reported verbatim.
3. Constrain it explicitly: read that ledger, run the project's reconcile command, launch nothing,
   and leave the schedules alone. A recovery test that provisions a replacement resource has
   changed the thing it was measuring.
4. Verify its claim independently - diff the record before and after, read the provider, and confirm
   no resource appeared.

Accept an honest inference as a pass: a fresh session that sees a reconcile exit `0` can only
*infer* that the provider still holds the resource, because that is all the command tells it. Say so
in the write-up instead of upgrading it to "observed".

## Failed job

Goal: prove failure is inspectable **and** still collectable.

1. A job that exits non-zero on purpose (a distinct code such as 7, not 1) after writing a partial
   output and printing to both stdout and stderr.
2. Expect the executor to record the non-zero exit code, mark the report failed, and still upload.
3. Recover the diagnostics from the artifact host and check their digests against the manifest:
   the partial output written before the failure, and the captured container log including stderr.
4. Then use the normal teardown. A failed job that uploaded is collectable like any other, so
   failure is not a reason for a different or skipped cleanup.

## Pitfalls

- **A refused launch is not a failed launch.** Validation that rejects the job before provisioning
  means no cloud call was made. Confirm that against the provider inventory rather than assuming an
  orphan was left behind - and equally, do not report the refusal as a launch failure.
- **Draft releases are not readable by name.** Assets in a draft release are absent from the public
  download URL and a release-download helper refuses drafts. Read them through the authenticated
  API with an `application/octet-stream` accept header, resolving the asset id from the release's
  asset list first.
- **Testing only the path that runs by itself.** The normal path is exercised every time; expiry,
  recovery and failure are not. Those three are the money-leaking paths.
- **Letting one test's resources warm the next test's baseline.** Confirm zero between tests, so
  each provider reading is unambiguous.
- **Waiting in the foreground.** A long poll loop run as a foreground command is cut off at the
  command ceiling, taking its accumulated output and exit status with it, and it cannot outlive the
  turn that started it. Run the wait as a background process with completion notification, have it
  print a timestamped line per poll, and let it exit on the event itself - then the lag it measured
  is still there to read afterwards.
- **Reporting the resource as gone without the acting path.** Two independent schedulers can run
  the same sweep, so name which one deleted the resource or the verification cannot be re-checked.
  Attribute it positively: the acting scheduler's own run record usually prints what it removed
  (the deleted resource ids), which is stronger evidence than the observed lag alone. Then
  *exclude* the other scheduler rather than assuming it was idle — list its runs and confirm none
  falls between the last poll that still saw the resource and the poll that found it gone. Two
  schedulers on different cadences will otherwise both look plausible, and the one you name is the
  one a later session will trust.
