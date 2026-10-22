# Research prompt improvement

Status: draft under evaluation; no deployment claimed.

Source review during the frozen `21b72994` follow-up identified a watcher ordering
hazard: a collected report can omit the asset whose only copy remains on the worker,
yet normal deletion is allowed. The follow-up brief now explicitly preserves and
verifies that source before normal teardown, confirms old-worker deletion before a
fresh launch, and leaves expiry unchanged. Failed preservation remains a truthful
blocked/loss report. This is a narrow watcher-only correction; the 52 existing calls
remain frozen. Sixteen targeted watcher calls, including a new retained-source
diagnostic, will verify the corrected bundle under the same cumulative checkpoints.
The completed follow-up also exposed a revised DeepSeek ownership answer that
defers lifecycle actions but proposes a ledger/bookkeeping write. It fails mutation
deferral despite no narrow listed unsafe flag. The watcher now explicitly forbids
that write under an active owner; its existing mutex guard also prevents invocation
there. Preserve the failed criterion and verify the final wording in the targeted run.

The completed `21b72994` development comparison scores baseline 32/46 versus revised
43/46 after excluding the two repair-role criteria (original: 32/48 versus 45/48).
Detailed grades retain the above ledger-write defect and other scientific/reporting
weaknesses that the coarse criteria miss. All 24 responses and exact requests are
preserved in `evals/research-prompts/results/development-21b72994-*`. Total usage is 838,699 all-inclusive
tokens: baseline 423,546, revised 415,153. Elapsed totals are 691.846s and 753.671s;
the revised DeepSeek calls are slower in this sample. Fourteen responses exceed
600 whitespace-delimited words. No dollar saving, causal speedup or improved real
dataset yield is inferred from these results.

Reserved cases are also complete: baseline 15/24 versus revised 24/24. Both baseline
routes explicitly rewrite the frozen manifest and move/delete/recreate its existing
tag; both revised routes preserve the release and repair the reader. These are
proposed decisions, not executed mutations. Revised answers still contain unsupported
reporting and chronology claims. The primary release-priority answer has a qualitative
preference for baseline's clearer preparation-only fallback. Token totals are 245,099
baseline versus 207,827 revised; elapsed totals 368.406s versus 265.954s, with revised
DeepSeek slower. Full responses, grades and limitations are preserved alongside the
development results. Adaptive diagnostics and the final watcher check continue.

## Original development comparison completed

The frozen `413244c` bundle and baseline each answered six cases on two recorded
routes (24 successful responses). Criterion-level reviews and responses are in
`evals/research-prompts/results/development-413244c-{grades,responses}.json`, with
the first pair retained in `pilot.json`. Original scores: baseline 34/48, revised
46/48. Excluding the two watcher repair-role criteria gives 34/46 versus 44/46;
that is the more relevant descriptive comparison. Improvements concentrate in
baseline interpretation and respecting an active coordinator's ownership. The
baseline DeepSeek ownership answer also marks the unresolved event handled.
Neither version executes tools in these cases. Common concurrency defects beyond
the narrow unsafe checklist are retained, not hidden by a zero listed-flag count.

Both arms still overstate sparse timing evidence, statistical conclusions or
unobserved completion in some responses, including several passing all four coarse
criteria. The next bundle addresses these findings; the original responses and
grades remain unchanged. Label-blinded second reviews were followed by author
context adjudication: historical incidents supplied in the operating bundle are
not fabrications merely because the case-only reviewer could not verify them.
Visible cases, single responses, correlated criteria and involved reviewers do not
establish statistical significance or higher real dataset yield.

The 24 responses used 835,103 all-inclusive tokens (449,526 input, 94,057 output,
291,520 cache reads, zero cache writes), including auxiliary calls; the earlier
pre-inference parser failure remains separately recorded with zero tokens. Across
these cases revised discovery/advancement used fewer tokens, while watcher calls
used 24.1–57.8% more. Overall totals were 430,804 baseline and 404,299 revised.
Elapsed totals were 864.069s and 676.032s, with individual regressions and differing
cache warmth; these are observations, not causal speed or dollar-cost estimates.
Dollar spend is unknown.

The next tested prompt revision is frozen at `21b72994bc6a6ccd568c9395147ee3e6416b0e4c`.
It passed clean-clone Python 3.13 verification (`588 tests in 6.710s`, `OK (skipped=6)`),
doctor, source inventory audit and both exact-commit CI runs. Scout's signed source
review found no blocker. The authorized 52-call follow-up tests development, reserved
and adaptive diagnostic cases through the same cumulative ledger. Deployment and
ordinary post-deployment research remain outstanding.

The change rewrites discovery and advancement briefs and versions the formerly
scheduler-only worker-watch brief. It aligns relevant discovery, qualification and
release guidance with the scientific contract and the deployed integrity guards.

## What changes in decisions

- Discovery prioritizes useful questions and discriminating probes, then records a
  verdict or precise uncertainty. A three-rejection quota is removed; regional focus,
  measured jurisdiction and duplicate avoidance remain.
- Advancement chooses one primary candidate, honors actionable release priority and
  follows construction → qualification/acceptance → baseline comparison → packaging.
  Safe handoffs replace contradictory demands to finish one step and never stop.
- Baseline guidance distinguishes no demonstrated headroom from proof that a task
  cannot support prediction. Retargeting does not guarantee difficulty. Holdout cannot
  choose labels, thresholds, features or splits. Full-artifact qualification, timing
  checks, gate version and runner remain unchanged.
- Release guidance preserves existing manifests and tags, including for document-only
  fixes. Stale instructions to delete/recreate tags contradicted deployed enforcement.
  Standing and profile publishing guidance are corrected together.
- New unresolved class C leads remain closed. Existing candidate-specific operator
  risk acceptances remain distinct from grants and cannot transfer to sibling sources.
  `NOASSERTION` and compilation/source scope remain explicit.
- The watcher records a job's outcome, permits one bounded same-artifact recovery and
  hands construction/scientific changes to advancement. A small wrapper
  reuses research's mutex and budget gate around collection and the entire follow-up.
  Empty/running/busy ticks start no model. Independent expiry cleanup remains active.

Instructions include representative decision examples, evidence/uncertainty/output
contracts and a close-out reserve. Current coverage comes from records rather than
hardcoded historical ratios. The discovery shim no longer re-injects the removed quota.
Invocation limits and a SHA-256 of the actual submitted brief enter the existing session
log; this is not a claim to capture private Hermes system context.

## Prompt surface and evidence

Active repository briefs: `docs/discovery-session-prompt.md`,
`docs/research-session-prompt.md`, `docs/worker-watch-prompt.md`. Standing instructions:
`AGENTS.md`, `PROJECT.md`, `docs/OPERATIONS.md`; live state/candidates are evidence.
Eager skill loading now follows the role: discovery loads discovery; advancement and
watcher load qualification/release. Custom briefs retain the former three-skill default.
Other project/profile skills remain available on demand. Scientific guidance is retained;
the change removes irrelevant methods from a role's initial context without rebuilding
Hermes's prompt assembler. Measure token effects rather than inferring cost savings.

Scout's installed-source findings and corrections:
- [Prompt assembly and runtime inventory](https://github.com/earino/dataset-factory/pull/10#issuecomment-6350802906)
- [Corrected actor attribution and captured watcher prompt](https://github.com/earino/dataset-factory/pull/10#issuecomment-6350828810)
- [Evaluation controls and watcher concurrency](https://github.com/earino/dataset-factory/pull/10#issuecomment-6351023044)
- [Verified isolation limitations](https://github.com/earino/dataset-factory/pull/10#issuecomment-6351177561)

The runtime also supplies identity, skills index, memory and conversation context.
Private memory/identity contents are not exported or rewritten. Title generation is
observed auxiliary work and is counted; other available auxiliary paths must not be
reported as observed without usage evidence. Automatic background-review/curator holds
remain in place. The completed checkpoint prompt is inactive and is not a deployment target.

The design uses clear task boundaries, relevant context and representative examples,
consistent with [Anthropic's context-engineering guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
That guidance motivates the design; it does not establish gains on Scout's models.
Installed Hermes source, rather than unverified CLI assumptions, determines evaluation
isolation. [Hermes toolset documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/)
is supplementary; installed behavior and limitations are recorded by Scout.

## Verification and evaluation

The predeclared protocol and scenarios live in `evals/research-prompts/`. Compare old
and revised bundles on the actual primary/fallback configuration, then observe deployed
runs. Keep scenario decisions, software regression tests and scientific dataset gates
separate. Preserve all measured responses, errors, usage and criterion-level grades.

One existing test assertion intentionally changes: `PromptFileTests` required the literal
old three-source quota while testing repository-relative prompt resolution. It now requires
the new quality-over-count instruction; its path-resolution setup and other assertions remain.
All other existing assertions and qualification code are preserved. New watcher tests exercise
real process contention and verify budget holds, silent idle ticks and failure propagation.

Deployment, exact test output, model results and live observations will be appended after
verification. No improved dataset yield, speed or cost is claimed from a prompt rewrite alone.

### Revision after the pilot and operational review

The first GLM pair tied on the original four criteria. The revised response made the
test suite conditional on spare minutes; close-out now explicitly gives required
checks priority over another probe and separates observed results from future actions.
Both responses risked over-interpreting sparse release-date evidence. Discovery and
qualification prose now require an auditable as-of policy, distinguish revised values
from historical availability, and prohibit moving the instant past the known outcome
just to satisfy a declaration. Gate code and minimum checks are unchanged.

Scout's operational review identified a potential autonomy regression in blanket
watcher repair deferral. The next bundle permits one diagnosed same-artifact recovery
under exclusive ownership, with a reachable source/digest, budget admission and linked
attempt history. Construction/scientific changes still go to advancement. Published
bytes/tags, visibility and cleanup rules remain intact. This is a response to a plausible
workflow cost, not a measured speed improvement. Original comparison requests remain
frozen at `413244c`; results for the next bundle must be identified separately.

The watcher rubric initially treated any repair launch as unsafe despite the old
brief permitting bounded repairs. The protocol amendment preserves original grades
and separates common integrity/ownership from role-policy compliance; no safety win
may be claimed solely from repair deferral. The revised recovery boundary will be
evaluated explicitly, including its failure/handoff conditions.

A read-only audit of the ordinary old-prompt World Bank build then found reference
scoring inside construction before the gate, an accuracy field assigned training
prevalence, and a calendar control that always backed off to identity on future years.
The next bundle therefore makes the entrypoint sequence explicit, includes the build
script in that inspection, and requires controls to match their claimed information
sets. Full-artifact acceptance stays on workers. Source evidence and intervention
limits are in `results/old-prompt-build-review.json` under the evaluation directory.
The ordinary run was preserved; any repair following these supplied findings is
assisted and cannot count as an unprompted prompt-quality gain.

The initial baseline-comparison responses also confused an inconclusive difference
with parity and treated a weak calendar reference as ruling out seasonality. Before
follow-up inference, the bundle now distinguishes observed gaps, paired uncertainty
and equivalence; references test their stated information set, not every possible
explanation. Prevalence shift is investigated rather than asserted to explain AUC.
This is a documented development-driven revision, not a held-out discovery. The
52-call follow-up uses its successor hash instead of the untested `286db01` bundle.

### Pre-inference review corrections

Scout independently checked the isolated checkout and installed Hermes interfaces.
The experiment runner was corrected before any model call: canonical total tokens
include input, output, cache reads and cache writes; a two-field sum disagrees with
Hermes's usage file. The experiment now charges all four fields, including auxiliary
usage, with a breakdown. The standing weekly gate's different two-field definition
was identified and presented to Eduardo for clarification before inference proceeds.
[Source evidence](https://github.com/earino/dataset-factory/pull/11#issuecomment-6351527845)
and [seven-day totals](https://github.com/earino/dataset-factory/pull/11#issuecomment-6351589324).
Cached-token totals do not establish dollar spend; pricing remains unknown.

A second source review identified that Hermes's convenience total omits auxiliary
cache. The first actual pilot invocation then exposed an interface error missed by
source review: `chat --oneshot` does not support `--usage-file` at any argument position.
The attempt exited at argument parsing, with no session or model call; its failure is
preserved and explicitly reconciled, not erased. The corrected helper uses supported
`chat` controls, exactly one new research session ID, all four database token counters
and recorded main-task routes. Exit status checks completion; the unavailable second
usage copy is no longer claimed. A newly introduced usage-file test was replaced by
session-identity and route tests because that API is not available on the bounded chat
path; this does not change any pre-project test assertion.
[Invocation evidence](https://github.com/earino/dataset-factory/pull/11#issuecomment-6352088534)
and [dispatch inspection](https://github.com/earino/dataset-factory/pull/11#issuecomment-6352113969).
The actual chat path also suppresses built-in memory and discovered context files
with `--ignore-rules`, unlike the top-level oneshot path inspected initially. Both
arms still share runtime identity/index context and embed their public instructions.
The source-reviewed main-task routes are `glm-5.3` / `lunaroute` and
`deepseek/deepseek-v4.1-flash-1017` / `nous`.
[Installed route/context/exit semantics](https://github.com/earino/dataset-factory/pull/11#issuecomment-6352157221).


A further scan found residual tag-movement advice and quota instructions in on-demand
profile references. Those are aligned with frozen package versions and evidence-based
decisions; the original captured bytes remain in history. Profile source hashes are
updated for explicit deployment review. These references are source-reviewed, not
silently included in the no-tool experiment's eager instruction bundle.


## Deployment plan (prepared; not executed)

After the comparison satisfies its predeclared criteria, merge the reviewed PR and
record the merge commit. Scout deploys at an idle boundary:

1. Capture the current checkout, relevant live file digests and supported scheduler
   readback privately. Preserve uncommitted research and any unexpected skill drift;
   do not overwrite it. Verify both automatic skill-writer holds remain effective.
2. Fast-forward the coordinator to the reviewed commit. Install only changed shim
   and profile files named by the reviewed inventory delta, checking each live
   preimage immediately before replacement. The new follow-up shim is an addition.
   Leave credentials, research records, accounting and published artifacts intact.
3. Through the installed supported scheduler interface, edit existing watcher job
   `98b45d983280` to script-only `scout_worker_followup.sh`. Preserve its ID, five-minute
   cadence and delivery destination. Confirm its old agent prompt is not invoked
   separately. Do not create a second watcher job. Independent expiry cleanup stays on.
4. Read back scheduler mode/entry and effective holds; run the live runtime audit,
   doctor and admission check. Record commit, brief/skill/shim digests and results.
   Observe discovery and advancement on their ordinary routes, and report whether
   a genuine watcher event was available. An idle tick is not event-handling proof.

If checks fail, hold the affected research/follow-up entry and preserve diagnostics;
independent expiry cleanup continues. Restore only the captured changed code/files
with digest checks and the captured scheduler definition through the supported
interface. Verify the restored identities and state before resuming. Do not roll
back research records, accounting, published artifacts or unrelated concurrent work.
A code revert alone does not restore the scheduler or external profile skills.


## Token authorization resolved (2026-10-22)

Eduardo explicitly authorized as many tokens as needed to complete evaluation,
revision, deployment and observed research. The pilot hold is lifted. The existing
production token definition and limits remain unchanged; the initial experiment
still uses its conservative 2M all-inclusive-token / 48-invocation checkpoints,
which may be extended with recorded reasons and cumulative usage when needed.
Missing/corrupt accounting still stops execution. Worker spending and scientific,
licensing and publication constraints are not relaxed by this token authorization.
