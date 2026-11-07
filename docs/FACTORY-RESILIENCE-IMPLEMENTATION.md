# Factory resilience implementation and acceptance ledger

Operator authorization, 2026-11-07: “i like the stricter gate. your goal is to finish
implementing all of this to make the dataset factory much more resilient, ship it,
and coordinate with scout to make sure we do a better job going forward”.

The self-audit briefing supplies R1-R6/A1-A5. The independent architecture review is
advisory: verify claims against code before changing it. The selected rule is strict:
demonstrated label-blind exact recovery blocks new releases without a retrospective-scope
or disclosure waiver. Ordinary statistical predictions that happen to be right are not
proof of exact reconstruction. Published data, tags and manifests remain frozen.

## Delivery sequence

| Work | Status | Acceptance evidence still needed |
| --- | --- | --- |
| R6: config-driven admission hold | Implemented on `codex/factory-admission-hold`; tests in `test_admission_hold.py` plus existing lifecycle/scheduler tests | Clean-clone suite, exact-commit CI, Scout deployment read-back |
| R1: deterministic label-blind battery, gate 1.6 | Pending | Historical A1 reproductions, published A2 comparison, exact-byte binding and worker integration |
| R2: scaffold/answer scrubber | Pending | Wildfire/CQC/ZA-CCT regressions and all-file package scan |
| R3: measurable claims from bytes | Pending | Dictionary/min-max/interval/prevalence/placeholder/digest regressions |
| R4: source licence evidence and generation | Pending | Browser-capable evidence path, unreadable and conflicting source refusals |
| R5: autonomous independent adversarial audit | Pending | Bounded auditor stage, digest-bound verdict, queue admission enforced |
| Review item 2: publication invariants/rule consolidation | Pending | Verify reported hash gap; strict recovery rule, normative-rule inventory |
| Review item 3: structured events and generated state | Pending | Byte-preserved narrative archive, deterministic current state under 20 KB |
| Review item 4: digest-bound approvals | Pending | Matching approval required at flip, historical evidence with honest gaps |
| Review item 5: deterministic reconciliation | Pending | Replay actual watcher events, preserve every verification |
| Review item 6: actor identity | In progress | Codex author on new commits; no history rewrite |
| A4: four blocked packages through full pipeline | Pending | Worker-side frozen-artifact outcomes; disposition remains operator's |

Each item gets a separate branch/PR. This ledger is implementation status, not a passing
audit or permission to publish. Do not treat partial code or synthetic unit fixtures as
historical-artifact acceptance.

## Verified observations and coordination

- `docs/OPERATIONS.md` contains the reported contradictory publication-authority prose;
  reconcile it with explicit operator approval of the private-to-public flip.
- The worker's existing `release: true` flag bypasses release preemption. The remediation
  hold independently requires a source-bundle pin and cannot be bypassed by this flag.
- Scout's Telegram status at 12:16 on 2026-11-07 reports deployed `310e3f5`, zero workers
  and IPs, reconciled ledger, about EUR 5.96 reserved of EUR 20, and an active scheduled
  ns-bwa editing session. These are Scout-reported observations, not independent read-back.
  Its uncommitted candidate edits must be preserved. The platform schedules remain active;
  the new config hold must be deployed before claiming scheduled work is held.
- Scout will operate the worker ledger for acceptance. Codex prepares reviewed bundles;
  no second coordinator launches against that ledger.
- Scout reports model-token accounting near the weekly ceiling. Keep coordination concise
  and do not alter session/worker allowances to evade admission.

## Next action

Finish the hold's clean-clone and CI checks, merge and have Scout deploy/read back the held
state while preserving concurrent edits. Then read all five referenced audit reports in full,
map each attack to pinned artifacts and regressions, and implement R1/R2. Keep the hold active
until measured acceptance is recorded; do not rebuild the blocked datasets as part of A4.
