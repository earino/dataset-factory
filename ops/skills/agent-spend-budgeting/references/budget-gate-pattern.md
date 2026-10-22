# The budget gate: a pre-check that can decline to wake the model

A scheduled agent job runs on a tick. Attaching a **pre-check script** to that job buys two
things at once: it decides whether the tick runs at all, and it hands the session its own state as
context. Both happen without a model call.

## The two-way output contract

- **Allow**: print the resume block, then a one-line machine-readable summary, and exit 0. The
  stdout becomes part of the session's context.
- **Hold**: print the reason in plain words, then end with the scheduler's skip directive as the
  **final non-empty line**, and still exit **0**. A non-zero exit is a *failure* and normally
  raises an alert, which is not what a deliberate hold means.

```text
RESEARCH SESSION CONTEXT ...
SKIPPING THIS TICK - <reason>
{"wakeAgent": false, "reason": "<reason>"}
```

The directive form is `{"wakeAgent": false}`; the scheduler consumes the last line and skips the
agent run entirely, so a held tick costs no tokens. Anything else on the final line (a resume
block, a status line) means the agent runs.

## Config schema

```json
{
  "allowance_usd": null,
  "period": {"kind": "monthly", "reset_day": 1},
  "stop_fraction": 0.95,
  "warn_fraction": 0.8,
  "reserve_usd": 0.4,
  "sessions_per_week": 3,
  "session_max_minutes": 45,
  "session_token_cap": 600000,
  "catch_up_window_minutes": 120,
  "routine_job_ids": [],
  "notes": ""
}
```

`allowance_usd: null` **is the fail-closed state**: it ships that way and stays that way until an
operator supplies a number. Keep the reasons in `notes` so the file explains itself to the next
reader.

## The hold conditions, each with its own message

1. **No allowance configured** - refuse, and say the operator must set one.
2. **Spend at or past `stop_fraction` of the allowance**, or remaining-after-this-session would
   fall below `reserve_usd` - print the measured figure, the fraction, and the reserve. The reserve
   keeps the *next* session affordable: admit a session only while `spend + reserve <= allowance`.
3. **A session already in flight** - decided by the **lock the session itself writes**, never by
   asking the run ledger whether a run of this job is in flight. The scheduler writes that ledger
   row *before* the job's script starts, so a ledger-based liveness check holds the job against its
   own fire and it never runs. The lock must carry a staleness bound (`session_max_minutes` plus a
   margin **and** the owning process's pid, with a dead pid treated as stale at once); past that,
   report the lock as stale and proceed rather than deadlocking the routine forever.
4. **Period session cap reached**, counted from the run ledger, **weighted**: a fire whose recorded
   tokens exceed `session_token_cap` counts double, so an overshoot costs future sessions instead
   of being merely logged.
5. **Fired beyond the catch-up window** - the tick is skipped, never caught up. Pair this with
   disabling the scheduler's own missed-run catch-up, or a burst of delayed ticks all runs at once.

Every reason is appended rather than short-circuited: a gate that reports one cause at a time
trains the reader to fix one thing per cycle.

## Resume block

The session's context should answer, in a few lines: the allowance and which period it belongs to,
spend so far this period and the remaining amount, the split by class (so auxiliary and
interactive spend are visibly *not* charged to it), sessions used against the cap, the stated
session limits, and - if the routine has a queue - the next actions. Generating it in the gate
means it costs nothing and cannot drift from the numbers the gate just used.

## Reading the period

A monthly period anchored to a reset day needs the *previous* month's anchor when today is before
that day; a weekly one anchors to the start of the week. Clamp an out-of-range reset day to a safe
maximum (28) rather than letting `replace(day=...)` throw for a short month. Compute the window
half-open, `[start, now)`, and filter on the usage rows' own timestamps.

## Tests that keep it honest

- One test per hold reason, asserting the decision **and** that the reason text names the cause.
- A test that the unset-allowance state holds - this is the one that silently rots into a default
  open.
- A test that a stale lock is ignored while a fresh one holds, and that a lock whose owning pid is
  gone is stale regardless of its age.
- A test that a job's **own** running ledger row does not hold it - the regression that otherwise
  stops the routine dead while looking like a budget hold.
- A test that a hold-path report still emits the deterministic fallback for a reporting job, so a
  held checkpoint reports instead of going silent.
- A test that other scheduled jobs neither block a session nor charge the allowance.
- A test that an overshooting fire counts double against the cap.
- A test that gate output ends with the skip directive on the hold path, and with a non-directive
  line on the allow path - the contract is a line position, so it needs a test.

## Keep the gate itself cheap

The pre-check is a plain script: read files and local databases, no network, no model. Bound its
work so it cannot become the thing that makes a tick slow, and let it degrade to "no recorded
usage" rather than erroring when a table or file is absent.
