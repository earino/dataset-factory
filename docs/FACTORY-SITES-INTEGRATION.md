# Connect the modern factory to the existing sites

Status: **proposed specification for discussion; implementation has not started.**
Written 2026-11-11 against factory commit `2bf708a`.

## Outcome

Keep the sites' current design. Connect them to the factory that now runs.
The dashboard must explain what is running, what has shipped, and what is waiting.
The public catalogue and dataset pages must describe the actual published benchmarks
and give readers working links to the correct versions on GitHub and Hugging Face.
Once connected, ordinary factory operation must keep these pages current without
a person preparing a second set of dataset records or approving each website.

This is an integration of existing code, not another factory rewrite. It extends
the deployed outcome in [FACTORY-REWRITE.md](FACTORY-REWRITE.md). It does not change
benchmark acceptance, model selection, worker ownership, or spending policy.
Approval of implementation is a later discussion; this document itself deploys nothing.

## The gap we are closing

The November 11 inspection found five modern public benchmarks missing from both
the dashboard and the catalogue. The dashboard had refreshed that morning, but
its candidate and release collectors still read `candidates/*/record.json` and
`release/*/MANIFEST.json`. The catalogue's last observed update was November 3.
A fresh page timestamp therefore did not mean fresh dataset coverage.

The modern factory stores candidate and attempt state in
`.factory/pipeline.sqlite3`. Successful publication adds a receipt to the candidate's
`data.publication`, with the artifact identity, version, destinations and anonymous
consumer results. Its public manifest uses the `factory-1` schema. The website
projector expects the legacy package schema, a `DESTINATIONS.json`, and a manually
prepared `sites/<dataset>.json`. These are the two specific integration gaps.

The dashboard also mixes development usage into a normal-operation token display.
At the November 11 readback, normal usage was about 35.37M tokens against a 40M
ceiling, while the page showed about 45.80M. The actual admission reason was the
weighted session cap. The integration must display the decision the factory uses,
not derive a different decision from a broader usage total. These observations
are a dated starting point, not values to hard-code.

## Scope and design boundary

The existing surfaces remain:

- [Factory dashboard](https://earino.github.io/dataset-factory-dashboard/), including
  its overview, cost, resources, reliability and candidate detail pages.
- [Public catalogue](https://earino.github.io/dataset-factory-site/).
- Dataset Pages sites in the existing public dataset repositories, including their
  version archives and existing GitHub/Hugging Face navigation.

Keep typography, colours, spacing, card styles, charts, layout, navigation and
responsive behaviour. Keep existing public URLs. Populate the existing components
with correct records. Change text, labels, counts, links and status values where
needed to state the facts. Do not add a new page family or visual system. A field
that cannot fit the existing views should first use their existing detail page or
status text; any actual design change returns to discussion.

Excluded: a new web framework, CMS, API server, database, scheduler, agent, worker
launcher, benchmark validation campaign, billing integration, search redesign,
new analytics programme, and the unbuilt P1/P2 dashboard features in
[DASHBOARD.md](DASHBOARD.md). No new datasets need to be built to complete this work.

## One source for each fact

The sites consume existing evidence through small adapters. Generated site records
are derived output, not another editable candidate or release ledger.

- **Modern progress:** read candidates and attempts from a consistent, read-only
  SQLite snapshot. Read active stage, attempt status, timestamps, retry time and
  recorded reason. Do not construct `Store` merely to display data: its constructor
  creates the database. A missing database means unavailable, not an empty factory.
- **Published identity and files:** use the accepted `factory-1` manifest and the
  matching successful publication receipt. Use the receipt's repositories and
  version; do not infer destinations from candidate names. Fetch missing compact
  public metadata from the pinned release and check its manifest digest.
- **Task and measured results:** use the accepted task description, manifest,
  `evaluation.json`, and other compact files bound to that manifest. The website
  must not independently reinterpret the task or quote a different build's score.
- **Runtime and resources:** use effective deployed configuration, controller and
  cleanup observations, job records, and the existing provider inventory. The
  checked-in `pipeline.enabled: false` default is not evidence that the deployed
  factory is disabled.
- **Admission and usage:** use the existing budget decision and its accounting
  windows. Separate normal operation from development. Label worker reservations
  as reservations, and estimates as estimates. Do not call either actual billed
  spend. Display all actual admission reasons without inventing another gate.
- **Legacy history:** retain the existing candidate, release and site records.
  Label the old workflow and its hold separately. Its queue does not describe or
  block the replacement controller. Preserve existing limitations and withdrawal
  notices; this integration does not approve or rehabilitate legacy artifacts.

Every displayed observation needs a source and observation time in the generated
snapshot. Reuse the current freshness presentation. A render time is distinct
from the time its input was last checked. Missing or stale evidence must not turn
into a green status, zero count, or deletion of an existing catalogue entry.

## Dashboard behaviour

The main operational view describes the modern factory. Existing historical data
remains available with clear legacy labels; it does not inflate the active queue.
Dataset totals count distinct dataset identities. Version history counts releases.
Where both formats refer to the same identity and version, show one release and
retain both evidence references. Do not merge datasets just because titles match.

Use the actual modern stages: discovery, build, evaluation, publication, published,
deferred and rejected. Distinguish a stage from active execution: a candidate in
`build` can be waiting for capacity or retry time rather than running a worker.
Show the latest relevant failure and next action or retry time when recorded.
Do not guess a completion time or describe every wait as a failure.

Show data publication and website synchronization as separate facts. A dataset
can be public and consumer-verified while its website is pending. A failed website
deployment must not make the dashboard report that the dataset failed to publish.
Conversely, a successful Pages deployment is not evidence of data verification.

Reuse existing health collectors, but identify which check ran, on which commit,
and when. Distinguish local checks, CI, controller health and release verification.
A stale or legacy check must not become an unexplained statement that the current
factory is broken. Keep the actual failure visible with its scope.

The hourly dashboard refresh remains deterministic. Successful refreshes include
the modern snapshot and website status. An unavailable input is shown as such;
the previous good output remains identifiable. The public `dashboard.json` and
detail pages receive explicit selected fields, never a dump of candidate `data`,
model prompts, private source samples, credentials or raw worker diagnostics.

## Catalogue and dataset page content

Add a modern-input adapter alongside the legacy adapter in `factory/site_model.py`.
Both supply the existing renderer's record contract. Adapt the schema-aware checks
in the existing publication code where necessary; do not forge a legacy package,
dummy suitability approval or `DESTINATIONS.json` to satisfy the old interface.

For a modern benchmark, the record contains:

- Dataset identity, artifact digest, version, recorded publication date and actual
  destination URLs. The website deployment date is not the dataset release date.
- Title and prediction question; population, target, prediction setting and split
  description from the accepted task. State retrospective assumptions where present.
- Split counts, file names, byte sizes, hashes and working version-specific download
  links. Preserve the actual nested Hub paths and GitHub release asset names.
- Baseline measurements and their evaluation scope. Public validation is not final
  holdout performance. Do not add a headroom figure or a forecasting claim that the
  release does not establish.
- Source references, distribution terms, attribution, compilation-rights scope,
  reproduction/loading instructions and the accepted limitations.

Generate the existing summary and release-post fields with deterministic templates
from that accepted material. A human-authored `sites/<dataset>.json` must not be a
prerequisite for modern releases. No routine model call is needed to write website
copy. Missing optional prose gets a factual template or an explicit omission;
missing identity, rights or verification evidence leaves that site update pending
with a precise reason. Do not invent values to fill a card.

Use the existing `sites/runtime.py` renderer and `sites/pages.yml` workflow. Keep
the catalogue's current ordering rule and presentation. Preserve all earlier
records, version URLs and editorial editions. A later website correction increments
`site_revision`; it does not change the dataset version or frozen release bytes.

## Automatic synchronization

Use the existing scheduled dashboard entry point to run one bounded site
reconciliation pass after it reads current factory state. This provides catch-up
without a new scheduler and keeps website work out of the minute worker-launching
controller. Process releases sequentially within a pass; retain the existing
per-bundle publication lock and fast-forward conflict checks. Scout remains the
only worker-launching coordinator; this integration launches no data workers.

Each pass:

1. Finds modern published releases whose successful receipt matches their artifact
   and both anonymous consumer results. Compares them with existing site receipts.
2. Prepares a stable bundle for each missing or changed website edition, using
   compact metadata only. Reuses the same bundle and digest on a retry.
3. Uses the existing inspect/publish/verify operations to publish the dataset page,
   verify it anonymously, then merge its record into the catalogue and verify that
   deployment. Preserve other catalogue records and unrelated repository files.
4. Saves the outcome in the existing `.factory/sites/` bundle and receipt mechanism.
   Exposes pending, failed or verified status in the dashboard. Does not mutate
   candidate stage or rewrite the publication receipt.

Bound each pass and network operation. Pending Actions runs resume on a later
refresh; do not hold the dashboard refresh open waiting for all deployments.
Process other eligible releases when one has an error. Reuse existing retry and
receipt mechanisms; add only the small state needed to schedule a later attempt.
No-op passes must not create commits, editions or deployment runs.

Target freshness is the next hourly reconciliation after a verified data release,
plus the provider's deployment time. Pending/failure status appears in that refresh.
Completion requires the expected live record and HTML links, not merely a push or
an Actions dispatch. This is a scheduling target, not a guarantee of provider uptime.

Under the proposed integration policy, an already accepted, public and verified
modern release authorizes its derived website automatically. Retain the prepared
bundle digest as an integrity check, but replace the per-dataset human approval
requirement for this path with the standing policy. Do not pass a flag that falsely
claims an operator reviewed the bundle. Legacy private releases remain private.

## Frozen releases and current navigation

The modern manifest differs from the legacy format in material ways: `version`
instead of `release_tag`, `rows` instead of the legacy split structure, and explicit
asset paths rather than an assumed `data/<filename>` layout. Its README and measured
evidence are also hashed assets. The adapter must handle these differences directly.

Never update a modern manifest's hashes merely to add website links. Keep tagged
manifests, data, release assets and other frozen package files unchanged. Add managed
website files separately. Current default-branch README/Hub navigation may receive
the existing bounded editorial link block, but verification and reproduction must
continue to use the frozen version, not those editorial copies. Preserve YAML and
all text outside the managed navigation block.

The data publisher's `tag_matches_main` receipt describes the publication instant.
Website commits can later advance the default branch. Website verification must
check the frozen tag against the recorded data identity and separately check the
website deployment commit. It must not move a dataset tag to restore equality or
treat a known website-only branch advance as data corruption. Test that website
retries do not cause data publication to run again.

## Delivery and migration

Implement in three small steps, with progress recorded here or in an accompanying
implementation note once work is approved:

1. **Read and preview.** Add modern dashboard readers and the modern site adapter.
   Render local previews with the existing design. Compare facts against compact
   real publication evidence and preserve legacy rendering.
2. **Connect and recover.** Extend the existing site publisher for the modern
   schema and standing policy. Add bounded reconciliation to the existing refresh.
   Test duplicate passes, a pending deployment, a failed request and restart recovery.
3. **Deploy and catch up.** Coordinate the deployed change with Scout. Reconcile all
   then-published modern releases, verify live pages, and observe a later scheduled
   pass without intervention. Update `WEBSITE-SYSTEM.md` and `DASHBOARD.md` to document
   the actual inputs and policy, without importing their deferred feature plans.

The known initial backfill is `ucmr5-first-sample-pfas`,
`cfpb-bank-account-monetary-relief`, `nhtsa-pe-recall`,
`fdic-bank-branch-closure`, and `nih-r01-competing-renewal`. This is an acceptance
sample, not a hard-coded allowlist. Discover additional completed releases from
the deployed store at implementation time.

Commit and push completed changes, inspect CI for each exact pushed commit, and
verify suite changes in a clean checkout. If rollout fails, disable only the added
site reconciliation, preserve its receipts, and keep the last good public pages.
Do not stop discovery, data publication or cleanup to repair a website.

## Acceptance criteria

**S1 — Same design.** Before/after previews of the dashboard, catalogue and a dataset
page at desktop and mobile sizes retain the existing visual design and navigation.
Differences are the intended content, labels, links and data-driven chart values.

**S2 — Correct operational state.** A deployed snapshot agrees with the same-time
SQLite stages, running attempts, effective configuration and budget decision.
Modern and legacy totals are distinct. Missing-input tests report unavailable,
not zero or healthy. Normal/development usage and reservation/billing labels agree
with their sources; the actual admission reason is visible.

**S3 — Existing releases visible.** All modern public releases found during rollout,
including the five listed above, appear in the dashboard and live catalogue and
have usable dataset pages. Existing legacy entries and version URLs remain.
Public counts and deduplication agree with the underlying identities.

**S4 — Correct public facts.** Anonymous reads of each backfilled page and catalogue
record agree with its pinned manifest and measured evidence. GitHub/Hugging Face
links select the right repositories, versions and files. A loading example is
checked against the released interface. No new full dataset download or baseline
run is required merely to prove the website adapter works.

**S5 — Automatic operation.** At least one real, already-published modern release
absent from the sites is picked up and deployed by the scheduled reconciliation,
without manually writing an editorial file or advancing candidate state. Observe
a later unattended pass. This can be part of the backfill; it does not require a
new source or a new dataset build.

**S6 — Recovery and no duplication.** Demonstrate that a pending deployment or
recoverable request failure resumes with the same bundle. A second successful
pass makes no new content commit or deployment. A failed site does not stop the
dashboard or other site updates. Missing metadata cannot erase the catalogue.

**S7 — Releases preserved.** Before/after checks show unchanged dataset tags,
frozen manifest identities and release-asset metadata. Current editorial navigation
is separate. Public outputs contain only selected display fields. Existing data
publication and cleanup continue; no additional worker launcher is enabled.

**S8 — Evidence, not just code.** Final sign-off links the implementation commit,
its passing CI, the live URLs and observed deployment receipts, the scheduled-pass
result, and recovery evidence. A rendered preview or passing unit test alone does
not establish that the integration is complete.

Stop when S1–S8 are met. Improvements outside this scope require a separate decision.
