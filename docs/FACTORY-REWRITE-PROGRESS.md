# Factory rewrite progress

Specification: [FACTORY-REWRITE.md](FACTORY-REWRITE.md).
Goal tool confirmed **active** at kickoff 2026-11-08 11:07:00 UTC.
Checkpoint 15:07:00 UTC; deadline 19:07:00 UTC.

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

## Acceptance evidence — 2026-11-08 16:38 UTC

This is an interim assessment, not completion sign-off.

| Criterion | Observed evidence | Remaining |
| --- | --- | --- |
| A1: one durable controller | Scheduled tick, exclusive-lock busy result, durable attempt/job identities across deployments; [cutover](../audits/rewrite/cutover/) and [first cycle](../audits/rewrite/first-cycle/). | Confirm the successful path also resumes from its recorded checkpoints. No forced-process-kill claim. |
| A2: mechanical worker outcomes | Real failed workers were staged, collected and deleted without model follow-up; [worker reports](../audits/rewrite/new-source-outcomes/). | Observe a successful construction worker advancing automatically. |
| A3: bounded inexpensive model | Recorded requested route performed real discovery and generated builders; exact prompts, responses and usage retained. | Write-only construction verified in the first-write-only evidence; successful semantic review remains. |
| A4: two complete real sources | Multiple real sources attempted; STATS19 reached full qualification, which failed. | Two sources through public publication without manual state edits. Deployment replays alone do not establish this. |
| A5: trustworthy consumable releases | Full-artifact checks rejected defective artifacts; package/consumer implementation tested in software. | Accepted reproducible releases, measured usefulness, and anonymous full-file verification on both platforms. |
| A6: automatic recovery | Failed candidates defer/refill; durable staging recovered after provider absence; [controlled transient-fetch recovery](../audits/rewrite/live_fetch_recovery.py) exercised against a real publisher. | Complete successful recovery evidence alongside the end-to-end path; controlled injection is not an organic outage claim. |
| A7: unattended production | Scheduled script-only ticks observed; three legacy launch/follow-up schedules paused; independent cleanup retained. | Retain final deployed configuration and unattended successful outcome. |
| A8: shipped, checked, signed off | Implementation pushed through `e2441df`, exact-commit CI green; Scout confirms it deployed at 16:37:29 UTC, scheduler resumed at 16:38. Progress and raw evidence retained. | Final criterion-by-criterion sign-off after the missing real outcomes. |

## Current work

- **Latest confirmed deployment (16:38 UTC):** Scout reports `e2441df` deployed
  at 16:37:29 UTC and the scheduler resumed. This includes negative-verdict reuse,
  the source-rights clarification, 600-second task bound and population-scoped
  construction checks. Its [exact-commit CI passed](https://github.com/earino/dataset-factory/actions/runs/42500521034).
  Source 11 RCRA remains in ordinary build repair after the second worker's header
  failure; source 12 is retrying discovery after non-JSON output. Zero replacement
  datasets have passed the full publication path. Scout reports worker reservations
  of EUR 9.98/20.00 (81 reservations), leaving EUR 10.02. The development token
  exemption remains active until 19:07 UTC. Historical observations follow.
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
