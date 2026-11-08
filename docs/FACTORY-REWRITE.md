# Autonomous Dataset Factory rewrite

Authorized by the operator on 2026-11-08. This specification supersedes conflicting
legacy workflow requirements for the replacement. Historical findings, published
artifacts, checksums and tags remain preserved. It does not certify old packages.

## Outcome and scope

Discover interesting real sources and publish trustworthy, reproducible datasets
for ML and agentic benchmarking without routine human intervention. Deterministic
code owns procedures; bounded LLM tasks own research, interpretation, construction
code and unfamiliar repairs. Initially use the hosted route corresponding to
`deepseek-v4.1-flash:1017`, recording the actual configured route and observed usage.

Keep the current lightweight coordinator, Hetzner workers, staging storage,
GitHub and Hugging Face destinations. Reuse working cloud/transfer/cleanup code,
substantive validators, source research and construction scripts. Bulk data and
ML run on workers. The existing benchmark checkout remains read-only.
The first deployed path uses that runner's binary classification CSV contract;
new task formats are outside this implementation timebox.

Operator clarification at 15:45 UTC: the 40,000,000-token rolling limit applies
to normal operation, not development. The current development exemption expires
at the 19:07 UTC implementation deadline. Keep measuring usage. Bounded model
tasks, worker spending/resource limits and the elapsed-time budget still apply.

Exclude dashboard/website redesign, general-purpose agent frameworks, speculative
validators, new benchmark protocols, and the deferred chronological adapter.
The old remediation campaign is historical work, not a prerequisite for this
replacement. Demonstrated defects relevant to the new path must be fixed.

## Lifecycle and ownership

`discover -> build -> evaluate -> publish -> published`; substantive failures go
to bounded repair or rejection, transient failures to bounded retry. Budget/access
waits are resumable and explicit. One candidate's rejection cannot stall others.
Task failures and completed construction-worker failures each have the configured
three-failure allowance. A failed publisher-terms capture gets a bounded research
repair within that worker allowance. Only source terms/documentation fields and
their evidence may change; the builder, download URLs, task and splits stay fixed.
Preserve the previous proposal, then re-run the unchanged captured-document check
and all artifact checks. Unresolved terms are rejected. A model startup failure does not consume a worker repair;
attempt identities and all failure evidence remain durable. Resource and spending
limits still apply across both categories.
Construction has six model turns within the same five-minute task bound: live
runs showed that two turns could be exhausted on documentation reads before any
code response. Licence excerpts are matched against captured publisher bytes,
normalizing HTML spacing and honoring explicit omissions only when all verbatim
spans occur in order. Semantic applicability remains part of source review.
An exit-1 runtime wrap-up may supply usable construction code. Retain it only
when its JSON/AST/descriptor contract and measured requested-model route pass;
record the nonzero exit and still require every artifact check and semantic
review. This is proposal reuse, never publication acceptance. Nonzero research
or review calls remain failures.

A small SQLite store owns operational candidate/attempt/job/artifact state. Git
holds code, source evidence and compact exported results, not live transactional
coordination. Updates are atomic; interrupted operations are reconciled using
stable identities before retry. Notes never act as executable state.
`STATE.md` remains the legacy repository projection; replacement runtime state is
read with `factory status`, not inferred from the historical candidate queue.

`python3 -m factory run --once` performs eligible work through a deterministic
controller, invoked by the existing no-agent scheduler. `status` explains current
state and next work without starting a model. Normal worker completion, transfer
verification, cleanup, retries and publishing do not need LLM calls. Preserve the
independent expiry sweeper. Only Scout's deployed coordinator launches workers.

Model tasks receive stage-specific context and structured outputs:
- Discovery: source, access/terms evidence, useful question, target and timing.
- Build/repair: construction code plus tests against source examples and failure
  diagnostics. Execute generated code in the existing worker isolation.
- Semantic review: assess source interpretation, prediction-time assumptions,
  usefulness and concrete concerns; return findings, not ceremonial approvals.

Malformed or failed model results are bounded failures. Model prose cannot waive
checks, alter budgets, authorize itself, or substitute for measured results.
Use the existing supported Hermes runtime rather than inventing an agent runtime.
Research and semantic review use the supported web-reading toolset. Construction
and JSON-format repair are write-only, using the supplied evidence and exact
previous proposal. A small adapter calls the installed Hermes Python constructor
with an explicit empty tool list, because its CLI argument parser substitutes
default tools for empty input. It preserves native turn/time bounds and accounting;
it does not implement another agent runtime. Recorded tool execution in a write-only
task is a failure. An unknown toolset alias is never used. Live six-turn repairs
spent every turn on documentation reads without producing code; increasing that
limit did not fix the missing writing capacity.

## Dataset acceptance and standing publication policy

The operator authorizes automatic publication of new versions meeting this policy
within existing configured spending/resource limits and destination namespaces.
Per-dataset operator transcripts/approvals and operator-relayed audits are removed
from the replacement. Keep credentials separate from generated code and data.
New repositories use the existing `earino` GitHub and Hugging Face namespaces and
the reserved `factory-` prefix. Existing repositories without the replacement's
ownership/manifest identity are not adopted or made public.

Acceptance requires readable compatible source terms with attribution; a clear
prediction question and target; evidence for feature/label availability and stated
evaluation scope; valid, non-overlapping splits appropriate to that scope; full-row
qualification of the exact artifact; no demonstrated label reconstruction from
shipped features or answer scaffolds; reproducible construction; valid baselines
and evidence of task usefulness; and consumer loading of the accepted bytes.
Existing scientific checks are retained or consolidated, not bypassed to ship.
Unknown semantic concerns lead to repair/rejection, not universal safety claims.

Use one immutable artifact manifest and measured results to generate documentation,
dataset cards and both destination uploads. Source/build/validator identities are
recorded for reproducibility; unrelated code edits do not require renewed prose.
Never mutate frozen historical bytes/tags. New corrections get new versions.
GitHub and Hugging Face retries resume independently; publication is complete only
when anonymous consumers verify the declared files on both. Websites are outside
the critical path and outside this project's acceptance criteria.
One publication worker reuses the existing GitHub transfer and Hugging Face
publisher, then tags, changes visibility and performs anonymous full-file loading.
It receives only accepted, digest-bound assets. Version tags bind the entire
package inventory; the qualification digest separately identifies the scored data.

## Implementation and migration

1. Add authoritative state and controller; make worker completion mechanical.
2. Connect bounded model discovery/build/review and worker evaluation.
3. Connect generated packaging and automatic two-destination publication.
4. Run real sources end-to-end, exercise recovery, deploy and retire old schedulers.

Implement on an isolated branch. Scout owns hosted execution, reports current
capabilities/budgets and source opportunities; Codex owns implementation/integration.
Do not run old and new launchers concurrently. Preserve existing candidate records
as history; import only explicit eligible candidates, never silently approve old
blocked packages. Take a compact operational backup before cutover. If rollout
fails, stop new work while retaining cleanup and durable results.

Tests prioritize real producer/consumer contracts, state restart behavior and
source transformations. Small synthetic tests prove code behavior only. Live
acceptance uses actual data and actual providers. Verify suite changes in a clean
checkout and inspect CI for each pushed commit before reporting it complete.

## Acceptance criteria

| ID | Observable completion evidence |
| --- | --- |
| A1 | Deployed deterministic controller owns candidate/job state; restart resumes without duplicate jobs or lost outcomes. |
| A2 | Successful and failed workers are collected/cleaned and candidates advanced without an LLM bookkeeping call. |
| A3 | Recorded live use of the requested inexpensive model route successfully performs bounded research/build/review tasks; usage and failures retained. |
| A4 | At least two materially different real sources traverse discovery, construction, full-artifact evaluation and automatic publication without manual state edits or per-dataset approvals. |
| A5 | Each accepted dataset has reproducible source/build information, substantive validation, baseline/usefulness evidence, and anonymous consumer verification on GitHub and Hugging Face. |
| A6 | Routine interruption, transient fetch failure and candidate rejection recover or defer automatically without corrupting state or blocking unrelated candidates. |
| A7 | An unattended scheduled run is observed; old research/follow-up production launch paths are disabled; independent cleanup remains active. |
| A8 | Changes pushed, exact-commit CI passes, progress record links evidence and limitations for every criterion. |

## Timebox and scope control

Kickoff: **2026-11-08 11:07:00 UTC**. Four-hour report: **15:07:00 UTC**.
Eight-hour deadline: **19:07:00 UTC**. Report at four hours and continue without
waiting. At deadline, safely wind down, retain resumable state and report unmet
criteria and estimated effort; do not claim completion or weaken checks.
Existing worker and inference allowances remain binding independently of elapsed time.

Every change must serve A1-A8 or fix a demonstrated defect on that path. Defer other
ideas in the progress record. Record justified design changes here explicitly.
Completion is an evidence-based Codex sign-off, not an additional human gate.
