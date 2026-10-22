# Usage and run surfaces on a Hermes instance

Where the numbers actually live, and which column means what. All of it is read-only and local:
no API call is needed to report the agent's own spend.

## 1. `$HERMES_HOME/state.db` - per-session model usage

Table `session_model_usage`, one row per (session, model, task class):

| Column | Use |
| --- | --- |
| `session_id` | join key to `sessions.id` |
| `task` | **the source of the auxiliary split** - empty for the main turn, `approval` / `title_generation` / `compression` (and similar) for auxiliary calls |
| `api_call_count` | how many calls, so an alert on call volume is possible |
| `input_tokens`, `output_tokens`, `cache_read_tokens` | token accounting |
| `estimated_cost_usd` | the spend figure |
| `actual_cost_usd`, `cost_status` | **the honesty check: expect `0` and `estimated`** |
| `cost_source` | e.g. `provider_models_api` - where the price came from |
| `first_seen`, `last_seen` | epoch seconds, for windowing a period |

Join to `sessions` for the platform:

```sql
select u.session_id, u.task, s.source, u.api_call_count,
       u.input_tokens, u.output_tokens, u.estimated_cost_usd, u.cost_status
from session_model_usage u
left join sessions s on s.id = u.session_id
where u.last_seen >= ? and u.first_seen < ?;   -- epoch seconds, half-open window
```

`session_id` alone does **not** identify the platform - `sessions.source` does (`telegram`,
`tui`, `cli`, `cron`, ...). Scheduled sessions are named `cron_<job_id>_<timestamp>`, which is the
reliable way to attribute spend to a specific job.

Classify in this order, and keep auxiliary first - it can otherwise be swallowed by the session it
belongs to:

1. `task` in the auxiliary set -> **auxiliary**
2. `session_id` starts `cron_<routine job id>_` -> **research / routine**
3. `session_id` starts `cron_` -> **other scheduled** (cleanup sweeps and the like)
4. `source` is an interactive platform -> **interactive**
5. anything else -> **unclassified** (child or delegated sessions); say so rather than folding it
   into a category it might not belong to.

`hermes insights --days <n>` prints the same story as a summary when a rough figure is enough -
but it labels the total "Estimated", and so must you.

## 2. `$HERMES_HOME/cron/usage_audit.jsonl` - per-fire tokens

One JSON line per scheduled fire: `ts`, `job_id`, `fire_id`, `prompt_tokens`,
`completion_tokens`, `total_tokens`, `model`, `duration_ms`, `error`, `deliver_target`,
`response_silent`.

This is the surface for two things the session table cannot answer well:

- **Per-session token caps.** Group by `job_id` within the window and compare each fire's
  `total_tokens` to the cap; a fire over the cap is how an overshooting session is detected after
  the fact.
- **Proving a job is free.** A no-model script job makes **no model calls**, so its `job_id`
  appears **zero** times here while its run shows delivered. That pairing - zero usage entries plus
  a delivered run - is the evidence that a monitoring job sits outside the budget it reports on.
  Absence alone is not evidence; the delivered run is the other half.

Do not assume the file exists or is JSON-clean: skip unparsable lines rather than failing, and
treat a missing file as "no recorded fires".

## 3. `$HERMES_HOME/cron/executions.db` - what ran

Table `executions`: `id`, `job_id`, `source`, `process_id`, `pid`, `process_started_at`,
`status`, `handoff_pending`, `handoff_started_at`, `claimed_at`, `started_at`, `finished_at`,
`error`, `delivery_outcome`, `scheduled_instant`.

- **Period session cap**: count rows per `job_id` with `status in ('completed','failed')` since the
  window start. Failed runs count - they were admitted and spent.
- **Overlap guard**: a row whose status is in flight (`running` / `claimed` / `handoff`) for a
  routine job means a session is already running, so this tick must skip rather than start a
  second one.
- **Scheduled versus delayed**: compare `scheduled_instant` with `started_at` to measure how late a
  tick fired - the input to a late-window skip.
- **Delivery**: `delivery_outcome` is where "did the message land" is recorded, separately from the
  run's `status`.

## What these surfaces cannot tell you

The provider's **subscription quota, reset period and remaining balance** live in the vendor's
portal behind the account owner's login, not here. These tables describe what this instance
recorded, priced by Hermes's own table (`cost_source`) - they cannot reconcile against an invoice.
Report the estimate as an estimate, ask the owner for the portal figure when a routine needs to be
checked against it, and record which of the two a given number is.
