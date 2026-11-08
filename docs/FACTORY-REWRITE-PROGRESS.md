# Factory rewrite progress

Specification: [FACTORY-REWRITE.md](FACTORY-REWRITE.md).
Goal tool confirmed **active** at kickoff 2026-11-08 11:07:00 UTC.
Checkpoint 15:07:00 UTC; deadline 19:07:00 UTC.

**Current implementation status: 1 of 2 required public benchmarks verified.**
UCMR `v-4a630108a6e75a6b` is public on
[GitHub](https://github.com/earino/factory-ucmr5-first-sample-pfas/releases/tag/v-4a630108a6e75a6b)
and [Hugging Face](https://huggingface.co/datasets/earino/factory-ucmr5-first-sample-pfas).
The publication worker anonymously verified all 33 files and loaded every split
on both platforms; root independently fetched identical public manifests without
authentication. `2963e1f` is deployed; the publication retry succeeded after the
tag-call correction. The bridge proposal is the second-source path; its literal
feature-naming failure is corrected in code and the saved proposal can be reused.
That correction passes 953 clean-checkout tests (13 skipped); deployment and the
bridge's full worker validation/publication are next. The goal is incomplete.

The first eight-hour run ended incomplete and was safely wound down; its cutoff
and final resource inventory remain preserved as historical evidence. The tool's
stored old goal is still paused and cannot be resumed by the agent's tools;
Eduardo explicitly authorized continuing this implementation in the current turn.
This is not a completion sign-off.

## 2026-11-08 21:52 UTC — recovery deployed; actual archive access failure

`b740521` passed [exact CI](https://github.com/earino/dataset-factory/actions/runs/42525699392)
and deployed at 21:37:59 UTC. The normal tick mechanically reconciled source-15,
reused its build-3 proposal with zero new model calls, and launched build-6.
This verifies the saved-proposal path in production, without manual state edits.

The worker stopped after 32.8 seconds because the FHWA disclaimer URL returned
HTML rather than a ZIP. It did not reach qualification or scoring. Root fetched
the compact staging manifest and failure diagnostic, and independently read the
8,161-byte disclaimer page: its ordinary link points to the direct archive;
it does not redirect. The saved source recipe already names that direct URL.
Evidence: `audits/rewrite/bridge-build6-access-failure/`. The normal bounded
construction repair must correct the access code; no new source-specific
controller or acceptance rule is needed. Second-source acceptance is still open.

Scout's inventory/correction export is in `audits/rewrite/inventory-2145/`.
The correction supersedes the original qualification wording and cumulative
usage label: 1,663,491 tokens / 92 calls belong to 15 factory oneshot sessions
started in the new window at its snapshot; 5,257,838 tokens belong to the old
window. These are recorded model-task usage, not actual spend, and do not include
all development conversation activity. Some task elapsed records are incomplete.
The live export is a snapshot, not final accounting. Its exact CI passed at
[ad554b8](https://github.com/earino/dataset-factory/actions/runs/42527045087).

## 2026-11-08 21:33 UTC — recover the pre-fix bridge deferral

Scout deployed `2963e1f` at 21:13:06 UTC, after source-000015 had already
exhausted five model-task attempts at about 21:12:44. Three failed on the
obsolete feature-name rule; two then failed JSON parsing. No construction
worker launched. The last JSON error and terminal deferral prevented the
ordinary saved-proposal reuse path from running. Evidence:
`audits/rewrite/bridge-deferral-state/` (Scout `bf3b61d`, exact CI passed).

The controller now reconciles this specific pre-worker failure class once.
It checks the retained attempt history, requires a saved proposal to pass
current construction and task-description validation, and resumes normal
construction with those exact bytes. Independent decisions, worker failures,
invalid proposals, and candidates with existing jobs/artifacts are excluded.
All five failed attempts remain; no allowance is reset. The latest bridge
build-3 proposal passes the corrected contract. Worker qualification and
semantic review remain mandatory. Clean checkout: 954 tests passed, 13 skipped;
30 focused controller/engine tests passed; rule inventory passed. This is code recovery, not a manual
candidate-state advance or evidence that the bridge is publishable.

## Revised plan after the timebox — 2026-11-08

The operator confirmed that **prediction benchmarks remain the product**. The
proposal to publish plain curated data instead was withdrawn before implementation.
[The revised specification](FACTORY-REWRITE.md) keeps A1–A8 unchanged and sizes
requirements to the benchmark's stated use. Dates, availability and leakage checks
remain material where they affect that use; unsupported forecasting claims,
cosmetic review loops and checks on irrelevant excluded rows are not additional
requirements.

Next work: one authoritative current task description; smaller repairs using saved
code/evidence; complete UCMR through automatic publication and anonymous consumers;
then prove the same path on a materially different source. Keep the existing
controller/workers/publishers. No new framework, reviewer cascade or general cache
is planned. Record actual stage timing and usage with existing records. The prior
2–4-hour estimate is not a reliable completion commitment.

This is a documentation change only. The implementation goal and production
admissions remain paused. No runtime configuration, worker, model call, candidate
state or release was changed. The revised behavior is not claimed as implemented.

## Four-hour checkpoint — 2026-11-08 15:07 UTC

Reported to the operator at the agreed checkpoint; continuing without awaiting a
reply. Goal remains active, with four hours until the 19:07 UTC deadline.

The replacement is deployed and running again. Scout confirmed `d16deb5` deployed
and the tick resumed at approximately 15:05 UTC. Automatic failed-worker handling,
queue advancement, durable staging recovery and scheduled operation have real
evidence. Old launch/follow-up production paths remain disabled, cleanup active.
Both import and repair-context fixes passed 927 tests (13 skipped) in a clean
checkout. Exact-commit CI passed for
[`ddbdf59`](https://github.com/earino/dataset-factory/actions/runs/42492642515) and
[`d16deb5`](https://github.com/earino/dataset-factory/actions/runs/42492795262).
Scout's measured checkpoint export also passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42492568074).

**Zero replacement datasets have completed the path.** Runtime integration defects
consumed too much of the first half. STATS19 reached full-artifact qualification
but failed; rejected bytes were not published. Sources 7 and 8 now lead the queue.
Successful write-only construction, full qualification/evaluation, semantic review,
publication and anonymous consumers remain on the critical path. The two-source
acceptance criterion is unchanged; deployment replays do not substitute for it.

Completion by the deadline remains possible, but is not yet a confident forecast.
At the checkpoint I reported 1,233,486 tokens of headroom. That interpretation was
wrong: the 15:00:01 UTC measurement left **3,233,486 tokens** before the actual
40M weekly admission ceiling, plus EUR 10.82 of worker reservation allowance.
Correction recorded at 15:17 UTC below. The remaining work stays
focused on actual blockers in the deployed path. No additional projects, allowance
increases, source resurrection or validation exceptions are planned. If the criteria
remain unmet at 19:07, wind down new work safely, retain cleanup/resumable state and
report the missing evidence and estimated additional effort.

## Final acceptance assessment — 2026-11-08 19:08 UTC

This records observed evidence and gaps. It is not completion sign-off.

- **A1 — observed:** the deployed scheduled controller keeps durable attempt/job
  identities across deployments and excludes concurrent ticks. See
  [cutover](../audits/rewrite/cutover/) and [first cycle](../audits/rewrite/first-cycle/).
  A successful publication restart has not been demonstrated.
- **A2 — observed for construction:** both failed and successful real workers were
  staged, collected and deleted mechanically. UCMR builds 5–7 reached review;
  the final ledger has no pending collection or active servers. A publication
  worker has not completed the real replacement path.
- **A3 — observed:** the requested inexpensive route performed bounded discovery,
  builder generation and substantive review on real sources. Prompts, responses,
  usage and failures are retained, including [UCMR review 2](../audits/rewrite/ucmr-evaluate2-review/).
  Reviews correctly requested repairs; this is not evidence of general model reliability.
- **A4 — NOT MET:** zero of two materially different sources completed automatic
  public publication. UCMR passed full qualification/packaging but needs corrected
  release descriptions and semantic acceptance. ClinicalTrials failed terms capture;
  the final queue marks it rejected. CMS exhausted its bounded attempts.
- **A5 — NOT MET:** exact-artifact receipts and all 33 package bindings were checked
  for UCMR builds 6 and 7. No accepted public replacement release has reproducibility,
  usefulness and anonymous full-file consumer evidence on both platforms together.
- **A6 — observed:** real failed-worker collection, durable staging recovery,
  semantic repair and bounded defer/refill occurred. The
  [controlled transient-fetch probe](../audits/rewrite/live_fetch_recovery.py)
  used a real publisher; it is not an organic outage claim. Publication recovery
  still lacks end-to-end live evidence.
- **A7 — observed:** unattended script-only ticks ran, three legacy launch/follow-up
  schedules were paused, and independent cleanup was retained. The timebox cutoff
  stopped new admissions safely. Successful unattended publication remains unproven.
- **A8 — partial:** implementation and evidence were pushed with exact-commit CI
  checks. Final implementation [CI passed](https://github.com/earino/dataset-factory/actions/runs/42512474404).
  This record maps every criterion to evidence and limitations. Overall completion
  sign-off is withheld because A4 and A5 are unmet.

## Current work

- **Final deployed implementation:** `6ac5f83` at 19:00:03 UTC. Admissions
  disabled at 19:06:21 UTC; zero active workers at final inventory. Development
  tokens remain measured separately from the normal-operation weekly ceiling.
  Earlier observations below are retained as history, not current runtime state.
- **Earlier deployment (14:50:19 UTC):** Scout reports `05fab28` deployed and
  the script-only tick resumed. Its [exact-commit CI passed](https://github.com/earino/dataset-factory/actions/runs/42491352932).
  The clean checkout passed 926 tests (13 skipped). No replacement dataset has
  passed all gates or been published. STATS19 reached full-artifact qualification
  and failed four checks, documented below; the next repair uses the corrected
  finalizer and focused diagnostics. The write-only adapter is deployed but its
  first successful live use is still pending observation.
- Source 6's SBA discovery omitted attribution fields entirely; this was not an
  explicitly empty credit. The next bounded discovery selected openFDA recall
  enforcement reports and advanced to construction. Exact responses are retained
  under `audits/rewrite/source-6-attribution/`. No evidence requirement was relaxed.
  Scout's export and correction both passed CI
  ([export](https://github.com/earino/dataset-factory/actions/runs/42491580661),
  [correction](https://github.com/earino/dataset-factory/actions/runs/42491611081)).
- **Earlier observation (13:14 UTC):** deployed `931f617`, scheduler resumed,
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
inference usage 35.76M/40M tokens (approximately 4.24M remaining). Dollar spend
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
`3c3c551` passed [CI](https://github.com/earino/dataset-factory/actions/runs/42487251797).

### Deployment recovery at 14:03 UTC

Scout deployed `3c3c551` and reopened source 3 (HURDAT2) and source 4 (STATS19)
under the controller lock, reusing their existing construction proposals unchanged.
The former had been discarded at the old model turn limit; the latter had hit the
publisher-quote formatting defect. Both previous workers were deleted. Original
attempt rows remain, and fresh queued candidates were preserved. Receipts and the
exact reused proposals are in `audits/rewrite/deployment-replay/`; the export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42487997311).
The source-3 receipt reflects a partially completed first migration pass, explicitly
recorded, rather than claiming an untouched before-state. These are deployment
recoveries and do not establish A4's uninterrupted autonomous path.

Codex independently parsed and validated both proposals. Source 4 writes `target`
while declaring `quality.target=ksi`, the same kind of mismatch that stopped the
previous HURDAT2 worker. The construction prompt now makes exact header agreement
explicit, and the worker error reports the declared name and observed headers.
It still rejects the mismatch before any measurement; it does not silently rename
columns or alter the frozen task. Normal bounded repair remains responsible for
correcting generated code. Full qualification/publication is still pending.

At 14:05:55 UTC the replayed HURDAT2 build-5 durably staged its failure
(release 438286225): exit 1, not OOM, 32.6 seconds. Its source assertion found two
disagreements between HU status and the >=64-knot rule. The exact failure bytes
were verified against the staging manifest and preserved alongside the replay
receipts. No qualification or scores passed. The controller's normal bounded
repair must resolve source semantics against the frozen target; no assertion was
manually removed. Source-4 launch was waiting for the prior worker's reconciliation.

The repair context previously supplied only the source and failure, discarding
the previous builder from the model's context. It now includes the exact saved
proposal in place of the generic schema example, so repairs can preserve working
code. Both live proposals fit the existing 64 KiB prompt bound even with the full
12,000-character failure allowance; model time/turn/spending limits are unchanged.

At 14:07 UTC Scout measured 36,339,072/40,000,000 rolling inference tokens and
123/200 sessions, leaving approximately 3.66M tokens. The earlier claim here of
1.66M headroom incorrectly applied the dollar stop fraction to tokens; corrected
at 15:17 UTC against the admission code.
Source 5 had completed discovery; source 6 was retrying malformed discovery JSON.
Full source-3/4 state exports explicitly distinguish reconstructed before-states
from observed after-states. These reconstructions are not original snapshots.
Header-contract change `c22aaf9` passed 922 clean-clone tests (13 skipped) and
[CI](https://github.com/earino/dataset-factory/actions/runs/42488312551).
Repair-context change passed 923 clean-clone tests (13 skipped). Scout's complete
state export passed [CI](https://github.com/earino/dataset-factory/actions/runs/42488252046).
`a06169d` passed [CI](https://github.com/earino/dataset-factory/actions/runs/42488715059)
and Scout reports deployment at 14:15:08 UTC with the scheduler resumed.
STATS19 build-2 staged at 14:15:48 UTC (release 438291663), exit 1 after 45.1 s,
not OOM. It reached the expected `KeyError: ksi` after construction. Its bundle
had been assembled before the clearer error was deployed; immutable attempt
bundles were preserved. Exact manifest and verified failure bytes are retained.
No passing qualification or publication is claimed for either replay.

### Construction needs a write-only capability (14:27–14:35 UTC)

HURDAT2 build-6 received its exact failed proposal but used all six turns on
12 web calls and returned only a 170-character exhaustion message. It deferred
at the existing limit; no further state reopening was requested. Exact prompt,
usage, final response and tool sequence are in `audits/rewrite/build-6-turn-exhaustion/`.
Source 5 (BTS flight arrival disruption) reached a worker but its terms URL
returned HTTP 403; the source was rejected without dataset acceptance. Source 6
(SBA corporate charge-offs) was retrying incomplete attribution evidence.

Installed-source inspection confirms `HermesCLI(toolsets=[], run_budget=...)`
preserves explicit zero tools and the native time bound. The argv parser alone
maps empty tool selections to defaults. The replacement's small write-task adapter
therefore calls that constructor and the existing quiet single-query procedure.
It retains the gateway, source/usage accounting, model route, admission lock,
outer timeout and native cleanup. Constructor assertions reject changed runtime
semantics before inference; measured tool execution rejects a write-only result.
Discovery and review retain web access. No model, spending limit, retry allowance
or scientific check was relaxed. Live verification of this adapter remains pending.
Clean checkout: 924 tests passed (13 skipped). The preceding evidence-only commit
`19da69b` passed [CI](https://github.com/earino/dataset-factory/actions/runs/42489589348),
and Scout's turn-exhaustion export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42490155457).

### First full-artifact qualification attempt (14:41:37 UTC)

STATS19 build-3 corrected its target header and reached the full gate. It exited 1
after 256.8 seconds, not OOM (staging release 438306422). The digest-verified report
and failure are in `audits/rewrite/new-source-outcomes/`. Four checks failed:
availability status values used `documented` instead of the gate's supported
statuses; training-label timing was `post_outcome` rather than an explicit
unverified retrospective assumption; timing observations included non-date text;
and worker-finalized event counts used full IDs while the gate groups key[:10].

The deterministic finalizer now matches the gate's existing conservative grouping,
including empty keys. A producer/consumer test checks agreement against the actual
gate; the gate itself is unchanged. Construction instructions specify the existing
status/timing schema and date-key grouping. Repairs receive failed check details
instead of a report dominated by passing evidence and hashes; full evidence stays
in the store. Unknown dates must stay unknown, and retrospective assumptions must
remain explicit. No new scores or accepted artifacts follow from this failed run.
The counter and diagnostic fixes passed 926 clean-checkout tests (13 skipped).
Write-only adapter `61b7da1` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42490660352).

### Write-task startup correction (14:59 UTC)

Both queued write tasks crashed before creating a model session: direct script
execution put `factory/` on Python's import path, so our `factory/http.py` shadowed
the standard-library `http` package imported by Hermes. Exact startup failures
are preserved in `audits/rewrite/write-task-import-shadow/`. Scout reports sources
4 and 6 deferred after the existing startup-failure allowance; no further state
reopening was requested. New work is paused for the deployment correction while
independent cleanup remains active.

The helper now removes only its own script directory from the import path before
loading installed Hermes. A subprocess test executes the actual script from a
neutral working directory and loads a CLI module importing `http.client`: it
reproduced the exact failure before the fix and passes after it. This test proves
the import correction, not inference or dataset acceptance. The clean checkout
passed 927 tests (13 skipped). Scout's failure export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42492433726).
The preceding status commit `7f02804` also passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42492253325).

### Repair context and remaining allowance (15:00 UTC observation)

Scout's checkpoint export is in `audits/rewrite/checkpoint-1507/`; its contents
were measured at 15:00:01 UTC, not at the later checkpoint name. Sources 1–4 and
6 are deferred; source 5 is rejected on unavailable publisher terms; source 7
has completed discovery and source 8 is in discovery. The tick paused at
14:59:57 UTC for the import repair; zero provider servers remain and cleanup
stays active.

Measured inference usage is 36,766,514/40,000,000 rolling-week tokens, with
3,233,486 before the configured 40M token ceiling, and 131/200 sessions
(corrected at 15:17 UTC; the original export misapplied the dollar stop fraction).
Worker reservations are EUR 9.18/20.00, leaving EUR 10.82. These are configured
allowances, not a claim about actual subscription spend. No limits were raised.

Before the import crash, STATS19 build-4 also hit the 64 KiB prompt-size refusal.
The earlier statement that the two then-existing proposals fit was true of those
proposals, not a guarantee about subsequent repairs. The adapter's input-size
bound is now 128 KiB to accommodate the actual builder, semantic descriptor,
source evidence and bounded diagnostics together. This changes the adapter's
request-size check only; turn/time limits, inference admission, worker budgets,
artifact qualification and publication requirements remain unchanged. It does
not reopen deferred attempts. Focused model-task tests pass.

### First successful write-only model task (15:11–15:14 UTC)

Source 7 (`usfs-firestat-wildfire-100ac`) produced a valid 11,275-byte builder
through the corrected adapter: one main call, requested DeepSeek route via Nous,
6,473 input / 45,994 output tokens, zero attempted or executed tools, exit 0,
246.6 seconds. Exact response, usage, discovery and worker record are retained
under `audits/rewrite/first-write-only/`. Scout's export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42493717884).
This verifies bounded write-only construction, not model suitability for all stages.
Semantic review remains unobserved.

Worker 175148469 (EUR 0.16 reservation) failed after 32.4 seconds, exit 1, not OOM.
The terms check rejected the supplied quote; staging release 438323271 contains
the durable report. Exact manifest and hash-verified failure are retained under
`audits/rewrite/new-source-outcomes/`. The controller collected/deleted the worker
and rejected the candidate automatically. The claimed quote was absent from both
the cited CC0 deed and the source metadata in a separate bounded read. This is a
rejection of unsupported proposal evidence, not a determination that USFS data
cannot be redistributed. No accepted dataset or score resulted. Source 8 discovery
has hit bounded timeouts and continues under its existing allowance.

Four-hour checkpoint commit `69e0ea4` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42493190422).

### Accounting interpretation correction (15:17 UTC)

Inspection of `scripts/research-budget.py:_evaluate` and the actual `run_gate`
call established that `stop_fraction=0.95` applies only to priced dollar spend.
The token gate compares input plus output tokens directly against
`weekly_token_budget=40,000,000`. It does not stop at 38M. My earlier correction
to Scout was itself wrong; the 15:00:01 measurement therefore left 3,233,486 tokens,
not 1,233,486. The user and Scout were notified, and affected prose above corrected.
The original measured usage export is unchanged. No code or configured limit was
changed. Source 7's write task used 52,467 input-plus-output tokens, not only its
6,473 input tokens. Current remaining headroom must still be remeasured after
subsequent tasks; these figures refer to their stated observations.

The first write-only evidence integration `1d3bc87` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42493852414).

### Ordinary discovery timeout recovery (observed by 15:17 UTC)

Source 8's first discovery hit the 330-second outer timeout during final JSON
generation after 12 web tool reads. The truncated 12,649-character response and
partial usage are preserved under `audits/rewrite/source8-discovery-timeout/`.
Its second ordinary attempt completed in 215 seconds with nine reads, selecting
`sba-7a-loan-chargeoff`, and the controller advanced it to build. This is observed
automatic recovery within the existing allowance, without a state edit or extra
probe. No additional runtime change follows from this timeout. Scout's export
passed [CI](https://github.com/earino/dataset-factory/actions/runs/42494068244).

The hosted capability inventory now records the verified empty-tool constructor
path and distinguishes it from the earlier temporary web-only construction path.
The budget-interpretation correction `fdcec77` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42494036812).

### Bounded source-evidence repair (15:30 UTC finding)

SBA source 8's first worker produced the same terms-quote failure as USFS. Its
exact manifest and digest-verified failure are retained in `new-source-outcomes/`
(staging release 438333639, manifest asset 724347456). The immediate terminal
rejection discarded the researched task and paid builder before a bounded
correction could repair the source claim.

Terms capture failures now use the existing worker retry allowance. On the next
attempt, a bounded research task can correct only terms/documentation fields and
their evidence. The controller preserves the previous source, reuses the builder,
and keeps download URLs, target/features and splits fixed. It re-runs the same
captured-document check and full artifact checks on a new immutable worker bundle.
A research verdict that cannot establish readable terms rejects the candidate.
Malformed repair output retains the repair classification across task retries.
No new stage, allowance, approval, or validation exception was added. Previously
rejected candidates are not reopened. Tests verify fixed task/code, prior evidence,
new worker dispatch, and refusal of out-of-scope or unsupported corrections.
The clean checkout passed 929 tests (13 skipped). Source 8's full construction
response, usage and worker record are retained under `audits/rewrite/source8-build-outcome/`.
It completed in 258.5 seconds, with 44,068 input-plus-output tokens and zero tool
messages; this was another successful write-only task, not a qualified dataset.

Recovery/capability evidence commit `8d3d4d3` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42494677743).

### Development token policy clarified (15:45 UTC)

Eduardo explicitly stated that the 40,000,000-token weekly limit is for normal
operation only and must not constrain development. The earlier headroom figures
remain measurements, but are not development stop conditions. Scout was notified.
The budget gate now supports the authorized exemption through this timebox's
19:07 UTC deadline; the normal 40M configuration is preserved. Usage accounting,
per-task bounds and other configured limits remain active. A test verifies that
45M measured tokens do not block development and that enforcement resumes at the
exact expiry. This is an operator policy change, not a model-approved exception.

Terms-repair commit `23f80a5` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42495677919).

### Development exemption deployed (15:54 UTC)

Commit `d29c11a7b90c178e86056c7acc278765a343267b` passed 930 tests (13 skipped)
in a clean checkout and [exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42496565927).
Scout confirmed deployment at 15:54:23 UTC with the exemption configuration
present, then resumed the scheduled controller. The deployment waits on actual
processes and an exclusive lock probe; an old scheduler running flag is not used
as evidence of an active task. Scout's deployment record is retained in `audits/rewrite/dev-exemption-deploy/note.md`.

Source 9's first construction attempt hit the 330-second outer timeout during
model generation. No worker ran. Scout corrected its earlier suggestion that
build-2 represented a terms repair: it is an ordinary construction retry. The
partial usage contains only title generation and does not establish the main
call's token usage. Awaiting the retry outcome; no candidate state was reset.

### Construction syntax repair preserves the paid proposal (15:57 UTC)

Source 9 build-2 generated a 17,889-byte builder in 317.7 seconds, but Python
parsing failed. The model response was retained on disk; the retry prompt did not
include it because construction validation failed before candidate state accepted
the proposal. The retry now reads that exact cached response and includes the
parser line, column and error. It remains repair input only; validation must pass
before any worker launches. This fixes a demonstrated loss of repair context,
without adding attempts or changing task definitions.

Source 10 is `nlrb-union-representation-election-wins`. Its first worker failed
at 32.6 seconds because the supplied terms URL returned HTTP 404. The exact
manifest and digest-verified failure are retained under `new-source-outcomes/`
(staging release 438348862, manifest asset 724415808). This is now eligible for
the existing automatic terms-evidence repair. No artifact has been accepted.

### Hosted output redaction damaged source code (16:12 UTC)

The source 9 export is now retained under `audits/rewrite/source9-parse-failure/`.
It is an EPA drinking-water violation task. The exact parser error is line 166,
column 63: an unterminated diagnostic string containing `PWS_TYPE_CODE=***`.
Scout compared the stored assistant message with captured stdout: both contain
the same damage. The installed runtime redacts assistant content before storage,
and its redactor reproduces the false positive on this public field name.
The original pre-redaction response is unavailable. This corrects the earlier
attribution of that syntax error solely to model-generated invalid Python.

The construction prompt now asks for separate public field/value properties and
descriptive diagnostic messages instead of apparent assignments in strings.
Actual source field references and filtering rules stay fixed. The runtime's
secret redaction remains enabled and unchanged. This is a narrow response-format
workaround for an observed integration defect, not a relaxed artifact check.
Live successful repair is still required. Scout's diagnosis is retained in
`audits/rewrite/redaction-false-positive/note.md`; its broader cautions are not
proof that every field containing a secret-like substring is redacted.

Scout confirmed `1f04213` deployed at 16:02:44 UTC. Its clean checkout passed
931 tests (13 skipped), and [CI passed](https://github.com/earino/dataset-factory/actions/runs/42497468603).
The source-9 export and redaction diagnosis passed CI
([source evidence](https://github.com/earino/dataset-factory/actions/runs/42497896732),
[diagnosis](https://github.com/earino/dataset-factory/actions/runs/42498439282)).

### Keep complete negative judgments without repeated research (16:20 UTC)

The first live NLRB terms repair returned a structured `defer` verdict explaining
that it could not establish applicable readable terms. Hermes exited 1 after the
session, so the adapter discarded the negative outcome and started another
research attempt. The next version retains a complete `defer` or `reject` with a
nonempty reason and measured requested-model usage on exit 1. Such an outcome can
only stop the candidate; `ready` and `accept` still require exit 0. Malformed
responses and missing reasons remain task failures. Existing task bounds apply.
Tests exercise negative retention and refusal of positive or incomplete results.
This change removes an observed repeated search; it does not establish that the
NLRB data lack redistribution rights or that the source is scientifically unsuitable.

The diagnostic-wording change `e129c9a` passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42498708037).

### Source-rights clarification and RCRA outcome (16:28 UTC)

The research prompts now distinguish a publisher licence grant from an applicable
statutory public-domain basis. The latter needs evidence that it covers the actual
records, with third-party rights and territorial scope preserved. A government
website is not sufficient evidence. This corrects the overly narrow interpretation
seen in the NLRB terms repair; it does not approve or reopen that candidate.
The [US Copyright Office law reference](https://www.copyright.gov/title17/index.html)
and [USAGov guidance](https://www.usa.gov/government-copyright) support this distinction
and its limits. Captured source evidence and final semantic review remain required.
The change adds no licence framework, exception flag or new acceptance gate.

Source 11, `rcra-cei-violation-finding`, captured its terms successfully but failed
construction after 41.8 seconds: the observed FOUND_VIOLATION domain included R,
which the generated code's expected domain omitted. No meaning for R is inferred
here. The ordinary bounded repair receives that failure; no candidate state or
label rule was edited manually. Exact manifest, failure and licence-capture bytes
are preserved under `audits/rewrite/new-source-outcomes/rcra-build-1-*`, with both
report digests verified against staging manifest asset 724479061 (release 438363329).

The e129c9a deployment at 16:19:12 UTC and its queue snapshot are preserved under
`audits/rewrite/e129c9a-deploy/`; the export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42499362741).
Negative-verdict retention commit 1b951b6 passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42499423893) and 931 clean
checkout tests (13 skipped); deployment has been requested. Source 9 exhausted
its bounded attempts and is deferred; source 10 is rejected after terms research.
No replacement dataset has yet completed qualification and publication.

### Give a bounded model response time to finish

The task wall-clock limit is now 600 seconds (630 including the adapter's existing
shutdown margin), within the configured 90-minute session maximum. This replaces
the initially chosen 300-second limit after source 8 discovery and two source 9
construction attempts hit the 330-second outer timeout. Successful construction
calls took roughly 247–318 seconds. The change addresses measured truncation and
repeated work; it does not add attempts, turns, tools or acceptance exceptions.
Its effect on successful live completion remains to be observed.

Scout confirmed in Telegram that 1b951b6 deployed at 16:27:52 UTC and the tick resumed.
Commit 64a1113 passed [CI](https://github.com/earino/dataset-factory/actions/runs/42500214846);
its next-boundary deployment is requested, not yet confirmed.

Source-rights clarification e2544e8 passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42500043837).

### Scope construction checks to the frozen task (16:33 UTC)

Inspection of the digest-verified RCRA source bundle shows the frozen population
explicitly requires FOUND_VIOLATION in Y/N. The generated builder nevertheless
asserted that the entire raw evaluation table contained only Y/U/N/blank before
applying that population filter (build.py lines 116–117). The observed R therefore
stopped construction even though it cannot enter the specified task.

The construction prompt now distinguishes checks on included records and their
transformations from an unnecessary exhaustive domain assertion on excluded data.
Explicitly excluded codes are counted, not silently recoded or made negative.
Unexpected values affecting included records still require evidence or failure.
The task, population, target and artifact gate remain fixed. No live candidate
proposal or state was edited. This corrects an observed generated constraint.

### RCRA repair advances to actual-header failure (16:35 UTC)

The ordinary second RCRA worker completed its earlier outcome-domain check and
failed after 42.0 seconds at a missing source column. Its error lists the actual
headers, including OPERATING_TSDF and FULL_ENFORCEMENT, while the builder expected
OPERATING_TSDF_CODES (and listed FULL_ENFORCEMENT_CODES as another required field).
The exact staging manifest 724514248 and digest-verified failure from release
438370585 are retained as `new-source-outcomes/rcra-build-2-*`. No qualification
or metric was produced. The ordinary repair receives these actual headers.

Prompt correction e2441df passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42500521034).
Scout was asked to include it at the pending deployment boundary, or the next
needed boundary if the preceding deployment had already resumed, avoiding a
separate pause solely for this prompt change.
Scout confirmed at 16:37 UTC that 64a1113 had merged with task_seconds=600;
applying e2441df and resuming the tick were in progress at that observation.

### Parse complete fenced JSON without repeating research (16:44 UTC)

Source 12's retained discovery response is complete JSON inside a bare Markdown
code fence. The parser accepted only fences labelled json, so it rejected this
response at line 1, column 1. Removing the wrapper makes the exact retained bytes
pass both JSON parsing and the existing source contract. This is a format correction,
not evidence that the dataset is scientifically qualified or ready to publish.

The parser now accepts one complete bare or JSON-labelled outer code block, with
normal line endings. It still rejects missing closing fences, trailing prose,
multiple objects/blocks, malformed JSON and non-object responses. A regression
check uses the actual CMS response, alongside malformed-wrapper cases.

The failed fenced attempt recorded 11 API calls, 149,751 input and 28,609 output
tokens over 304.4 seconds. Scout reports that discover-3 repeated research and
advanced with an unfenced response; those duplicate-attempt costs are not measured
by this usage file. The supplied queue snapshot still shows the earlier discover
failure, so its bytes alone do not prove that later advancement. Evidence is kept
in `audits/rewrite/source12-discover2-nonjson/`; no live task was rerun manually.
The source is CMS nursing-home inspections, materially different from EPA RCRA.

The preceding RCRA evidence commit e520032 passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42500974752).

### Correct event timing applicability and date comparison (16:54 UTC)

RCRA build-3 reached the full artifact gate after 85.6 seconds. The exact report
fails three checks: feature availability lag, selection period, and rows within
split windows. Its manifest, quality descriptor, failure and qualification report
are retained as `audits/rewrite/new-source-outcomes/rcra-build-3-*`, with report
bytes verified against staging manifest 724549181 (release 438377548). No scores
or base rates from this failed artifact are accepted findings.

The window failure compares a date string with midnight on the same date as if
the date were earlier. Gate 1.6.1 parses ISO month/date/timestamp values and compares
actual times in linear time. Equal starts pass, equal exclusive ends fail; invalid
or incompatible timestamps fail. Regression tests also cover timezone-equivalent
instants and overlapping actual ranges.

The other two findings expose the periodic descriptor being applied to inspection
records. The existing PREDICTION-CONTRACT already permits retrospective research
with explicit timing assumptions; it does not require invented publication dates.
Gate 1.6.1 adds an explicitly unverified event-time result for administrative
records with current/mixed vintage, non-periodic instants, retrospective scope,
unverified training-label timing and stated limitations. It records the event
selection rule without claiming prediction-time eligibility. Known late features,
statistical-release observations, explicit future-period selection, historical
forecasting evidence and every leakage check retain their requirements.
The builder prompt explains the existing administrative-record source type and
null unknown lags. The unchanged RCRA descriptor still lacks that type and is not
accepted by the patch. No live proposal or candidate state was edited; new full-row
qualification and semantic review remain necessary.

New qualification/claim receipts require version 1.6.1. Historical 1.6.0 reports
remain usable as historical evidence only. The gate selftest passes: broken fixtures
still fail their expected checks and the corrected fixture passes. Focused date and
timing regressions pass; the full working-checkout suite passed 933 tests (13 skipped)
before the final timezone regression addition. The final clean checkout also passed
933 tests (13 skipped), including the timezone and historical-receipt regressions.
Runtime inventory, rule inventory, 22 suitability reviews and historical approval
checks passed. No passing real-artifact receipt is inferred from these tests.

Parser fix d80511b passed [CI](https://github.com/earino/dataset-factory/actions/runs/42501504485)
and 931 clean-checkout tests (13 skipped). Scout's source-12 evidence export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42501241367).

### Tested gate batch and CMS terms access failure (16:57 UTC)

Batch 08b28f5 passed [CI](https://github.com/earino/dataset-factory/actions/runs/42502349062)
and has been sent to Scout for deployment at an actual free process/flock boundary.
Deployment is not yet confirmed. It includes parser d80511b and qualification 1.6.1.

CMS `nursing-home-next-survey-harm-citation` reached worker build-1, which failed
at 32.5 seconds because its terms URL returned HTTP 403. Staging release 438383146,
manifest 724574499 and the digest-verified failure are preserved as
`new-source-outcomes/cms-build-1-*`. This is a source access/evidence failure,
not a finding that the data are scientifically unsuitable or unredistributable.
The existing bounded terms-repair path should handle it; no manual retry, approval
or candidate edit was requested. Next: confirm deployment, observe this normal
repair and the next discovery, then inspect the first successful full qualification
and public two-platform consumer results. Zero replacement publications so far.

### Keep development tokens separate after the exemption expires

The first exemption stopped enforcing the token ceiling during development, but
would have charged the same development tokens to normal operation after 19:07.
That conflicts with the operator's clarification that the 40M limit is only for
normal operation. The authorized development window is now explicit: sessions
started from kickoff 11:07 UTC through (but not including) 19:07 UTC are excluded
from the normal weekly token calculation. Their full measured usage remains in
reports and monthly cost accounting. New sessions at the deadline are normal
operation. Existing worker, priced-cost, session and per-task limits are unchanged.
This does not classify earlier remediation sessions by guessed titles.

A ledger regression verifies that 45M recorded development tokens remain visible
and do not block normal operation after expiry, while a new 40M normal-operation
session at the deadline does trigger the normal ceiling. All 31 budget tests pass.

### Six-hour checkpoint and deployed gate (17:11 UTC)

The six-hour user update reported zero completed replacement publications and
uncertain completion within the remaining two hours. Acceptance criteria remain
unchanged. Work remains focused on actual source outcomes and their demonstrated
failures.

Scout confirms 08b28f5 deployed at 17:02:53 UTC, with the scheduled tick resumed
at 17:03 and runtime inventory passing. At 17:03:12, RCRA source-11 was deferred
after its third worker failure; no manual reopening occurred. CMS source-12 was
entering normal terms repair after the captured 403. Source-13 has identity
`rw-2ce60e8ae8f7`; its exact research outcome is not yet retained here. Scout's
message describes both a build-stage queue and a just-started discovery process,
so it is not evidence of completed construction. Provider count was zero at that
snapshot, with the CMS ledger mid-transition. Reserved worker budget was EUR
10.30 of 20.00. These are timestamped observations, not current-state guarantees.

Development accounting commit 999e076 passed 934 tests in a clean checkout
(13 skipped) and [exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42503361418).
Deployment was requested at the next free process/flock boundary. Its deployment
and subsequent source outcomes remain to be confirmed.

### UCMR 5 first construction and useful repair diagnostics (17:15 UTC)

Source-13 is `ucmr5-first-sample-pfas`. Its first worker completed in 36.0 seconds
and failed on missing additional-data concepts or join keys. Terms capture passed.
Staging release 438394116 and manifest 724624851 bind the preserved failure and
licence-evidence reports in `audits/rewrite/new-source-outcomes/ucmr5-build-1-*`.
Report sizes and SHA256 digests were verified against that manifest. The source
archive was inspected in memory without retrieving the dataset.

The builder recorded missing-name details in a local check list, but raised only
a generic exception before returning that list. Consequently, automatic repair
receives neither the missing names nor the actual headers. The construction prompt
now requires bounded observed headers, missing names and the selected archive
member in schema-failure messages. No source mapping, target, candidate state or
acceptance check was changed. The normal bounded repair remains responsible for
resolving the actual schema from evidence.

### Development exemption and schema prompt deployed (17:19 UTC)

Scout exported [the deployment and queue record](../audits/rewrite/c1a072a-deploy/note.md):
999e076 went live at 17:13:05 UTC, then c1a072a at 17:17:34 UTC, each at a free
controller boundary with cleanup retained. The latter commit passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42504050660) and 17
focused engine/model tests. Scout's evidence commit 66e2378 also passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42504276920).

The UCMR5 first worker was reconciled and deleted after its failed result was
preserved. CMS remained at build, temporarily waiting on the existing active-job
admission rule. The exported queue is a snapshot, not a claim that its next repair
has completed. The prompt change instructs future builders to expose schema
details; it does not retroactively add absent headers to the first failure.
No replacement publication has yet been observed.

### Preserve missing-history rows in the reference baseline

Inspection of UCMR5's digest-verified construction proposal found that its selected
`prior_ucmr3_max_pfoa_pfos` reference explicitly permits missing history. The
evaluator previously passed missing predictions to metrics that reject them,
and rejected constant training ranges outright. This defect was found from the
actual proposal and evaluator code before a qualified UCMR artifact reached it;
it is not a claim that the current worker failed at evaluation. The small proposal
excerpt and its source-archive identity are retained with the other UCMR evidence.

The reference now uses the training-label prior for missing history or an absent/
constant training range. It retains every validation row, leaves source features
unchanged, and reports missing counts, fallback counts, training range and whether
that range was informative. Available values still use the existing training-only
min/max ranking; reverse direction does not reverse the fallback prior. Invalid
text and infinite values still fail. This changes a baseline's handling of absent
history, not source qualification, acceptance thresholds or dataset selection.
Three regressions cover missing observations, out-of-training-range values,
reverse direction, absent/constant training ranges and invalid inputs. All 11
rewrite-worker tests pass; runtime source inventory passes.
The full clean-checkout suite passes 937 tests (13 skipped).

CMS build-2 also completed at 17:25 UTC: the unchanged terms URL again returned
403 after 32.4 seconds. Its source proposal changed, while the builder hash stayed
the same, confirming reuse of the paid construction code. Release 438400893,
manifest 724655938 and digest-verified failure are retained as `cms-build-2-*`.
The terms-repair prompt now distinguishes worker access from reuse rights and
asks for an accessible official alternative after a 403/404. Changing the quote
on the same blocked URL cannot fix the observed access failure. No particular
replacement URL or legal conclusion is supplied by the controller.

### Baseline and access-repair corrections deployed (17:32 UTC)

Batch d357930 passed [CI](https://github.com/earino/dataset-factory/actions/runs/42505038554)
and its final clean checkout passed 937 tests (13 skipped). Scout confirms
deployment at 17:30:21 UTC; the [deployment record](../audits/rewrite/d357930-deploy/note.md)
was exported in fc059da, whose [CI](https://github.com/earino/dataset-factory/actions/runs/42505358404)
also passed. The earlier evidence-only commit 230d86f passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42504636657).

At the 17:30:37 snapshot, UCMR5 build-2's model response had failed JSON parsing
at line 1, column 42. Its build-3 model task was starting (Hermes child PID 25213).
CMS remained at build after its second terms access failure. Reserved worker
budget was EUR 10.62 of 20.00. The failed UCMR response has been requested for
inspection; the snapshot does not establish that the current task has finished.

### Reuse paid construction text after JSON syntax failures (17:36 UTC)

Scout exported the [UCMR5 build-2 response and usage](../audits/rewrite/ucmr5-build2-syntax/note.md)
in 45c92af, with passing [CI](https://github.com/earino/dataset-factory/actions/runs/42505574729).
The recorded call used 313.0 seconds, 17,546 input and 45,217 output tokens across
one main call plus title generation, with zero tool results. The retained response
is 45,848 bytes. Local parsing places its error at end-of-input, column 45,849,
not the earlier queue's column 42. Diagnostic inspection shows a missing object
closure: `references` and `construction_notes` remain inside `quality`. Its Python
code parses once the surrounding text is decoded. That is syntax evidence only;
the code and scientific interpretation have not passed artifact validation.

Previously, this malformed response was retained on disk but omitted from the
next construction attempt, which instead received the older valid proposal.
The driver now checkpoints the malformed text and asks the next ordinary bounded
write-only attempt to correct JSON syntax/nesting while preserving its code and
claims. It does not add attempts, accept malformed JSON, restart live work, or
bypass Python/descriptor/full-artifact/semantic checks. Context must fit the
existing 128 KiB limit. A format-task failure retains the paid draft; a parsed
proposal takes precedence when later Python/descriptor repair is needed.

The regression uses the retained response to verify exact text reuse, no worker
launch on a failed format call, retention across retries, successful proposal
validation before launch, and clearing of the text draft. It uses simulated model
output only to test this transport boundary, not to accept or edit the live source.
All 18 focused engine/model tests and the full clean-checkout suite of 938 tests
(13 skipped) pass. UCMR build-3 was left untouched.

UCMR subsequently launched worker attempt `rw-2ce60e8ae8f7-build-4` automatically.
It passed the previous header-resolution point but failed reading source rows:
UTF-8 decoding rejected byte `0xb5` at position 455. Runtime was 35.7 seconds,
with no OOM. Release 438407058, manifest 724686538 and its digest-verified failure
are preserved as `ucmr5-build-4-*`. This is an ordinary encoding repair for the
existing bounded path; no manual code or candidate edit was made. Attempt numbers
include model-only failures and do not equal the completed-worker failure count.

### Correct the initial repair allowance (17:44 UTC)

The three-failure cap was an implementation choice, not a user-imposed quality
requirement. RCRA exhausted it while advancing through two schema errors and then
qualification; UCMR5 has advanced from schema resolution to source decoding while
also paying for malformed model responses. Abandoning every such candidate after
three distinct integration failures forces fresh discovery and construction,
despite available worker allowance and remaining development time.

The replacement now permits five task failures and five completed-worker failures
per stage for active candidates, using the existing separate counters. This is a
configuration change, not a new recovery framework. Individual model tasks remain
bounded to 600 seconds, the EUR/resource limits and 19:07 deadline remain binding,
and all artifact and semantic checks remain required. It does not reopen terminal
sources or alter their recorded reasons. This deliberately revises the earlier
plan to keep the initial retry cap unchanged, based on observed progress through
different failures. It does not promise that more retries will produce acceptance.

### First successful full-artifact build: UCMR5 (17:53 UTC)

Scout confirmed 286a6fa live at 17:47:09 UTC, with the tick resumed at 17:48 and
max_attempts=5. The existing UCMR5 build-5 worker was preserved through rollout.
The commit passed [CI](https://github.com/earino/dataset-factory/actions/runs/42506462575)
and 26 focused controller/worker/engine tests. Its predecessor 05cd95e passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42505943473) and 938
clean-checkout tests (13 skipped).

UCMR5 build-5 succeeded in 161.0 seconds, exit 0, no OOM. Staging release 438414591
and manifest 724725535 bind the compact evidence in `new-source-outcomes/ucmr5-build-5-*`.
Qualification 1.6.1 reports 47 passing checks; all 21 source checks pass. The worker
ran exact-artifact acceptance before and after evaluation, then packaged the result.
Independently, the root checked all 33 package-asset digests/sizes against the staging
inventory, collected only compact metadata, and ran the production
`qualification_receipt.check(..., external_assets=True)` with no problems. The
[binding receipt](../audits/rewrite/new-source-outcomes/ucmr5-build-5-binding-verification.json)
records artifact `d80df819308eae1dd6e1dae2dbe88bc6a07568bf85af843efbb1e3a18a7b252e`
and package `v-4bf5b4de3232149b`.

Only after that exact-artifact check, the measured public-validation result is
reported: 3,769 rows, baseline model AUC 0.77976 and Brier 0.06850, versus training
prior AUC 0.5 and Brier 0.07663. This is retrospective research, not a holdout or
historical forecasting score. The calendar/identity reference fell back for every
validation row; the persistence reference used the training prior on 3,714 rows
with absent history. These limitations prevent treating those controls as strong
evidence of general headroom. Train/eval/holdout row counts are 3,874/3,769/2,430.
The subsequent semantic review found five advertised features empty and other
construction defects; these prototype measurements do not establish usefulness
of the intended full-feature dataset or authorize release.

Semantic review, successful-worker cleanup/advancement and public publication are
not yet confirmed. Scout received the verified result through `/btw`, explicitly
leaving these steps to the controller; no semantic approval or candidate edit was
issued. Two complete public datasets remain required.

### Correct semantic repair routing (18:05 UTC)

The [17:57 snapshot](../audits/rewrite/snapshot-1757/note.md) confirms automatic
collection/deletion of the successful UCMR worker at 17:51:16 and advancement to
evaluate. Source-14 discovery was live (PID 27623, 19 seconds at snapshot), CMS
had a repair worker, and reservations were EUR 11.10/20.00.

The [complete UCMR review](../audits/rewrite/ucmr5-evaluate-1/response.json) returns
**repair**, explicitly saying the source and label should not be rejected. It
confirms the label direction/units, then identifies four substantive defects:
five declared features were empty because long-format rows were parsed as column
names; two checks were hardcoded true; prior-history missingness contradicted its
description; and effective population exclusions were not clearly documented.
The initial truncated snapshot's apparent label/units rejection was misleading.
The measured review used 222.284 seconds, three main-model calls, two tool results,
and the requested model route. Its evidence export 204cfc6 passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42507709105).

Code inspection identifies the actual routing defect: `Driver.evaluate` returned
reject for every verdict other than accept, including repair. This was not failure
allowance exhaustion as Scout's export title inferred. The correction routes a
concrete repair verdict back to construction, retains the previous artifact/job
and findings, supplies those findings across subsequent build failures, and asks
the next review to check them. Successful qualification/evaluation and a new
semantic acceptance are still required. Five semantic repair verdicts exhaust
the bound; they cannot cycle indefinitely. A saved review is reused on restart
under its exact attempt identity instead of calling the model again.

A deterministic reconciliation corrects only the earlier misrouting class:
candidate rejected, last attempt evaluate/reject, stored verdict repair with
findings, and unchanged matching reason. It preserves the original attempt,
records the correction, and cannot reapply it. True rejections, independent later
decisions and deferred candidates are untouched. This is a specific bug correction,
not a per-dataset approval or a general reopening of terminal work. The construction
prompt also forbids literal-true checks and silently empty declared features.
Focused regressions cover the actual review, restart reuse, bounded reconstruction,
preserved history, true rejections and changed decisions; all 29 pass.

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

## Seven-hour update — 18:12 UTC

Reported to Eduardo: zero replacement publications, the first qualified prototype
needs substantive repair, and completing two public datasets within the remaining
time is unlikely. Work continues within the unchanged acceptance criteria. Scout
was asked to deploy `75137d7` at a free tick boundary and arrange the existing
scheduler/config cutoff for 19:07 UTC, preserving resumable state and cleanup.
The cutoff arrangement and deployment remain unconfirmed at this observation.

The semantic repair correction passed 941 tests (13 skipped) in a clean checkout
and [exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42508580209).
Scout's earlier snapshot export also passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42507566957).

CMS build-3 again failed before construction with HTTP 403 during terms capture
(32.5 seconds, exit 1, no OOM). Its compact failure bytes were checked against the
staging manifest before retention:
[cms-build-3-manifest.json](../audits/rewrite/new-source-outcomes/cms-build-3-manifest.json)
and [diagnostic](../audits/rewrite/new-source-outcomes/cms-build-3-failure.json).
This is source-access failure, not a measured dataset quality result.

### Deployment and cutoff confirmed — 18:16 UTC

Scout confirms `75137d7` deployed at 18:13:06 UTC. Its export passed
[exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42508913756).
[Deployment and cutoff record](../audits/rewrite/75137d7-deploy-cutoff/note.md).
The existing scheduler has a one-shot no-agent job `f0852e8c6392`, due at
19:07:00 UTC with catch-up, which sets local `pipeline_enabled=false`. This stops
new controller admissions, preserves saved attempts/results, permits admitted
work to finish, and leaves cleanup `e80975eddd4a` active. Its execution still needs
verification at the deadline. The normal token ceiling resumes for sessions
started after the development window; earlier development sessions remain measured
and excluded from normal-operation charging.

A compact post-deployment state export was requested to confirm automatic UCMR
repair routing and identify the current second-source path. No manual queue edit
or extra worker coordinator is used.

### Automatic semantic repair transition observed — 18:19 UTC

The [18:16 snapshot](../audits/rewrite/snapshot-1816/note.md) confirms UCMR5
returned to `build` through the deployed reconciliation, with prior attempts
preserved and fresh construction/review required. Build-6 had not started in that
snapshot. Source 14 selected `clinicaltrials-gov-early-termination` and reached
build after its second discovery attempt. These are state transitions, not accepted
datasets or complete end-to-end runs.

CMS build-4 subsequently staged a durable failure at 18:17:10 UTC, release
438429615: HTTP 403 in terms capture, 32.5 seconds, exit 1, no OOM. Its
[manifest](../audits/rewrite/new-source-outcomes/cms-build-4-manifest.json) and
[hash-verified diagnostic](../audits/rewrite/new-source-outcomes/cms-build-4-failure.json)
are retained. The snapshot's inference that provider absence meant a launch window
is not established; durable staging proves this attempt had already finished.
The normal controller must reconcile it; no manual queue change is warranted.

The snapshot export passed
[exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42509271447).
At 18:20:36 UTC Scout confirmed live ClinicalTrials construction
`rw-72e1332cd9b8-build-1`, `hermes_write_task.py` PID 30097, elapsed 210 seconds
within its six-turn/600-second bounds. Scout is observing that exact process with
a bounded read-only wait; no restart or added model-driven schedule was requested.
The earlier deployment/cutoff evidence commit `0d73a06` also passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42509141563).

### Both construction proposals completed — 18:29 UTC

ClinicalTrials build-1 completed at 18:21:42 UTC: write-only, zero tools,
259.7 seconds; requested DeepSeek route recorded one main call plus title generation.
The parsed builder is 27,233 bytes. Its [response and usage](../audits/rewrite/clinicaltrials-build1-outcome/)
passed export [CI](https://github.com/earino/dataset-factory/actions/runs/42509662901).
This proves a generated proposal, not successful dataset construction.

UCMR build-6 completed its semantic repair proposal at approximately 18:27 UTC:
231.6 seconds, zero tools, 35,134-byte parsed builder, previous review findings
retained. [Response and usage](../audits/rewrite/ucmr-build6-repair/). The proposal
pivots long-format additional-data elements, computes the formerly constant checks,
represents prior non-detects using source MRL values, and reports the effective
population/exclusions. These are proposed corrections, awaiting full worker checks
and fresh semantic review; they are not accepted scientific claims.

Scout confirms CMS build-4 was automatically collected at 18:22:03 and deleted
at 18:22:16 UTC. ClinicalTrials had no launch record at 18:27:15, after its
pre-launch wait on the older worker ledger. No manual queue changes or additional
model-driven follow-up schedule was used. The controller remains responsible for
worker admission and advancement.

### Repaired UCMR full worker result — 18:32 UTC

Build-6 succeeded on the real source: exit 0, no OOM, 54.5 seconds; staging release
438436154, manifest asset 724821692. Gate 1.6.1 passed with no failed checks.
All 33 package assets match staged sizes/hashes, and the exact-artifact receipt
passes against the staged inventory:
[binding verification](../audits/rewrite/new-source-outcomes/ucmr5-build-6-binding-verification.json).
Artifact `d3f9e077320eedadac890402e3ced0c52c4e9b47887a984eda87ca68648cbeaa`,
package `v-1590eda10ccee07a`. No CSV or source archive was downloaded locally.

The [source checks](../audits/rewrite/new-source-outcomes/ucmr5-build-6-source-checks.json)
now record nonempty coverage for every additional-data feature, independent label
recomputation, UCMR3 MRL/units and the 234 excluded first samples. The pipeline
performed construction, qualification, evaluation and packaging. Fresh semantic
review, automatic publication and anonymous consumers remain outstanding.
The requested-model repair export passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42510148595).
This is live evidence of repair execution, not acceptance of the resulting dataset.

### Finish ready work before new research — 18:37 UTC

UCMR reached evaluation after automatic collection/deletion at 18:30:02/18:30:13,
while another CMS terms-repair attempt ran and staged an HTTP 403 failure at
18:34:45 (this time fetching documentation, after terms capture succeeded).
[CMS build-5 manifest](../audits/rewrite/new-source-outcomes/cms-build-5-manifest.json)
and [verified diagnostic](../audits/rewrite/new-source-outcomes/cms-build-5-failure.json).
The fifth worker failure reaches the configured limit; no allowance increase is made.

Code inspection found that oldest-updated ordering could also start fresh discovery
ahead of ready publication. The scheduler now resumes admitted attempts first,
then prioritizes publication, semantic review, construction and discovery, retaining
oldest-first ordering within each stage and honoring retry delays. This implements
finish-first scheduling without another agent, approval or resource-policy change.
The focused pipeline/engine checks pass (23 tests), including waiting-work fairness,
active-attempt resumption and publishing before an older discovery candidate. Clean
checkout and exact-commit CI verification follow before deployment.

### Fresh review and description propagation correction — 18:50 UTC

The [second UCMR review](../audits/rewrite/ucmr-evaluate2-review/response.json)
confirmed the empty-feature defect fixed and requested further repair: independent
label validation, accurate prior-feature/population descriptions, and checks for
the stated negative selection conditions. The task completed in 356.4 seconds;
[export CI](https://github.com/earino/dataset-factory/actions/runs/42511620176) passed.
The deployed controller correctly returned it to build, preserving the findings.
Scout also confirms `7b77595` deployed at 18:43:22 UTC; its clean checkout passed
942 tests (13 skipped) and [CI](https://github.com/earino/dataset-factory/actions/runs/42510942948).

A real contract defect prevented descriptive repairs from reaching the release:
`quality.task.population` already described the excluded first samples, but review
and packaging continued to use discovery's original `source.task`. Construction
now carries corrected population/prediction-time/usefulness/reference text into
that source record, preserving the earlier task in attempt history. Existing feature
meanings can be corrected through `quality.feature_meanings`; availability text is
carried from the existing evaluation contract. The helper retains the original
question, target, feature identities, split policy and source access/terms. New
artifacts still require complete qualification and fresh review. This removes an
artificial inability to repair documentation; it is not a semantic approval.

ClinicalTrials did launch normally: release 438445539 appeared at 18:45:54 UTC.
Its first worker failed because the supplied terms quote was absent from the
captured document. The earlier 'stuck behind reconcile guard' inference is
superseded by that actual launch/result; no queue or ledger repair is needed.

### Existing descriptor format retained — 18:55 UTC

Build-7 also completed full construction/qualification/evaluation/packaging
(success, 61.0 seconds), staged at release 438449041. Its exact-artifact receipt
and all 33 package asset bindings pass:
[verification](../audits/rewrite/new-source-outcomes/ucmr5-build-7-binding-verification.json).
Inspection found that this real repair already writes corrected feature meanings
into `quality.task.features`. The propagation correction therefore uses that
existing named-feature descriptor list, not the extra `feature_meanings` mapping
proposed in the preceding entry. Unknown/new feature names are rejected; the
original feature identities and task target/splits remain unchanged. A test against
this actual build-7 descriptor proves its corrections reach the effective source.
This requires a fresh bundle/full checks/review; no staged artifact is changed.

ClinicalTrials build-1's [manifest](../audits/rewrite/new-source-outcomes/clinicaltrials-build-1-manifest.json)
and [hash-verified failure](../audits/rewrite/new-source-outcomes/clinicaltrials-build-1-failure.json)
are retained (35.2 seconds, supplied terms excerpt absent from captured document).
No successful ClinicalTrials artifact or replacement publication exists at this
observation. Scout has been asked to verify the 19:07 cutoff with a disabled tick,
active-worker/expiry inventory, cleanup status and concrete resume steps.

## Closeout preparation — 19:04 UTC

Implementation changes stopped before the deadline. Final implementation commit
`6ac5f833ce6a517db1ea15f56776b4f387aab8de` passed 944 tests (13 skipped) in a
clean checkout and [exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42512474404).
The preceding description propagation commit also passed
[CI](https://github.com/earino/dataset-factory/actions/runs/42512126554).
Final deployment/cutoff confirmation is being collected from Scout.

The objective remains incomplete. No two-source publication demonstration exists.
The remaining acceptance work is concrete:

1. Run a fresh UCMR repair bundle through the deployed description propagation,
   full qualification and semantic review. A passing build alone is insufficient;
   the previous review's material findings must be resolved in the actual release.
2. Repair ClinicalTrials' captured terms evidence, then demonstrate its full
   construction, qualification, evaluation and semantic review, or select another
   materially different real source if bounded repair cannot establish access/terms.
3. Complete automatic GitHub and Hugging Face publication for both accepted
   datasets and retain anonymous full-file consumer verification. Observe the
   successful unattended completion path, including any actual publishing repairs.
4. Recheck the full acceptance mapping and sign off only after those outcomes.

Estimated additional effort: **2–4 hours**, conditional on the current source
repairs converging. Source replacement or a first-live-publication integration
failure could require more. This is an estimate, not a new authorized timebox.
The main remaining uncertainty is end-to-end source/release reliability, not test
execution. No additional allowance or validation exception is assumed.

On authorized resumption, inspect the final cutoff snapshot and `factory status`,
keep Scout as the sole launcher, preserve stable attempts and existing staged
artifacts, and use the normal controller. Re-enable its local admission flag only
for the resumed work. Keep development accounting separate from normal-operation
limits; do not reopen genuinely rejected/deferred historical candidates merely to
fill the demonstration. The existing automatic repair and source-refill paths
remain responsible for progress.

## Final cutoff and handoff — 19:08 UTC; recorded after the deadline

Scout's [final snapshot](../audits/rewrite/final-cutoff-snapshot/note.md) confirms
`pipeline_enabled=false`, a waiting tick with no new admissions, no live model or
tick processes, and a reconciled ledger with zero servers and primary IPs. The
scheduled cutoff fired idempotently at 19:07 after the manual 19:06:21 cutoff.
Already-running model tasks finished; their results remain in `.factory/model-tasks/`.
No replacement release was published. No additional implementation was started.

**Resume correction:** the initial Scout snapshot incorrectly prescribed legacy
R1–R4 operator approval as a prerequisite. `factory/admission.py:require` already
supersedes that hold for recorded running replacement build/publish attempts while
`pipeline.enabled(root)` is true. Build-8 saw the legacy hold because the cutoff
had disabled the pipeline. That is a shutdown observation, not a new human gate.
Scout corrected the handoff in `dd737f9` without restarting work. On authorized
resumption, inspect saved attempt results and re-enable the replacement flag;
do not add per-dataset approval or reopen unrelated historical remediation work.

The final source inventory changes the earlier second-source plan: ClinicalTrials
is now rejected, so inspect its preserved reason and use ordinary discovery/refill
for another materially different source; do not silently reset its state. Source
15 is queued for discovery and was not admitted. UCMR needs a newly constructed,
fully checked package with corrected descriptions; build-7 must not be published
as-is. The outstanding work remains UCMR acceptance, a second complete source,
two automatic dual-platform releases, and anonymous consumer verification.

Estimated additional effort remains **2–4 hours**, with low confidence until a
second source passes construction and the first real publication succeeds. Further
source or publication defects can extend this estimate. No new timebox is assumed.
The objective is incomplete and work stops under the user's eight-hour instruction.

Final runtime evidence was exported by Scout in `1983f07` and corrected in
`dd737f9`. The original export passed [CI](https://github.com/earino/dataset-factory/actions/runs/42513596675);
the corrected export and this closeout commit receive exact-commit CI checks before
the final user report. Runtime code remains `6ac5f83`; these are evidence-only changes.

## New authorized implementation run — 2026-11-08 19:58:14 UTC

Eduardo submitted the revised goal with no new elapsed-time limit. Implementation
work resumes under `b83c19a`; the goal tool still reports the prior goal paused and
rejected replacement creation because it is unfinished. This tooling limitation
was reported; no false completion was recorded. Scout was asked to inspect/export
saved UCMR build-8 results before new calls or workers, and remains sole launcher.

Development accounting now supports a separately recorded open-ended window while
preserving the first closed window. Closing the new window retains its session
usage exclusion after normal operation resumes; the gap between windows remains
normal usage. This follows the operator's development exemption without inventing
a new deadline or raising worker allowances. Two ledger regressions cover resumed
usage/closure and invalid-window refusal; all 33 budget tests pass locally.
Runtime deployment and saved-result inspection remain pending at this entry.

## Saved UCMR build-8 executed — 2026-11-08 20:07 UTC

Resumed accounting commit `46c2794` passed 946 tests (13 skipped) in a clean
checkout and [exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42517889649).
Scout exported the intact paid construction in `19fbc5b`, whose
[CI passed](https://github.com/earino/dataset-factory/actions/runs/42518189664).
[Saved response and usage](../audits/rewrite/ucmr-build8-resumed-run/) show
27,082 input / 35,409 output tokens, two calls, zero tool results, 208.7 seconds;
that work finished during the prior run's wind-down and was reused, not regenerated.
The response passes construction validation; the deployed description function
propagates its corrected population and all feature meanings.

The resumed worker succeeded in 61.0 seconds, exit 0, no OOM. Staging release
438490129 / manifest asset 725056408 contains the new package
`v-93f486e9bff11b10`, artifact
`8b7b4f29f264cc9c3bb20b321927e48e0752f8cc097dd36a511f690eedda6e89`.
Full qualification 1.6.1 passed. The independently retrieved compact reports match
staging digests; all 33 package bindings and the exact-artifact receipt verify.
The manifest population now matches the saved corrected description.
[Binding report](../audits/rewrite/new-source-outcomes/ucmr5-build-8-binding-verification.json).
No local CSV download was used. This is construction/evaluation/packaging evidence,
not semantic acceptance or public-consumer verification. Those remain next.

## Repair scope and recipe propagation — 2026-11-08 20:20 UTC

[Resume state](../audits/rewrite/ucmr-build8-resumed-run/resume-state.md) confirms
`46c2794` deployed, worker collected at 20:10:04 and deleted at 20:10:17. UCMR
review started after collection; source-15 discovery used the worker wait and did
not displace a ready review. No scheduling defect was established or patched.
The earlier cutoff wording that source-15 was unadmitted was imprecise; retained
runtime evidence explains its actual progression.

[Review 4](../audits/rewrite/ucmr-evaluate4-review/response.json) affirms target,
units, population selection, exact event-key joins, splits and independent label
audit. It requests two repairs: the population claims missing dates were counted
when only nonempty unparseable dates were counted; initial access_recipe text
still describes the older three-key join. Neither finding establishes a bad
split/label. Correct the false reporting claim or measure the count, and correct
the recipe. Do not invent a new historical-date requirement.

A demonstrated interface gap prevented access_recipe corrections from propagating.
The repair response can now supply `source_access_recipe` (description only), with
its old text retained in history. Download URLs, rights and frozen task fields
remain separate. A repair can omit unchanged top-level construction fields; saved
code/references are reused, the merged proposal is checkpointed and fully validated.
If quality changes it remains a complete descriptor, avoiding a new patch language.
The format-repair path preserves partial fields instead of inventing missing code.
No semantic verdict is overridden and normal full-artifact checks still run.

Tests exercise a metadata-only repair of the actual build-8 response through the
driver to bundle assembly, unchanged builder/references, recipe propagation/history,
source URL preservation and invalid repair refusal. All 17 engine tests pass locally.
Scout paused the tick at a safe boundary at 20:19:51, retaining cleanup. UCMR
build-9 has not started; source-15's already-running construction is allowed to
finish and preserve its result. The tested correction will deploy before resuming.

## UCMR accepted; publication started — 2026-11-08 20:43 UTC

`fdaf39b` passed 948 tests (13 skipped) in a clean checkout and
[exact-commit CI](https://github.com/earino/dataset-factory/actions/runs/42519807541),
and Scout confirmed its deployment with the tick resumed at approximately 20:25.
Build-9 completed in 63.7 seconds, exit 0/no OOM, staging release 438502804 /
manifest asset 725114902. Its full gate 1.6.1 report passes, all 33 manifest assets
match staging and the exact-artifact receipt verifies. The package is
`v-4a630108a6e75a6b`, artifact
`1bf9c8af47a3cd62f65faa7f22efd3fd66ddc1f8ba0fbb0762b391cf6fb04a10`.
[Binding verification](../audits/rewrite/new-source-outcomes/ucmr5-build-9-binding-verification.json).

The new code counts blank collection dates (observed count zero) and the source
recipe now describes the exact event-key join. All three CSV hashes are unchanged
from build-8. New code/metadata/evidence were packaged and fully checked; frozen
old releases were not edited. The repair model used 132.5 seconds, two calls,
26,890 input and 26,824 output tokens, zero tools.

**Evidence correction:** Scout's build-9 export note says construction_notes was
omitted/inherited. The exported construction-response.json actually contains all
five fields, including new construction_notes describing these two repairs.
It also returns build_py and references. Therefore this run proves recipe-text
propagation, not omitted-field reuse in production. Omitted-field reuse is covered
by the real-proposal driver test only; do not infer a live efficiency result.

[Review 5](../audits/rewrite/ucmr-evaluate5-acceptance/response.json) accepted the
artifact with zero findings at 20:41:20 UTC (489.2 seconds, six calls, 69,977 input /
61,933 output tokens, four web results). Both prior findings were confirmed fixed;
retrospective timing, censoring and population limitations remain explicit.
The acceptance export [CI passed](https://github.com/earino/dataset-factory/actions/runs/42521441343),
as did the [repair/state export](https://github.com/earino/dataset-factory/actions/runs/42521539611).
The controller advanced UCMR to publish; publish-1 was provisioning at 20:42:39.
No public-consumer success is claimed yet.

Source-15 is National Bridge Inventory: prediction of a Fair-condition bridge
being rated Poor at its next routine inspection, a materially different domain.
Its paid response is retained for ordinary repair of a feature-description naming
failure. The exact proposal/failure is requested before deciding whether any code
change is justified. No candidate-state reset or new discovery campaign was made.

## First real publication failure — 2026-11-08 20:51 UTC

[Publish-1 manifest and note](../audits/rewrite/ucmr-publish1-failure/) retain the
199-second worker result. Private GitHub transfer and complete HF file verification
succeeded. The public-release step raised UploadError, but the helper suppressed
its stderr and the executor intentionally recorded only the error class. Root
could not establish the exact failing call from that report. GH was still private;
anonymous HF metadata read returned 401. The accepted dataset was not changed.

The current upstream HfApi source confirms the existing private=False/dataset call
signature; no unsupported API-change guess was used. A small helper receipt now
records the named operation, exception class and optional HTTP status. It does not
persist error messages, tracebacks, stderr or credentials. Publication stages also
distinguish HF visibility, GH visibility, GH release and final tag verification.
Two focused regressions cover structured failure capture and secret-message
exclusion; all three release-worker tests pass locally. Full clean-checkout and
CI verification are next. Scout paused new attempts at a safe boundary, preserving
cleanup and source-15's completed paid repair, so retries need not run blindly.

## Definite publication call defect found — 2026-11-08

Upstream `huggingface_hub` source defines create_tag(repo_id, *, tag, ...): tag
is keyword-only. HUB_CONTROL passed it positionally as create_tag(repo, tag, ...).
This is a concrete call defect, not evidence of a newly changed visibility API.
The call is now create_tag(repo, tag=tag, ...). The helper test uses that actual
keyword-only contract and exercises tag creation through public revision checks;
the old call raises TypeError against it. The original worker's exact exception
was discarded, so its recorded error class remains UploadError; do not rewrite
historical evidence as a captured TypeError. Both fixes deploy together so another
provider failure retains its safe operation/error/status details.
Primary source: https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/hf_api.py

## Bridge feature vocabulary and paid-proposal reuse — 2026-11-08

[Bridge build-1](../audits/rewrite/bridge-source15-build1/) and
[build-2](../audits/rewrite/bridge-source15-build2-repair/) expose a concrete
interface error: discovery names groups (component_ratings, age, ownership),
whereas construction names the twelve actual CSV feature columns. Both paid
proposals failed the literal-name rule before any worker measurement. The saved
build-2 descriptor fully describes its declared output columns; its target,
question and split policy are unchanged. This is not evidence of feature leakage
or score-driven selection. No benchmark number is quoted from this unqualified proposal.

Construction now accepts complete descriptions matching exactly the declared
physical features, updates the single current task description, and retains the
original group plan in task history. Review receives that plan plus construction
notes to judge source interpretation and input validity. Partial descriptive
corrections still refer to existing names; duplicate/undeclared/incomplete concrete
contracts still fail. The research plan is context, not an additional obligation
to implement every suggested input group.

A proposal rejected solely by the previous feature-description rule is reused
mechanically if full construction validation and current description validation
now pass. It proceeds through a new ordinary attempt and all worker/semantic gates;
no model call or candidate-state edit is needed. If it is still invalid, ordinary
bounded model repair remains available rather than another validation-only loop.
Tests exercise both real saved bridge responses, unchanged paid code, history,
original-plan review context, invalid descriptions and the fallback repair path.
All 19 engine tests pass locally. Full clean-checkout and CI checks follow.

## First complete public benchmark — 2026-11-08

[Publication receipt](../audits/rewrite/ucmr-publication-success/publication.json)
and [worker manifest](../audits/rewrite/ucmr-publication-success/manifest.json)
prove publish-3 succeeded in 143.4 seconds, exit 0. Both anonymous consumers
verified 33 files and loaded train=3,874 / eval=3,769 / holdout=2,430 rows under
`v-4a630108a6e75a6b`, artifact
`1bf9c8af47a3cd62f65faa7f22efd3fd66ddc1f8ba0fbb0762b391cf6fb04a10`.
The uploaded publication.json receipt was independently hash/size checked.
Root also fetched each platform's public tagged MANIFEST.json without credentials:
[anonymous checks](../audits/rewrite/ucmr-publication-success/anonymous-manifest-check.json).
Both equal the accepted manifest, SHA256
`8ab0f948b992f10527fad689bd14062efe0393b7a2475e6a81aeb12abf94da53`.

Publication retry preserved the same GitHub release 438509765 and all 35 remote
asset IDs across attempts 1, 2 and 3. The successful HF retry skipped all 35
already uploaded files: [recovery evidence](../audits/rewrite/ucmr-publication-success/recovery.json).
This is real automatic retry across a deployed bug fix, without a manual flip,
new construction, or model-driven publishing decision. The second failure came
from a pre-fix bundle already admitted before the pause; the next attempt used
the corrected keyword-only call. The tag-call fix passed 951 clean tests/13 skips
and [CI](https://github.com/earino/dataset-factory/actions/runs/42522742179);
the diagnostics commit also passed [CI](https://github.com/earino/dataset-factory/actions/runs/42522459505).

The bridge feature-contract correction now passes 953 tests (13 skipped) in a
clean checkout. A test proves its actual saved build-2 proposal advances to bundle
assembly without an LLM call, preserves question/target/splits, and supplies the
original research feature plan to semantic review. This is software evidence;
the second real worker/release remains outstanding. No overall sign-off yet.
