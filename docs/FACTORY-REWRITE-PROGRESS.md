# Factory rewrite progress

Specification: [FACTORY-REWRITE.md](FACTORY-REWRITE.md).
Goal tool confirmed **active** at kickoff 2026-11-08 11:07:00 UTC.
Checkpoint 15:07:00 UTC; deadline 19:07:00 UTC.

## Current work

- Base: `1e6aa8207a5f39b0b30d473fe30081b23764a0ff` (latest Scout failure closeout).
- Branch: `codex/factory-rewrite`; worktree `/private/tmp/factory-rewrite-worktree`.
- Specification written; implementation not yet started.
- Next: coordinate hosted ownership/capability/budget inspection with Scout; implement
  transactional state and deterministic worker completion against existing APIs.

## Milestones

| Milestone | Implemented | Local tests | CI | Deployed evidence |
| --- | --- | --- | --- | --- |
| Controller and state | No | — | — | — |
| Mechanical worker lifecycle | No | — | — | — |
| Model tasks and evaluation | No | — | — | — |
| Automatic publication | No | — | — | — |
| Cutover and unattended acceptance | No | — | — | — |

## Acceptance evidence

A1-A8: pending. No real-data acceptance, publication or deployment claimed.

## Known findings relevant to implementation

- Standard upload ledger assets omit names, while the audit collector requires them.
- PriceCatcher per-month weekly aggregation discards part of boundary-spanning weeks.
- Existing scheduler and worker admission disagree about operator-blocked candidates.
- Legacy bookkeeping only handles already collected/deleted/committed jobs.
- Session timing extract supports repeated follow-up activity; aggregate percentages
  are unreconciled and are not an acceptance prerequisite.

## Deferred

Dashboard/website redesign, old remediation matrix completion, experimental
chronological benchmark adapter, global overhead-percentage study.
