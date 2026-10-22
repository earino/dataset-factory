# The long-job watchdog

A watcher for work that outlives the turn that launched it. The point is not the alert; it is that
nothing should depend on the operator noticing.

## Shape

One scheduled job with two roles, both satisfied by the same source script:

- **script** - its stdout is injected as context for the agent that handles the change.
- **monitor** - the same command, used as a change detector. Unchanged output suppresses the agent
  run entirely, so watching costs nothing until a watched item changes state.

The agent's prompt must be self-contained: a scheduled run has no chat context. Give it the recovery
and verification steps explicitly - collect the result, check the completeness claim before the
slice-level verdict, record the outcome in the project's state file, commit and read CI for that
commit, tear the resource down, then report in a few lines. Deliver to the originating conversation,
attach the job to its session so the operator can reply, and set the working directory to the
project so a fresh session loads the project's own instructions.

## The source script

```python
def state_of(item):
    # A locally collected result wins: after collection the resource may be gone, and polling
    # cannot distinguish a dead resource from a live one.
    local = ROOT / ".factory" / item / "result.json"
    if local.is_file():
        payload = json.loads(local.read_text())
        return {"item": item, "state": payload.get("status"), "exit": payload.get("exit_code"),
                "minutes": round((payload.get("elapsed_seconds") or 0) / 60)}
    out = run("sh scripts/<launcher> status-collect", item)   # cheap, read-only
    if explicit_running_answer(out):
        return {"item": item, "state": "running"}            # only THIS means running
    return {"item": item, "state": "gone", "detail": tail(out)[:140]}


def render(state):
    if state["state"] == "running":
        return f'{state["item"]}: running'                    # nothing time-varying here
    return (f'{state["item"]}: {state["state"]} exit={state["exit"]} '
            f'minutes={state["minutes"]}')
```

Discover the watched set from the system's own records - every item whose recorded status is still
in flight - so no launch can be forgotten. The record's field names are worth reading before
filtering on them: a filter keyed on a field the record does not have matches nothing, silently,
and a filter that treats a nested specification object as the identifier watches a dict instead of a
job.

## Verifying the watcher itself

Three checks, all cheap, and all of them for failure modes that are otherwise invisible:

1. **In-flight emits.** Set a finished item's recorded status back to in-flight, run the source, read
   the line, then restore the record. Confirm it names the item and its state.
2. **Terminal is silent.** With everything terminal, the source prints nothing - which is what makes
   the change detector free.
3. **A swept resource is terminal.** Point it at an item whose resource is already gone and confirm
   the state reads terminal with a recovery route, not `running`.

Pin these in the normal test suite, not in a manual checklist: a watcher that silently matches
nothing passes all three of the naive checks by simply printing nothing.

## What the alert should say

Enough to act without a second round trip: which item, how it ended, wall clock, whether artifacts
were uploaded, where they are, the completeness and verdict results, the cost, and the next action.
When the verdict is about an artifact, bind it to the bytes that were actually stored rather than
re-running a local acceptance path - bulk data should not be collected to satisfy a check.

## Wiring the scheduled entrypoint

The scheduler chooses the interpreter from the file's **extension**: `.py` runs as Python, `.sh` and
`.bash` through the shell. A shell script named `.py` therefore raises a syntax error on every tick,
and a job that fails on every tick is indistinguishable from a watcher with nothing to report - the
only evidence is the job's own failure field, which is easy to miss because the watcher was built
precisely so nobody has to poll.

- Keep the implementation versioned in the repository and the shim trivial, but give the shim the
extension that matches it (`.sh`, not `.py`).
- Point **both** roles of the job - the source and the change detector - at the renamed path; a job
  left pointing at the old name fails the same way.
- Assert in the normal suite that a scheduled entrypoint's extension matches its contents, so this
  fails a test instead of failing quietly on a timer.
- After rewiring, read the job's own record back: a status that has flipped from failure to success,
  plus a recorded output hash for the source (the hash of an empty output is a fine result - it means
  the source ran and had nothing to say), are the two signals that it is genuinely watching now.

## Keeping a finished item visible until it is handled

How an item ends determines what the watcher does next, and the dangerous transition is the one from
"in flight" to "done":

```python
def watchlist():
    for record in records():
        # A locally collected result wins, and once collected the resource may already be gone.
        result = ROOT / ".factory" / record.id / "result.json"
        if record.status == "running":
            yield record.id
        elif result.is_file() and not (result.parent / "handled").exists():
            yield record.id          # finished, NOT yet reported: keep rendering its outcome line
```

The second branch is the whole point. Without it the finished item disappears from the source's
output, the change detector fires on that disappearance, and the agent is handed a diff that says
only that a line went away - so a successful run of real duration produces no notification at all,
which is indistinguishable from the watcher working. With it, the output goes
`<item>: running` -> `<item>: succeeded exit=0 minutes=27 ...`, a change that carries the outcome.

The handling prompt then has to close the loop in this order: do the work, **report it in the final
response**, and only then write the `handled` marker. A marker written first silences the item before
anyone has been told, and the run looks handled while the result is lost. State in the prompt that an
empty or one-word reply on a finished item is a failed run.

`e3b0c442...` (the SHA-256 of the empty string) as the recorded output hash means the source ran and
matched nothing. That is a healthy result for a quiet project and a red flag for one whose work has
just finished - diff the two readings before believing either.
