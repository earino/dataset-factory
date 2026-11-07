# Autonomous adversarial audit

The internal audit follows packaging and verified private staging on both platforms.
It supplements the deterministic construction gate and the operator-relayed independent
audit. It does not authorize publication. Exact demonstrated recovery remains a hard
block; scope restrictions, disclosure and an approval cannot waive it.

`python3 -m factory audit` owns the following sequence. On hosted Scout use
`sh scripts/scout-factory audit ...` to supply existing credential-file paths.
No new credential, model route, allowance, scheduler or worker coordinator is created.

1. `audit prepare <dataset>` checks current qualification, claims, licensing, package
   integrity and suitability, then reports the immutable input binding and prompt size.
   Preparation is read-only. A failed prerequisite stops before model spend.
2. `audit model <dataset>` starts one fresh bounded Hermes session. It uses the existing
   research budget gate, OS admission lock, session marker, `oneshot` usage accounting,
   process-group deadline and configured model route. The remediation hold applies.
   Its turn limit is at most two and wall-clock limit at most ten minutes, additionally
   capped by the existing session settings. Token limits retain their existing advisory
   semantics; this does not claim a new provider-side token ceiling.
3. `audit worker-plan <model-directory>` validates the actual session receipt and prepares
   a candidate-local `bundle.json` and `job.json`. A blocking/incomplete model verdict
   stops here. Use the printed standard assembler, worker plan and launch commands.
   The source pin, monthly allowance, release reserve, one-worker rule and expiry rules
   remain the existing launcher's responsibility. Preparation never launches a worker.
4. Collect and destroy that worker through the ordinary worker commands, prove provider
   absence and commit its ledger. Then `audit accept <candidate-audit-directory> <job-id>`
   uses the mechanical bookkeeping path for live staging/provider checks, collects only
   the pinned compact audit reports, and validates the complete evidence chain. A pass
   writes `verdict.json` and the candidate's `autonomous_audit` pointer, then sets
   `awaiting_operator`. A refusal records `last_autonomous_audit` and leaves the flag false.
5. `audit check <dataset> <candidate-audit-directory>` rechecks the local evidence chain.
   Obtain the operator-relayed independent review and explicit publication approval next.
   A passing internal model response is never that independent review or an approval.

Model attempt files live under `.factory/autonomous/<binding>/model`; the reviewed
session evidence is copied into the candidate's audit directory when a worker is prepared.
Attempts are exclusive, not overwritten: a failed or interrupted attempt remains visible.
Reconcile it before choosing a new attempt; do not run a recurring model poll. Update the
structured event log and regenerate `STATE.md` after the outcome is committed.

## Inputs and evidence

The binding includes every staged package file (including auxiliary compact files absent
from the manifest), the manifest and core artifact version, destination commits, current
suitability evidence and implementation hashes. CSV hashes are obtained from the accepted
manifest on the coordinator; only workers fetch and inspect all rows. Current private
GitHub and Hugging Face commit/tag identity is checked before inference, worker preparation
and acceptance. Existing publishing credentials are used only for metadata reads.

The current review snapshot stays separate from immutable package bytes. If it cites the
candidate record, its four queue bookkeeping fields (`awaiting_operator`, `autonomous_audit`,
`last_autonomous_audit`, `next_action`) are excluded from that evidence projection, avoiding
a self-referential verdict. All substantive candidate fields remain bound. This exclusion
does not apply to any file in the actual staged package.

The generated prompt supplies every compact package/review file within a 240 KiB capsule.
It mandates analysis of label recovery, prediction timing, claims, licensing, data truth
and novelty, with attacks beyond the fixed battery. An oversized capsule refuses as
incomplete; it is never silently truncated. Findings must quote real hash-bound supplied
text. Missing coverage, invented citations, unsupported programs, target references and
contradictory pass/block verdicts refuse admission. These checks establish evidence
consistency, not the semantic correctness or completeness of a model's reasoning.

The auditor has no tools. `config/adversarial-runtime.json` must pin a reviewed installed
runtime. Before each invocation, the existing hosted evaluation's zero-tool resolution is
tested in the installed interpreter. An unknown toolset name alone is not evidence of
tool isolation. The invocation uses a neutral directory and the reviewed `--ignore-rules`
path, without preloaded skills or conversation resume. Recorded tool offers/calls and
usage are checked afterward; a missing empty tool pin is reported honestly and requires
the independent runtime preflight plus zero attempted/executed tool messages. Source
upgrades invalidate the capability pin until reviewed again.

The typed expression interpreter supports arithmetic, text/date transforms, unique
same-entity time joins, and group aggregates, with same-split and all-shipped donor scopes.
It has no Python evaluation, filesystem/network APIs or target column. Ambiguous donors,
invalid operations and uncertain rounded counts abstain. Programs are bounded to sixteen,
96 nodes each, depth twelve and 80 million row/node operations across scopes; excess work
refuses instead of sampling. This is a finite attack language, not a claim of exhaustive
search or a sandbox for arbitrary generated Python.

On the worker, both novel and fixed predictions are frozen before scored-label access.
Novel predictions are also frozen before the fixed battery reads training labels for its
supervised controls. Changing a label cannot change the novel vectors, but invalidates
the artifact receipt. The fixed battery's proven identities use the unconditional strict
rule. A novel program that predicts covered labels without error is an unresolved semantic
finding and blocks the internal pass; coincidental accuracy is not relabelled as a proven
identity. Resolving such a finding requires evidence and a fresh reviewed audit, not a
boolean waiver. No row-level vectors leave worker scratch; only compact aggregates are
collected. The worker never executes shipped construction or loader code.

## Queue and validation boundary

Worker preemption, scheduled advancement, candidate checks and the review notifier call
the same verifier. A bare `awaiting_operator: true`, stale report, changed artifact, missing
usage, failed worker, changed code, mismatched staging manifest or invented digest cannot
make a candidate an audited human wait. `operator_decision_pending` still identifies a
recorded disposition choice rather than readiness for publication.

Unit/integration fixtures exercise phase separation, target/code rejection, ambiguity,
mutation, current packaging gates, actual standard assembly, session accounting and
the full receipt chain. They are not real-dataset acceptance or a live model evaluation.
The current four blocked historical packages fail deterministic prerequisites and are
not eligible for paid model audits. Their A4 run remains a separate recorded gate comparison.
