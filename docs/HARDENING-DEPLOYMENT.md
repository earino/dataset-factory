# First hardening rollout — deployed and verified

Prepared 2026-10-22; the operator subsequently explicitly authorized merge/deployment.
PRs #1–4 and #6–9 are merged. Scout deployed the hardening stack and fixture follow-up
by fast-forward; final tested code is `8046b1b77ff0259e95675eb8ecaa78f657730404`.
Doctor and the 122-file live audit passed. See the
[deployment evidence](https://github.com/earino/dataset-factory/pull/4#issuecomment-6350157615)
and the verification follow-up below. The following procedure records the reviewed rollout.
No worker launch, allowance increase, credential, dataset tag or public-destination
artifact change is part of this rollout. The operator selected an explicit token-ceiling
policy for unpriced research in PR #7; the existing numerical limits stay fixed. PR #2 restores original factory manifest bytes after
concurrent repairs; see `docs/HARDENING-INCIDENTS.md` in that PR.

## Reviewed scope and evidence

- PR #1, `3ec0b64`: Scout's sanitised runtime handoff, scheduler-entry shims and 14 custom skills.
- PR #2, `58e0a96`: typed release reads, fail-closed manifest writer, isolated reconciliation,
  offline preview validation, all-package conformance (now eleven, including private EUTL), 26 new tests.
- PR #3, `4584fe2`: immutable job assembly, ownership hashes and structured refusal messages,
  13 new tests. Existing unmarked bundles are preserved; changed inputs need a new attempt ID.
- PR #4, `35bb2d6` (code and inventory): pinned runtime/project skill inventory, read-only drift/shadow audit,
  source audit in CI, 12 new tests, plus corrections to the captured publishing skill.
- PR #6, `4a1cb30`: pinned Hub verification, collected worker evidence, read-only Hub
  verification jobs, manifest-owned target paths and immutable tags, 35 new tests (including four preserved from Scout's active-session repair).
- PR #7, `40d33df`: atomic session admission, strict gate decisions, truthful scheduler
  exit codes, process-group supervision and fail-closed accounting; 44 new tests.
  Unavailable/invalid ledgers hold research. Unknown dollar pricing stays unknown;
  the operator-selected policy requires the existing positive weekly token ceiling.
- PR #8, `ec31e52` (supervisor code `256bd79`): supervised worker-host transfer/HF disk and
  runtime limits, 23 new regressions. Source review addressed procfs observation,
  late child cleanup and bounded reaping; incomplete cleanup refuses artifact upload.
  No paid worker probe.
- PR #5, `63472c1`: evidence patches only. They are not approved skill changes and must not
  be applied as part of deployment.

Recheck each listed head and any later documentation commit through exact-commit
GitHub Actions before deployment. Earlier green heads are not current-state evidence.
The Hub regression was also checked with Scout's installed client in an isolated checkout:
TSB without new worker evidence exits 2/incomplete, leaves its prior receipt byte-identical,
and writes a separate attempt diagnostic. No worker or remote mutation was used for that test. Independent Python 3.13.1
clean-clone results: #2 449 tests, #3 432 tests, #4 431 tests, #6 480 tests, #7 467 tests,
#8 503 tests, each OK
with six existing host-dependent skips (see each PR for its exact tested revision).
The combined integration at `c122064`, reconciled with main `0f853fa`, passed:

```text
Ran 572 tests in 6.540s

OK (skipped=6)
```

Original assertions and test-count semantics are preserved. Eduardo explicitly approved
a valid empty accounting database fixture for two existing lock tests in #7, which
otherwise relied on the missing-ledger fallback. The combined checkout stays clean;
PR #2 isolates an existing fake-client test that changed a real Austin destination timestamp. The #2 clean
clone also passed doctor, dashboard generation and the published Austin manifest command;
every file under `release/` had identical before/after SHA-256. Gate 1.4.0 and its code are
unchanged. No CI result substitutes for the post-merge exact-commit checks below.

## Establish a stable runtime before updating

Scout is the only coordinator. Its 18:00 research and subsequent watcher close-out
independently produced the worker repair and private EUTL package. Engineering launched
no extra worker. Main advanced to `f42e5b0` during review, including unreviewed skill edits
and manifest rewrites; #2 restores the original records while retaining new research.
A fresh integration initially failed three checks and passed only after that restoration.
Do not infer an idle host from the earlier session ending. Ask Scout to identify an idle research window and existing
worker activity using the supported ledgers. Do not launch from an engineering checkout,
kill a running research session, or delete its lock. Retain worker cleanup/watch functions.

The live Hermes curator modified both repository skills and unversioned custom skills during
review. Preserve any newer differences, with complete before/after digests, in the evidence
branch before restoring anything. Do not use a blanket stash/reset/clean or copy over unknown
work. Existing PR #5 patches only capture particular timestamps, not future curator changes.

Scout inspected the installed Hermes source and identified two independent writers. Per-turn
review checks only `auxiliary.background_review.enabled` (and fails open on config read errors).
Interval curation alone respects `hermes curator pause`; `pin` protects deletion, not content.
There is no review queue. Before changing anything, record the effective values and source
paths of the background-review master switch, both memory/skill nudge intervals and curator
paused state. Config and curator state are outside Git; a code revert cannot restore them.

The conservative rollout controls are **both**
`auxiliary.background_review.enabled: false` and `hermes curator pause`. Read both effective states
back, verify configuration loads successfully, and confirm no already-started background review
or curator pass remains active before capturing the final patch set. Do not edit platform-managed
`/opt/hermes`. The master switch pauses auxiliary automatic memory edits as well as skill edits;
it does not disable Scout's main research conversation or explicit STATE/memory work. The
proposed hold must disclose that cost. The narrower skill-nudge setting is insufficient: warm agents retain its old value, and even
memory-only forks retain skill_manage. The 120-second setting is an HTTP request timeout,
not a thread lifetime; cancellation can return without the thread acknowledging it. A quiet
log or elapsed timeout is not proof of drain. After setting the two controls, use a supported
controlled process restart and verify the new process/config before restoration; do not
kill or patch platform-managed processes by guesswork. If that mechanism is unavailable,
stop before restoration and report the exact operator action needed. Source-level evidence:
[Scout's final source review](https://github.com/earino/dataset-factory/pull/4#issuecomment-6348148964).

Scout verified the hosted restart mechanism is the supported s6 service manager: `hermes gateway
restart` signals the supervised `gateway-default` unit and it respawns. Do not use `stop`, which
leaves it down. A restart from a Scout tool interrupts that conversation's process and can lose
its immediate response; persist the handoff first and verify a new gateway PID and reconnect
before continuing. Prefer an outside shell, or the supported detached restart path confirmed by
Scout. This is a brief messaging interruption, not a runtime upgrade. Exact source/host evidence:
[restart mechanism](https://github.com/earino/dataset-factory/pull/4#issuecomment-6348202315).

Restore only individually identified, preserved skill files to their reviewed inventory
versions, with a precondition that each live file still matches its just-recorded digest.
If anything changed, stop and recapture/review; never overwrite the newer version silently.
Keep both automatic skill writers disabled until a review-before-apply workflow exists. `hermes curator run --dry-run` may preview supported curator work; it is not a dry-run switch
for the separate per-turn review fork, and does not approve applying changes. This hold concerns skill auto-editing,
not the discovery/research schedule or the qualification gate.

Reject the preserved instruction to remove a measured number when a reference baseline
beats the model. Keep negative results and comparable reference results visible; narrow an
unsupported claim instead. Horizon precision is a useful proposal to review independently.
Do not merely update inventory hashes to make a drift alert green.

## Merge and deploy

1. Fetch current `main`; check for new Scout research commits and integration conflicts.
   Merge #1, #2, #3 in that order, preserving their reviewed content. Retarget #4 from #1's
   branch to `main`, inspect its resulting diff, then merge it. Retarget #6 from #2 to main,
   inspect its diff and merge it. Merge #7 after reviewing its diff against current main.
   Retarget #8 from #6 to main, inspect its supervisor-only diff and merge it after
   resolving any source-review findings; it changes future worker bundles only.
   Retain all STATE and OPERATIONS entries
   when resolving append-only conflicts. No force push to `main`.
2. Require checks for the resulting full commit SHA, not an earlier branch head:
   `gh api "repos/earino/dataset-factory/actions/runs?head_sha=<full-sha>"`.
   Read every required run's completed success; pending is not success.
3. Re-run the suite in a clean Python 3.13 clone of that exact commit, plus doctor,
   `python3 scripts/check-runtime.py --source-only`, dashboard generation and an existing
   public manifest no-op. Compare all release-file hashes before/after. Inspect the generated
   eleven-package rows: nine public destinations include site; EUTL is private/packaged;
   NHS remains private/dropped,
   with its historical baseline explicitly labelled; NOAA keeps two protocol scores.
4. Scout updates `/opt/data/dataset-factory` by fast-forward only, after preserving and
   resolving the known local skill differences. Specifically: preserve the final two repository
   skill diffs and hashes; restore only `skills/dataset-release/SKILL.md` and
   `skills/dataset-qualification/SKILL.md` to their current HEAD bytes with digest preconditions;
   require `git status --porcelain` to be empty, then fast-forward. Apply the reviewed profile
   skill corrections with the same preserve/compare procedure. If there are other local edits or divergent
   commits, stop and reconcile them; do not reset the checkout. No shim replacement is
   expected: PR #1 captured the deployed shims verbatim.
5. On the host run `python3 -m factory doctor` and
   `python3 scripts/check-runtime.py --home /opt/data`. Require a clean audit and the
   intended checkout SHA. Source audit should check 61 files; live audit checks 122 and is
   expected to pass only after the known profile/project drift is resolved. Run source tests in an isolated checkout, not the working ledger.
   Do not run `--verify` publishing commands merely as read-only checks: complete checks record
   destination evidence. PR #6 now preserves that receipt on incomplete/error results and writes
   a separate attempt diagnostic. Obtaining new worker evidence remains a separately budgeted
   operation; no worker launch is part of this rollout.
6. Build and inspect the dashboard offline, then use its existing publish procedure once.
   Verify the Pages workflow for the pushed dashboard commit and anonymously read back
   `dashboard.json` and rendered HTML. A pending Pages build remains pending; resume its
   verification instead of repeatedly generating new commits. Check row counts, baseline
   scopes, destination pills and public/private status in the live response.
   Run the deployed budget script with `--json` only (never `--write-lock` for this check).
   Confirm the selected unpriced policy, 40,000,000-token ceiling, measured token counts
   and null dollar spend when pricing is absent. Do not backfill rates, delete ledger rows
   or loosen limits to make admission green. A legitimate limit/lock hold is not a deployment
   failure; an accounting read failure needs investigation before resuming research.
7. Record the source SHA, dashboard commit/deployment URL, curator status, runtime-audit
   result, doctor result and artifact-hash comparison in STATE and the deployment report.
   Re-check schedules/allowances were preserved and leave one specific next action.

Dataset websites and data publication remain under their existing reviewed-plan procedures.
No dataset release tag is moved to deploy framework or dashboard code.

## Rollback and remaining work

### Deployed verification and fixture repair, 2026-10-22

Exact-main [CI passed](https://github.com/earino/dataset-factory/actions/runs/39844619533).
A clean Python 3.13.1 clone of `50135b2` ran 572 tests in 6.722s, OK (skipped=6),
plus doctor, source audit, dashboard and the published-manifest no-op. Every release
file hash stayed unchanged; the original ten manifests match their original `beab726`
bytes. No qualification code changed.

Scout verified the supported restart from PID 22628 to 7867, then reconciled the
preserved skill drift with digest preconditions. Both automatic writers remain held
(`background_review.enabled=false`, curator paused), including auxiliary automatic
memory editing. Research/discovery admissions were briefly held 19:58:39–20:02:56 UTC
and restored; cleanup and worker watch remained enabled. Manual research and explicit
recordkeeping remain available.

Dashboard commit `5c9324a96ff3102be819b89b386098f2f67ae39c` has a
[successful Pages deployment](https://github.com/earino/dataset-factory-dashboard/actions/runs/39845163707).
Independent Chrome and anonymous JSON inspection confirmed the release fixes. All eleven
live records match the verified build's split, baseline, destination and publication
fields. Nine public records have site destinations; EUTL stays private/packaged and NHS
private/dropped. The budget decision reports 8,718,221 weekly tokens against the unchanged
40,000,000 ceiling, with dollar spend null and pricing unavailable.

The initial dashboard truthfully reported a failed local test run: eight existing
`AssembledBundle` tests attempted assembly in the live `.factory/jobs/austin-003`.
That historical directory has no ownership marker, so the new assembler correctly
refused to overwrite it. Scout reproduced this in a copy of the live checkout;
the clean hosted clone passed. The fixture repair copies the exact canonical inputs
to a temporary root and passes its generated absolute job path to the offline planner.
Every assertion is unchanged (verified by AST comparison), the test count is unchanged,
and the production ownership refusal is unchanged. An independent Python 3.13.1 clone
containing an unowned historical-job sentinel produced:

```text
Ran 572 tests in 6.781s

OK (skipped=6)
```

The sentinel remains byte-identical and unowned. Scout independently verified the
repair in a copy of the live tree, including all historical job directories:

```text
Ran 572 tests in 12.735s
OK
exit 0
```

All 34 assertion ASTs match; the Austin destination receipt, historical job digest
and absence of its ownership marker remain unchanged. The hosted checkout stays
clean. [Scout's signed review](https://github.com/earino/dataset-factory/pull/9#issuecomment-6350248422)
records the method and evidence. PR #9 merged after both branch checks passed;
[exact-main CI](https://github.com/earino/dataset-factory/actions/runs/39846677244)
also passed at `8046b1b`. No old job was erased or marked owned to make tests pass.

### Final public readback and ordinary research admission

Dashboard commit `7a799aa1c1b6096008e1921df5148381d7da68ce` passed its exact-commit
[Pages workflow](https://github.com/earino/dataset-factory-dashboard/actions/runs/39846876826).
Independent anonymous JSON and HTML readback reports snapshot `2026-10-22T20:12:35+00:00`,
source `8046b1b`, `tests={count: "572", ok: true}`, successful CI, 71 candidate checks
passing, and no alarms. All eleven release rows still match the independently
verified split/baseline/destination/publication fields. The live cost page explicitly
renders dollar spend and remaining allowance as unknown; the 40M token ceiling is
unchanged. The deployed host's 263 tracked release files match Git with no missing
files or mismatches. Qualification remains 1.4.0, executable SHA-256
`4e51d2e9494fd66dd220517476119d7b3f2edea4ffde276caa90999a28cc0a87`.
[Scout's final deployment evidence](https://github.com/earino/dataset-factory/pull/9#issuecomment-6350323879)
confirms doctor and the 61/122-file audits at `8046b1b`. The later budget read showed
8,808,258 weekly tokens and correctly refused overlap because the real discovery
session held the lock; this was not an accounting/pricing failure.

Both research admissions are enabled again. Next scheduled times in the verified
snapshot are research `2026-10-22T22:00:00Z` and discovery `2026-10-23T00:00:00Z`.
The ordinary 20:00 discovery tick ran once on resume at 20:02:53Z, with execution
`ddf1eea4eb4d4c6facb8e5b17b64525c` and real `scout-research` session
`20261022_200258_ef9347` (started 20:03:03Z). This verifies normal admission and agent
startup; its research outcome was still pending at rollout close-out. Scout must
record the eventual outcome and usage in the normal session records. No extra
research tick or paid worker probe was launched for engineering verification.

Both automatic skill writers remain held until a review-before-apply workflow exists;
this also holds auxiliary automatic memory editing. Explicit research recordkeeping
continues. PR #5 is preserved evidence only. Dataset visibility, publication and tags
were not changed by this rollout. The remaining hardening work below is separate
from this completed deployment.

If preflight fails, do not deploy. If the host checks fail after updating, hold new research
sessions through the existing scheduler controls while preserving cleanup/watch duties and
all ledgers. Restore behavior through a reviewed revert commit on main and fast-forward
that commit onto the host; never erase newer research records or rewrite published tags.
A dashboard rollback uses the existing website repository's reviewed revert and Pages
verification. The recorded pre-change config values make a deliberate runtime rollback possible;
do not silently re-enable unreviewed writers just because code was reverted. Keep the writer
hold while resolving skill integrity failures, and disclose any continued auxiliary-memory hold.

This batch does not claim to finish every hardening task. Remaining work includes
runtime-audit enforcement before scheduled research, a review queue for proposed skill
changes, dashboard health/CI unknown states and Pages-pending semantics, stronger candidate
evidence validation, and worker pre-container fetch/staging-upload bounds. Host-side HF
and transfer runtime/disk supervision is included in #8; it is sampled enforcement, not
an OS quota or complete memory isolation. Inventory coverage is explicit: additional
project-relevant custom skills must be reviewed and mapped before calling the handoff
complete. No new worker spend is implied by this list.
