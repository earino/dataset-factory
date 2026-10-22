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
| `skills/` | the two project-relevant custom skills (`open-data-source-vetting`, `agent-handoff-packaging`) with references and template, plus load paths and precedence |

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

## Check drift before using this handoff to recover a host

```sh
python3 scripts/check-runtime.py --source-only
python3 scripts/check-runtime.py --home /opt/data
```

The first command checks that `ops/runtime-files.json` covers exactly the reviewed shim and
custom-skill files and that their hashes match. CI exercises it. The second also compares live
copies and flags profile skills with the same name as a repository skill. It also compares the
live project skill Markdown/Python files with the reviewed checkout, so uncommitted curator edits
are visible. The live project defaults to `<home>/dataset-factory`; `--project` overrides it. It is read-only, does
not execute the files, and reports paths/reasons without their contents. Missing/changed/unsafe
files cause a nonzero exit. A mismatch requires inspection, never automatic replacement.

The inventory records source-to-host paths; after an intentional reviewed change, update its
SHA-256 and review both diffs together. These checks establish file identity only. They do not
verify scheduler registration, credential availability, budget, upstream Hermes behavior or
publication. Restore only the reviewed files, preserve live state, and validate those separate
operational prerequisites before enabling schedules. No secret or raw scheduler/session database
belongs in this inventory.
