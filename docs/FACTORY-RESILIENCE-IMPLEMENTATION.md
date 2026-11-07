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
| R6: config-driven admission hold | Shipped in PR #26, merge `16657ab`; exact-commit CI passed; Scout deployment read-back in `d1e6030` below | Hold remains active until R1-R4/A4 acceptance |
| R1: deterministic label-blind battery, gate 1.6 | Pending | Historical A1 reproductions, published A2 comparison, exact-byte binding and worker integration |
| R2: scaffold/answer scrubber | Implemented on `codex/answer-artifact-scrubber`: assembly and package guards, all-file inventory, pinned historical warnings | Clean-clone/CI, worker-generated artifact integration with R1, full worker A3/A4 |
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

## R6 deployment read-back (Scout, 2026-11-07 ~19:0xZ)

Deployed merge `16657ab343d25d4dcb54026234251ecb191f11c0` on the coordinator
(fast-forward from `310e3f5`; the concurrent session's ns-bwa edits had been
committed by their session and were preserved in `fce2373` - working tree clean
at pull). Verification, all read-only, no paid calls, platform schedules and
cleanup untouched:

- `config/admission.json` reads back `hold: true`, allowlist empty.
- Both research-wrapper roles report `GATE: HELD - Factory remediation hold:
  ...` via `--dry-run --source-tag verification` (default research prompt and
  the discovery prompt file); no model started.
- Candidate creation refused pre-write (`factory.candidates.create` ->
  "Factory remediation hold blocks discovery: ..."; no directory created).
- Source capture refused (`scripts/standing-capture.py --all` -> hold message).
- Package generation refused (`scripts/release-manifest.py
  za-cct-substation-evening-peak-exceedance` -> "Factory remediation hold
  blocks package construction: ...").
- Worker launch refused BEFORE any provider call, with `release: true` on the
  spec and an empty allowlist: `worker launch
  candidates/ocha-fts-appeal-funding-trajectory/requal/job.json` -> hold
  message; zero ledger records created by the attempt; admission sits before
  the ssh/github/cloud calls and repeats inside the launch lock.
- Test modules on the deployed tree: `test_admission_hold`, `test_workers`,
  `test_session_admission`, `test_research_session_wrapper`,
  `test_research_schedule` - 91 tests, OK.
- Live state at deployment: 0 servers, 0 IPs, ledger fully reconciled, no
  active or interrupted job records; nothing awaiting flip; the four blocked
  packages stay private.

## R2 static evidence (Codex, 2026-11-07)

`factory/artifact_scrub.py` scans every package file, with bounded text/AST analysis
without executing package code. It refuses fixture answers, literal salts, raw fixture
identifiers, scored-row/date outcome examples, unresolved placeholders and uninspectable
non-split files. Intentionally labelled CSV splits are inventoried but excluded from the
scaffold scan. Both job assembly and `check-package.py` enforce the result. The scanner
is bounded static analysis, not a guarantee that arbitrary code hides no answer.

`audits/resilience/2026-11-07-answer-scrub.json` records the local tracked code/document
findings on all four blocked packages. This reproduces the R2 defect shapes without
fetching data rows or changing frozen artifacts. It is not worker qualification or A4.
The 14 published package identities and existing editorial hashes are frozen in
`config/frozen-releases.json`; only exact old files receive historical warnings.
New/changed files and a self-asserted `published: true` cannot bypass the guard.

Validation at `6b0faf9`: 103 targeted tests passed; a fresh clone ran the complete
745-test suite successfully (13 platform-specific skips). Runtime source inventory
passed. Exact-commit remote CI remains required after pushing.

## Next action

Ship R2 after clean-clone and exact-commit CI. Implement R1 with the generated-artifact
scrub on the worker, bind every diagnostic to the scanned bytes, and run pinned historical
acceptance through Scout. Keep the hold active; do not rebuild the blocked datasets in A4.
