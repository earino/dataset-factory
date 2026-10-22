# Verifying a third-party scheduled job

Scope: you configured a hosted service (GitHub Actions and similar) to run a job on a schedule, and now have to prove it does what the design needs — not merely that it was accepted.

## Configure its credentials and variables through stdin

- `gh secret set NAME --repo owner/repo < /path/to/token` — file input keeps the value out of the process table, shell history and run logs. Never as an argument.
- For variables, read the value out of the config file the runtime itself consumes rather than retyping it: `--body "$(python3 -c "import json;print(json.load(open('config/local.json'))['project'])")"`. Two hand-maintained copies of the same string drift, and the drift shows up as a job that runs against the wrong resource.
- Confirm with `gh secret list` / `gh variable list`: they expose names and timestamps, not values.
- The service's copy of a credential is independent of the local file. Changing one does not change the other; say so when recording the setup.

## Prove the job executed, not that the workflow was accepted

- **A run-level conclusion is not evidence.** A job gated by `if: vars.X == 'true'` concludes `skipped` while the run still reports `completed`, and a dispatch is accepted before anything has run.
- Read the **job's steps** (`gh run view <id> --json jobs`, check each step's `conclusion` and `startedAt`) and the step's own stdout (`gh run view <id> --log`). Only then claim execution.
- Have the job print a machine-readable summary and inspect it — an `errors: []` array from your own script is the signal that its credential worked and the call completed; a bad token surfaces there instead of as a crash.
- Note which env values the runner masks in the log; that is expected and is not evidence of a leak.

## An empty mutation list proves the wiring, not the capability

A sweeper that reports `deleted: []` because nothing existed has still never exercised the deletion path: the ownership re-check, per-resource cleanup, the error handling on a real target. Write the record as an explicit pair — **scheduler/credential plumbing verified**, **side effect not verified** — rather than letting a green run imply the whole feature works. Then schedule the missing piece into the smoke cycle where a real resource exists to delete.

## Name which deletion path is primary

The design usually has two: the agent deletes each resource as part of finishing the job, and the scheduled sweep catches leftovers. Write the roles down where the schedule is documented, because it changes how a run reads:

- An **empty deletion list is the expected result** while the primary path is working — say so, or the next reader takes a healthy run as evidence the sweeper is broken.
- The interval is a **backstop cadence, not a deadline**. A per-job cost reservation should cover the extra post-expiry time that a delayed sweep implies; check that and record it rather than implying the schedule guarantees deletion.
- Run the primary path's own boundary in the docs: a sweep that has never deleted a real resource leaves the deletion code unproven, however green the schedule is.

## Scheduled runs are delayed, and can be dropped

- Cite the provider's own documentation instead of guessing: the `schedule` event can be delayed during periods of high load (the start of the hour is named as a peak) and queued jobs **may be dropped** under sufficient load. Scheduled runs execute on the default branch, in UTC unless a timezone is declared — so a cadence change only takes effect once the workflow file is on that branch.
- Compare the *observed* cadence against the cron expression before promising a frequency — list runs with `event == schedule` and diff the timestamps. A 15-minute expression producing runs hours apart is normal, and it changes what the backup path is worth.
- **Bound the wait.** Poll in a tracked background process with a deadline, and filter by `createdAt > <the moment you enabled it>`. Without that cutoff the newest pre-enablement run (usually the `skipped` one) satisfies the filter and you announce success on the wrong run.
- Report **pending** as an honest intermediate result while the watcher runs — never infer success from the configured interval.
- A long wait belongs in a tracked background process with a completion notification, not a foreground call: an over-long foreground timeout is promoted or killed, and its output is lost.

## Choose the interval from the metered-budget, not from taste

Hosted CI rounds each execution up, so a short job still costs a full minimum minute. Compute `runs/day × 30` against the plan's included minutes for the repository's visibility (private repos have a monthly allowance; public ones do not) **before** recommending an interval, and surface the arithmetic as an explicit decision for the operator. Hourly on a private repo fits a free-tier allowance where a 15-minute cron does not — so the cheaper interval can also be the correct one on cost grounds.

When the interval is long, pick the **minute off the hour**: the same documentation that describes delays names the start of the hour as a peak, so a `17 * * * *` expression is strictly better than `0 * * * *` at identical cost. Keep manual dispatch available for on-demand runs.

If the diagnostic number you want (billing usage, quota) needs a scope the existing credential does not carry, **report the gap instead of widening it** — do not refresh or re-scope a working credential as a side effect of an inspection task.
