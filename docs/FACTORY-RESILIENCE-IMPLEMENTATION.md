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
| Review item 3: structured events and generated state | Implemented on `codex/structured-operational-state`; not deployed | 1,364,901 original bytes preserved by monthly partitions; 4,354-byte generated view; clean-clone/CI and Scout handoff next |
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

## A1-small historical acceptance worker: resilience-a1-small-002 (Scout, 2026-11-07 ~19:5xZ)

First bounded R1 acceptance run, executed by Scout as sole launcher on reviewed
commit `dc0cb94` (branch codex/deterministic-recovery-gate), job pinned to
source-bundle SHA256 `3828cf1485bbf296068c4445f0dec99a59315cb63dfbe12f9dd40c57c0ac8384`
(pin verified at plan; hold stayed true; one cx23, EUR 0.06 reservation,
inside policy). Worker elapsed 39.9 s; collected; destroyed; provider read-back
0 servers / 0 IPs; ledger reconciled. No retry, no extra jobs, no rebuild, no
publication.

acceptance-summary.json: ok=true, all four cases exit 0 (nzea, unhcr, nsbwa,
ocha). Compact per-case evidence committed under
audits/resilience/2026-11-07-a1-small-002-acceptance/ (summary, per-case
acceptance/battery/qualification). Full results JSONL and the 4.6 MB fetched
historical bytes remain worker scratch and staging release 437762044 only.

- nzea: ok, strict gate REFUSED, bytes unchanged; 8.2 s, peak RSS 56,424 KiB.
- nsbwa (e8ed2a53): ok, strict gate REFUSED, bytes unchanged; 7.3 s, peak RSS
  32,432 KiB.
- unhcr (6fa7becd core + pinned members): gate 1.6.0 refused with
  failed_checks including battery.exact_recovery, artifacts.no_shipped_answers,
  contract.cross_row_probe_0; the battery reproduced the documented successor
  recoveries exactly - 12 exact rules (self/all x successor_flag x
  successor_count x eval/holdout x declared), 0 errors, AUC 1.0 on covered
  rows; successor_missing_zero heuristic 0.9753 eval / 0.9830 holdout.
- ocha (e7441e1f): battery probes recorded in the per-case files; strict
  refusal in its qualification.json.

Acceptance meaning: the draft gate reproduced the specified historical defects
and refused the old artifacts. This is experimental acceptance of a draft gate
under the hold - not production deployment, not A1 complete (remaining cases
pending), and no blocked package was repaired or requalified by this run.
## A1-fixtures historical acceptance worker: resilience-a1-fixtures-001 (Scout, 2026-11-07 ~20:1xZ)

Second bounded R1 acceptance run on branch codex/deterministic-recovery-gate
(merged tip 13737a6: my evidence d2ba315/58e127e merged with Codex d75cbf5, no
reset/rebase). Job pinned to source SHA256
`a00d503cbe4471e88c574b9b132f9b413dd5921710e49bb437cd9097e45db8d5` (verified at
plan), one cx23, EUR 0.06 reservation. Worker elapsed 172.9 s; collected;
destroyed; provider read-back 0 servers / 0 IPs; hold stayed true; no rebuild,
no publication, no retry.

acceptance-summary.json: ok=true, both cases exit 0. Expected fixture
recoveries reproduced exactly and the strict gate REFUSED both old artifacts:
- cqc (afe9ee20-era fixture channel): fixture:code/build.py lookup recovered
  4/4 eval labels, 0 errors; gate failed checks: battery.exact_recovery,
  battery.recorded_in_quality, artifacts.no_shipped_answers. 127.8 s,
  peak RSS 184,772 KiB.
- ab-wildfire (c2c8ceb5-era fixture channel): fixture:code/build.py recovered
  3 eval and 4 holdout labels, 0 errors; gate failed checks additionally
  include units.validation_receipt. 32.3 s, peak RSS 71,512 KiB.

Evidence committed by manifest logical path (single-object acceptance/battery/
qualification per case, validated), plus receipt.json binding staging release
437775462, manifest sha corrected to 0b62e5a9... by independent download below; per-file asset IDs/digests and runtime.
Full results JSONL and the 17.8 MB historical bytes remain staging-only.
Compact evidence: audits/resilience/2026-11-07-a1-fixtures-001-acceptance/.
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

## Independent fixture verification and remaining CPCB A1 run

Codex verified all seven fixture worker reports byte-for-byte against staging
manifest asset 721626471 (12,477 bytes, SHA256
`0b62e5a9003f65d28ff3f41b6965ec99bba2358091cfbc95453228eac45731cb`).
The previous receipt's manifest hash was inaccurate; the correction preserves that
previous claim and its evidence. Worker report bytes are unchanged. Full vectors
are temporary worker scratch; bounded diagnostic JSONL remains in private staging.
See `audits/resilience/2026-11-07-a1-fixtures-independent-verification.json`.
CQC recovered four eval labels and wildfire three eval plus four holdout labels,
all without errors; gate 1.6 refused both original artifacts. This completes six
of the seven A1 recovery families, not A2/A3/A4 acceptance or release clearance.

Scout reported zero servers/IPs and a reconciled ledger after both jobs. Existing
worker options are cx23 at EUR 0.02/h, cpx32 at EUR 0.08/h and cpx42 at EUR 0.15/h;
no policy allowances changed. The remaining original CPCB panel is prepared as
`resilience-a1-cpcb-001`, cpx32, 6 GiB container, four CPUs, 120-minute timeout,
180-minute lifetime, maximum reservation EUR 0.32 including existing cleanup grace.
The exact source-bundle pin is
`b5a4f3eb9e849cc585ef6b6d71dea30c6483bea55082977b8915f35296b84758`.
The 89,081,808 bytes of historical inputs move only to the worker. Expected exact
coverage is pinned before launch: self eval 125,277; all-scope eval 125,776 and
holdout 143,793, each with zero errors. Scout must verify the plan, budget, exact
pin and absence of active workers before one attempt, collect bounded reports,
destroy/reconcile, preserve evidence and check the exact pushed commit's CI.
No rebuild, publication or scoring-adapter experiment is authorized by this job.

## A2 transport preparation (no comparison results yet)

`scripts/prepare-frozen-audit.py` creates deterministic code/document-only archives
from the existing frozen registry. It refuses changed bytes, escaped/symlink paths,
bulk-file entries and existing output directories. The prepared fourteen archives
plus inventory total 4,014,080 archive bytes and are in private draft staging release
437790346. Server digests were checked; the inventory and staging receipt are under
`audits/resilience/2026-11-07-a2-document-*.json`. Dataset bytes and version tags are
unchanged. The draft requires numeric release-ID lookup; REST releases/tags is not
an appropriate lookup for this draft.

The historical audit driver adds `published_comparison` mode, requiring the actual
frozen MANIFEST.json, the registered editorial files and the requested artifact or
level identity. It runs the full gate and retains bounded diagnostics without
rewriting historical data. A completed comparison is labelled historical review,
`release_eligible: false`, and never grants new-release clearance. A1's strict known
recovery expectations remain separate and unchanged. Transport tests pass; full
clean-clone/CI and actual A2 runs remain to be done.

The 14 releases include 40 Chicago food targets, 45 MSHA targets and two NOAA
protocols. All levels need comparison, with sequential bounded worker batches
sized from measured runtime. Thirteen staging manifests map the published CSVs.
Frozen EC merger meta/quality and OCHA quality must come from their exact frozen
editorial copies, since original staging differs. PriceCatcher's recorded staging
reference could not be resolved by REST or gh release lookup; a pinned published
source must be fetched on a worker. No local full datasets were downloaded.

### All-level A2 declarations

`audits/resilience/2026-11-07-a2-batches.json` records eighteen unlaunched bundles
covering all 98 core task artifacts, with source pins and explicit input sizes.
Each core hash set is checked against its frozen manifest by a transport test.
The PriceCatcher fallback uses public release 420542550: the server's asset digests
and sizes match the frozen manifest. Only the worker may download its CSVs, with
an explicit public-fetch flag, fixed HTTPS release URL, size limit and full digest
check. Other dataset CSVs use the existing authenticated worker fetch from private
staging. No A2 hold exceptions have been registered and no A2 jobs have launched.
The combined ceiling reservation is EUR 5.76 (eighteen times EUR 0.32), not a billing
measurement or permission to exceed the current remaining allowance. Scout must
plan each job, run only one worker, collect and clean up before advancing. Use the
CPCB and first comparison measurements to assess later batch sizing. The transport
precursor d4b7848 passed 773 clean-clone tests and exact-SHA CI; the complete plans
and public-fallback change still need their clean-clone and CI pass.

CPCB's measured 853.168-second runtime and 1,119,604-KiB peak RSS support the
existing 6-GiB container choice. For runtime margin, the original five-case large
A2 batch was split into three before launch, yielding eighteen batches and a
EUR 5.76 combined maximum reservation. The superseded local declaration and sealed
bundle were preserved; no job with that old id ran. These runtime estimates do not
replace the configured per-job deadline or Scout's live budget gate.
