# Factory sites integration: acceptance record

Status: **implemented, deployed and verified on 2026-11-11.**
Implementation commit: `68892143c1a684fb92fda9ff7114a38580c06855`.
[Exact-commit CI passed](https://github.com/earino/dataset-factory/actions/runs/43012087411).
Scout deployed this code at 11:31:05 UTC. The existing hourly job ran at 11:50 UTC,
finished successfully at 11:51:58 UTC, and is next due at 12:50 UTC. No new
scheduler or worker launcher was added. The initial deployment bootstrap and the
later unattended timer execution are recorded separately below.

## S1 — Existing design

Desktop and mobile inspections cover the catalogue, a dataset page and dashboard.
The existing fonts, colours, navigation, cards and layout remain. Two concrete
content/sizing defects were fixed: long baseline labels squeezed the dataset
table, and a dashboard grid child caused horizontal overflow at 390 pixels.
The dashboard sizing guard leaves desktop pixels identical and removes mobile
page overflow. A fresh live navigation, without injected styles, confirmed the
guard and a 390-pixel document width.

Evidence: [dataset inspection](../audits/sites-integration/visual/dataset-check.json),
[dashboard/catalogue inspection](../audits/sites-integration/visual/dashboard-catalogue-check.json),
[live mobile check](../audits/sites-integration/visual/dashboard-live-mobile-check.json).
The earlier [stylesheet comparison](../audits/sites-integration/style-preservation-check.json)
predates the one-line dashboard sizing guard; it does not claim that final CSS is byte-identical.

## S2 — Operational facts

The deployed dashboard reads modern stages and publication receipts, retains
labelled legacy releases, and uses effective local controller/worker settings.
Normal-operation token and weighted-session counters govern the cost display;
development tokens are identified separately. Provider reservations are not invoices.
Absent/corrupt database tests report unavailable rather than zero. A held open
attempt now has neutral stage wording with its recorded reason and retry time.

Evidence: [final anonymous dashboard check](../audits/sites-integration/dashboard-final-check.json),
`tests/test_dashboard_modern.py`, `tests/test_site_state.py`.
The hourly snapshot identifies deployed code `6889214`, current configuration,
37 modern candidate records, the actual weighted-session hold, and neutral stage
labels for held attempts. [Hosted runtime and preservation readback](../audits/sites-inventory/2026-11-11/deployment/deployment-runtime.json)
and [scheduler/provider readback](../audits/sites-inventory/2026-11-11/deployment/cron-provider-readback.json)
agree with the public observations. Historical chart points remain saved
observations; missing modern coverage was added at integration rather than
inventing historical measurements or rewriting the history file.

## S3 — Releases and history visible

All five modern datasets have public dataset pages and catalogue entries. The
catalogue retains its 14 earlier release records; the dashboard all-time headline
is 19 distinct shipped datasets. Short dataset names are separate from prediction
questions. Historical records and saved history points were retained; the all-time
publication chart includes earlier history while the active queue remains modern.

Evidence: [five version records](../audits/sites-integration/dataset-live-record-check.json),
[live short names and all-time headline](../audits/sites-integration/names-history-live-check.json),
[historical record preservation](../audits/sites-integration/release-preservation-check.json).

## S4 — Public facts match accepted releases

All five real releases were projected and rendered from compact pinned public
metadata, checked against matching anonymous publication receipts. Baseline JSON
must match its manifest hash before display. Asset names, nested Hub paths,
versions, split counts, source terms and citations come from accepted evidence.
Loading links use the actual repository/revision and the released default Hub
configuration. No data rows or new baseline runs were needed for website verification.

Evidence: [real-release previews](../audits/sites-integration/real-release-previews.json),
[final anonymous fact checks](../audits/sites-integration/public-facts-final-check.json),
`tests/test_site_modern.py`, and the preserved
[original publication receipts](../audits/sites-inventory/2026-11-11/publication-receipts.json).
All five current edition-2 records match pinned manifests, measured baseline
results, accepted task summaries and limitations. Their version-page links and
loading recipes match the released interface. [Current provider readback](../audits/sites-integration/https-final-check.json)
also confirms HTTPS enforcement on all six managed sites; older saved receipts
retain their original certificate-deferral observations.

## S5 — Automatic operation

The normal reconciliation code detected and deployed the five missing modern
release records without editorial JSON files or candidate-state changes. Scout
invoked the initial pass during deployment. The installed hourly shim invokes
the same CLI and public metadata path, using existing publishing credentials.

The real 11:50 UTC scheduled run invoked the installed shim, verified all five
complete website records, published the new dashboard and finished with status
`ok` at 11:51:58 UTC. The next execution is 12:50 UTC. Initial bootstrap was a
deployment invocation of the normal reconciler, not per-dataset preparation;
the later timer run establishes unattended execution of that same path.

Evidence: [hosted cron outcome](../audits/sites-inventory/2026-11-11/deployment/cron-provider-readback.json),
[independent scheduled-window readback](../audits/sites-integration/scheduled-window-public-observation.json),
[five deployment receipts](../audits/sites-inventory/2026-11-11/deployment/per-release-receipts.json).

## S6 — Recovery and no duplication

The initial real deployments returned pending while Actions built the pages;
later passes resumed saved bundles. The discovered shared-README retry loop was
fixed and reproduced in a two-release regression test. Scout reports all five
short-name bundles complete and a no-op pass at 11:26:44 UTC with no commits or
dispatches. Failure-isolation and missing-metadata tests preserve other records
and do not mutate candidate state.

Evidence: [retry defect](../audits/sites-integration/catalogue-retry-defect.json),
`tests/test_sites.py`, `tests/test_site_sync.py`.
The [hosted receipts](../audits/sites-inventory/2026-11-11/deployment/per-release-receipts.json)
record complete status, exact bundle identities, single dispatch attempts and
verified live records. The real hourly pass was another verify-only no-op.
An independent [provider comparison](../audits/sites-integration/noop-after-scheduled-window.json)
against the [11:30 baseline](../audits/sites-integration/noop-before.json) found no
new commits or workflow runs across all five dataset sites and the catalogue.
The dashboard's expected timestamp commit is separate from website no-op checks.

## S7 — Frozen releases and production boundaries

Both platforms' five version tags still resolve to the original publication
commits. GitHub asset inventories and all 14 earlier catalogue record blobs are
unchanged. Website editions and current navigation are separate from frozen
manifests and assets. Public projections select display fields instead of copying
candidate payloads or SDK diagnostics. Scout remains the sole worker coordinator.

Evidence: [final frozen-release comparison](../audits/sites-integration/release-preservation-final-check.json),
[legacy record preservation](../audits/sites-integration/release-preservation-check.json),
`tests/test_site_state.py`, `tests/test_site_modern.py`.
The hosted readback confirms the minute controller and cleanup remain enabled,
superseded launchers remain paused, and no live provider workers remained at
capture. Limits and private configuration were preserved.

## S8 — Observed sign-off

Live destinations are the [dashboard](https://earino.github.io/dataset-factory-dashboard/),
[catalogue](https://earino.github.io/dataset-factory-site/), and each catalogue-linked
dataset version page. Code and focused suite changes have passed clean-checkout
verification and exact-commit CI. Scout's evidence is preserved from commit
`a6f1c23` ([its CI passed](https://github.com/earino/dataset-factory/actions/runs/43015832628)),
including the [deployment record](../audits/sites-inventory/2026-11-11/deployment/note.md).
Root independently checked public facts, the scheduled-window snapshot, unchanged
provider heads/workflow counts, and frozen releases. All evidence above was read
before this sign-off; code, mocks and CI alone were not used as completion proof.

Routine operation now uses the existing hourly script. It requires no routine
human review, editorial file, model turn or separate worker coordinator. Stop
implementation here; further product changes require a separate scope decision.
