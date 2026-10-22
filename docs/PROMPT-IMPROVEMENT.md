# Research prompt improvement

Status: draft under evaluation; no deployment claimed.

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
- The watcher records a job's outcome and hands repairs to advancement. A small wrapper
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

A further scan found residual tag-movement advice and quota instructions in on-demand
profile references. Those are aligned with frozen package versions and evidence-based
decisions; the original captured bytes remain in history. Profile source hashes are
updated for explicit deployment review. These references are source-reviewed, not
silently included in the no-tool experiment's eager instruction bundle.
