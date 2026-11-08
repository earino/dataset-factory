# Autonomous Dataset Factory: revised implementation specification

Revised 2026-11-08 after the initial eight-hour run and the operator's clarification:
**the product is useful prediction benchmarks, with requirements sized to that
purpose.** A plain data export is not a substitute. This specification supersedes
conflicting legacy workflow requirements for the replacement. Historical releases,
checksums, evidence and tags remain intact.

**Status:** the implementation goal is paused after its timebox. This document
specifies the next changes; it does not claim they are implemented or restart
production. The deployed implementation is `6ac5f83`; the initial run produced
zero complete public replacement benchmarks. See [progress and evidence](FACTORY-REWRITE-PROGRESS.md).
The prior specification remains available in Git history at `a2a1baa`.

## Outcome and limits

An agent discovers interesting real-world sources and produces useful, trustworthy,
reproducible prediction benchmarks for ML and agentic evaluation, through public
publication without routine human intervention. Known procedures run in code.
LLMs handle source interpretation, task choice, source-specific construction and
material semantic questions. Initially use `deepseek-v4.1-flash:1017`; retain the
actual requested route, usage, failures and task results. Cheap tokens alone do
not establish a cheap or fast process.

Keep the small coordinator, one worker-launching owner (Scout), SQLite state,
existing worker isolation/cleanup, staging, and GitHub/Hugging Face publishers.
Bulk data and ML stay on workers. Reuse the existing binary-classification runner;
`../harness_benchmark` remains read-only. No new agent framework, scheduler,
benchmark protocol, dashboard, website project or general patch engine is needed.
The legacy remediation campaign is not a prerequisite for this replacement.

## What makes a release good enough

A release answers five practical questions. It does not claim universal safety,
perfect historical knowledge, optimal model performance or proof of novelty.

1. **What are we predicting, and why is it useful?** State the target, population,
   input features, prediction setting and outcome horizon. Establish that labels
   and transformations mean what the release says. Keep a concrete use case;
   novelty or an elaborate story is not an additional release gate.
2. **Is the test valid for that setting?** Use appropriate disjoint train,
   development and final-scoring splits. Keep holdout labels and answer scaffolds
   outside evaluated agents' inputs. Check actual leakage paths, including joins,
   duplicated entities/events and cross-row exposure when applicable. A timestamp
   or identifier is not automatically leakage; its role in the task matters.
3. **Does it work as a benchmark?** Run the existing runner on the exact artifact,
   retain a simple reference baseline and measured usefulness evidence. Report
   class balance, missingness and relevant coverage. No universal minimum row
   count, target AUC band or exhaustive model search. A degenerate task or an
   invalid score needs repair; an unremarkable score is not itself a defect.
4. **Can others use and reproduce it?** Preserve source references/rights,
   acquisition and construction code, dependencies, input identities, meaningful
   validation and limitations. Verify complete files, schema and hashes on the
   worker. Public consumers must load the declared bytes on both destinations.
5. **May we distribute it?** Establish readable, applicable source terms, preserve
   attribution and upstream restrictions, and use the documented standing policy.
   A government domain alone is not proof of permission. A network access failure
   is not proof of incompatible rights; use bounded access repair or defer it.

### Dates and claims

Dates are a means to validate a task, not a separate certification project. A
split-boundary error, use of an outcome recorded after prediction as an input, or
training on labels unavailable at a claimed historical cutoff is material. A
parser disagreement about equivalent dates is a software bug. Missing publication
lags in an administrative source do not justify inventing dates or rejecting a
clearly scoped retrospective task automatically.

For a historically faithful forecasting claim, establish input and label
availability for that claim, including source vintages. For a retrospective
prediction benchmark, state what timing is assumed or unknown and check the
actual declared setting. Do not call it verified real-time forecasting. Known
answer leakage remains a defect in either setting. Follow the distinction already
made in [PREDICTION-CONTRACT.md](PREDICTION-CONTRACT.md); do not require forecasting
proof for a benchmark that makes no forecasting claim.

### What blocks publication

Block on a concrete defect in the five questions above: unsupported distribution
rights, wrong labels or units, materially false feature/population descriptions,
known answer exposure, invalid splits/scores, unusable files or mismatched bytes.
Uncertainty blocks the claim that depends on it; a narrower honest claim is
permitted when the prediction task remains useful and valid. Disclosure cannot
make a known-invalid task valid.

Each blocking finding identifies the affected claim or artifact, supporting
evidence, and the needed correction. Cosmetic prose, hypothetical concerns with
no task-specific basis, checks on excluded records that cannot affect the task,
and demands to prove every possible property are not additional release gates.
Generated assertions that always return true are not evidence. A check should
measure its stated property, not merely repeat the builder's declaration.

Reviewers may discover new material defects during repair. They should check the
existing findings and changed assumptions first, reuse established evidence, and
avoid restarting broad source research or adding unrelated requirements. Retain
one bounded semantic review stage; do not add a reviewer cascade or human sign-off.

## Smaller tasks and one current benchmark description

The existing failure pattern was a large generated builder/descriptor followed by
large regenerations. The replacement should retain source-specific generated code,
but make a repair operate on the smallest affected component.

- **Research:** return source evidence, an interesting task and the specific
  assumptions needed to construct it. Reuse captured evidence. Resolve missing
  source facts with a focused research task rather than asking the constructor
  to browse again.
- **Construct:** generate the source-specific acquisition/transform/label logic
  and the semantic declarations that cannot be derived. Code already handles
  packaging, hashes, row counts, qualification execution, baselines and transfer;
  the model should not reimplement those procedures.
- **Repair:** supply the exact saved proposal, source evidence and concrete failure.
  Return only changed structured fields or the affected source file where practical.
  Reuse unchanged code and evidence. A full file is acceptable when it is the
  smallest reliable edit; no new patch language or general editing framework.
- **Review:** judge meaning and actual benchmark usefulness from source evidence,
  code and measured results. Return accept, material repair, or rejection with
  reasons. Deterministic checks do not need another model's approval.

One current task description supplies construction, review, manifest and public
documentation. Discovery's proposal and later revisions remain history, not
competing editable authorities. Use the existing candidate record and formats;
consolidate duplicated fields at their current boundaries before introducing a
new schema. Generate mechanically derivable descriptors from that record and
measured results. A corrected feature meaning must reach the release without
another model rewriting it. Task, target and split changes remain explicit and
versioned; do not tune benchmark selection to agent outcomes or holdout scores.

Keep dependency-aware reuse simple: retain the existing immutable input/artifact
identities. Changed data or transformation logic requires full-artifact checks
and updated measurements. A text-only correction does not require model code
regeneration or rerunning unrelated numeric work; verify the corrected meaning
against the existing data and bind the new package to its evidence. Never edit
frozen releases in place or apply a receipt to different bytes. Where the existing
implementation cannot yet establish safe reuse, rerun the required checks rather
than introducing a generic cache system.

## Controller and publication

Keep `discover -> build -> evaluate -> publish -> published`. The deterministic
controller owns admission, stable attempt/job identities, retries, collection,
cleanup, publication and restart reconciliation. SQLite owns operational state;
Git holds code and compact evidence. Notes are not executable state. The existing
script-only scheduler invokes `python3 -m factory run --once`; `factory status`
reads replacement state. `STATE.md` remains the historical workflow projection.

Resume admitted work first, then finish publication/review ahead of fresh builds
or discovery. A transient access or runtime fault retries or defers; it does not
become a claim that the dataset is scientifically unsuitable. Rejection/refill
remains automatic. Distinguish model startup/format failures from worker and
semantic failures, preserving previous responses so paid work is not discarded.
Bound retries within configured allowances; do not raise them to hide a loop.

Use the existing Hermes adapter and explicit write-only construction capability.
The current configuration is six construction turns, twelve research turns and a
ten-minute task bound, with configured five-failure limits. These are deployed
settings, not evidence that they are optimal. Measure before changing them. Keep
native time/turn accounting; no speculative runtime replacement.

Standing policy authorizes automatic publication in owned `earino` GitHub and
Hugging Face `factory-` repositories after acceptance. No per-dataset operator
approval. Never adopt an unrelated repository or publish known-defective artifacts.
Keep write credentials separate from inference credentials and generated code.
The existing publisher moves bulk accepted files on a worker, resumes each
platform safely, binds the version tag to the complete manifest, changes visibility
and verifies anonymous full-file consumption on both platforms. A staging upload
or a public repository alone is not completion. Websites remain outside scope.

## Next implementation sequence

**First: finish one real benchmark.** Start with UCMR's retained source and build-8
attempt; inspect its saved result before spending another model call. Trace only
its path through `factory/engine.py`, `factory/construction.py`, task prompts,
packaging and `factory/automatic_publication.py`. Correct description ownership
and the smallest demonstrated repair inefficiency on this path. Check worker-side
source access/schema early within existing execution where that avoids a costly
build; do not create a new preflight service or stage.

Publish a corrected UCMR version automatically to both destinations and verify it
as an anonymous consumer. Do not hand-edit candidate state, accept the known wrong
build-7 descriptions, or change validation to rescue UCMR. If a substantive source
problem exhausts bounded repair, record it and use another suitable candidate.
During this first implementation step, avoid expanding the discovery campaign;
this is a work priority, not a new permanent admission gate.

**Second: prove generality.** Use normal discovery for a materially different
source and complete the same path without source-specific orchestration or human
state changes. Repair shared components only where the second run demonstrates a
gap. ClinicalTrials' recorded rejection and historical failures remain evidence;
they are not silently reset to fill the demonstration.

**Third: verify unattended repetition and sign off.** Retain observed recovery and
cleanup evidence, verify restart/retry across the complete path and observe
scheduled operation with old launchers still disabled. Map A1–A8 to actual results.
No milestone requires routine human approval, and no further feature phase follows
once the acceptance criteria are met.

For both sources, record elapsed time by stage, model calls/input/output tokens,
worker time, retries and their causes using existing task/job records. Separate
implementation/deployment delays from normal operation and allow for overlapping
work. Report time and measured usage per completed benchmark, not test count or
an invented overhead percentage. Use these observations to judge the model route
and task sizing; do not invent a latency target without data or make telemetry a
new project.

Tests focus on the actual boundaries that failed: repair routing, saved-response
reuse, description propagation and publication restart/consumer contracts. Keep
existing relevant checks; remove or narrow a rule only with a concrete explanation
of why it does not test the stated task. No new validation campaign, blanket gate
bypass, or acceptance based on fixtures. Verify suite changes in a clean checkout
and inspect exact-commit CI after every push. Maintain the progress document as
work proceeds, separating implemented changes from observed release outcomes.

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

## Timebox, development accounting and present status

The initial run started 2026-11-08 at 11:07 UTC and ended at 19:07 UTC, with its
four-hour report at 15:07. It did not meet A4/A5. Admissions were disabled at
19:06:21, the scheduled cutoff confirmed that setting, and final inventory at
19:08:46 showed no live workers or pending collection. Cleanup remains available.
This documentation revision does not grant a new implementation timebox or resume
the goal. The earlier 2–4-hour completion estimate is not a reliable commitment;
the first public release remains unproven.

The 40,000,000-token ceiling applies to normal operation, not development. Keep
measuring development usage and exclude it from normal-operation accounting.
The deployed exemption currently records the initial 11:07–19:07 window; a resumed
development session needs its actual window recorded before admission, without
raising worker spending/resource limits. Do not classify development as normal
operation merely because the first timebox expired.

On resumption, Scout remains the sole launcher. Inspect saved results and enable
the replacement's local flag for the resumed work; the legacy R1–R4 human approval
hold is not a prerequisite. Preserve cleanup, stable attempts and historical
artifacts. Defer unrelated improvements. Completion means all A1–A8 have observed
evidence, including two real public prediction benchmarks, not code completion or
a simpler data-export substitute.
