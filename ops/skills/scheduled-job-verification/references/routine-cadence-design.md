# Keeping a scheduled routine pointed at its purpose

A recurring session does whatever its brief leaves open, and a brief that says "advance one step"
will pick the nearest step every time - usually finishing something already in progress. The
routine then looks healthy (green runs, real output, no errors) while one half of its job silently
stops happening, and only counting the outputs over time reveals it.

## Symptoms

- Every run reports progress, but the same class of work for weeks.
- Run status is `ok`/exit 1 from the iteration cap rather than an error; nobody investigates a cap.
- The queue looks full because a single long task (packaging, publishing) keeps generating
  follow-on steps, so "the step that unblocks the most work" is always that task.
- No candidate or lead has been opened since the routine was created.
- Runs end at `killed by the wrapper after the run budget elapsed`, with no report.

## Fixes, in order

1. **One brief per mode, one job per mode.** A discovery pass and a packaging pass are different
   work with different success criteria; sharing one brief and one slot means the mode that
   reports visible progress wins every tick. Separate jobs, separate templates, and a sentence in
   each brief forbidding the other mode's work (naming it explicitly, not "other work").
2. **Make the quota countable and per session.** "Find more sources" cannot be checked; "at least
   N new sources taken to a recorded verdict, each in its own record with the reason" can. State in
   the prompt what a short session should report, so it states its count instead of inventing one.
3. **Count rejections as output.** If only accepted candidates count, the quota is met by lowering
   the bar; a rejection with its evidence is the honest way to clear a lead, and the brief should
   say so.
4. **Keep every mode inside the same accounting.** Modes carrying a different source tag or job id
   escape the period cap and the spend report unless they are added to the config that classifies
   them - register the new job id in the same change that creates it.
5. **Report the mode mix, not just the run count.** A digest that says "3 sessions ran" hides a
   month of packaging; state how many were discovery and how many were advancement.

## Overlapping jobs share one lock

Two jobs that both open a session lock cannot be offset by a few minutes.

- **Offset by the other job's worst-case duration.** A 50-minute session ceiling with the next job
  25 minutes later means the second job is refused on every single fire; the routine then looks
  scheduled and does nothing. Give each job its own hour (`0 */2` and `5 1-23/2`), and when in doubt
  put more gap between them than the measured run duration, not less.
- **Read held rows as evidence, not noise.** Repeated `skipped - lock held for Ns by <session>` in
  the runner's log is a scheduling defect. Count how many of the last N fires were held; more than
  a couple in a row means the cadence is wrong, not that the work is unlucky.
- **Check the blocker's expiry before scheduling a retry.** A one-shot job is *consumed* by a skip.
  Compute `written_at + run_budget + grace` from the lock file and place the retry after it.
- **Size the slot from the hard stop, not the budget.** A run gets its budget plus the wrapper's
  grace before it is killed, so the slot must exceed `budget + grace` with margin. Two 90-minute
  sessions in adjacent 2-hour slots collide on the kill tail; alternating types across 4-hour slots
  (`0 */4` and `0 2-22/4`) gives each run a 2-hour slot that a 90-minute run and its 95-minute hard
  stop always fit inside.
- **Raise the stale-lock window with the budget.** The gate treats a lock older than
  `session_max_minutes * 60 + grace` as dead, so a 90-minute session under a 40-minute setting is
  declared stale while it is still working and the next tick starts a second one on top of it.
  Every field that encodes "how long a session lasts" moves in the same change as the runner flag.

## Widening the window: measure which limit binds first

A session that ends `killed by the wrapper after the run budget elapsed` at a modest token count is
telling you the wall clock binds, not the budget. Before changing anything, read per-session
`started_at`, duration, `message_count`, `tool_call_count` and token totals from the session ledger
and compare the two ceilings.

- **Time-bound looks like:** killed at the ceiling, 100k-200k tokens, many tool calls, no report.
  Widening costs little because the unused token headroom is already paid for by the cadence.
- **Token-bound looks like:** sessions stopping inside the wall clock near the token cap, or the
  weekly gate holding fires. Widening here just moves the failure to the budget.
- Recompute the weekly arithmetic after the change (sessions/day x measured tokens) and state it,
  because a doubled window with an unchanged cadence is roughly a doubled token spend.
- **Fewer runs that finish beat more runs that die.** When discovery and advancement share a token
  budget, cutting discovery from hourly to four-hourly to fund a 90-minute window is the right trade
  once the candidate bench is full: the constraint has moved from finding work to finishing it.

## An idle gate makes a high cadence cheap

Frequent ticks are only affordable if an empty tick costs nothing. Run a plain script first and let
it decide whether there is work; only then start the model.

- Scan the system's own records for **actionable** states (`ready`, `qualified`, `packaged` and not
  waiting on a person, a GO verdict awaiting construction) and exit 0 with no output when the set is
  empty. The scheduler treats empty stdout as "nothing to say", so an idle tick is invisible.
- **Do not count states that are waiting on a human.** A packaged item awaiting an approval is not
  work; including it makes every tick look busy, burns the budget, and starves the queue on a
  person's reply time. Exclude it explicitly (a boolean on the record) rather than by inference.
- Pass the same gate to the runner as a flag (`--if-work`) so the cron job stays argument-free and
  the behaviour is testable: one test per state, asserting which ones count as work.

## A wall-clock kill loses the report, not the files

When a runner is killed at its budget, what it wrote to disk survives and its final summary does
not - so the unit of durable progress must be smaller than the session.

- **Write each unit the moment it is decided** (one verdict, one artifact, one record), never
  batched at the end. A killed tick that wrote as it went still moved the pipeline; one that held
  three results in its head delivered nothing.
- Say so in the brief: record as you go, and if time is short, stop probing and write up what you
  have, including the sources opened but not settled.
- **Alarm on the outcome field.** `killed` in the runner's ledger is invisible in downstream records.
  Two of the last three runs ending that way is a defect worth an alarm on the dashboard, and it is
  the only place that signal exists.
- **Read the outcome string, not the elapsed time.** `killed by the wrapper after the run budget
  elapsed` and a provider abort (exit 1, `provider has been unresponsive for N consecutive stale
  attempts`) both end with no report, but they are different defects: the first is a cadence or scope
  problem, the second needs a failover route. Widening the window on a provider stall just buys more
  time waiting on the same silence.
- **A session with no new messages for tens of minutes is blocked in one call, not thinking.**
  Compare the session's last-message timestamp against now, and its per-call latency, before
  concluding the work is heavy; a 60-second stale-stream threshold plus six aborts can consume half a
  window without a single tool call being made.
- **If every run dies at the ceiling, the ceiling is the defect.** Raise the budget and lower the
  cadence rather than repeating the kill; then re-measure the run duration before trusting the new
  number.

## Verification that the cadence actually changed

- Count sessions per mode from the routine's own log, not from the job's status.
- Count the **distribution** of what discovery opened, not only how many: a per-session quota with
  no coverage measure is met every tick from the cheapest source. Measuring it by publisher
  jurisdiction is `open-data-source-vetting` -> `references/discovery-coverage.md`.
- Read one run's delivered report for the countable quota (how many leads, how many verdicts); a
  report with no count is the previous behaviour under a new name.
- Confirm the new job fires on its own schedule, not only via the manual fire used to test it.
- Confirm the idle gate by its own log: an `idle` row on a tick with nothing to do, and a `session`
  row on a tick with work. Silence alone does not distinguish the two.
