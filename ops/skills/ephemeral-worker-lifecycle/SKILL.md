---
name: ephemeral-worker-lifecycle
description: "Use when running a job on paid ephemeral compute."
version: 1.1.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [cloud, worker, hetzner, smoke-test, teardown, cost, verification, artifacts]
    category: devops
    related_skills: [scheduled-job-verification, post-push-verification, hosted-agent-capability-audit]
---

# Ephemeral worker lifecycle

## When to use

Any task where a machine is created to do a job and must not outlive it: a cloud VM or container
for a build, a data extract, a benchmark or a model run; a paid API-backed sandbox; the first ever
execution of a pipeline whose launch path has never actually run.

A worker is not "done" when the job exits. It is done when the artifacts are verified **and** the
resource is confirmed gone from the provider's own API.

## Procedure

1. **Dry-plan first, and require the plan to be free.** Assemble the job and run the offline plan
   before spending anything; a plan reporting zero provider calls plus a reservation is the evidence
   that the bundle, the policy and the limits are coherent. A first-ever paid run must never also be
   the first test of the assembly path.
2. **Baseline the whole account, not your own records.** Immediately before provisioning, query the
   provider for every resource carrying the project's ownership label and record the count. A
   baseline of zero makes the after-state unambiguous: nothing else can account for what appeared,
   or for what is missing at the end. Keep this probe tracked in the repository as a small
   read-only script rather than in ignored scratch, so the next cycle does not rewrite it.
3. **Label every resource at creation** with owner, job id and expiry. Those labels are what the
   expiry sweep matches on, and what lets you enumerate exactly your resources instead of guessing
   from names.
4. **Open the enablement gate for the window only.** Set the policy flag the launch path actually
   reads, read it back, and note its previous value. Launches stay disabled by default; the gate
   opens for one supervised cycle and closes immediately afterwards.
5. **Stay with the job.** For a first cycle, watch it through teardown rather than launching and
   walking away - the interesting failures (image pull, entrypoint, artifact transport) happen in
   the first minutes and are cheap to catch with someone watching. When the run is longer than the
   turn that launched it, hand it to a scheduled watcher before ending the turn rather than leaving
   the operator as the polling mechanism: the launch notice fires when the launch exits, and the
   resource's status describes the machine. `scheduled-job-verification` ->
   `references/long-job-watchdog.md`. If a cleanup sweep takes the machine before the result is
   collected, the artifacts are still recoverable - uploads are tagged per job, and the run's own
   report can be checked against the stored digests without moving the bulk.
6. **Verify artifacts against the producer's own manifest, not just their presence.** Re-read each
   uploaded asset's size and integrity digest from the artifact host and compare with what the
   worker reported; a half-finished upload still produces a release and a list of names. Confirm
   the container actually executed - image digest, exit code, elapsed time, out-of-memory flag -
   since "a report exists" is also compatible with a cached or skipped run. Compare the built units
  against the count the run was supposed to consume: a job can exit cleanly having silently dropped
  a fraction of its inputs, and integrity, exit status and every check can still agree.
  When the job also
   produces a verdict of its own, bind that verdict to the same bytes: the report's recorded
   artifact identity must still match the manifest, which is checkable from the small files alone
   (`validation-gate-design`). When a *later* job has to measure against an artifact that was
   already accepted, and the worker cannot read the private store to fetch it, rebuild it on the
   worker and prove the rebuild is the accepted artifact before measuring anything:
   `references/running-a-pinned-benchmark.md`. When the worker *can* reach the store with a
   credential of its own, prefer fetching the bytes and mounting them read-only over rebuilding:
   that measures the published artifact rather than a reproduction of it, and a transfer into
   another repository is the same shape - one asset at a time, never through the coordinator.
7. **Destroy as soon as collection is verified**, not at the end of the day. A machine that has
   finished but is still running is the entire cost of the exercise. Nothing tears a machine down at
   its own expiry, though: a periodic sweep does that, so the sweep's **cadence** sets how long a
   finished machine keeps billing, and an interval measured in hours can leave one idle for most of a
   day. Tighten the interval to something proportionate, and confirm the sweep stays silent when it
   has nothing to delete before tightening it - a cheap frequent sweep is useless if it also becomes
   a stream of messages. Compute what was actually spent from the job records rather than quoting
   reservations: each record carries the machine's creation and deletion timestamps and the type's
   hourly rate, and the difference between its total life and its lifetime is the idle slice - which
   is routinely the largest single line in the bill and is invisible if you report only reservations.
8. **Confirm teardown against the provider.** Re-run the same inventory probe and require zero of
   every resource type you created, including the secondary ones - a floating or primary IP
   outlives the server that used it. Then run the project's sweep and require no errors, but treat
   an empty sweep as wiring evidence rather than proof of deletion: on the normal path it is exactly
   what an already-clean account returns.
9. **Test the other cleanup paths before trusting the system unattended.** The normal path is
   exercised every time; expiry, a lost artifact transfer, a failed job and the loss of the
   coordinator's own session are not, and those are the ones that strand paid machines. Do them one
   worker at a time and name which path acted. **Name the recovery paths distinctly** - upload
   recovery is the artifact transfer, coordinator-session recovery is picking the ledger back up;
   collapsing both into one label makes the untested one look covered. Recipes:
   `references/cleanup-path-tests.md`.
10. **Close the gate and read it back.** Set launches disabled again, leave cleanup enabled, and
    confirm that a further launch is actually refused by the launch path.
11. **Record the cycle in the project's state file**: job, server and IP identifiers, artifact
    links, timeline, reservation, estimated cost, and how deletion was confirmed. A fresh session
    must be able to answer "did that cycle leave anything behind?" without re-querying.

## Priority inside a fixed allowance

A paid queue is not first-come. When one class of work turns an already-finished artifact into a
shipped one, it outranks new construction, and that has to be enforced rather than intended:

- **Preempt at launch, never mid-flight.** A construction job is refused while higher-priority work
  is pending, naming what it is waiting for. Killing a running machine to start another pays twice
  for nothing.
- **Hold a reserve for the priority class.** Construction may spend at most `allowance - reserve`;
  the priority class may spend the whole allowance. Without the split three long builds can leave no
  money for the job that ships anything, so "top priority" would be untrue exactly when it matters.
  Refuse a reserve that is not smaller than the allowance instead of silently producing a negative
  cap.
- **Exempt work that is blocked on a human.** If the pending item is waiting on an operator decision,
  it must not block the queue at all, or a three-day wait starves the whole pipeline. Encode the
  distinction as a field on the item (`awaiting_operator`), not as a judgement call at launch time,
  and let the dashboard show the wait instead.
- **Prove the guard by reverting it.** Run the new launch tests against the pre-change launcher and
  watch them fail ("FactoryError not raised"), then restore. A guard whose failure you have never
  seen is indistinguishable from a guard that never fires.

## Pitfalls

- **Treating your own ledger as evidence.** A job record, or your own API client, reporting
  `deleted` is bookkeeping, not the provider's word. Deletion is confirmed by reading the provider's
  resource list.
- **Freeing a path by deleting what is in it.** Scope every destructive operation to an exact path
  you own, and have generated output directories carry an ownership marker so that unfamiliar
  contents produce a refusal instead of a cleanup. A recursive delete over a variable path is how
  uncommitted work and whole directories disappear.
- **Treating the reservation as the bill.** The reservation is a conservative planning ceiling at
  the policy rate; providers commonly bill whole hours, so a machine up for four minutes rounds up
  to an hour. Report both figures and say which is which, and derive the actual from the records
  rather than from memory: the pair of timestamps on each job record times the hourly rate gives it,
  and it will usually exceed what the reservations suggested because of time spent idle after the
  work was already done.
- **Losing the diagnostics with the machine.** Teardown must not be the first thing that happens on
  failure: a failed run should still write its report, logs and partial artifacts somewhere
  collectable, *then* have its resource released - otherwise the only evidence of the failure
  leaves with the machine. The same applies *inside* the run: a stage whose output is only
  redirected to a file leaves nothing behind when the container dies before the upload, so the log
  stops at the step header with no error and the next attempt starts blind. Pipe each stage's output
  to the run log as well as the file (tee), and give the stages that can fail silently their own
  explicit status line, so a mid-run death still says what it was doing.
- **Deleting before artifacts are verified, or never deleting.** The same mistake from opposite
  ends. Make collection a precondition of teardown, and teardown a precondition of the next job; a
  blocked teardown is resolved before anything else is launched. The launch path commonly refuses
  while **any** earlier record is not fully terminal, and a job that has merely been *collected* is
  not terminal - its machine is still billing. Read that refusal as a queue position rather than a
  failure: find which record is not yet deleted, collect and destroy it, then launch. Never work
  around it by reusing an id or editing a record to look finished.
- **Raising the worker limit by editing the number.** A launch path written for one machine commonly
  hard-refuses any other value ("this version supports one worker at a time"), so the config change is
  either inert or a failed launch. Read the guard before changing the figure, replace it with a bounded
  range check, and count in-flight work from **both** the ledger and the provider's own server list
  against that limit - a destroyed-but-unrecorded record otherwise buys an extra paid machine. Prove
  the new tests fail on the pre-fix launcher. Then say which brake binds first: a fixed monthly
  allowance divided among N workers does not raise throughput, it only shortens how many jobs fit, so
  report the concurrency and the allowance together rather than the concurrency alone.
- **Assuming a small job timeout buys a small machine lifetime.** The launch path enforces a floor
  relating the two - commonly `timeout_minutes + 15 <= lifetime_minutes` - so a job designed to
  fail in seconds still reserves a 20-minute machine. Compute the reservation from the lifetime,
  and treat the refusal as a pre-provisioning validation result rather than a failed launch.
- **Assuming an expiry sweep covers you.** A sweep only helps while its scheduler is alive; if that
  scheduler is the very thing not yet verified, the fallback is the sweep you can run by hand. That
  is a reason to stay with the job, not a reason to skip the run.
- **Launching a job straight from the directory its JSON lives in.** The launcher packs the
  directory of the job file it is given, so a job file kept beside candidate material ships the
  payload but not the gate script, the runner or the runner manifest — and the worker dies seconds
  after fetching its inputs with `can't open file '/workspace/qualify_dataset.py'`, exit 2. The
  fetched bytes are fine; the bundle is not. Run the project's assembler first (it resolves helpers
  and runner files from their real homes) and launch the assembled bundle, and assert in the normal
  suite that an assembled bundle carries every file the job's first command names.
- **Pinning the job id in more than one place.** The operations rule is that each attempt gets a
  new job id; an assembly path that hardcodes the id cannot express a second attempt at all, so the
  documented re-run procedure becomes unfollowable and the second attempt silently reuses the first
  entry. Keep exactly one source of truth for the id (the candidate's own job file) and have the
  assembler read it, with a test asserting the assembled job and the source agree — then after a run
  fails its own checks, fix and re-run under a **new** id, because the failed run's diagnostics
  belong to the id that produced them.
- **Treating a failed check on the worker as a failed run.** A build that produces its artifact and
  is then refused by its own gate did exactly what it was built to do: collect the report,
  rendering and artifact before teardown, then diagnose from the rows. Resist the two shortcuts —
  deleting the check so the artifact passes, and copying the artifact down to re-qualify it locally.
  A gate that reads the data has to run where the data is. Its refusal is evidence about the
  artifact only once the check's premise holds - a check that fails valid work for a property the
  artifact never claimed is a defect in the check, and reading that verdict as a data problem sends
  the next session to change good data. Settle which it is from the artifact's own rows before
  editing either side, then re-run under a new id; see `validation-gate-design`.
- **Comparing a rebuild to an accepted artifact without pinning its clock-derived fields.**
  Metadata commonly embeds a build timestamp, so a rebuild matches on every data file and still
  fails the identity check in exactly one field - and the failure reads as data drift when it is a
  clock. Make the timestamp an explicit input of the build (`--built-at <iso>`) and pass the
  recorded value, rather than weakening the check to ignore the field: if the artifact's identity is
  computed over that file, ignoring it means the object you verified is not the one anyone accepted.
  Carry the flag into the reproduction instructions too, or the documented rebuild does not rebuild.
- **Relaxing a gate permanently by describing the exception.** When an operator authorizes a
  limited exception, write it into the project's operations document with its bounds - how many
  runs, supervised or not, and what remains unverified - so a later session cannot read it as a
  standing change.

- **Assuming one credential reaches both ends of a transfer.** A token scoped to the store you read
  from commonly returns 404 on the repository you write to, and an unhandled authentication error
  kills the worker *before* it writes a report - so the job looks permanently in flight and the
  resource has to be recovered through the interrupted-job path instead of simply deleted. Check both
  scopes at planning time, use the narrower token for each direction, and move bulk artifacts
  store-to-store through the worker rather than through the coordinator.

- **Assuming a job that runs no container is still bounded by the container's limits.** The
  runtime ceiling is usually enforced inside the container-wait loop, so a host-side job - a
  transfer, a fetch, a publish - never passes the check that stops it: a hung one runs until the
  worker expires and its report may never be written. Give host-side jobs their own deadline,
  checked between units of work, and record an explicit runtime-limit failure when it trips.
- **Assuming the worker can install a client the way your machine does.** A stock image can create
  a virtualenv and still have **no pip inside it** (`ensurepip` ships as a separate package) and no
  package-runner binary at all, so the first attempt fails in seconds on a paid machine. Decide the
  installation route in the job: use the runner if present, else install the package that provides
  pip, else bootstrap it - and assert the client imports before doing any work with it. Keep that
  client in a virtualenv **beside** the job rather than in a container, so the credential never
  enters an image, a mount or a dataset-job input path.
- **Treating generated helper scripts as code the test suite covers.** A helper written to disk as
  a source string and executed as a subprocess is imported by nobody, so a missing `import` in it
  survives every local test and fails three minutes into a paid run. Assert statically, in the
  normal suite, that every helper body parses and imports every module its text uses.
- **Recording only the exception type.** Reports are often deliberately trimmed of raw output to
  keep credentials out, but a type alone ("UploadError") cannot distinguish a missing binary from a
  rejected token from a typo, and the next step is a login to the worker. Capture a bounded slice of
  the error text (a few KiB) in the report instead - enough for a one-line `NameError` to be visible.
  Record the **cause**, not the request: a message that interpolates the URL and is then truncated to
  a fixed length keeps the URL and cuts the exception, so hundreds of failures collapse into one
  repeated line with nothing to act on. Put the status code or exception type first and truncate from
  the end.
- **Making a failed multi-stage job start from zero.** Verify each unit against the destination's
  own record and skip anything already at the expected digest, so a re-run after a failure late in
  the sequence re-sends nothing - observe and report the skipped count, since "resumed cheaply" is
  then a measurement rather than a hope.

- **Sizing a job against the policy floor but never reading its ceiling.** The launch path enforces
  maximums as well as the timeout/lifetime relationship, and a plan exceeding one refuses with a
  policy error - the cheap outcome, but only if you planned before provisioning. Read the enforced
  maximums out of the configuration before assembling the job, and budget the wall clock against the
  same number: when the work is thousands of small remote calls, measure the per-call cost, multiply
  it out, and pick a modest concurrency that fits inside the cap with headroom to spare. Assume that
  a bulk fetch against a public service **will** lose a slice of its calls to throttling and timeouts
  - retry with exponential backoff, wait substantially longer specifically on 429, 403 and 5xx, and
  lower the concurrency rather than increasing the attempt count alone. A publisher can answer 403
  as well as 429 for an over-limit client, so classifying 403 as a permanent refusal retries it
  instantly and loses exactly the calls that a cooldown would have recovered. Count the losses and report them,
  because a partially failed batch leaves no trace in the artifact otherwise.
- **Parallelising a fetch without proving the output is unchanged.** Concurrency is the usual way a
  long serial build fits inside a job cap, and it is also a correctness risk in anything
  order-sensitive. Run the same bounded slice serially and concurrently and compare digests of every
  output file: only a byte-identical match licenses the speedup, and the comparison is cheap because
  it reuses the slice you already have.
- **Raising a runtime cap as if it were free, and expecting it to reach a job already running.** A
  ceiling on job runtime is a policy decision with a price attached: the reservation is computed from
  the *lifetime*, so permitting a longer job means a longer lifetime - the timeout needs boot and
  upload slack inside it - and therefore a larger reservation on every job that uses it. Recompute
  the cost before granting the extension and report both figures rather than the new limit alone. Two
  consequences follow. A job that is already provisioned keeps the sizing recorded when it was
  launched, so re-assembling or editing the local bundle does not change the machine that is running:
  leave that bundle alone and apply the new sizing to the next job. And a test that asserts the
  reservation should compute it from the documented formula (`ceil((lifetime + grace) /
  minutes-per-hour) x the type's ceiling`) instead of hard-coding the current numbers, so the next
  sizing change does not require editing the test that guards it. A cap tight against the measured
  wall clock is the other half of this: a run killed minutes from the end for finishing slightly late
  has spent the whole reservation and produced nothing, so size from the measurement with headroom
  rather than from what the last job happened to need.
- **Reading the resource's status as the job's outcome.** The status and lifecycle commands
  describe the *machine*, not the work: a job that finished in half an hour still shows its resource
  as running until the lifetime or an explicit destroy, so elapsed time on the resource says nothing
  about progress and "still running" is routinely a finished job with an idle machine next to it.
  The job's own outcome - exit code, wall clock, whether artifacts were uploaded - is in the
  collected result, which is readable without tearing the machine down. Decide from the job record,
  never from the resource's state; conflating them turns a completed run into a suspected hang.
  A launch notice arriving long after teardown is the same trap in a delayed form: it reports the
  state captured when the launch exited, so a destroyed job's notice still reads `running`. Resolve
  it against the provider inventory, and treat an unexpected notification as a prompt to re-run that
  probe rather than as news that something is billing. The same staleness applies to **any** queued
  output, not only launch notices: the stdout of a job that finished hours earlier is delivered when
  the queue gets to it, and a report reading "created", "published" or "exit 0" describes the moment
  it ran, not now. Date such a report from the artifact it names - a release's own publication
  timestamp, the commit it cites - and answer it with a fresh probe instead of acting on it. Never
  re-execute a mutating step because a stale notice says it was performed: a second create can fail,
  and where the create step hardcodes a default it can silently re-privatise or overwrite what the
  first one published.

- **Treating a clean exit and green checks as a complete artifact.** Checks assert the properties
  they name; nothing in a leak, timing, shape or contract check asserts that the run *consumed all of
  its inputs*. A build can lose a sixth of its units to failed calls, exit zero, pass every gate, and
  still be published as if it were the full panel - and the shortfall is visible only by counting.
  Make coverage a first-class recorded claim: units and periods expected, built and missing, written
  into the run's summary, with the build failing when anything was lost. A lost unit is not a
  footnote to be discovered from a downstream statistic that reads plausibly but sits below the
  count you measured beforehand - and a loss rate that looks "close enough" on an aggregate is how an
  incomplete artifact gets accepted.

- **Two writers on one ledger.** The job ledger is a single-writer resource, and the failure mode is
  not a conflict message - it is a second session launching a job between your steps, re-pointing the
  records you are working from, or reverting a source change you just made, so your sequence runs
  against a tree that no longer matches what you assembled. Before starting any multi-job paid
  sequence, read the ledger and the recent commits and confirm nothing else is mid-flight; if a
  parallel session is detected, stop and reconcile rather than interleaving. Re-read your own working
  tree and the artifact identity immediately before each launch, because "unchanged since I wrote it"
  is an assumption another writer can invalidate - and when a superseded artifact is replaced,
  re-verify which bytes the destination holds rather than trusting the step you performed earlier.
- **Assuming a rebuild reproduces the accepted artifact because the build is deterministic.**
  Determinism on your side is not stability on theirs: publishers revise and re-publish historical
  values, so a re-pull of the same window returns slightly different rows, sizes and digests - every
  file differing by a few bytes, with no error anywhere. Decide which it is before measuring: pin
  the clock-derived fields to rule out the timestamp, then compare a bounded sample of values
  between the two pulls. A rebuild that differs because upstream changed is a **new artifact** and
  needs its own gate report, its own identity and its own release - never a silent replacement of
  bytes a consumer may already hold. Record the difference and its cause in the artifact's
  measurements, because the next session will otherwise read the drift as a build defect.
- **Blaming the source for a batch that failed on one machine.** When calls that failed remotely
  succeed when repeated directly, the loss was environmental - throttling, DNS, a saturated link -
  rather than a property of the publisher or the data. Reproduce one failing unit from a different
  machine before concluding anything about the source, and keep the retry policy and the coverage
  count as the fix rather than weakening the fetch.

## Related

Shipping the verified artifact to the places consumers fetch it from - one manifest driving several
destinations, per-destination completion, idempotent resumable uploads - is covered by
`multi-destination-publishing`.

## Reporting the cycle

Use `templates/smoke-cycle-report.md`. The operator expects identifiers, artifact links, the
reservation **and** the estimated real cost, and provider-confirmed deletion in the same message -
with anything still unverified named as unverified rather than implied.
