# Factory rewrite progress

Specification: [FACTORY-REWRITE.md](FACTORY-REWRITE.md).
Goal tool confirmed **active** at kickoff 2026-11-08 11:07:00 UTC.
Checkpoint 15:07:00 UTC; deadline 19:07:00 UTC.

## Current work

- Base: `1e6aa8207a5f39b0b30d473fe30081b23764a0ff` (latest Scout failure closeout).
- Branch: `codex/factory-rewrite`; worktree `/private/tmp/factory-rewrite-worktree`.
- Specification committed at `8eafdd924432cd7f7be95eeb3e16230389dddac4`;
  [exact-commit CI passed](https://github.com/earino/dataset-factory/actions/runs/42474453958).
- Implemented SQLite attempts, restart checkpoints, exclusive controller tick,
  bounded retries, and mechanical worker collection/deletion/staging recovery.
- Corrected uploader asset names; producer-to-consumer integration now exercises
  actual uploader output through the existing audit collector.
- Local full suite: 899 tests passed, 13 skipped (2026-11-08 11:17 UTC).
  This is software verification, not deployed acceptance.
- Scout readiness: zero workers/IPs at 11:10:15 UTC; EUR 11.94 remaining reservation
  allowance; about 4.9M of 40M weekly inference tokens remain. Dollar inference
  spend is unknown. Requested DeepSeek route is installed and previously used.
- Implemented the complete controller stage driver, canonical construction/qualification/
  existing-runner evaluation bundle, reproducible source snapshot, and one deterministic
  publication worker using existing transfer/Hub code. Integration testing is underway;
  production remains disabled pending cutover. No public dataset acceptance claimed.
- Foundation commit `0219d1a1443048b2f76df54515466794d35eef6d` passed 903 clean-clone tests
  (13 skipped) and [CI](https://github.com/earino/dataset-factory/actions/runs/42475577407).
  Task contracts `02fa6105e3114920737d6bfcc3b2396b1aafd311` also passed
  [CI](https://github.com/earino/dataset-factory/actions/runs/42475905909).
- First actual DeepSeek discovery: Scout reports 153.9 seconds, 9 API calls,
  38,248 input / 15,892 output / 206,208 cache-read tokens, 12 web tool results.
  Recorded route `deepseek/deepseek-v4.1-flash-1017`, provider `nous`.
  Proposed TESS TOI vetting source remains unqualified; current-vintage features
  and outcome-conditioned selection require review, not forecasting claims.
- Runtime finding: `--usage-file` is top-level-only and is ignored by the bounded
  `chat --oneshot` path. Removed it; retain measured `state.db` accounting.
  The first parser failure made zero model calls. Startup diagnostics now
  distinguish no session from multiple sessions and preserve safe parser errors.
- Integrated software tests now exercise the canonical full qualification report through
  automatic publication admission, both provider transfers and anonymous full-file consumers,
  interrupted private staging with safe retry, captured terms, and host operation exit status.
  These remain software tests; live publication acceptance is outstanding.
- Deployment uses `config/local.json.pipeline_enabled=true`; legacy admission hold remains
  intact. Only running SQLite build/publish attempts may launch replacement workers.
  Old research and follow-up entrypoints exit without models when the replacement is enabled.
- Next: finish clean-clone checks, commit/push, verify CI, and coordinate the single-ledger
  cutover with Scout while retaining the independent cleanup scheduler.

## Milestones

| Milestone | Implemented | Local tests | CI | Deployed evidence |
| --- | --- | --- | --- | --- |
| Controller and state | Implemented | Restart, retry, lock, queue tests | Foundation passed; integration pending | — |
| Mechanical worker lifecycle | Implemented | Collection, cleanup, recovery, upload integration | Foundation passed; integration pending | — |
| Model tasks and evaluation | Implemented | Source replay, qualification/package/consumer tests | Pending | Discovery pilot only |
| Automatic publication | Implemented | Two-platform transfer, anonymous loading, retry, exact qualification | Pending | — |
| Cutover and unattended acceptance | No | — | — | — |

## Acceptance evidence

A1-A8: pending. No real-data acceptance, publication or deployment claimed.

## Known findings relevant to implementation

- Standard upload ledger assets omitted names while the audit collector required them;
  fixed in the replacement branch, including compatibility with older nameless ledgers.
- PriceCatcher per-month weekly aggregation discards part of boundary-spanning weeks.
- Existing scheduler and worker admission disagree about operator-blocked candidates.
- Legacy bookkeeping only handles already collected/deleted/committed jobs.
- Session timing extract supports repeated follow-up activity; aggregate percentages
  are unreconciled and are not an acceptance prerequisite.

## Deferred

Dashboard/website redesign, old remediation matrix completion, experimental
chronological benchmark adapter, global overhead-percentage study.
