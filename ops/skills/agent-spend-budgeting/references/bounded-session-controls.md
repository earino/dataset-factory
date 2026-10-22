# Bounding one unattended agent session

How to make a scheduled or unattended agent run stop at a finite limit that the runtime
actually enforces, rather than one you account for afterwards.

## Pick the control surface first

| Surface | Scope | Use when |
| --- | --- | --- |
| Per-invocation flags on the agent CLI | that one run | **Default.** A scheduled routine is one run, so a per-run ceiling bounds exactly the work you meant to bound. |
| Global config (`agent.max_turns`, `agent.run_budget_seconds`) | every conversation, including the operator's own chat | Only if the operator wants their own sessions bounded too. A tighter global cap silently truncates interactive work mid-task. |
| Job record fields | the job | Usually absent: job schemas carry toolsets, model and schedule, not execution budgets. Check before promising a per-job knob. |

Write the limit down as *which surface*, *which value*, and *enforced or advisory* - a report that
says "45 minutes" without saying which of the two it is has not answered the question.

## The flags that do the work

- an **iteration cap** - the number of tool-calling iterations one conversation turn may take
- a **wall-clock budget** in seconds for the run, which also emits a wrap-up notice at 80% and caps
  provider stale timeouts to what remains, so one hung call cannot eat the whole run
- quiet mode, so the delivered output is the final response rather than the interactive UI
- a **source tag**, so usage accounting can tell a routine's session from a person's chat later
- a query file, so a long self-contained prompt needs no shell quoting
- optionally a preloaded skill list and a restricted toolset list

Run the CLI with `--help` once and read the current names; they are cheap to check and expensive
to guess. A nested CLI invocation from a scheduler script is an established pattern, so a thin
wrapper is the intended shape, not a workaround.

## The wrapper shape

One script, called as the job's script in no-model mode, so its stdout is the delivered message:

1. **Gate first** (see `budget-gate-pattern.md`). If held, print nothing routine and exit 0 - no
   agent process is created, so a held tick costs zero.
2. **Build the prompt** from a versioned template file plus the gate's resume block, so the
   session starts from saved state instead of rediscovering it.
3. **Run the agent once**, with the iteration cap and the wall-clock budget, quiet mode, the source
   tag, the prompt file, and the skills the work needs preloaded.
4. **Hold a lock** across the run and release it in a `finally`, so a crash cannot leave the
   routine permanently blocked.
5. **Strip the CLI's trailing session-info lines** from stdout and deliver the final response;
   log outcome and elapsed time beside the run for later accounting.

A held tick is silent on purpose: a cap, an overlap or a late tick is not news. Only report a hold
that needs a human decision - an exhausted allowance does.

## Verify that a limit stops a run

The session *ending* is not evidence: a model can finish early, refuse, or stop for its own
reasons. The evidence is the **runtime's own exhaustion notice**, in the transcript:

- the iteration cap injects a message telling the model it has reached the maximum number of
  tool-calling iterations and must answer without further tools;
- the wall-clock budget injects a wrap-up notice as the budget is nearly exhausted telling it to
  stop new work.

So the test is: give the session a task that would exceed the limit, then read the transcript for
that notice and confirm the planned work was left unfinished. A test that ends with the work done
proves nothing about the limit. Test at a small value first - the mechanism is what you are
verifying - then set the production value, and say which value you observed and which is shipped.

**Token totals are the usual advisory case:** no runtime control reads them, so a token figure
attached to one *session* is advisory - label it and give it a consequence (an overshoot counting
double against the period's session allowance). The exception is a **period** token ceiling checked
by the gate before the run starts: it is enforced, because the gate decides whether any model call
happens. Use that when the provider prices calls at zero and a dollar allowance cannot bind, and
state the measured used/limit rather than the token estimate the runtime cannot act on.

## What an unattended session can actually run

With no user present, a flagged command is **refused**, not approved: nobody can answer the
prompt, so the gate denies. Expect interactive-style one-liners and arbitrary-code tools to be
refused, and ordinary commands, file writes and **running a script file** to work.

- **The workaround is the intended path:** compute by writing a small script into the project's
  scratch space and running it as a file. Put this in the session's prompt, or the session spends
  its budget discovering it - and a session that cannot compute will report the routine as
  unusable rather than adapt.
- **Do not widen approvals to make a routine convenient.** Auto-approving for unattended sessions
  hands a scheduled script the same reach as an interactive one, and it is hard to walk back.
  Keep the refusal, and change the session's command shapes instead.
- **Test any allowlist entry before relying on it.** Permanent-approval lists are matched against
  the exact command text or a glob, so a rule-key entry may match nothing at all, and a command
  containing shell operators can be skipped by the matcher entirely. Add the entry, re-run the
  command in the unattended context, and keep the entry only if the refusal actually goes away.

## Excluding verification runs from a cap

Verifying a routine creates real sessions, and if they carry the routine's normal tag they consume
its period cap and its allowance - the routine then holds itself out of work it should be doing.
Two acceptable fixes, in order of preference:

1. **Tag probes distinctly at creation** (a separate source tag for verification runs), so they are
   never classified as work in the first place.
2. **List earlier verification sessions by id in the config, with the reason**, so the exclusion is
   auditable and cannot silently grow. Delete the entries once they age out of the window.

Do not rewrite the service's own ledger to reclassify history: the exclusion belongs in your
config where it can be reviewed.
