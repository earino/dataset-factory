# Factory rewrite progress

Specification: [FACTORY-REWRITE.md](FACTORY-REWRITE.md).
Goal tool confirmed **active** at kickoff 2026-11-08 11:07:00 UTC.
Checkpoint 15:07:00 UTC; deadline 19:07:00 UTC.

## Current work

- **Latest observed state (13:14 UTC):** deployed `931f617`, scheduler resumed,
  source 1 reopened by the recorded deployment correction, source 3 at build,
  source 4 at discovery. One failed real worker collected and cleaned; zero
  accepted or published replacement datasets. Two complete public runs remain
  the critical path. Earlier entries below retain the implementation history.
- **13:40 update:** deployed `0ddaeae` at 13:31 UTC. Three real construction
  workers have now produced durable failure reports (NID, STATS19, HURDAT2);
  none passed qualification. Two construction model failures were caused by
  the two-turn allowance being consumed by documentation reads. It is now six
  turns, still bounded to 300 seconds and the existing global allowances.
  STATS19's quote rejection was reproduced as a formatting defect against the
  actual publisher page and fixed without accepting invented or reordered text.
  HURDAT2's missing target column is an ordinary builder repair, not a gate waiver.
- **13:49 update:** six-turn/quote fix `d330178` deployed and the tick resumed.
  HURDAT2 build-4, already in flight under the old cap, exhausted the task allowance
  and became deferred. Its measured usage and original failure are preserved under
  `audits/rewrite/hurdat2-build-4/`. Earlier build-2's complete 33,567-character
  construction response passes the construction descriptor/AST contract locally.
  The adapter now retains a valid construction proposal even if Hermes exits 1
  after its iteration-limit wrap-up: measured requested-model usage and the full
  construction contract are required, and all worker and semantic gates still
  follow. Research/review responses do not get this exception. No artifact is
  accepted on the basis of process output alone.
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
- Complete-path implementation `b803f7e31ae1bf86cc2064397f59842086345228` passed
  [CI](https://github.com/earino/dataset-factory/actions/runs/42479249229).
  Integrated Scout's discovery evidence at `778e97546e23bb0c9ebba1ad8dc765a25ee98739`;
  clean clone passed **914 tests, 13 skipped**, with bytecode writing enabled, plus
  doctor/runtime/suitability/historical-approval/rule-inventory/state checks.
  Both [branch CI](https://github.com/earino/dataset-factory/actions/runs/42479305668)
  and [main CI](https://github.com/earino/dataset-factory/actions/runs/42479411071) passed.
- Fast-forward shipped to main at 12:16 UTC. Scout received exact-hash cutover instructions:
  backup live state, pause three old launch/follow-up schedules, retain cleanup, install
  the script-only tick, enable replacement locally, and start a fresh unattended queue.
  Scout confirmed activation at 12:22 UTC: deployed exact hash, runtime inventory
  128 files/zero problems, prior uncommitted evidence retained in backup and stash.
- New scheduler `07d6f8be3783`: every minute, `no_agent: true`, script
  `scout_factory_tick.py`; global script timeout 6000 seconds, shim bound 1200.
  Legacy jobs `86fe52e55ef9`, `69a5bc676d10`, `98b45d983280` paused at
  12:19:17–26 UTC. Cleanup `e80975eddd4a` remains active.
- The **scheduled** 12:21 UTC tick initialized the fresh queue and began bounded
  discovery `rw-4fa4bc1fda01-discover-1`. Scout's simultaneous manual verification
  returned `busy`/exit 0, demonstrating the deployed single-controller lock.
  Two queue slots are seeded; actual source discovery/build results are still pending.
- Next: verify deployed scheduler/model/worker operation, repair actual runtime failures,
  and observe two materially different sources through public consumer verification.
- First deployed discovery completed in 296.3 seconds/11 model calls, selecting
  USACE National Inventory of Dams. No artifact or scientific result yet.
- Actual startup defect: hosted gateway rejects `__none__` as an unknown toolset,
  although local `get_tool_definitions` returns an empty list. Two construction
  attempts failed before session creation. The replacement now uses the already
  working web-only toolset for construction too; no new runtime or permission gate.
  Bounded, redacted stderr is retained for future startup failures.
- A second discovery encountered a provider model-not-found error; Scout's one-turn
  diagnostic probe overlapped a subsequent accounting window. Both failures remain
  evidence; no claim of successful research from those attempts. Tick `07d6f8be3783`
  paused at 12:35:32 UTC for this repair; independent cleanup remains active.
- Accounting now prefers the quiet CLI's actual `session_id:` stderr field, verified
  as a new recorded oneshot session, instead of assuming no unrelated session can
  start during the task. This directly addresses the observed concurrent diagnostic
  probe. Exact model route/usage checks remain; no manufactured usage records.
- Adapter repair `71a1b05a389a91c671772f9dee685c967ba44514` passed **915 clean-clone
  tests, 13 skipped**, and [exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42481365780).
  Sent Scout the exact hash and instruction to resume the existing queue at 12:43 UTC.
  Progress checkpoint `2c87ae88819ad97d88bae44c32732544e98a14fc` also passed
  [CI](https://github.com/earino/dataset-factory/actions/runs/42480221748).
- Scout confirmed repaired revision deployed and tick resumed at 12:44 UTC.
  Original discovery response/usage and startup failures are preserved under
  `audits/rewrite/cutover/`. Scout evidence branch `c9d3661` passed
  [CI](https://github.com/earino/dataset-factory/actions/runs/42481681445).
  Integration clarifies that source inspection of empty-tool mapping did not
  prove the classic CLI accepts an empty string end-to-end; the replacement
  deliberately uses the observed working web-only capability.

## Milestones

### First deployed construction cycle (12:48–12:55 UTC)

- Scout reports construction task `rw-4fa4bc1fda01-build-3` completed in 218.6 s,
  3 model calls, about 15.1k input / 43.8k output tokens. Worker 175132504
  launched from the sole live ledger at 12:48:13 UTC (EUR 0.16 reservation).
- Worker exited 1, not OOM, after 161.3 s. Its five durable staging assets are
  in release 438244578 of `earino/dataset-factory-staging`. Codex directly read
  the manifest and `failure.json`: the generated vocabulary assertion omitted
  the source's `Not Available` condition value. No qualification, measurement,
  or publication was accepted.
- The controller collected the failure, reconciled provider absence, retained
  diagnostics, and deferred the candidate. Source 2 also exhausted discovery
  attempts on invalid JSON; the scheduler seeded source 3 without intervention.
- Retry accounting defect: two pre-worker startup failures consumed the first
  source's construction allowance. Task and worker failures now have separate
  three-failure bounds. A narrowly scoped deployment correction preserves the
  original SQLite row and candidate snapshot, classifies the observed worker
  failure, and reopens only that candidate for ordinary bounded repair.
- Provider absence was observed before the recorded collection timestamp;
  the precise deletion origin is not established. All failed-worker artifacts
  were durably recovered, so this is not evidence of lost construction output.
- No successful real dataset release yet. Semantic review and both public
  consumer checks remain outstanding.
- Retry correction `ee752b433d40e98e90af06824bbd44d87287b529` passed 917 clean-clone
  tests (13 skipped) and [CI](https://github.com/earino/dataset-factory/actions/runs/42482888850).
  Original first-cycle evidence is integrated under `audits/rewrite/first-cycle/`;
  Scout's export also passed [CI](https://github.com/earino/dataset-factory/actions/runs/42482805116).
- Exact malformed discovery bytes reveal incorrectly escaped quotes at line 63,
  column 334. Future discovery retries reuse the retained research in a bounded
  format-repair task instead of repeating full web discovery. Source validation
  still follows; successful JSON parsing is not scientific acceptance.

| Milestone | Implemented | Local tests | CI | Deployed evidence |
| --- | --- | --- | --- | --- |
| Controller and state | Implemented | Restart, retry, lock, queue tests | Passed | Scheduled queue advancement, exclusive lock, failed candidate replaced |
| Mechanical worker lifecycle | Implemented | Collection, cleanup, recovery, upload integration | Passed | Failed worker collected/cleaned with preserved evidence |
| Model tasks and evaluation | Implemented | Source replay, qualification/package/consumer tests | Passed | Discovery and code generation; full evaluation/review pending |
| Automatic publication | Implemented | Two-platform transfer, anonymous loading, retry, exact qualification | Passed | — |
| Cutover and unattended acceptance | Deployed | Lock/legacy guard tests | Passed | Scheduled ticks, legacy schedules disabled, controlled real-source fetch retry/cache replay |

## Acceptance evidence

A1: deployed controller/lock observed; separate scheduled ticks resumed the same
worker identity through collection. Forced-interruption demonstration not claimed.
A2: failed worker collected/cleaned without model bookkeeping; successful worker
advancement remains pending.
A3: live discovery and code generation recorded; semantic review pending.
A4–A5: two complete real-source publications and consumer verification pending.
The source-1 deployment correction is explicit state migration, so its later
success alone will not prove an untouched end-to-end autonomous run.
A6: failed candidates deferred and the queue refilled; the deployed source-fetch
helper recovered from an explicitly injected 503, fetched real HTTPS metadata,
then replayed cached bytes without network. Receipts are in
`audits/rewrite/correction-deploy/`; organic source outage recovery is not claimed.
A7: Scout reports scheduled execution, legacy paths paused and cleanup active;
compact receipts are preserved under `audits/rewrite/cutover/` and subsequent exports.
A8: implementation and evidence shipped with passing exact-commit CI; final
acceptance/sign-off remains open. No completed dataset release claimed.

Latest verification: format-repair change `9e778d7` passed 918 clean-clone tests
(13 skipped) and [CI](https://github.com/earino/dataset-factory/actions/runs/42483088563).
Recovery demonstration `931f617` passed [CI](https://github.com/earino/dataset-factory/actions/runs/42483341561).
Scout's correction export passed [CI](https://github.com/earino/dataset-factory/actions/runs/42484030195).
The observed construction timeout now also preserves measured partial usage and
bounded redacted failure diagnostics; clean clone passed 919 tests (13 skipped).
Allowance at 13:14 UTC: EUR 11.78 worker reservation remaining; measured rolling
inference usage 35.76M/40M tokens (stop fraction 0.95 still applies). Dollar spend
remains unknown; no spending limits were changed.

`0ddaeae` passed [CI](https://github.com/earino/dataset-factory/actions/runs/42484303994).
Second-round Scout exports passed [CI](https://github.com/earino/dataset-factory/actions/runs/42485472885)
and [CI](https://github.com/earino/dataset-factory/actions/runs/42485810110).
Turn/quote fixes passed 920 clean-clone tests (13 skipped). Original worker
manifests and digest-verified failures are retained in
`audits/rewrite/third-worker-outcomes/`; the local real-page quote check is a
transport/format diagnostic, not dataset qualification or publication evidence.
`d330178` passed [CI](https://github.com/earino/dataset-factory/actions/runs/42486489329).
Scout's HURDAT2 build-4 export passed [CI](https://github.com/earino/dataset-factory/actions/runs/42486829140).
Construction-proposal retention passed 921 clean-clone tests (13 skipped).

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
