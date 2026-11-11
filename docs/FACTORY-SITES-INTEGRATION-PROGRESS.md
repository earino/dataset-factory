# Sites integration progress

Implementation authorized by Eduardo on 2026-11-11. Scope and completion criteria:
[FACTORY-SITES-INTEGRATION.md](FACTORY-SITES-INTEGRATION.md), S1–S8.

## Current work

- Added modern dashboard collectors and connected them to the existing renderer.
  Modern stages, active queue and release receipts are primary; legacy candidates
  remain in detail pages and releases are labelled by workflow. Missing modern
  state is explicitly identified as unavailable with legacy history shown.
- Dashboard overview, cost display, token alarms and new history points use normal
  operation tokens. The session gauge uses weighted normal-operation sessions;
  development usage is identified separately. History from the old workflow is
  not drawn as a modern throughput series. Effective controller/worker settings
  and separate website status are included without changing CSS or layout.
- New dashboard tests cover real published metadata, private-field exclusion,
  actual modern stages, legacy hold separation, missing-state labels and usage
  accounting. Dashboard/state checks: 41 pass, one existing optional skip.
- The hourly shim inventory hash was updated after CI caught the stale entry.
  Correction commit `d869700` passed Linux CI; the runtime audit also passed in a
  clean checkout.
- Added `factory/site_sync.py` and `scripts/site-sync.py` for bounded modern-site
  catch-up. The existing hourly shim invokes it before dashboard generation with
  a 600-second outer limit. It processes releases independently, retains receipts,
  checks completed bundles without republishing, and leaves candidate state alone.
  `site_reconciliation_enabled: false` in private local config disables only this
  added step. The script uses the existing publishing credential file on Scout.
- 44 focused site tests pass. New tests cover stable real-data projection, website
  edition reuse, failure isolation and completed-bundle no-op behaviour.
- Scout's fresh read-only inventory is on branch
  `scout/sites-integration-inventory`, commit `fd5d3b9`, under
  `audits/sites-inventory/2026-11-11/`. Collection was 10:35–10:40 UTC: five modern
  published candidates, all five matching publication receipts; controller enabled,
  max_workers 1; publisher has existing admin/push access to all current targets.
  Deployed code remained `2bf708a`. No site deployments occurred during inventory.
- Shared bundle preparation now accepts the validated modern projection. Modern
  bundles record standing-policy authorization; the CLI has `--standing-policy
  <plan-sha>` separately from legacy operator approval.
- GitHub navigation leaves modern manifests unchanged. GitHub tag verification
  checks the original consumer-verified commit. The Hub adapter binds verification
  to that receipt's immutable commit, checks release blobs, and edits only the
  current README navigation. It does not download bulk files or move tags.
- 41 focused tests pass, including stable modern bundles, unchanged manifests,
  later editorial branch commits and mismatched Hub publication commits.
- Added `factory/site_modern.py`: the modern manifest/receipt adapter supplies the
  existing renderer record. It reads measured baseline results only from compact
  metadata whose bytes and hashes match the pinned manifest, preserves nested Hub
  paths and actual release asset names, and derives prose from the accepted task.
- Modern pages use the released documentation paths and evaluation scope. No CSS,
  layout or navigation design changed. Real pinned UCMR metadata (43 KiB) is retained
  as the regression fixture; no dataset rows were downloaded.
- The 35 focused site/state/legacy lifecycle tests pass. The previous state-reader
  commit `29ed4f1` passed Linux CI. A full clean macOS run had 16 platform errors
  including Linux-only `os.waitid`; focused state tests passed in that clean clone.
- Added `factory/site_state.py`: a consistent read-only SQLite reader and a compact
  public projection. Missing/corrupt state is unavailable, not an empty factory.
  Candidate data and attempt diagnostics are not serialized into the public view.
- Added receipt identity checks for both anonymous consumers, artifact, version,
  repositories and row counts. These reuse existing evidence; they do not change
  dataset acceptance or candidate state.
- Four focused tests pass for absent/corrupt inputs, private-field exclusion,
  running attempts and mismatched consumer evidence.
- Asked Scout in the main Telegram session to capture fresh compact deployed
  evidence on `scout/sites-integration-inventory`. A preceding `/btw` answer was
  explicitly based on the 10:10 UTC readback and had no tools; it is not a fresh
  deployment observation. Scout remains the sole worker-launching coordinator.

## Next actions

1. Exercise bounded site reconciliation and dashboard generation with Scout after
   exact-commit CI. Verify actual schema compatibility across all five releases.
2. Deploy the matching hourly shim and verify its runtime inventory; resume saved
   site bundles until the anonymous live checks pass on all surfaces.
3. Verify clean-checkout tests and exact-commit CI, deploy with Scout, backfill,
   inspect live desktop/mobile pages, and observe scheduled recovery/no-op passes.

No site code has been deployed. S1–S8 remain unproven. The existing untracked
`docs/.FACTORY-SITES-INTEGRATION.md.swp` has been left untouched.
