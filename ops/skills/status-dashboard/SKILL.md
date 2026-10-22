---
name: status-dashboard
description: "Build a generated, published status/ops dashboard."
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [dashboard, static-site, github-pages, visualization, mobile-first, observability, reporting]
    category: software-development
    related_skills: [claude-design, post-push-verification, scheduled-job-verification]
---

# Generated status dashboard

Build the thing the operator checks instead of asking. A dashboard in this class is not a designed
mockup and not a live console: it is a **generated artifact** whose every number is read from the
system's own records, published on a schedule, and verified to be publicly live.

## When to use

- The user says some variant of "I shouldn't have to message you for status" / wants executive and
  operational views.
- A pipeline, worker fleet, or scheduled-job system has enough state that prose updates are lossy.
- An existing dashboard is being redesigned for mobile, legibility, or trust.
- The operator asks "what have we spent / what is still running" — that is a Resources page, not a
  chat answer, and the ledger usually already exists in the job records.

Do not use for a one-off visual concept (that is `claude-design`) or for a single metric page.

## Architecture: generator, not server

1. **Split collection from rendering.** `scripts/build-<thing>.py` collects a single JSON snapshot
   (with provenance per figure); `factory/<thing>_render.py` turns it into HTML. The renderer must
   never read the filesystem or the network — everything it shows is already in the snapshot. This
   is what makes the snapshot testable, diffable and replayable.
2. **Publish to its own static site.** If the machine has no inbound ports, the dashboard is static
   HTML on GitHub Pages, refreshed by a scheduled script. Say so plainly: it is a pull dashboard
   with an `as of` stamp, not a live console.
3. **Never inject pages into a site repo whose deploy is a reviewed workflow.** If the catalog site
   builds `_site` from a watched directory and deploys only on that path, adding `dashboard/` either
   bypasses the review or teaches the reviewed builder about a directory it does not own. Create a
   dedicated Pages repo instead: create it via API, push the root, enable Pages
   (`POST /repos/{owner}/{repo}/pages` with `{"source":{"branch":"main","path":"/"}}`).
4. **Schedule the whole loop, not just the build.** One script does build → publish → anonymous
   read-back, exits non-zero on any failure, and keeps output local unless it is an exception.
   Schedule it offset from the data-producing job (e.g. `50 * * * *` when collection runs on the
   hour) so one build reflects a finished cycle.

## Procedure

1. **Inventory what is real before designing anything.** List the files/APIs that hold the truth
   (`candidates/*/record.json`, `release/*/MANIFEST.json`, scheduler `jobs.json`, a budget script's
   `--json`, CI API). For each panel, name the source path. If a panel has no source it does not
   ship — write "no data" and plan to instrument it, never estimate.
2. **Define the snapshot schema** with `schema`, `generated_at`, and per-section provenance. Every
   derived figure is computed in code, not in the template.
3. **Reuse the canonical metric script.** When another script already owns a definition (coverage,
   budget, gate status), call it (`--json`) and consume its numbers. Recomputing "the same" metric in
   the dashboard silently creates two definitions that disagree in front of the user.
4. **Render three or four pages, not fifteen.** Executive (is it healthy, what shipped, what is
   queued), Cost (utilisation against every ceiling), Resources (paid infrastructure: what is
   billable now and what it has cost), Ops (gates, last-run status, next run, repo head). Detail
   lives in the JSON, not crammed into the UI. Add a page when the operator has a question the
   existing pages cannot answer; four is still a dashboard, eight is a wiki.
5. **Publish and verify in the same run.** A publish that does not appear publicly is a failure, not
   a success. Poll **every page**, not just the index, with a cache-busting query for a marker unique
   to this build (timestamp) plus a structural marker, allowing ~2 minutes for the Pages build. A new
   page can 404 behind a healthy index, so index-only verification reports success for a dashboard
   that is missing a tab.
6. **Report the URL, not a description of the URL.** Then let the schedule do the talking.

## Honesty rules (these are the product)

- **Missing input is "no data", never `0`.** Zero is a fact about an empty list; absent is a fact
  about an unread file. Render them differently, and give the path you looked for.
- **A figure stated in prose is still a figure.** Records often carry a measurement as a sentence in
  a notes/measurements block ("persistence: train 0.897 / eval 0.893") rather than as a numeric
  field. A renderer keyed only on structured keys prints "no data" for a value the record contains,
  and that is the most damaging kind of blank: it hid a model sitting *below* its own reference.
  Extract with a narrow pattern when the structured key is absent, print the number, and when the
  measured value is worse than its reference say so on the card ("persistence — the model is BELOW
  it") instead of leaving two numbers for the reader to compare.
- **Unmeasured is not failing.** A gate that was not run renders "not run" (neutral), not "fail".
  A dashboard that cries failure because it skipped a check trains the operator to ignore it.
- **No fabricated history.** Start the series when the feature ships and label a one-point sparkline
  "series begins today". Back-filling a trend is the most convincing possible lie.
- **Stale is louder than healthy.** Any panel whose data exceeds its freshness SLA is greyed and
  labelled; the page banner says which panels are stale.
- **Secrets never render.** Before writing files, scan the output for every credential file's value
  and abort the whole build on a hit. Publish only the budget/ceiling figures the page displays, not
  the whole config block.
- **The repo is the record; the dashboard renders it.** When they disagree, the dashboard is wrong.
  The same holds for prose: before telling the operator an item is "ready", read its record and name
  the status and what is still missing. Recalling the plan instead of the record turns "qualified,
  no package yet" into "ready for you" and the operator catches it - a status sentence is a claim
  about a file, so quote the file.
- **Public URL, unlisted.** Pages cannot enforce auth. Add `noindex,nofollow` and a `robots.txt`
  disallow, and state plainly which internal facts (candidate names, next actions) are visible.

## Mobile-first layout rules

- One column to ~560px, two to 900px, 12-column grid above. `clamp()` for display type; never a
  fixed 48px hero.
- Fixed bottom tab bar with 3–4 items under 900px (thumb reach), with a non-colour active indicator
  (bar/dot), not colour alone; top nav above. Four tabs still fit 390pt; a fifth does not.
- `viewport-fit=cover` + `env(safe-area-inset-bottom)` padding.
- **Tables become cards below 640px.** Render both markups and switch with CSS; a six-column table
  cannot be read at 390pt, and horizontal scrolling is not a design.
- Tap targets ≥44px; muted text still has to clear ~4.5:1 on the dark surface.
- The headline states a fact ("4 datasets shipped"), not a mood ("Attention needed" at 52px).
  Reserve prominence for things that need an action; a running job is a notice, not an alarm.

## Charts

Inline SVG, no library, no network, no script — the artifact must survive being emailed or archived.
See `references/charts.md` for copy-paste primitives (sparkline with honesty fallback, semicircular
gauge, donut + legend, funnel bars, bar list) and the sizing rules.

- **Long-tailed money or duration data needs buckets that widen with the value** (1-2-5 steps, not
  equal width), or 90% of the bars sit in the first slot and the distribution reads as "nothing
  happened". Label only the first, middle and last edges, format them compactly (`€0.05`, not
  `€0.050000`), and assert in a test that the bucket counts sum to the population.

## Cost and resource panels (paid infrastructure)

- **Live inventory comes from the provider API**, not from your own bookkeeping: count what is
  billable right now and show the account-wide totals beside it. An orphaned server or IP after a
  job ends is the exact failure this panel exists to catch, and internal records cannot see it.
- **Cost = recorded lifetime × the rate recorded at launch** (`deleted_at - created_at`,
  `provider_hourly_eur`), the same arithmetic as the launcher's monthly reservation guard. Reusing
  the formula is what stops the page and the budget guard disagreeing in front of the operator; label
  it a cost ledger, not an invoice.
- Show **month-to-date against the ceiling**, a linear projection to month end, jobs and server-hours,
  and unit economics (spend ÷ artifacts published). A job with no end time is "no data", not zero.
- **A scope card is compulsory**: list what the total excludes (free egress, IPv6, volumes, resources
  created outside the pipeline). An unstated exclusion makes the number wrong rather than partial.
- **A failed inventory read renders "no data"**, never `0` — a provider outage must not look like
  "nothing is running, nothing was spent".
- **Normalise cost by rate, not by duration.** For a distribution across mixed server types, price
  every job's lifetime at one reference rate (the modal rate actually paid) and print that rate on
  the card. Dividing cost by duration collapses the chart onto the three server prices and shows
  nothing; the reference rate is what makes a c2-large job and a small job share an axis. Assert in a
  test that the histogram's buckets sum to the job count.
- **The resource page usually needs no new instrumentation.** Job records written by the launcher
  already carry `created_at`, `deleted_at` and the hourly rate; look there before declaring spend
  "not recorded" and shipping a `no data` panel.

## Detail pages: a status is not a dataset

An executive page answers "is it healthy"; it never answers "what *is* this thing". Once more than
a handful of entities are in flight, add **one page per entity** (artifact, candidate, service) and
link it from every row that names the entity - work queue, release table, alerts. A drilldown nobody
can reach is a dead page.

Each page, in this order: the question the artifact exists to answer, what is predicted, the
information cut-off, where the data comes from with its stated licence, how it is split (rows and
positive rate), the measured baseline against its reference, the licence posture, the job history,
and what unblocks it. Facts, not prose: fill from the record, and say "not recorded" where the field
is absent.

- **Resolve each fact through a fallback chain, and know which source answered.** A live entity keeps
  its measurements in its record; a published one usually keeps them in its release manifest, and its
  licence in a separate descriptor. Reading only the record renders "splits not recorded" on a shipped
  artifact - every fact exists, and the page still looks broken. Read record -> per-artifact
  descriptor -> release manifest, and label a value that came from the manifest as representative
  (one config) rather than implying it covers the whole artifact.
- **Do not restate a truncated field in the hero.** If the full text appears in a card immediately
  below, cut the hero line instead of printing the first N characters with an ellipsis: a sentence
  that stops mid-clause reads as a rendering bug, and the reader has already been given the real one.
- **Verification has to enumerate the dynamic pages too.** Build the poll list from the data (every
  live entity) rather than a literal tuple of filenames, or the index and tabs pass while every
  drilldown 404s - the same failure as index-only verification, one level deeper. Detail pages for
  terminal entities (dropped, parked) can exist without being polled.
- **Test the fallbacks, not only the happy path.** A fixture whose record has an empty measurement
  block must render the manifest value; one with neither must say "not recorded"; a packaged entity
  must say it is waiting on the operator rather than just printing its stage enum.
- **Every surface that names an entity links to it, and a test asserts the href.** Queues and tables
  get wired first; the secondary card (work that waits on a human, alerts, a "ready to ship" list)
  is the one that ships as plain `<div>` text and gets reported as "that link doesn't work". Enumerate
  the surfaces deliberately - queue, releases, ready-to-ship, alarms - and assert
  `href="<entity-page>"` in a test, because a missing anchor is invisible to every static check.

## Surfacing work that waits on a human

A pipeline with a human-in-the-loop step (a private-to-public flip, an approval, a licence decision)
needs that queue rendered explicitly, split into **actionable now** and **waiting on you**. Both
carry an age. Without the split a row reading "packaged" does not say whether the machine is working
it or the ball is in the operator's court, and the one chat message the routine is allowed to send
should be exactly that request. Name the state in the operator's language ("awaiting flip"), not the
ledger's, and state what happens next so the page answers "what do I do" without a conversation.

## Render the scheduler's outcome, not just its status

A job record's `last_status: ok` says the script exited, not that the run did anything. When a routine
writes its own run ledger (outcome, elapsed, turns, tokens), render it: the Ops page shows the last
handful of runs with their outcome, and the executive page alarms when the most recent ones were
**killed at the wall clock** rather than completed. That signal exists nowhere downstream — the
records a killed session did not write cannot report their own absence — so the dashboard is the
only place it can surface, and it is how a routine that looks green for hours gets caught.

- Distinguish `killed` (ran out of time, produced no report) from `skipped`/held (gated before work
  started). They need different responses: a kill is a budget or scope defect, a hold is the gate
  doing its job.
- **A non-zero exit is also a failed run.** A provider that stops answering mid-stream, a crash, or a
  wrapper abort produces `exit N`, not `killed`; both mean the tick was paid for and delivered
  nothing. Count them together in the alarm, or a provider outage reads as a slow but healthy job.
- **Before calling a killed run wasted, check what it wrote.** Files survive a kill; only the final
  summary is lost. A `find -newermt` over the records it was meant to touch turns "three hours lost"
  into the accurate "three verdicts written, three reports missing".
- Show the same numbers the operator would ask for — start time, duration, turns — so "it died" is a
  measurement rather than an impression.

## Verifying the design, not just the HTML

Static checks do not see truncation, clipping or bad hierarchy. Render and look:

```bash
chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=390,1400 --screenshot=/tmp/m.png <url>
```

One capture per fresh session; then ask a vision model for **concrete defects only** (truncation,
clipping, contrast, alignment), fix them, re-render. See `references/visual-qa.md` for the loop and
the defect checklist. Budget two rounds: the first finds real bugs (labels truncating, a gauge
clipping its card), the second confirms.

## Pitfalls

- **GitHub Pages serves the previous build for a minute or two.** A plain `curl` right after the push
  returns the old page with HTTP 200, which reads as "publish succeeded but content is old". Poll with
  `?ts=<epoch>` and verify a marker from *this* build; do not conclude the push failed.
- **A Pages build can sit in `building` for many minutes, and that is upstream, not yours.** Before
  re-pushing or editing the generator, read the build status: `GET /repos/{owner}/{repo}/pages/builds/latest`
  returns `status` and the `commit` it is building. If the commit is your publish and the status is
  `building`/`queued`, the content is correct and the only action is waiting (or `POST /pages/builds`
  to enqueue another). Re-pushing to "fix" it adds snapshots nobody needs and hides the real cause.
- **A cached 200 looks like a live page.** A stale CDN entry can return the GitHub 404 page at 200;
  always cache-bust before judging.
- **Computing a headline metric twice.** A dashboard "non-US share" disagreed with the canonical
  coverage script because one counted live-by-work-queue and the other live-by-not-parked. Import or
  invoke the owning script; never re-derive.
- **One logical field, several physical shapes.** Row totals and baseline AUCs are written by
  different builders: `{"train": {"rows": n}}`, the same nested under a level
  (`{"temporal": {"train": {"rows": n}}}`), a map of file *paths* with the counts in a sibling
  `summary.json`, and a baseline whose single figure sits in `result.*` rather than `levels.*`. A
  collector written against one shape prints "no data" for datasets that are published and fine —
  the most damaging kind of blank, because it reads as a pipeline failure. Sum recursively through
  the nesting, fall back to the sibling file, and pin all four shapes in tests (including one where
  the count genuinely does not exist, which must still render "no data").

  The baseline figure has the same problem with more aliases: one corpus stores it as `eval_auc`,
  `train_py_eval_auc`, `auc_from_train_py`, `auc_eval_runner_measured` and
  `eval_auc_from_train_py`, sometimes as a *string*. Coerce before comparing, accept a value only
  inside (0, 1), and when the manifest predates the number read the producer's own baseline result
  beside the release instead of printing a dash - the figure exists, it is simply in the older of
  the two files. A normaliser that returns the value *and* its scope also stops a suite median
  from being rendered as one model's score.
- **A suite has no single score, so label the statistic you print.** When a release is N configs,
  the honest headline is the median with its scope ("median of 40 configs"), not a bare 0.72 that a
  reader takes as one classifier's AUC. Carry a scope string beside the value and render it next to
  the number; a comparator that silently takes `max()` across levels invents a better score than
  any config achieved.
- **Reset per-entity fallback values at the top of the loop.** A scope or label computed inside a
  fallback branch and read after the loop keeps the previous entity's value when this entity did
  not enter that branch — one release's "median of 40 configs" then annotates an unrelated
  single-model release. Initialise every conditional field where the entity's record begins.
- **Destination pills are facts about an evidence file, not about the service.** The page reads
  `DESTINATIONS.json`, so a site that is live but was never recorded there renders as absent - the
  dashboard is right and the record is incomplete. Record a destination in the release's own status
  file when its publish step succeeds (a receipt is not that file), and backfill the ones that
  already exist by measuring them, not by assuming.
- **A long-running job is not an alarm.** A budget gate refusing because a lock is held is normal
  operation; classify lock-only refusals as a notice, or every hourly tick paints the dashboard red.
- **History that grows on every rebuild.** Append one point per interval (e.g. ≥20 min apart, capped
  at N), or a 40-minute deploy loop produces a plot of your own refresh rate.
- **Emulated device metrics can wedge a screenshot pipeline.** If captures start timing out after
  `Emulation.setDeviceMetricsOverride`, use a fresh session or render with headless Chromium at a
  fixed `--window-size`; the fixed-width render is deterministic and needs no emulation.
- **Scripted string replacement of a renderer silently no-ops.** Editing generated HTML code with
  `text.replace(old, new)` that prints "patched" proves nothing: an anchor that no longer matches
  leaves the old behaviour in place and the build still succeeds. Assert each anchor is present
  before writing, then grep the rendered output for the new marker (a currency symbol, a class name)
  — a bar chart with unformatted numbers and a `money=True` signature that never changed is the
  normal shape of this bug.
- **UI strings are not status codes.** Map ledger enums to operator language before rendering
  (`deleted` → "destroyed", `succeeded` → nothing at all). A raw enum on screen reads as an error
  state to anyone who did not write the schema.
- **A bar drawn from inline spans has no height.** `<span class="track"><span class="fill"
  style="width:40%"></span></span>` renders an invisible bar because `height:100%` does not apply to
  an inline element; the markup and the numbers are correct, so only looking at the page catches it.
  Set `display:block` on both the track and the fill (or use divs) and re-render before believing a
  chart works.
- **A scheduled run can die at the scheduler's ceiling, not its own budget.** Script-only cron jobs default to `cron.script_timeout_seconds: 3600`, so a wrapper told to run a 90-minute session is killed at 60 with no report — and the kill looks like a provider or code failure until you read the wrapper's own ledger. Size the whole wrapper (session budget + grace) inside the scheduler ceiling, or raise the ceiling in config and confirm the loader re-reads it (config is cached on file signature).
- **Donut charts without a legend are decoration.** Ship counts and shares beside the ring, and give
  the "other" segment a visible colour rather than the surface colour.
