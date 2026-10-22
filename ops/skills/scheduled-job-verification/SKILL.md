---
name: scheduled-job-verification
description: "Use when verifying scheduled jobs and their alerts."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [cron, scheduling, github-actions, alerting, verification, watchdog, delivery]
    category: devops
    related_skills: [hermes-agent]
---

# Scheduled job verification

## When to use

Any work that creates or relies on something running on a timer:

- Configuring a cron job, an expiry sweep, a recurring report or a failure alert.
- Being asked to prove that a scheduled run happened, or that an alert would reach a human.
- Deciding whether an unobserved scheduled run should block further work.

A scheduled job is not "set up" until you have read, from the service itself, that one of its runs
fired and — if it delivers somewhere — that the message landed. A tool returning `success`, a job
record showing `last_status: ok`, and a person receiving the message are three different claims.

## Procedure

1. **Prove the destination before anything depends on it.** Create a throwaway one-shot job a
   couple of minutes out (`in 2m`), aimed at the real destination, with a prompt that produces one
   short identifiable line. A destination that has never carried a message is an assumption.
2. **Read delivery back from the transport log, not the job record.** The job record's `ok` means
   the agent turn finished; sending is a separate step with its own failure field
   `last_delivery_error`, `last_delivery_unverified`). Confirm all three: job status `ok`, no
   delivery error, and a log line naming the target — for example
   `delivered to telegram:<chat_id> via live adapter ... message_id=<n>`. Then point every later
   job at that same destination and record it in the project's state file so a fresh session does
   not re-derive it.
3. **For a host-scheduled workflow outside Hermes (e.g. GitHub Actions), require all four:**
   `event` is the schedule (not a manual dispatch), the run is `completed` with a conclusion other
   than `skipped`, the job's step conclusions are `success`, and the step's own stdout shows the
   work. A run that exists but is `skipped` proves nothing — enablement is commonly gated behind a
   repository variable, so pre-gate runs report success-with-skip.
4. **Keep scheduled logic in the repository; put only a shim where the scheduler demands.** A
   runner that requires scripts in its own directory still wants the real implementation tracked,
   reviewed and versioned with the project. Put the logic in the repo and leave a few-line
   forwarding shim behind, propagating stdout, stderr and exit status. **The shim's extension
   selects its interpreter** - `.py` is executed as Python, `.sh`/`.bash` through the shell - so a
   shell script named `.py` raises a syntax error on every tick while producing exactly the silence
   a healthy job with nothing to report produces.   Name the shim for what it actually is, and assert
   in the normal suite that a scheduled entrypoint's extension matches its contents. **Resolve every
   file the job reads - prompt template, config, state - against the repository root, never against
   the process's cwd.** The scheduler invokes the shim from its own directory, so a relative path
   that works in an interactive shell dies on the first tick with `FileNotFoundError`, and a
   no-model job reports that as a failed run rather than as a missing file. Cover it with a test
   that chdirs elsewhere first; it fails on the cwd-relative code and passes after.
5. **Write the watchdog output contract explicitly.** For a no-LLM scheduled script: print nothing
   on the normal path (empty output sends nothing), print exactly one actionable line when
   something needs a human, and exit with the underlying command's status so a failure shows up in
   run history as well as in the message.
6. **Exercise both branches before trusting it.** Run the script in the normal case and confirm
   silence with a zero exit; then force the failure case (a deliberately invalid argument, project
   or path) and confirm it prints one line and exits nonzero. A watchdog that has only ever been
   seen to pass is untested.
7. **Offset redundant schedules by the other job's worst-case duration, not by minutes.** A second
   sweep that backs up a primary can take a different minute (a primary at `17 * * * *` paired with
   a secondary at `47 * * * *`). But when the two jobs share a lock, a budget gate or a machine, a
   short offset guarantees the second one is refused: an advancement tick 25 minutes after a
   discovery tick whose session ceiling is 50 minutes will find the lock held on **every** fire.
   Give each job its own hour, and size the cadence from the observed run duration rather than from
   eagerness. A run of `skipped - lock held for Ns` repeated across ticks is a scheduling bug, not
   jitter. Overlap, idle gating and wall-clock kills: `references/routine-cadence-design.md`.
8. **Treat a missing scheduled fire as pending, not broken — up to a point, then count the misses.**
   Hosted schedulers delay runs under load and can drop queued jobs outright; a service that
   documents this will miss slots by tens of minutes and, on low-activity repositories, fire on a
   much looser cadence than configured. Record the gap with the time it was observed, keep the
   dependent work gated, and re-check. **One missed slot is jitter; two consecutive missed slots
   under a cron expression already on the default branch is a different finding** — the scheduler is
   not delivering on its configured cadence for this repository, which is not the same claim as
   "still pending" and should be handed over as such. **The sharpest comparison available is the job's own behaviour
   before the change under test:** when the window with no fire is longer than every gap the job
   produced beforehand, the configured cadence is not being honoured for this repository - a
   stronger and more useful claim than a pair of missed slots. Before attributing a miss to the
   scheduler, rule out your own side: the workflow is `active` on the default branch, the committed
   expression is the one you believe it is, the enablement flag is set, and a manual dispatch still
   executes. State the slot times you expected and did not see, so the reader can judge the pattern
   rather than a single gap. Say plainly which parts are proven and which are still pending rather
   than inferring one from the other.

   **Once a delayed scheduler finally fires, quantify it instead of relaxing.** Measure the gaps
   between its actual fires and state the mean and the maximum against the configured expression, so
   the reader can see the real distribution rather than "it works now". Then assign each guarantee
   to the scheduler that earns it, and describe each one as the **schedule** it is rather than as a
   deadline: a frequent local tick is *scheduled* hourly, which is a promise to attempt, not a
   promise to finish by then - it only runs while the machine hosting it is alive, it can be missed,
   and it bounds nothing at all if that machine is down. A delayed remote one contributes durability
   across that machine being gone entirely, on a multi-hour timescale. Two schedulers running the
   same command are not two copies of the tighter guarantee, and writing either of them up as
   "deleted within an hour" is a claim the measurements contradict.
9. **Bound the watch.** Poll the scheduler's own run list (not a proxy for it) on a fixed interval
   with an explicit time budget, print a timestamped line on each poll, and end with an explicit
   `PENDING` plus the reason when the budget runs out — so the result is a recorded observation with
   a window rather than an open-ended wait. Extend the budget to cover the next expected slot before
   concluding anything, and restart it if that slot is the one you are waiting on.

10. **Read the job's own usage and run record, not only its status.** The run ledger (status,
   `error`, `delivery_outcome`, `scheduled_instant` vs `started_at`) and the per-fire usage log
   answer questions a status field cannot, and they are what makes two common claims checkable.
   A job that makes **no model calls** is provable: its id appears **zero** times in the usage log
   while its run shows delivered - that pairing is why a digest or sweep can safely be scheduled
   next to a budget it reports on. And a job that does call the model has per-fire tokens there,
   which is how an over-long session is detected after the fact. Surfaces and columns:
   `agent-spend-budgeting` -> `references/hermes-usage-surfaces.md`.

11. **Separate a manual fire from a scheduled one when reporting.** Running a job by hand proves
    the script, the wiring and the delivery path; it does **not** prove the schedule fires. Say
    which one you observed and when the first scheduled fire is due - "manual fire executed and
    delivered; first scheduled fire pending until <time>" is the honest form, and the difference
    between "set up" and "verified".
12. **Get a scheduler-fired observation now, without waiting for the production slot.** A recurring
    job's next slot can be days away, and a manual fire cannot stand in for it. Create a throwaway
    one-shot job a couple of minutes out that runs the **same** script or wrapper with small limits
    and a bounded, read-only instruction. The scheduler fires it, so the *scheduled* path is
    observed end to end - timer, script, work, delivery, usage record - while the production job's
    own first fire stays pending. Report both, separately: the probe fired by the scheduler at
    <time> and what it produced; the production job's first scheduled fire due at <time>. Read the
    probe's saved output, then remove the job.

    **A probe is not a substitute for the real job's own state.** If the production job appears in
    a list its own pre-check consults - an inventory, a budget, an overlap guard, a set of ids -
    a differently-named probe never matches those paths, so it exercises the path while skipping
    exactly the guards under test. Reproduce a suspected scheduling fault on the **configured**
    job, including its own record in the scheduler's ledger as it fires, and verify the fix there.
    The probe proves scheduler -> script -> work -> delivery; it does not prove the real job's
    guards let it through.

## Watching work that outlives the turn

A remote job finishes long after the turn that launched it, and nothing returns on its own: the
launch command's completion notice fires when the **launch** exits, and the resource's status
describes the machine rather than the work. Left there, the only thing that surfaces the result is
the operator asking - which makes them the polling mechanism. Hand every long job to a watcher
before the turn ends.

- **Watch from the system's own records, never from a list maintained by hand.** An item that is
  still running is watched by construction, so a forgotten launch cannot go unwatched, and an
  explicit list is only an override for what the records do not cover. A hand-kept list is the same
  gap as having no watcher at all, wearing the costume of one.
- **Emit deterministic output per watched item.** One line each, with anything time-varying (elapsed
  time, timestamps, ticking counts) omitted until the item reaches a terminal state. Identical
  output is what lets the scheduler suppress the agent run; output that changes every tick wakes a
  model every tick.
- **Treat only an explicit in-flight answer as in-flight.** A refusal, an unreachable resource, a
  message that the resource is gone - all terminal. A watcher that reads "cannot tell" as "still
  running" waits forever, and it is indistinguishable from one watching honest work.
- **Parse the collector's output as one document, not line by line.** A status command that prints
  pretty-printed JSON spreads a single record across many lines, so a reader that looks for a line
  starting with `{` matches nothing, falls through to its default, and reports a running item as
  finished - silently, and in the direction that stops the watching. Read the whole captured output
  as one value (stdout first, then stderr, then the first brace-to-brace span), and keep **"the
  source said it is gone"** distinct from **"I could not read what the source said"**: the second is
  its own state, never folded into the terminal one, because the classifier's default decides whether
  in-flight work keeps being watched at all. Pin the shape you actually observed - the real output of
  the status command, quoted into the test - rather than a shape you assumed, and re-read the raw
  output the moment the classifier disagrees with the resource.
- **Prefer a locally recorded result over a fresh poll.** Once an item has been collected its
  resource may already be gone, and polling cannot tell a dead resource from a live one.
- **Prove the watcher matches something.** Simulate an in-flight item and confirm it emits a line;
  confirm silence once everything is terminal. A watcher that silently matches nothing looks exactly
  like a watcher with nothing to report, and the failure stays invisible until the work it was meant
  to announce is long overdue.
- **Count a cleanup sweep taking the machine as a state change, not as patience.** The artifact
  usually survives the resource: uploads are tagged per job, so the completion message should carry
  the recovery route rather than leaving the job "running" until someone notices.
- **Make the alert replyable and contextual.** Deliver to the originating conversation, attach the
  job to that session so the operator can answer it, and anchor it to the project directory so the
  fresh session handling the alert starts with the project's own context loaded.
- **Keep a finished item visible until it has been handled, then go quiet.** The reflex is to stop
  reporting an item the moment its work is over, or the moment its record goes terminal. Resist it:
  the agent run is triggered by a *change* in the watcher's output, so dropping the item turns the
  output from a state line into nothing, and the agent wakes to an empty diff with no item to act on
  - a successful run whose result reaches nobody. Keep rendering the terminal line (state, exit,
  elapsed, where the artifacts went) until the handling session has actually reported, marked by a
  `handled` marker written beside the result **after** the report and never before. Say plainly in
  the handling prompt that an empty reply on a finished item is a failed run: the session's final
  response *is* the notification. Going quiet is the end of handling, not a consequence of
  termination.

Wiring, including the change-detector source and the local-result-first order:
`references/long-job-watchdog.md`.

## Keeping a scheduled routine pointed at its purpose

A brief that says "advance one step" will pick the nearest step every time, so a routine can run
green for weeks while one of its modes silently stops. Splitting modes into separate briefs and
jobs, making the quota countable, and reporting the mode mix:
`references/routine-cadence-design.md`.

## When a scheduled run produces nothing: is it us or the provider?

A wrapper that exits non-zero or is killed with no report, and whose log shows the stream going quiet,
is a different failure class from a broken prompt or a bad script. Diagnose it before changing code.

- **Read the agent log line, not the job summary.** Generic wrapper text reports every provider failure
  as a rejection ("refused the request, retrying won't help"), which conflates an auth refusal with a
  stall. The stall signature is `stream stale for Ns — no chunks received`, then `Broken pipe`, repeated,
  then an abort after several consecutive stale attempts: the request was accepted and never answered.
- **Separate rejection from degradation with status codes from that provider in the window.** 401/403/429
  from the model provider means rejection or quota; their absence plus stalled streams means the
  backend is degraded. A 429 from a *different* provider (vision, auxiliary) is not evidence about the
  primary, and reading it as such sends you chasing the wrong outage.
- **Measure the latency of the calls that do succeed.** Answering in tens of seconds where the same key
  used to answer in a few is the degraded state that precedes an abort. Report that shape - "up but
  limping, 50-90s per call, six consecutive no-answer streams" - rather than "the provider is down".
- **Check what the run wrote before calling the tick wasted.** Files written before the stall survive;
  the final summary is what is lost. A `find -newermt` over the records it was meant to touch turns
  "an hour lost" into the accurate "three verdicts written, one report missing".
- **Configure failover instead of retrying into the same wall.** A fallback provider chain in config
  lets a stalled stream move to a healthy route with no human involved; validate the parsed config
  through the loader, and remember it applies to the next run - the one already streaming keeps its
  route.

## Pitfalls

- **Taking a manual-fire response's `last_error` as the state of the run it just started.** A run
  request can return the job record as it stood *before* the fire, including the previous fire's
  traceback, while the new run is already alive - the error describes work that no longer exists.
  Match the response's timestamp against the run you asked for, and confirm liveness from the job's
  own live marker and process, then from the wrapper's log when it finishes. The same applies to a
  background completion notice that arrives for a superseded fire: check whether it predates the fix
  before acting on it.
- **Reporting success from the success response.** A create call that returns a job id, or a job
  record that says `ok`, is not delivery and not execution. Read the state back from the service
  that owns it — the log line, the remote ref, the run's step output.
- **Reading a job's silence as a job with nothing to report.** A scheduled job that dies before its
  own logic runs - the wrong interpreter for the file, a missing target, a script the runner cannot
  execute - produces the same absence of output as one with nothing to say, so the failure is
  invisible from the outside and can persist for many ticks. After any change to a job's wiring,
  read the job's own record (`last_status`, `last_error`) and confirm it flipped to a successful
  state, and prefer a positive signal that the source ran at all - a change-detector's recorded
  output hash, including the hash of an empty output - over the absence of an alert.
- **Counting a manual run as the schedule being verified.** A hand-fired job that delivers
  correctly says nothing about whether the timer fires, and a job whose next slot has not yet
  passed has an unverified schedule no matter how green the manual run looked. Report the two
  separately rather than letting the manual run stand in for the timer.
- **Reading an absence of usage entries as a broken or unregistered job.** For a no-model script
  job, zero usage entries is the *expected* result; pair it with the delivered run before drawing
  any conclusion from it.
- **Calling a schedule gate "working" because a run appeared.** A run with conclusion `skipped`
  means the gate is closed, which is the opposite of the evidence you need.
- **Leaving the enablement gate open against a quota.** A run that executes costs billed minutes
  whether or not it finds work, so a sweep every fifteen minutes can exceed a small private-repo
  Actions allowance long before it finds anything to delete. Set the interval from the cost budget
  and the actual failure window, not from eagerness.
- **Disabling launches only in prose.** When a check fails, set the policy flag itself — the config
  field the launch path actually reads — and read it back to confirm. A note in a state file does
  not stop a launch.
- **Assuming a cleanup step deletes anything.** An empty result list is the *expected* output when
  the normal path already cleans up; it demonstrates the wiring, not the deletion. State that
  distinction instead of counting an empty sweep as verification of deletion.
- **Gating a test behind the thing it tests.** If evidence can only be produced by running the
  system, it belongs to the exercise of that system, not to the prerequisites for starting it.
  Demanding it first makes the evidence unreachable, and the project stalls on a circular gate.

- **Restricting a verification job's toolset below what its own prompt needs.** A probe that must
  load a skill or read a file cannot satisfy itself if the job allows only some toolsets; it fails
  on its own constraints and looks like a failure of the system under test. Allow what the probe
  needs, or do not restrict at all.
- **Scheduling a retry for when you want it rather than for when the blocker releases.** A one-shot
  job that fires while the blocking job still holds its lock is **skipped and consumed** - it will
  not fire again, and the work it was meant to do silently never happens. Compute the blocker's
  release instant (its start plus its budget and any grace), place the retry after it, and confirm
  from the run's own log that it ran rather than skipped.
- **Assuming a paused or disabled job can be run on demand.** Manual runs are refused until the job
  is resumed, and a run can hold its slot long enough that an immediate second attempt is rejected
  as already running. Resume first, then run, and treat the refusal as a scheduling detail rather
  than a broken job.
- **A wrapper's own run budget does not bound the scheduler's script timeout.** A no-agent job that
  shells out to an agent run is killed by the scheduler's script ceiling
  (`cron.script_timeout_seconds`, 3600 by default), which is independent of the `--run-budget`
  handed to the agent. Lengthening a session to 90 minutes while that ceiling stays at 60 kills the
  job at exactly 3600 s with "Script timed out" — which reads like the session failing, not the
  scheduler enforcing a second, outer limit. Size `run_budget + grace < script_timeout_seconds`, or
  raise the ceiling; the config is cached on file signature, so the next fire picks it up without a
  restart. Whenever a session length changes, check both numbers and say which one binds.
- **Deleting a verification job before reading what it produced.** Removing a job takes its saved
  output with it, so a later question about the run is unanswerable. Read the artifact, then clean
  the throwaway up.
- **Reading an empty tool response as evidence of absence.** A filtered run list that comes back
  empty may mean the filter does not do what its name suggests. Confirm the query returns a run you
  already know exists before concluding that nothing ran.
- **Widening what is watched without migrating the backlog.** A rule change that stops dropping
  finished items - the fix above - resurfaces every historical item at once, so the first tick after
  it reports the entire archive as if it had just happened. Backfill the marker onto the pre-existing
  items in the same change and say so where the change is recorded; otherwise the correction arrives
  as a wall of alerts that reads like a wave of new failures.
- **Selecting watched items by a rolling window.** "Finished in the last N hours" moves on its own as
  items age, so the output changes every tick with nothing new happening and the detector wakes a
  model every tick; the same query also answers differently tomorrow, which makes the observation
  unreproducible. Choose a rule that is a *state* and stops matching once the item is handled.
- **Waiting for a distant slot to verify a schedule, or dressing a manual fire up as one.** A
  recurring job's next fire can be days out, which tempts either an unbounded wait or a manual run
  reported as if the timer had fired. Neither is needed: a throwaway one-shot job pointed at the
  same script gets the scheduler to fire the path for you now, and both facts can then be stated
  plainly - scheduled path observed via the probe, production slot still pending.

## Gates that run inside a scheduled job

A pre-check that decides whether the job may run at all - an overlap guard, a budget gate, a cap - is
part of the scheduled path and needs the same evidence as the rest of it.

- **A job must not be held against itself.** The scheduler writes a `running` row for a job **before**
  its script starts, so a guard that reads "is any run of this job in flight" holds every fire of
  that job and it can never run. Decide overlap from a marker the job itself writes (removed when it
  finishes, treated as stale when its owning process is gone), or exclude the current fire by id -
  never from the ledger row the scheduler created for the fire being checked.
- **A reporting job held by the limits it reports on must still deliver.** A digest, checkpoint or
  audit subject to the same caps as the work it describes will eventually be held by them, which is
  precisely when its report matters. Give reporting jobs a **deterministic fallback**: when held,
  compute the report from the stored records with no model call and state the hold reason. Keep
  routine work ticks silent on a hold; never let a reporting tick be silent.
- **Name the cap's location and its sizing when reporting a cadence.** A gate that holds a fire is
  not an outage: report the schedule, the cap as it is configured (file and field), the guard that
  enforces it, and the ledger's held rows, so the reader sees a rule doing its job. Give the
  arithmetic the cap is sized against rather than the bare number, and state the next slot as a
  candidate admission rather than a guaranteed run.
- **Count the unit you mean, in the report and in the limit.** A report that printed scheduler
  execution rows under the word "sessions", while the cap counted sessions from the ledger, showed
  a held tick (which ran no session) as a session and disagreed with its own limit. Derive both from
  one source and name them apart - `sessions this week: 2/3` and `ticks fired: 5 (includes held
  ticks that ran no session)`.
- **Frame an instruction the scheduler attaches to one run.** Text appended raw after a job's
  standing prompt is indistinguishable from injected content, and a session is right to refuse it
  and report it as a prompt-injection attempt. Render it under its own heading, state who set it and
  that it selects **this** run's task, and say explicitly that it does not lift the standing limits,
  budget or safety rules.
- **Keep exclusions auditable.** When measuring anything, sessions or fires deliberately left out of
  the count (a verification run, a probe) are listed by id with the reason, not silently skipped: an
  exclusion nobody can inspect is indistinguishable from a miscount.

## Related

- `references/routine-cadence-design.md` - keeping a recurring routine on purpose: symptoms of a
  single-brief drift, per-mode briefs and jobs, countable quotas, and how to verify the mix changed. - a worker, container or VM that
exists to run one job and must be proven gone afterwards - is covered by
`ephemeral-worker-lifecycle`.

Verifying a pushed change before reporting it complete - reading CI for the exact commit,
reproducing runner-only failures locally, and reporting a pending or blocked check honestly - is
covered by `post-push-verification`.

Bounding what a scheduled job is allowed to **spend** - measuring the agent's own usage, gating a
run before it wakes the model, and keeping monitoring outside the budget it reports on - is
covered by `agent-spend-budgeting`.

Hermes' own cron tool, delivery targets and script resolution rules are documented by the
`hermes-agent` skill and the cron tool schema; this skill covers how to prove a scheduled job
actually ran and reached the right place.
