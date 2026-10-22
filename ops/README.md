# Ops handoff — index

Two documents, captured 2026-10-22T17:15Z on branch `ops/scout-runtime-handoff` (commit base
`beab726`), plus refreshed machine exports.

| File | What it is |
| --- | --- |
| `HANDOFF-2026-10-22.md` | runtime identity, effective non-secret config, scheduler, skills, state locations, restart survivability, gaps, overlap with scheduled work |
| `OPERATING-NOTES.md` | the working procedures: candidate workflow, interrupted-session recovery, authority order when records disagree, repetitive chores, overlapping processes, obstructive rules, status definitions; plus what to preserve and hardening recommendations |
| `../deployment/scout/versions.json` | Hermes version, upstream revision, install method, local customisations (regenerated 2026-10-22 by `scripts/scout-snapshot.py`) |
| `../deployment/scout/config-export.json` | allowlisted non-secret configuration fields |
| `../deployment/scout/STATE-SNAPSHOT.md` | schedules, budgets, destinations, queue, recovery notes — each with its source |
| `schedule-export.json` | allowlisted machine-readable scheduler state: 13 jobs with schedule, enabled/state, kind, script, per-job overrides and delivery *kind* (no prompts, no chat ids, no history) |
| `shims/` | the eight schedule-entry wrappers, verbatim from `/opt/data/scripts/`, with sha256 and the omission list |
| `skills/` | fourteen custom profile skills with their references, templates and `SKILL.md` hashes, use counts, load paths and precedence |

## Sanitisation

Nothing here was typed from memory where a file could be read, and nothing was copied wholesale.

Excluded by construction: `.env` files, token or auth values, private keys, `state.db` and any raw
session or tool history, full conversations, personal memory, and the private staging repository and
provider identifiers. Credential **names and paths** appear; values do not. The snapshot writer
refuses to emit a file containing a secret-shaped string, and `--check` verifies that gate.

Regenerate the three deployment exports with:

    python3 scripts/scout-snapshot.py            # write
    python3 scripts/scout-snapshot.py --check    # verify committed exports are clean

## Gaps, stated rather than papered over

- Scheduler definitions/prompts/overrides live in `/opt/data/cron/jobs.json`; execution history
  is `/opt/data/cron/executions.db`, and per-job output is `cron/<job_id>/`. The allowlisted export
  deliberately omits prompts, delivery identifiers and history. `state.db` holds conversation data,
  not scheduler definitions. Do not export these raw state files.
- Eight schedule-entry wrappers are now preserved verbatim in `ops/shims/`. Four other host
  helpers remain out of scope, with reasons in `ops/shims/README.md`.
- Published-artifact digests are in each `release/*/MANIFEST.json`; this handoff does not duplicate
  them.

## Check drift before using this handoff to recover a host

```sh
python3 scripts/check-runtime.py --source-only
python3 scripts/check-runtime.py --home /opt/data
```

The first command checks that `ops/runtime-files.json` covers exactly the reviewed shim and
custom-skill files and that their hashes match. CI exercises it. The second also compares live
copies and flags profile skills with the same name as a repository skill. It also compares the
live project skill Markdown/Python files with the committed inventory fingerprints, so uncommitted curator edits
are visible even when the audit runs from that same live checkout. The live project defaults to `<home>/dataset-factory`; `--project` overrides it. It is read-only, does
not execute the files, and reports paths/reasons without their contents. Missing/changed/unsafe
files cause a nonzero exit. A mismatch requires inspection, never automatic replacement.

The inventory records source-to-host paths; after an intentional reviewed change, update its
SHA-256 and review both diffs together. These checks establish file identity only. They do not
verify scheduler registration, credential availability, budget, upstream Hermes behavior or
publication. Restore only the reviewed files, preserve live state, and validate those separate
operational prerequisites before enabling schedules. No secret or raw scheduler/session database
belongs in this inventory.

## Automatic skill writers are separate controls

Installed-runtime inspection by Scout found two independent paths. The per-turn background
review checks `auxiliary.background_review.enabled`; it does not check curator paused state.
`hermes curator pause` controls only interval curation. Pinning a skill blocks deletion, not
patches or writes. Before restoring reviewed skill bytes, disable background review, pause the
interval curator, verify writers have drained, and preserve live diffs with digest preconditions.
See [the prepared rollout](../docs/HARDENING-DEPLOYMENT.md) and
[Scout's source-level evidence](https://github.com/earino/dataset-factory/pull/4#issuecomment-6347671806).
This supersedes the earlier assertion that pausing interval curation alone stopped skill edits.

Later source inspection ruled out nudge intervals as a safe substitute: cached agents keep old
values and memory-only forks still receive skill_manage. The background-review timeout is
per request, not a thread lifetime; a controlled supported restart is needed to prove old
threads are gone before restoring files. The master-switch hold also pauses auxiliary memory
edits; it does not stop ordinary research or explicit repository/memory work. See
[the final source review](https://github.com/earino/dataset-factory/pull/4#issuecomment-6348148964).
