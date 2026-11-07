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
| R1: deterministic label-blind battery, gate 1.6 | In progress on `codex/deterministic-recovery-gate`: two-phase stdlib battery, full generated-artifact scan, quality receipt and strict package admission | Historical A1 reproductions, published A2 comparison, exact-byte binding and worker integration |
| R2: scaffold/answer scrubber | Shipped PR #27, merge `a2578ed`; both exact-commit CI workflows passed; deployed/read back by Scout in `fbc8fee` | Worker-generated artifact integration is in R1; full worker A3/A4 pending |
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

## R2 answer-artifact scrubber deployment read-back (Scout, 2026-11-07 ~19:2xZ)

Deployed merge `a2578ed5bc5515ef4312e781880d0c7a2f28a7c0` (PR #27) by clean
fast-forward (working tree clean; concurrent work already committed). CI on the
exact SHA: check success, preview success (read back via the GitHub API).

Read-only verification on the deployed tree:
- `tests.test_artifact_scrub` + `tests.test_assembly_safety`: 26 tests, OK.
- `check-package.py` (now scanning every file) against the four blocked
  packages REFUSES each (exit 1) and reproduces the 2026-11-07 audit findings:
  ab-wildfire (MANIFEST fixture answer data + raw fixture IDs + @@TOTAL@@,
  builder FIXTURES table), cqc (embedded pseudonym salt, answer lookup,
  builder fixtures, scored-window example), za-cct (scored-window worked
  example in README + builder, raw fixture station IDs), cpcb (fixture
  answer data, raw fixture IDs, and unresolved placeholders @@THIN@@ and
  @@GAPFULL@@ - the latter two beyond what the audit listed).
- Historical-warning split verified: published ec-merger package passes
  (exit 0) with 7 historical-warning lines for exact pinned old files.
- Website previews: `site-preview-all.py` refuses cqc (salt/answer lookup)
  and unhcr (fixture answers in MANIFEST/measurements/quality) offline; all
  published packages prepare.
- Hold unchanged: config/admission.json hold=true, empty allowlist; platform
  schedules and cleanup untouched; no worker launched; the four blocked
  artifacts untouched and private. R2 evidence is
  audits/resilience/2026-11-07-answer-scrub.json plus this local read-back -
  static, not full qualification.

## Next action

Run pinned R1 historical acceptance through Scout, then complete the remaining gates
and architecture items. Keep the hold active; do not rebuild the blocked datasets in A4.

## R1 implementation checkpoint (Codex, 2026-11-07)

The new stdlib modules freeze feature-only predictions before scored-label access,
keep supervised controls separate, and bind receipts to all inspected inputs and code.
Audited recipes cover successor/lag/recency, rounded count/rate and rolling-mean
identities, plus literal fixture lookups. Generic joins and rank/token/lookup controls
remain explicitly statistical or heuristic. Scored-label mutations leave frozen
predictions unchanged; data/auxiliary/vector mutations refuse later acceptance.

Gate 1.6 and package/manifest guards require the matching computed receipt. The
constructor explicitly records it with `--record-battery`; historical audit is read-only.
The assembler includes canonical dependencies. Unit evidence is counts-only, preserving
source-validation provenance outside the scored package instead of shipping answers.
The CQC and UNHCR-corridor legacy builder rehearsals now require rejection for their
retained defects, while their construction/format regressions remain exercised.
See `docs/RECOVERY-BATTERY.md` for finite bounds and provenance.

Targeted suites have passed (117 construction/gate tests, 119 receipt/site tests,
and 15 battery algorithm/phase tests in separate runs). Full clean-clone and CI
validation, pinned historical worker acceptance and complete A1/A2/A4 remain pending.
No new gate has been claimed deployed and no real-artifact recovery numbers have
been computed on the coordinator.

At `02b0345`, a fresh clone passed all 765 tests (13 platform-specific skips), gate
selftest, runtime source inventory and suitability checks. Both push and PR CI
workflows passed for the exact SHA. PR #28 remains draft pending historical evidence.
The first reviewed worker attempt `resilience-a1-small-002` fetches four original
artifacts and original source members directly from private staging (4,580,565 bytes).
Its exact source-bundle hash is pinned while `hold` remains true. Archive safety,
plan identity and degraded-recovery regressions passed with assembly safety (19 tests).
This is preparation, not a completed acceptance run. Scout must read back the live
plan and bounded allowance, operate the sole worker, collect diagnostics and clean up.
