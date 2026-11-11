# Sites integration progress

Implementation authorized by Eduardo on 2026-11-11. Scope and completion criteria:
[FACTORY-SITES-INTEGRATION.md](FACTORY-SITES-INTEGRATION.md), S1–S8.

## Current work

- Commit `6a0241d` passed exact CI `43009932470` / `43009932420` and 72 focused
  clean-checkout tests. Sent Scout the tested short-name and history corrections.
  Root anonymously observed the restored `19 datasets shipped` headline at
  11:16 UTC. The active title readback watcher is waiting for the five short names
  to appear in the catalogue; its session is `23142` (15-minute observation window).
- Desktop/mobile checks now cover the live catalogue and dashboard. A concrete
  dashboard overflow at 390 pixels was corrected by a single grid-child sizing
  guard. The browser measurement dropped from 449 to 390 pixels; desktop screenshot
  pixels are identical before/after that guard. No fonts, colours, spacing or cards
  changed. Evidence and screenshots are in `visual/dashboard-catalogue-check.json`.
- Eduardo identified two presentation regressions: prediction questions used as
  dataset names, and a shipped headline limited to modern releases. Corrected the
  adapter to derive short names from stable dataset IDs while keeping the accepted
  question as summary. The dashboard headline now counts all distinct published
  datasets across workflows, and its publication chart retains earlier all-time
  history. Modern queue/funnel and scoped usage remain separate. Existing history
  files are not rewritten. The combined 72 focused tests pass (one optional skip).
- Independent anonymous dashboard readback at 11:09 UTC confirmed all four pages
  carried the 11:06:11 snapshot, modern state was available, controller enabled and
  max_workers 1. All five modern releases were present. This is the pre-correction
  dashboard; later readback must verify the restored all-time headline.
- Both platforms' five frozen version tags match original publication commits;
  GitHub asset inventories and all 14 old catalogue record blobs remain unchanged.
  Evidence is in `release-preservation-check.json`; stylesheet comparison against
  `2bf708a` is in `style-preservation-check.json`.
- Diagnosed a real convergence defect during rollout: the shared catalogue README
  was rewritten with each current dataset's navigation. Live README history cycles
  through the releases; an alternating-two-release regression reproduces pending
  after earlier completion. The README now has a stable catalogue link. The new
  regression and 34 focused tests pass. Evidence is in
  `audits/sites-integration/catalogue-retry-defect.json`.
- Asked Scout to finish its current bounded site pass and defer more manual site
  retries until the fix passes CI. Dashboard publication must proceed independently;
  controller and cleanup remain active. This is not a pause of the factory or goal.
- Anonymous catalogue readback now includes all five modern benchmarks plus its
  14 earlier records (19 total). The public dashboard at the same check still
  served its legacy snapshot from 10:50 UTC; dashboard rollout remains pending.
- Used an isolated browser for visual checks. The desktop dataset page retained
  the existing design. A demonstrated 390-pixel mobile defect came from long
  control metric labels squeezing the value column. The renderer now shows short
  headline labels for the full model; full metrics remain unchanged in the release
  record and linked evaluation. The fixed preview has no page overflow and a
  174-pixel value column. Screenshots and measurements are retained in
  `audits/sites-integration/visual/`. This correction still needs deployment.
- At 10:55 UTC root anonymously read all five dataset version `release.json`
  records: 5/5 match the exact public projections prepared earlier. Evidence:
  `audits/sites-integration/dataset-live-record-check.json`. The earlier partial
  check is retained separately. Catalogue readback still had its 14 earlier
  records and no modern entries at the preceding check; catalogue/dashboard and
  unattended completion remain unproven.
- Documentation/evidence commit `c87dd40` passed exact-commit CI `43007103290`.
  Browser-extension control returned an API error during preview inspection;
  native Chrome fallback encountered concurrent user activity and was left alone.
  Desktop/mobile visual acceptance remains open; no visual success is claimed.
- Root prepared all five real modern releases from pinned public metadata and the
  matching Scout publication receipts: 5/5 projections and offline renderer builds
  passed. Compact results are in `audits/sites-integration/real-release-previews.json`.
  Temporary preview bundles remain at the recorded local path for visual checks.
- Updated the website and dashboard operating docs to describe modern inputs,
  standing-policy authorization, bounded scheduled catch-up, scope labels and
  recovery. Historical instructions are explicitly scoped to the legacy path.
- Scout acknowledged the deployment handoff and independently verified both CI
  runs. Its 10:50 UTC message reports deployment starting after capturing before
  state. Root's anonymous check at that point still saw the old public dashboard
  and catalogue, with zero of the modern release IDs; live completion is pending.
- Dashboard integration commit `cb60cef66b9b828fe48e45e242c6c69a3baf0bc8` passed
  exact-commit Local checks `43006437889` and Website preview `43006437641`.
  The combined 90 focused tests passed in a clean checkout (one optional skip).
  Sent Scout the concrete rollout instruction in the main Telegram session:
  fast-forward code, copy only the reviewed hourly shim, verify runtime inventory,
  run one bounded sync and dashboard publish, then resume pending bundles. No
  deployment success has yet been observed by root.
- Root independently recorded all five frozen GitHub tag commits and release
  asset names/sizes/digests in `audits/sites-integration/pre-rollout-identities.json`.
  All tag commits match the earlier consumer-verified publication receipts. Use
  these identities for post-rollout comparison; no data files were downloaded.
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
