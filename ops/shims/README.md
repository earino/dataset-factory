# Schedule-entry shims

These wrappers are reviewed sources for the Hermes scheduler entries under
`/opt/data/scripts/`. The table below is the original capture measured
2026-10-22T17:15Z, not a claim that later revisions are already deployed. Current
source identities live in `ops/runtime-files.json`; verify live copies separately.

| File | sha256[:16] | Bytes | Job it serves |
| --- | --- | --- | --- |
| `scout_discovery_session.py` | `4c74e98c2ee963e9` | 3,481 | `scout-discovery-session` (`0 */4 * * *`) |
| `scout_research_session.py` | `eb53d7ba2fdc8f8a` | 457 | `scout-research-session` (`0 2-22/4 * * *`) |
| `scout_advancement.py` | `7357df26038c6861` | 780 | same as above (the job's script entry) |
| `scout_job_watch.sh` | `c9885ca214fe3ab9` | 331 | `scout-worker-watch` (every 5 min) |
| `scout_dashboard.py` | `414584ed6bbdd981` | 1,972 | `scout-dashboard-refresh` (`50 * * * *`) |
| `scout_release_notify.py` | `7532e2c8c36ef1b8` | 300 | `scout-release-notify` (`55 * * * *`) |
| `scout_cleanup_sweep.py` | `567340b87fe7eed1` | 749 | `scout-cleanup-sweep` (`*/10 * * * *`) |
| `scout_weekly_digest.py` | `e1b0a638b1057ee1` | 1,298 | `scout-weekly-research-digest` (Mon 08:00) |

## What they do

They are deliberately thin. Each one either forwards into the repository
(`scout_job_watch.sh` execs `scripts/scout-job-watch.py`; `scout_research_session.py` runs
`scripts/scout_research_session.py` by path) or makes one decision — the region to research — and
then calls the repository's runner:

```
hermes chat --query-file <prompt> --oneshot -Q --source scout-research \
    --max-turns 120 --run-budget 5400 -s <role-specific-skills>
```

Discovery preloads `dataset-discovery`; advancement and worker follow-up preload
`dataset-qualification,dataset-release`. Custom briefs retain all three. The prompts
are in Git (`docs/discovery-session-prompt.md`, `docs/research-session-prompt.md`,
`docs/worker-watch-prompt.md`), so scheduler behaviour is reconstructible from this directory
plus the repository — which is the point of vendoring them.

## Sanitisation review

Each file was read before copying. Findings:

- **No credentials, tokens, keys or `.env` values** in any of the eight.
- **No chat identifiers, thread ids or user ids.** Delivery targets are set on the job, not here.
- **No private repository names, provider hostnames or server ids.** Paths are `/opt/data/...` only.
- Two files contain only an absolute path to a credential *file* (`/opt/data/.secrets/hetzner.token`
  in `register_worker_key.py`, `/opt/data/.secrets/github-staging.token` in `verify_staging.py`).
  Names, not values — and both are excluded below as out of scope anyway.

## Deliberately not vendored

| File | Why omitted |
| --- | --- |
| `fill_candidates.py` (26.5 KB) | operator tooling, not a schedule entry; large enough to deserve its own review |
| `register_worker_key.py` | one-shot provisioning helper; references a credential path and is not needed to reproduce the schedule |
| `verify_staging.py` | operator verification tool; references a credential path, out of scope for a scheduler handoff |
| `wait_scheduled_run.py` | one-shot helper used by hand, not scheduled |
| `scout_budget_checkpoint.sh` | served a completed one-shot (2026-10-03); nothing schedules it now |
| `scout_schedule_probe.sh` | diagnostic script, no job |

None was omitted because of a secret; they are out of scope, and any of them can be reviewed and
added later under the same procedure.

## Verifying a copy

```bash
python3 scripts/check-runtime.py --source-only
python3 scripts/check-runtime.py --home /opt/data
```

The proposed `scout_worker_followup.sh` replaces the active watcher entry via a
supported edit to its existing job. Keeping the old shim in history/inventory does
not authorize enabling both paths. Deployment and readback are tracked in
`docs/PROMPT-IMPROVEMENT.md`.
