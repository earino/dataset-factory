---
name: agent-spend-budgeting
description: "Use when bounding what scheduled agent work may spend."
version: 1.1.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [budget, quota, cost, cron, autonomous, allowance, accounting, gating]
    category: devops
    related_skills: [scheduled-job-verification, ephemeral-worker-lifecycle, hosted-agent-capability-audit]
---

# Agent spend budgeting

## When to use

Any routine that will wake a model unattended, or any request to bound what the agent itself
costs:

- "Make this a repeatable operation within a defined quota."
- "Continue within the existing allowance" for *model* work (not for paid compute).
- Being asked where the spend went, or to stop a routine from spending more.

This is the **model-spend** budget: inference, auxiliary calls, delegation. Paid compute on a
rented machine is a different budget with different mechanics (`ephemeral-worker-lifecycle`) -
keep them separate, in separate config, and say which one a figure belongs to.

## Procedure

1. **Establish the allowance by asking, never by inferring it from what has been spent.** The
   provider's subscription quota, its reset period and its usage page belong to the account owner
   and are commonly invisible from the agent's own instance. Ask for the number and the period,
   and say plainly which figures you cannot see. Do **not** widen a credential to fetch a billing
   number (`hosted-agent-capability-audit`).
2. **Fail closed.** Ship the allowance config with a null value and make the gate refuse to wake
   the model while it is null. An unconfigured budget is not an unlimited one, and a routine that
   defaults to running is a routine that spends before it is bounded.
3. **Measure from the agent's own records, and split the accounting by class.** Main turns,
   auxiliary calls, scheduled sessions and interactive chat are separate lines: auxiliary work
   (approval classification, titles, compression) is charged and invisible unless you look for it,
   and delegated subagent work bills to the session that spawned it. Concrete tables, columns and
   joins: `references/hermes-usage-surfaces.md`.
4. **State enforced versus estimated in every report.** Cost figures from the agent's own records
   are usually estimates with no provider-reported actual, so the budget guards *planned* work and
   cannot reconcile against a bill. **An allowance priced at zero by the provider cannot bind** -
   check the usage table's cost column before promising a dollar ceiling, and enforce a measured
   unit (tokens for the period) when it is zero. Keep a short table of which limits are mechanically enforced,
   which are advisory, and which are estimates - and never present an estimate as the
   subscription's usage.
5. **Gate before waking the model, through a pre-check that can decline the run.** Attaching a
   script that ends with the scheduler's skip directive means a held tick costs **zero** tokens -
   which is the whole point, since a gate that spends a call to decide is not a gate. Design,
   config schema and the directive: `references/budget-gate-pattern.md`. **Gate on work as well as
   on money.** A budget gate answers "may this run spend?"; a second, equally cheap check answers
   "is there anything to do?" - scan the queue and exit before starting the model when every item
   is terminal, published, or waiting on a person. With that check in place the schedule can be
   frequent (a long enough cadence to keep latency low) without paying for empty ticks; without it,
   the only way to avoid waste is a rare schedule, which turns the clock into the bottleneck.
6. **Feed the session back its own state.** The same gate script is the cheapest place to hand the
   session a compact resume block - allowance, spend, remaining, sessions used, limits, and the
   queue of next actions - so a scheduled session starts from saved state instead of rediscovering
   it at full price.
7. **Prevent overlap, catch-up and retries at the scheduler.** Decide overlap from a marker the
   session itself writes - created when it is admitted, removed when it ends, and treated as stale
   when it exceeds the session ceiling **or its owning process is gone**. Do **not** decide overlap
   from "is any run of this job in flight": the scheduler writes that row *before* the job's script
   starts, so the job reads itself as overlapping and is held on every fire - it can never run, and
   each tick looks like a legitimate budget hold. The run ledger is for counting what ran, not for
   liveness. Disable missed-run catch-up at the scheduler, and skip a tick that fired beyond a late
   window rather than catching it up. Cap sessions per period, counted from the ledger rather than
   from a counter you maintain - and report the same period figures from that same source, so the
   cap and the digest cannot disagree about how many sessions were used.
8. **Enforce a finite execution limit with the runtime's own controls, then verify it stops a run.**
   A pre-check decides *whether* a session starts; it cannot interrupt one already running, so a
   limit that only counts an overshoot afterwards is accounting, not a spending limit. Run the
   session through the agent CLI's per-invocation ceilings - an iteration cap and a wall-clock
   budget - and prove each one by reading the runtime's own exhaustion notice in the transcript,
   not by the session merely ending. Prefer per-invocation flags over global config, which would
   bound the operator's own interactive sessions too. Keep the word *advisory* for what the runtime
   genuinely cannot enforce (token totals), and even then give it a consequence: an overshoot
   counting double against the period's session allowance. Flags, wrapper shape, and how to verify
   each stop: `references/bounded-session-controls.md`.
9. **Reserve the next session's cost before starting this one.** Admit a session only while
   `spend + reserve <= allowance`, with the reserve taken from the upper end of a measured session,
   so a run cannot consume the budget the following run needs. State the reserve figure in every
   report rather than reporting only what is left.
10. **Keep monitoring and cleanup outside the quota.** A digest and a cleanup sweep that report on
   the budget must not consume it: make them no-model script jobs, which also keeps them working
   when the allowance is spent or still unset. One periodic digest carrying progress, usage,
   remaining allowance and decisions needed, plus a **separate** alert path for actionable
   failures - and report the next run time when you report the schedule.
11. **Prove the gate before trusting it.** Both branches: a hold for each reason (no allowance,
    spent, cap reached, already running, too late) and an allow when nothing binds. Then verify a
    real scheduled run against its usage record, not against the job's status field.
12. **Recommend changes to the budget; never make them yourself.** After a review window, report
    whether the schedule fits the allowance with the arithmetic shown, and name the specific options
    (fewer sessions, tighter caps) with what each would cost. Changing an allowance or a schedule is
    the account owner's decision: an agent that quietly raises its own spend limit has removed the
    control it was asked to respect. When they do direct a change, change the limit that actually
    binds: raising a dollar allowance while a session cap or token ceiling is the nearer limit
    changes nothing, so say which limit is nearest and what the new headroom is in sessions.

## Priority lanes inside one allowance

When one class of work must never be starved - a release that is ready to ship, a customer-facing
delivery - a single shared allowance cannot express it: three long builds can consume the last euro
before the job that ships anything runs. Carve it in the launcher, not in the prose.

- **Hold a reserve only the priority class may spend.** Construction is capped at
  `allowance - reserve`; priority jobs may spend the full allowance. Validate that the reserve is
  smaller than the allowance (a reserve larger than the budget silently blocks all normal work), and
  make the refusal message name the reserve so the operator can see which rule bound the launch.
- **Enforce preemption at the launch gate.** While an *actionable* priority item exists, refuse new
  low-priority launches and name the item. Preemption only before launch: killing a run already paid
  for wastes what it has spent.
- **Exempt anything waiting on a human.** The priority item that blocks work must be one the system
  can act on; a record carrying `awaiting_operator`, an approval or an unanswered licence question
  is not work. Without the exemption a single pending decision freezes the whole queue and the
  priority rule becomes a permanent stop. Represent it as an explicit field on the record, never
  inferred from the status alone.
- Report the reserve and the current priority item on the same page that reports spend, so a reader
  can tell "budget is free" from "budget is free but reserved".

## Pitfalls

- **Trusting a catalogue of dollars when the meter reads zero.** When every usage row records
  `estimated_cost_usd = 0`, `spend / allowance` never reaches `stop_fraction` and the gate admits
  every tick: the routine is unbounded while every report says it has a budget. Check the cost
  column in the usage table before relying on a USD ceiling; if it is zero, add a **measured**
  ceiling in the unit the records do carry - tokens per trailing period - and print its used/limit
  in the resume block. Keep the USD figure as the operator's stated intent, not as the brake, and
  say which of the two is enforced.
- **Raising the cadence without re-sizing the brake.** When the operator says "amp up", three
  numbers move together: the schedule, the period session cap, and the measured ceiling - sized from
  a *measured* per-session cost, not a guess. Raising the schedule alone produces a routine that
  trips its own brake within days and then reads as a failure rather than as a decision; replay the
  arithmetic (sessions/week x measured tokens) and state which of the three is nearest to binding
  after the change, including any per-job execution ceiling that now sits closer than the schedule.
  When the throttle is raised because work is queueing rather than because budget is spare, say
  which capacity is actually short - the brake being far away is not evidence that the new rate
  produces more finished work.
- **Sizing the session to its own budget but not to the slot and the scheduler's ceiling.** Two
  numbers sit outside the wrapper. A script-only cron job is killed at `cron.script_timeout_seconds`
  (3600 by default), which must exceed the session budget *plus* the wrapper's grace, or a 90-minute
  run dies at 60 with no report and the kill reads as a code or provider failure. And the job's slot
  must exceed the same total, or the next ticket fires into a session still holding the gate: the
  overlap check refuses it and the tick is silently skipped, which looks like a job that stopped. Run
  two lock-sharing jobs on alternating slots (`0 */4` and `2-22/4`) instead of interleaving them in one
  hour. After raising the ceiling, confirm the loader re-reads it (Hermes caches config on the file
  signature) and check the next real run's duration against the new budget rather than assuming.
- **Deciding the run was the wrong size without both measurements.** Before widening a window, read
  the run ledger's elapsed time *and* tokens per session. When most of the wall clock is remote calls,
  time binds first and widening is nearly free; when tokens already approach the per-session cap,
  widening spends more per run and the period ceiling binds instead. Widen the constraint the
  measurement names, and report which one it was - the same instruction can be correct or wasteful
  depending on that split.
- **Holding a session's writes until the end.** A run killed at the wall clock loses its final report,
  not its files - but only if it wrote as it went. Require the brief to persist each decision the
  moment it is made (one verdict written to its own record, as decided, not three batched at the end)
  and to stop probing and write up when the wrap-up notice arrives. Then a kill costs one unit instead
  of a tick, and on recovery `find -newermt` over the intended outputs before calling the run wasted:
  files survive a kill, only the summary does not.
- **Defaulting to open.** A gate that runs when its config is missing spends money before anyone
  has decided the number. Refuse instead, and make the refusal visible in the run ledger and the
  digest so it reads as "waiting on a decision" rather than as a broken job.
- **Enabling the schedule before the number arrives.** Being asked to make a routine repeatable is
  not permission to start spending; configure, hold, and ask. The holding state is a deliverable -
  report it as prepared-and-waiting with the outstanding question restated in one line.
- **Counting the wrong sessions.** Session identifiers do not encode the platform, and auxiliary
  rows share a session id with the main turn. Classify by joining the usage table to the session's
  own source and task columns; an id-substring guess silently mis-buckets whole categories and
  makes the allowance look spent or untouched.
- **Trusting a lock file's existence rather than its age or its owner.** A run that dies mid-session
  leaves the lock behind; without a staleness bound the routine stops permanently, and checking only
  the file's age keeps a crashed session's lock honoured for the whole timeout when the owning
  process is already gone. Record the owner's pid in the marker and treat a dead pid as stale.
  **Move the bound with the ceiling:** the value describing a normal session length is usually the
  same one that decides a lock is dead, so raising sessions from 40 to 90 minutes while it stays at
  40 makes every healthy long run look crashed and admits a second session on top of it. Change both
  numbers in one edit and say which one you changed.
- **Reading your own ledger as the spend.** Run counts, last-status fields and your own counters
  are bookkeeping - verification of what actually ran and delivered is a separate claim
  (`scheduled-job-verification`).
- **Reporting a period cap as a guarantee.** A cap bounds *admission* of new sessions; it does
  nothing about a session already running, which is bounded only by the scheduler's own limits.
- **Explaining a cadence from the schedule expression alone.** Asked when a routine next runs, or
  why its cap is the number it is, answer from three surfaces and name each: the schedule (an
  attempt to run, not a promise to have run), the cap's **config file and field**, and the guard
  that enforces it together with the ledger's held rows - a held row states the rule that bound it,
  so a skipped tick is read as the gate working rather than as a job that stopped. Give the sizing
  arithmetic (the reserve held per session against the period allowance is what makes the cap that
  number) so the reader can judge the limit instead of only receiving it. The schedule alone
  overstates the rate: the effective rate is min(schedule, cap), and a held tick costs nothing and
  produces no session.
- **Treating the allowance question as answered by silence.** An unanswered allowance is a held
  routine, not a licence to pick a number: record the open question where the next session will
  read it and keep the gate closed.
- **A gate that only announces itself when it says no.** Anything downstream reads the gate's
  output to decide whether to proceed, so emit a machine-readable decision on **both** branches -
  a caller that parses only the hold path concludes "no decision" and holds every session, which
  looks exactly like a budget block and costs a debugging session to tell apart.
- **Bounding a routine with a global knob.** A global iteration or wall-clock setting applies to
  every conversation, so tightening one to govern scheduled work truncates the operator's own
  sessions mid-task. Put the ceiling on the invocation instead.
- **Widening approvals so an unattended session can do its job.** Auto-approving for no-user
  contexts hands a scheduled script the reach of an interactive one. Teach the session which
  command shapes work unattended (write a script file and run it) instead of relaxing the gate.
- **Letting verification runs count as work.** Runs made to prove the routine can consume its own
  period cap and leave it holding itself out of real work; tag probes distinctly, or exclude them
  by id in config with the reason.
- **Letting a held review go silent.** A periodic review or checkpoint is exactly the job the
  period cap will hold, so it must still deliver - and deliver something deterministic: the
  ledger-derived report plus the reason it was held, assembled from the usage and run records
  rather than by a model. A review that says nothing when held is indistinguishable from one that
  is broken, and the run that decides whether the schedule fits the allowance is the one you can
  least afford to lose.
- **Scheduling rarely to save tokens.** One tick a day is cheap and slow: work that becomes ready an
  hour after the tick waits a day, and an operator watching a queue reads that as the system being
  stuck. Prefer a frequent schedule plus a work pre-check that exits before the model runs, and size
  the frequency from the measured per-session cost against the period ceiling rather than from a
  guess. The same arithmetic as raising a cadence applies - name which limit binds.
- **Letting a frequent routine narrate itself.** At a high cadence, delivering every session's
  summary turns the dashboard's job into chat noise. Keep routine output local and give the one
  message that needs a human its own tiny script job: it prints only when the state is new, keyed on
  the item **and the timestamp of the state change** (`id@packaged_at`), so repeating the work
  notifies again while retrying the same tick stays silent. Silence is the default and the report is
  the exception.
- **Gating the whole queue on an item that is waiting for a person.** A preemption rule keyed only
  on a status (`packaged`, `awaiting approval`) blocks every other launch forever while the operator
  is away, and the pipeline looks busy but makes no progress. Split the state into *actionable by the
  machine* and *waiting on a human*; only the first may preempt.
- **Stopping a session at a step boundary.** A bounded session that ends after one step while the
  next step of the same item is unblocked, cheap and within the ceiling has paid the full setup cost
  for half the progress. Tell the brief to carry one item through consecutive steps and stop only at
  a real blocker (a human decision, a missing licence, an unresponsive source) or the ceiling.

## References

- `references/hermes-usage-surfaces.md` - the concrete usage and run tables a Hermes instance
  keeps, the columns that separate main / auxiliary / scheduled / interactive spend, the joins
  that classify correctly, and how to prove a job made zero model calls.
- `references/budget-gate-pattern.md` - the pre-check gate: config schema, the skip directive, the
  resume block, lock and ledger checks, the weighted session cap, and the tests that keep each
  hold-branch honest.
- `references/bounded-session-controls.md` - bounding one unattended session: which control surface
  to choose, the per-invocation execution limits, the gate-then-run wrapper shape, how to verify a
  limit actually stopped a run, what an unattended session may run, and how to keep verification
  runs out of the period cap.
