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

- Scheduler **prompts and per-job overrides** live in the Hermes state DB and are summarised here;
  their verbatim text is not exported. The shim bytes they call are hashed in the handoff.
- The 12 cron shims live outside Git and are recorded only as name + sha256 + size.
- The host's `state.db` (155 MB) is the only copy of scheduler definitions and history; it is not
  exported and would be lost with the host.
- Published-artifact digests are in each `release/*/MANIFEST.json`; this handoff does not duplicate
  them.
