# Sites integration deployment evidence — 2026-11-11

All times UTC. Scout (Hermes) executed; root (Codex) authored and CI-verified every commit;
Eduardo authorized implementation/public deployment under docs/FACTORY-SITES-INTEGRATION.md.

## Deploys (each fast-forward at a tick boundary; CI verified at the exact SHA first)

cb60cef → a364181 → 8fa9fc4 → 6a0241d → 404dabf → 6889214 (deployed 11:31:05Z, in time for
the 11:50 hourly run). Private `config/local.json`, `.factory/pipeline.sqlite3` and
`build/dashboard/history.json` preserved at every step; 0 tracked modifications after each pull.
The hourly shim was installed once (`d8962179…`, from `ops/shims/scout_dashboard.py`) and its
hash is unchanged through all commits. Full chain with CI run IDs: `deployment-runtime.json`.

## Site sync (scripts/site-sync.py, standing policy FACTORY-SITES-INTEGRATION-2026-11-11)

- Initial pass 10:51 created the first 5 bundles (pending) — superseded by the a364181
  renderer fix, then by the 6a0241d short-name fix; superseded bundles and receipts preserved.
- Root demonstrated the catalogue retry defect (shared catalogue README rewritten per release,
  keeping deployments pending); the 8fa9fc4 stable-README fix converged the catalogue.
- All five modern dataset websites complete (11:23:40Z), site_revision 2 each after the
  short-name refresh; editions 1 and 2 both preserved; dataset tags, assets and the 14 old
  catalogue records unchanged (root-verified; see `tag-asset-identities.json`).
- No-op confirmation pass 11:26:44Z: ok, verify-only, no new commits or dispatches.
- The real 11:50 hourly shim run repeated the no-op: site-sync ok at 11:50:01.

## Dashboard (scripts/build-dashboard.py --publish)

- Manual publishes: `f58cf3e` 11:06 (cb60cef), `4e5ba2a` 11:14 (6a0241d all-workflows totals),
  `9f34f2c` 11:25 (404dabf mobile grid fix) — anonymous verify ok on every page each time.
- Real unattended publish: `066c7ea` generated 11:50:31 by the hourly cron (6889214
  held-attempt label fix).
- Live readback: headline "19 datasets shipped · 19 fully verified · all workflows"
  (5 modern + 14 earlier), 27 release records including all 5 modern datasets, mobile
  `.grid > * {min-width:0}` present in style.css, history.json 500 points (appended,
  published_scope=all_workflows).
- Budget-held attempts now label as "Stage discover/evaluate: <cap reason>" instead of
  "Running" (verified in the live 11:50 dashboard.json).

## Cron and provider readback

- scout-dashboard-refresh `4d8053a69ed2`: last run 11:51:58Z ok (the run described above),
  next 12:50:00Z. Tick `07d6f8be3783` every minute ok (11:53:02Z). Cleanup `e80975eddd4a` ok
  (11:50:01Z). Release-notify ok. Legacy launchers paused. Dec-1 allowance reset scheduled.
- Provider: 0 live servers (no-op). Details: `cron-provider-readback.json`.

## Files

- `deployment-runtime.json` — SHA chain, CI run IDs, shim hash, preserved-file readback.
- `site-sync-final-status.json` — final `.factory/sites/status.json` (all 5 complete).
- `per-release-receipts.json` — per-release: site_revision, record_sha256, artifact_version,
  dataset/catalogue commits, dispatches, live URLs, HTTPS enforcement.
- `tag-asset-identities.json` — after-state identities per release; before-state reference:
  tracked `audits/sites-integration/pre-rollout-identities.json` (root-verified unchanged).
- `dashboard-readback.json` — publish commits, verify results, live headline/CSS readback.
- `cron-provider-readback.json` — hourly/tick/cleanup/cleanup timestamps, provider no-op.

No candidate state writes, no extra data builds, no model tasks, no scheduler changes.
