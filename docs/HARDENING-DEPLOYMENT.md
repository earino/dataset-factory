# First hardening rollout — prepared, not deployed

Prepared 2026-10-22. The operator requested broad hardening and deployment after an
original instruction to open a PR without merging. Resolve that remaining merge boundary
before executing this rollout. No worker, budget, credential, dataset tag or dataset artifact
change is part of this rollout.

## Reviewed scope and evidence

- PR #1, `3ec0b64`: Scout's sanitised runtime handoff, scheduler-entry shims and 14 custom skills.
- PR #2, `5605236`: typed release reads, fail-closed manifest writer, isolated reconciliation,
  offline preview validation, all-ten-package conformance, 26 new tests.
- PR #3, `4584fe2`: immutable job assembly, ownership hashes and structured refusal messages,
  13 new tests. Existing unmarked bundles are preserved; changed inputs need a new attempt ID.
- PR #4, `35bb2d6` (code and inventory): pinned runtime/project skill inventory, read-only drift/shadow audit,
  source audit in CI, 12 new tests, plus corrections to the captured publishing skill.
- PR #6, `472cf79`: pinned Hub verification and immutable tags, 18 new tests.
- PR #5, `63472c1`: evidence patches only. They are not approved skill changes and must not
  be applied as part of deployment.

Each code head passed its exact-commit GitHub Actions runs. Independent Python 3.13.1
clean-clone results: #2 445 tests, #3 432 tests, #4 431 tests, #6 463 tests, each OK with six existing
host-dependent skips. The combined local integration at `6df4a76` passed:

```text
Ran 488 tests in 1.986s

OK (skipped=6)
```

All 419 original tests are unchanged. The combined test checkout stays clean; PR #2 fixes
an existing fake-client test that changed a real Austin destination timestamp. The #2 clean
clone also passed doctor, dashboard generation and the published Austin manifest command;
every file under `release/` had identical before/after SHA-256. Gate 1.4.0 and its code are
unchanged. No CI result substitutes for the post-merge exact-commit checks below.

## Establish a stable runtime before updating

Scout is the only coordinator. Ask Scout to identify an idle research window and existing
worker activity using the supported ledgers. Do not launch from an engineering checkout,
kill a running research session, or delete its lock. Retain worker cleanup/watch functions.

The live Hermes curator modified both repository skills and unversioned custom skills during
review. Preserve any newer differences, with complete before/after digests, in the evidence
branch before restoring anything. Do not use a blanket stash/reset/clean or copy over unknown
work. Existing PR #5 patches only capture particular timestamps, not future curator changes.

Scout inspected the installed Hermes source and identified two independent writers. Per-turn
review checks only `auxiliary.background_review.enabled` (and fails open on config read errors).
Interval curation alone respects `hermes curator pause`; `pin` protects deletion, not content.
There is no review queue. Supported rollout controls are **both**
`auxiliary.background_review.enabled: false` and `hermes curator pause`. Read both effective states
back, verify configuration loads successfully, and confirm no already-started background review
or curator pass remains active before capturing the final patch set. Do not edit platform-managed
`/opt/hermes`. Source-level evidence and call paths are in
[Scout's review](https://github.com/earino/dataset-factory/pull/4#issuecomment-6347671806).

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
   inspect its diff and merge it. Retain all STATE and OPERATIONS entries
   when resolving append-only conflicts. No force push to `main`.
2. Require checks for the resulting full commit SHA, not an earlier branch head:
   `gh api "repos/earino/dataset-factory/actions/runs?head_sha=<full-sha>"`.
   Read every required run's completed success; pending is not success.
3. Re-run the suite in a clean Python 3.13 clone of that exact commit, plus doctor,
   `python3 scripts/check-runtime.py --source-only`, dashboard generation and an existing
   public manifest no-op. Compare all release-file hashes before/after. Inspect the generated
   ten-package rows: nine public destinations include site; NHS remains private/dropped,
   with its historical baseline explicitly labelled; NOAA keeps two protocol scores.
4. Scout updates `/opt/data/dataset-factory` by fast-forward only, after preserving and
   resolving the known local skill differences. If there are other local edits or divergent
   commits, stop and reconcile them; do not reset the checkout. No shim replacement is
   expected: PR #1 captured the deployed shims verbatim.
5. On the host run `python3 -m factory doctor` and
   `python3 scripts/check-runtime.py --home /opt/data`. Require a clean audit and the
   intended checkout SHA. Run source tests in an isolated checkout, not the working ledger.
   Do not run `--verify` publishing commands merely as read-only checks: some record evidence.
6. Build and inspect the dashboard offline, then use its existing publish procedure once.
   Verify the Pages workflow for the pushed dashboard commit and anonymously read back
   `dashboard.json` and rendered HTML. A pending Pages build remains pending; resume its
   verification instead of repeatedly generating new commits. Check row counts, baseline
   scopes, destination pills and public/private status in the live response.
7. Record the source SHA, dashboard commit/deployment URL, curator status, runtime-audit
   result, doctor result and artifact-hash comparison in STATE and the deployment report.
   Re-check schedules/allowances were preserved and leave one specific next action.

Dataset websites and data publication remain under their existing reviewed-plan procedures.
No dataset release tag is moved to deploy framework or dashboard code.

## Rollback and remaining work

If preflight fails, do not deploy. If the host checks fail after updating, hold new research
sessions through the existing scheduler controls while preserving cleanup/watch duties and
all ledgers. Restore behavior through a reviewed revert commit on main and fast-forward
that commit onto the host; never erase newer research records or rewrite published tags.
A dashboard rollback uses the existing website repository's reviewed revert and Pages
verification. Keep the curator paused while resolving skill integrity failures.

This batch does not claim to finish every hardening task. Next work should address the
research runner's atomic session admission/failed-gate handling, runtime-audit enforcement
before scheduled research, dashboard health/CI
unknown states and Pages-pending semantics, and stronger candidate evidence validation.
Inventory coverage is explicit: additional project-relevant custom skills must be reviewed
and mapped before calling the handoff complete. No new worker spend is implied by this list.

PR #6 on `hardening/hub-integrity` is stacked on #2:
existing tags never move, creation pins the verified commit, plain metadata is hashed through a
bounded download, and size-only/bulk-without-digest cases fail. Its exact-head push and PR CI passed, and it is included in the 488-test combined integration. Runtime skill corrections in #4 agree
with this behavior; captured originals remain in #1.
