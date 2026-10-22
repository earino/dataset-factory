---
name: open-data-source-vetting
description: "Use when vetting public data sources for a task."
version: 1.2.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [open-data, datasets, reconnaissance, licensing, apis, prediction-tasks, leakage, evidence]
    category: research
    related_skills: [grounded-citations]
---

# Open data source vetting

## When to use

Any task that starts from "find a real-world dataset and do something with it":

- Discovery for a prediction-task, benchmark, or analysis project.
- Deciding whether a source has enough history, scale, or freshness to be worth building on.
- Deciding whether a source may be used in something that gets **published** (license and redistribution).

This skill covers choosing and proving out the source. Citing the finished write-up is
`grounded-citations`; building the task on a remote machine is the project's own tooling.

**When the construction is done and the files exist, stop and switch to
`dataset-qualification`.** That skill is the gate before any number from the built files
is reported: leakage, prediction timing, units and reference frames, temporal split
capacity, and the runner's input contract. Vetting a source well does not make the
artefact correct - a defect introduced at write time (a shipped label source, a
host-timezone assumption) is invisible from the source's metadata. Checklist and detail:
`references/artifact-qualification.md`.

Two rules belong to that handoff. **Run the gate where the rows are** - it reads the data, so a
bounded local sample cannot stand in for it; run it on the remote machine as part of the build
job, and have the build exit non-zero when the gate fails while still writing the report and its
diagnostics to the collected output, so a failure preserves evidence instead of losing it.
**Acceptance is by content hash**: a passing report is only good for the exact artifact version
it recorded, so re-verify the report and the file digests together before scoring or accepting
anything, and refuse a report that failed, is stale, or came from a different checker version.

## Discovery needs useful decisions and measured coverage

A recurring discovery slot can drift into other work or repeatedly investigate the easiest
sources. Separate its purpose and measure coverage; a fixed verdict quota can reward cheap
rejections. Prefer probes that resolve important uncertainty in a promising task.

- **Separate discovery from advancement.** One brief per mode, one job per mode, and a sentence in
discovery's brief that explicitly forbids building, qualifying, packaging or publishing any
existing candidate - naming the modes rather than saying "other work". Otherwise the tick spends
itself on whatever is nearest to finished, and the bench empties while every run looks green.
- **A quota on the number of sources still funnels to the cheapest source.** National APIs answer
anonymous in one call; a regional portal needs a catalogue search, a language you may not read, and
an untested licence. Unless the *distribution* is measured, every session lands on the same
handful of publishers and the count is satisfied without any new reach.
- **Record the publisher's jurisdiction as a required field.** `jurisdiction: {country, region,
publisher}` on every candidate record, enforced by the checker so it cannot be omitted. Geography
means the **publisher's** jurisdiction, not the subject matter: data about another country issued by
a domestic agency is a domestic source. A missing value is reported `unknown` and fails the check -
never inferred from a URL, a domain suffix or the language of the page.
- **Measure coverage with a script, and let it exit non-zero.** Count candidate records by country
and region, exclude non-sources (smoke tests, scratch records), print the share of *live* candidates
outside the home country, and fail on any unrecorded jurisdiction. A prose claim of
"international" is unverifiable; `live non-US: 0/6` is a finding that changes behaviour.
- **Rotate regions deterministically from the wall clock.** Order the regions so consecutive ticks
never share one, derive the index from the timestamp, and append the region and the portals that
serve it to the brief. Deterministic rather than random, so a delivered report can be reproduced
from its timestamp, and the rotation is inspectable.
- **Report the bench as numbers, including the gap.** State the distribution and what it moved
to after the change; an empty regional result is a recorded outcome, not a reason to backfill with
easy domestic sources.

Implementation - record shape, coverage report, backfill and guard-test order, and the region list:
`references/discovery-coverage.md`.

## Procedure

1. **Catalog API before the open web.** Socrata's cross-domain catalog answers "which portal
   has this, and under what license" in one call: `https://api.us.socrata.com/api/catalog/v1?q=<query>&limit=10`,
   add `&domains=<domain>` to restrict. Each result carries `resource.id`, `resource.name` and
   `metadata.license`. This surfaces datasets a plain web search never ranks, and it is the fastest
   way to compare several candidates.
2. **Metadata endpoint before the data.** Read the schema without touching rows:
   - Socrata: `https://<domain>/api/views/<id>.json` → `columns[].fieldName`, `name`, `license`, `view.rowsUpdatedAt`.
   - OpenDataSoft: `/api/explore/v2.1/catalog/datasets/<slug>` and `/records?limit=2` (a `total_count` and real rows in one request).
   This is where you learn the label column, whether a license field exists at all, and whether
   the dataset is official or a community-created view of another one.
3. **Measure scale with aggregate queries, never with a download.** Socrata supports
   `$select=count(*)`, `$select=date_trunc_y(<date>) AS y, count(*)&$group=y`, `$order=`, `$where=`,
   and `$select=min(<date>),max(<date>)`. One call per question returns a few hundred bytes and
   answers: enough rows? how recent? what is the class balance? Recipes: `references/api-recipes.md`.
4. **Take a bounded sample, then stop.** `$limit=2` with `$select=<only the fields you must
   interpret>` is enough to confirm units and formats — a duration in seconds versus minutes, an
   id that encodes a year, a timestamp with or without a timezone. Bulk data belongs on a worker
   or remote machine; the coordinator keeps evidence, not rows.
5. **Record evidence as measured numbers plus the query that produced them.** Anything not
   measured stays labelled unmeasured — an unmeasured base rate is the first thing the
   construction step fixes, not a number to estimate for the write-up. "The file is present" and
   "the file is valid" are different claims; do not collapse them.
6. **Write the prediction-time contract before choosing features.** State the moment the
   prediction is made, then sort every column into (a) known at that moment, (b) post-hoc outcome,
   (c) the derived label. Post-hoc columns are excluded even when they look predictive. A flag
   whose *timing* is unconfirmed (set at intake versus determined later) is excluded until the
   field documentation says otherwise — that is the difference between a real task and a leak.
   Read the column documentation for **every** candidate feature, not only the suspicious ones: a
   perfectly ordinary-looking categorical can carry a timing you would never guess (a "priority
   level" documented as assigned when the first unit arrives is post-hoc, however dispatch-like it
   sounds).
   Then **test the documented derivation of the label against the rows**: recompute the arithmetic
   the docs describe and compare it to the portal's own label column. If they disagree, or if the
   derivation's start instant is not a column in the table, the label cannot be recomputed and the
   portal column is the only valid target. An addendum worth stating in the release: when the label
   begins slightly before the prediction-time snapshot, the target includes a fixed slice of time
   that no feature can see — document it rather than pretending to correct it.
   **Excluding a column from the feature list does not stop it shipping.** Scoring harnesses
   commonly hand every column except the target to prediction code, so a declared feature list
   is documentation, not a control: anything present in the written file is available to a
   solver, whatever the manifest says about it. A label source must be *absent from the file*,
   fetched only to derive the label, while staying recorded in the manifest for provenance.
   Verify it by reading the artefact, never the declaration: for each shipped column compute the
   best single-column AUC against the target, and treat a perfect score as proof that column is
   the answer under another name. Two refinements keep that scan usable — score categorical
   columns by their per-level positive rate only when every level has at least a handful of rows,
   and report near-unique columns (identifiers, free timestamps) as *high cardinality* to be
   declared rather than as leaks, since those reach a perfect score by memorising one row per
   level.
7. **Name the split trap explicitly.** Rows versus entities: when one case, docket, facility or
   device spans many rows, a row-level split puts the entity on both sides — split by the entity
   id. Per-entity target thresholds ("high traffic for this sensor") must be computed from the
   training window only, or the label definition itself leaks the holdout. Any published forecast
   for the same target (a model's prediction of the very thing you are predicting) is leakage,
   not a feature.
8. **Check that the series is current and whether it mutates.** A dataset updated in place after
   the outcome occurs needs a frozen extract with recorded checksums, or the holdout changes under
   the task. A series that stops years back is historical-only: usable, but it weakens any "fresh"
   claim, so say so. Before writing "the series ended", search the catalog for a successor dataset
   covering the same events — portals frequently publish a replacement under a new id — then re-test
   that successor before writing it off: a refusal can be a transient bot wall in front of the
   portal rather than an absence. Retry with backoff, and only a *persistent* refusal counts as
   unverified. Successor datasets also rename columns, so re-read the schema before querying them.

## Establish the task's shape before promising it

"Could this source be a multi-label classifier?" is answered with a measured profile of the target,
not with recollection about the domain. Three questions about its shape, all answerable from
aggregate queries, plus the trivial reference any model must eventually beat - none of them needs a
model download:

- **What is the grain, and what target structure follows from it?** `count(*)` against
  `count(DISTINCT <entity key>)`. One row per entity means every categorical column holds one value
  per row, so no per-row label *set* can exist and the task is k-way multiclass - a set folded out of
  several single-valued columns is a derived reshuffle whose labels co-occur by construction, and the
  solver can see the columns it was folded from. Answer the shape that was measured, which is
  sometimes the one the operator did not ask about.
- **Does the target actually carry set-structure?** For a blob-encoded label, parse it and report
  distinct labels, labels per row (mean/median/max), the share clearing 1%, and the top co-occurring
  pairs. Labels that co-occur far above chance are a multi-label task; labels that cannot co-occur are
  one-hot in costume.
- **Compute the reference the task must beat before calling any model a baseline.** Persistence -
  the entity's own last observed value carried forward - and a calendar-only model (entity plus
  cyclical season, no other features) are the two honest floors for a temporal series. Measure both
  on the eval rows and publish them beside the model, including when the model **loses**: a shipped
  baseline of 0.87 against a one-line persistence rule at 0.89 is a finding about the construction,
  not a number to leave for the reader to discover. A baseline that cannot beat the trivial
  reference has not established that the task is predictable, and publishing it without the
  comparison overstates what was measured.
- **Is there headroom beyond the trivially available answer?** Compute the target's entropy, the
  information each candidate feature carries about it, and the trivial baselines (majority class, a
  near-copy column, top-k from the best single column) - all from two-way group-by counts. This
  answers "can we predict X from Y" with numbers before any modelling, and it usually relocates the
  honest task: a single column carrying most of the information while location and time carry ~1%
  each means the interesting prediction is not the one the framing suggested.

A feature's documentation is a claim, not a measurement: count values per column, because a column
documented as informative ("known at dispatch") can be a constant across every row, and that is a
zero-information shipped feature. For a blob label, the blob stays out of the feature list - its prose
is written during the observation - and a non-null blob is not an outcome, since a concluded-less row
can carry text from an earlier visit. Recipes for all three probes: `references/api-recipes.md`
section "Is the target one class or a set?".

## Licensing is a vetting gate, not a footnote

- An explicit open statement ("Public Domain", "CC0", "CC BY 4.0") is usable.
  **"See Terms of Use", or no license field at all, is not** — that needs the operator's review
  before anything derived is published.
- When two candidates are otherwise comparable, **decide on the risk you cannot fix yourself**:
  a clean license outranks a marginally more interesting question, because the license is a
  publication blocker and the modelling work is not.
- Without clear redistribution rights, publishing construction scripts, schema documentation and
  checksums is the fallback that does not redistribute the records. Say which path you are taking.
- Read the license from the dataset page when the API doesn't return one. Do not infer a license
  from the portal's general practice, and record "licence not confirmed" as a finding rather than
  assuming the portal's usual license applies to this dataset.
- **A generic aggregator licence is not a licence.** A funnel catalogue that lists a dataset as
  `other-open` (or similar) with a null licence URL names no terms and does not unblock
  publication. Record it verbatim and mark the candidate blocked.
- **Sweep the channels exhaustively before declaring a licence unconfirmed**, because "I did not
  find one" is only useful with the list of places you looked: the dataset's own metadata endpoint,
  the information page HTML, the state or national catalogue that harvests it, and the portal's
  terms pages. Note which of those failed to load as well as which returned nothing — a blocked
  page is not a clean negative, and the distinction is what lets the operator decide. **A bare
  fetch that answers 403 is often a user-agent wall, not a dead page**: retry the same URL through a
  real browser before writing it down as unreachable, because the licence statement is frequently on
  exactly the page the scraper cannot open.
- **The instrument attached to the dataset outranks the publisher's general terms.** A site-wide
  copyright page naming a CC licence for a publisher's *publications* is not the licence of a
  *dataset*: dataset pages frequently link a separate "data policy" or "terms of use for data
  compilations", and that document is what binds a derivative. Follow the licence-shaped links on
  the dataset's own page and read the clauses covering **alteration** and **transfer to third
  parties**, because a derived panel is an alteration however permissive the general policy reads.
  Quote the clause verbatim in the candidate record; "their terms allow it" is not evidence.
- **Check that the licence can be applied by you at all.** Some instruments are restricted to a
  class of licensor - CC BY-NC-SA 3.0 IGO, for instance, may only be applied by an
  intergovernmental organisation - so adopting one over a private project's compilation is a false
  claim even where the use itself would have been permitted. Read the licence's own terms of
  applicability, not only its permissions.
- **Never substitute a near-miss licence for an unresolved one.** When the instrument is missing or
  restricts derivatives, the honest label is `NOASSERTION` (with `license: other` on a Hub card and
  a plain-language `LICENSE.md`), not the closest-sounding open licence. A licence claim the
  publisher cannot be shown to have made is an accuracy defect in the artifact itself, and it is
  the one defect a later note cannot repair.
- **Absence of a licence field is not permission.** A metadata endpoint and response headers with no
  licence, terms or copyright field record "not stated"; they are not evidence of permissive use.
- **Classify the licence before characterising the task, and let the class decide whether you continue.**
  Four classes: **A** explicit open, permitting redistribution *and* derivatives; **B** open with
  conditions (attribution, share-alike, or a compilation licence over a source carrying its own
  terms); **C** unclear, unstated, or "contact us"; **D** prohibited - no redistribution or
  derivatives, or an authorisation you do not hold. Only A and B get probed and built. The
  classification is cheap - the dataset page, its metadata endpoint, the portal's terms - and doing it
  first is the whole point: in one pipeline more than half the parked candidates had already been
  characterised before anyone read their terms, so the expensive work was spent on sources that could
  never ship. Record the class on the candidate and sort the build queue by it.
- **An unreadable licence is a closed door, not a queue position.** When the sweep is exhausted and
  every channel is consistent - open in intent, unstated in terms - drop the candidate in the same
  breath: record the class, the absence, and the one line of evidence that would reopen it, then
  stop. Do **not** draft a permission enquiry, do not park it with a revisit date, do not wait for an
  answer. The standing rule is to build only on sources already known to be clean; a source that must
  be asked permission for is a source that is not used. An operator risk acceptance is a separate,
  explicit decision recorded against the artifact - never a default path for class C, and never
  available for class D. Do not let a generic aggregator category (`other-open`) stand in for terms
  on the way to that decision.

## Novelty is a vetting gate, not a footnote

The subject is not only the source but **the task**. Raw material being published says nothing about
whether the *prediction task* is worth building on: if an ML-ready formulation of the same task
already exists - with splits, a feature contract and a scored baseline - then rebuilding it produces
a mirror, and a mirror is not a contribution. The operator's standing rule is to publish nothing
rather than republish something a consumer can already download.

- **Search for the task, not the data.** Query dataset catalogs (Hugging Face, Zenodo) and preprint
  indexes (arXiv) for the formulation, then the literature for the operational equivalent: mature
  fields often run this exact prediction in production even though nobody ships it as a benchmark.
- **Separate "the publisher has the data" from "the task exists".** The first is expected and fine.
  The second is the veto. The easier the fetch, the *less* the access is worth - so state explicitly
  what is ours: the frozen entity panel, the label anchored to an external threshold and validated
  against the publisher's own counts, the feature contract that excludes what is unknowable at
  prediction time, the splits and the gating.
- **A publisher's deployed model is precedent, not automatically a mirror.** When the publisher (or
  the literature) already runs this prediction in production, read what it predicts before the
  verdict: an operational binary version ("will this visit find any serious defect", a scheduling
  score) does not make a set-prediction formulation of the same source a mirror - but it does mean the
  publisher has handed the neighbourhood over, so the write-up names it as the nearest precedent, says
  what differs, and states that an easy fetch lowers what our access is worth. Keep the verdict a
  separate, explicit judgement rather than letting the prior art decide it.
- **Record the verdict, not just the search.** A search with no judgement is not a check: write the
  queries, the notable hits, what already exists and what is ours, with one of three verdicts -
  *no precedent*, *differentiated*, or *mirror* - and treat *mirror* as unpublishable. The evidence
  makes the claim reviewable by someone else.
- **Look for the strongest available differentiator before settling.** Where the source supports it,
  a generalisation split (train on some entities, evaluate on held-out ones) is a contribution that
  a per-entity public product cannot offer, because it tests transfer rather than the memorisation
  of one entity's local behaviour.
- **Expect mirrors to demonstrate the risk in the catalog search itself.** Observation-level copies
  of the same underlying series are common; finding one is evidence that republishing the
  observations would add another, not evidence that the task is unoriginal.

**Make it mechanical, or it will be skipped.** The search is automatable and the judgement is not,
so encode both: a script that runs the sweep and writes the queries, the hits and the verdict into
the candidate record, taking the verdict as an explicit required argument from a fixed vocabulary
(*no precedent*, *differentiated*, *mirror*) and refusing to record a search without one. Require
that block from the earliest stage at which the rule binds - before construction spends a worker,
not at release - and make *mirror* a refusal in the candidate checker rather than a warning, since a
verdict recorded at packaging has already paid for the build it was meant to prevent. Endpoints, the
verdict vocabulary and the record shape: `references/novelty-check.md`.

The same test applies retroactively to an accepted dataset: a task is not validated by the source
being open, only by the formulation being absent.

## Preparing a release for review

When a qualified artifact is going to be published, the deliverable is a **reviewable package plus
the list of decisions that are the operator's** — not a published repository. A public repo and a
public release are far harder to undo than a commit; prepare, say plainly that nothing is published,
and hand over the choices.

- **The data's licence is not the code's licence.** A Public Domain source says nothing about the
  script that derives it; leaving the code unlicensed means all rights reserved. Surface this as an
  explicit decision with real options rather than picking one.
- **Generate the manifest and checksums from recorded evidence**, in a script, from the accepted
  artifact's hashes and the collected measurements. A manifest assembled by hand from the write-up
  disagrees with the artifact as soon as either changes. Never retype a hash from a display — a long
  value your own tooling showed as a prefix is a fabrication when completed by eye.
- **Pin the commit in the reproduction instructions**, and pin any clock-derived build field the
  artifact embeds (a build timestamp in metadata) or the documented rebuild does not reproduce the
  version it claims to.
- **Until publication is authorized, ship plan-only tooling.** Print what would happen, do nothing
  without an explicit confirmation flag, resolve each artifact file to exactly one staged asset through the producer's
  manifest, and do not ship an upload path you have never run.
- **Keep the metric's scope attached to the metric.** A baseline through a runner's contract is a
  floor for what an agent might do, not a result about any agent; where no comparison has been run,
  say so rather than leaving the absence to be inferred.

**Once assembling into a repository IS authorized** — commonly a private one, to be made public only
on a later word — the package has to actually work, and that changes what it must contain:

- **Keep it private until told otherwise**, and say in the handover that it is private and what is
  still unverified. Authorisation to assemble is not authorisation to publish.
- **Ship the code the documented commands invoke.** A reproduction path that calls a gate, a runner
  or a harness living in a private repository the consumer cannot reach is not a reproduction path.
  Copy those files in verbatim with their provenance and hashes, and flag any whose upstream carries
  no licence as a decision for the operator rather than implying a grant.
- **A release asset name cannot contain `/`.** Use flat names plus a download tool that restores the
  documented layout, with the name-to-path mapping recorded in the manifest rather than described in
  prose — and test both the tool and the by-hand equivalent.
- **Have the manifest cover every published file**, not only the data, so a consumer can verify the
  clone itself and not just the download.
- **Verify from a fresh consumer environment, then state what the check did not cover.** Clone at the
  tag, check every file against the manifest, download the assets, run the checksum command, run the
  gate, run the baseline, and require the recorded number. A credential-free environment cannot run
  the credentialed download, and a rebuild needs scratch space — name both rather than letting a
  passing check imply more than it tested.
- **Move the bytes through an ephemeral worker, never through the coordinator**, and keep the read
  and write credentials separate: a token scoped to one repository returns 404 on another. Probe both
  during planning so the refusal lands before provisioning, and keep the container credential-free by
  design.

Depth — the seven-document set, the decisions worth surfacing, the plan-only publish shape, and the
release/asset mechanics that cost time (draft releases, redirects, digest verification, the consumer
check): `references/release-packaging.md`.

## Choosing the target threshold

A binary target built from a continuous label needs one threshold, and guessing it wastes the work
that follows. Measure `P(label > T)` at a **family** of thresholds, over the whole series *and* over
the proposed training window, and choose a T where:

- the two rates agree closely — a threshold whose base rate moves between the full series and the
  training window is a moving target that will not survive a temporal split;
- the positive rate is well clear of 0 and 1, so a trivial majority-class baseline cannot score
  deceptively well;
- T sits in the body of the distribution rather than the far tail, where timestamp and entry noise
  dominate the label.

When the threshold comes from outside — a regulatory, published or vendor level rather than a
quantile you choose — measure its base rate **pooled and per entity** before adopting it. Such
levels are frequently set for rare events, and a pooled figure hides the spread: a real measurement
can run from 0% at several entities to a few percent at others, which is a task where some entities
can never produce a positive. Report both numbers.

**Keep the external threshold.** Do not substitute a per-entity quantile merely to balance the
classes. A published, regulatory or vendor level has physical meaning and outside validity, and a
quantile invents an event nobody else calls an event — which destroys the task's claim to be about
something real. Handle the imbalance in the metrics and the baseline instead: report precision and
recall alongside AUC, treat the base rate as an explicit baseline to beat, and document the
imbalance as a property of the phenomenon. Offer a quantile only as a clearly-labelled secondary
target if the operator asks for one.

**Validate the measurement against one event whose answer you already know before reporting any
rate.** Pick a documented record or a known occurrence for an entity in the sample and confirm your
method flags it. A result that is uniform across every entity — all zero, or all positive — is a
methodology red flag until that check passes, because uniform nulls are what a units, timezone or
reference-frame mismatch looks like, and it reads exactly like a finding. The validation is cheap
and it is the difference between a measured number and a plausible one.

**Then cross-check against the publisher's own derived product, if one exists - and validate where
the quantity is large.** Portals that publish raw observations usually also publish their own counts
for the same quantity; look for that product before recomputing anything. Two requirements follow:

- **Run the comparison on the entity-period with the most events, not the handiest one.** Where the
  quantity is near zero, two different methods agree trivially, so a quiet window "validates" a
  reconstruction it never tested. Agreement is demonstrated on the window carrying real signal -
  re-run it there before reporting a match, and compare entity by entity rather than only on the
  total.
- **When your derivation and the publisher's product disagree, the publisher's determination is the
  label.** Shipping your own reduction of the same series as the target makes the dataset contradict
  the source's own product and leaves no good answer to "why does this disagree with their
  counts?". Measure the candidate causes side by side - sampling resolution, calendar frame (local
  versus UTC day), completeness or verification filtering - to locate the driver, then adopt the
  publisher's product for the label. That is also the better provenance: theirs is the definition of
  the event. A common and healthy split is the publisher's product for the *label* and the raw
  reduction for the *features*.

**Look for the publisher's own reduction of the raw series before budgeting the raw fetch.** The
same instinct that finds the summary product for cross-checking also finds the cheaper route to the
task itself: a publisher that bisects a fine-grained series into a daily or hourly aggregate usually
serves that aggregate as a first-class product, and it can cost an order of magnitude less than
pulling the raw rows and reducing them yourself - one request per year instead of one per month,
small enough that a multi-gigabyte fetch collapses to a few hundred megabytes. It frequently arrives
*already quality-flagged* (a completeness percentage, a verification status), which is provenance
you would otherwise have to reconstruct. **Ask what the publisher already computes at the granularity
the label needs before writing the extraction script**, and read the API's own product list rather
than assuming the raw series is the only route; a reduction the publisher maintains for this exact
purpose is both cheaper and better-evidenced than the same reduction computed privately.

Two rows follow from this, and they are requirements rather than courtesies. **A public API is a
shared service: touch it once per build, with the cheapest product that carries the label, and never
re-read it downstream** - the published artifact is the source for every later step, so a
verification pass re-reads your own release, not the origin. And **do not move bytes you can derive
or already hold**: a second fetch of something you have on disk, or a second copy made by reading it
back out of the first destination, is data movement with no evidence attached to it. When you do recompute, agreeing with their number **entity by entity**, not only on
the total, is the strongest validation available: a twelve-entity year matching exactly is a far
better claim than internal consistency, and it is what turns a reconstruction into a measurement.
Read the summary fields carefully — a `count` in such a response is frequently the number of records
*returned* (days, pages, rows) rather than the number of events, and reading it as an event count
makes a real series look like everything happened every day.

Record the whole family in the candidate record, not just the winner, and freeze T before any
scoring. A threshold picked from the holdout is leakage with extra steps.

## Resampling and split capacity

Two measurements stand between "I have a rate" and "this task can be scored". Both are cheap and
both are routinely skipped.

**Match the sampling interval to the event you are labelling.** When labels come from a coarse
series (hourly, daily, per-visit) but the event itself is brief, the coarse series misses events the
finer one catches. Measure it rather than assume it: take the entity-periods with the most known
events, build the label from both the finest available resolution and the coarse one, and count the
days the coarse pass misses. A measured miss rate — one event in seventeen, in one real case, at a
station whose daily-maximum gap was only 0.06 ft — makes the coarse figure a **bound rather than the
value**. Report it as a lower bound, build the real extract at the finer resolution, and budget for
whatever per-request window that API imposes on fine-grained retrieval.

**Count the positives per split before promising a score.** A split is not evaluable just because it
is large; what matters is the class that is rare. Report positive counts for train, eval and holdout,
and then report how many **distinct event instants** those positives occupy: positives cluster across
entities on the same day, storm or outage, so 250 positive rows can be 120 independent events, and
confidence intervals belong on the clustered count. State whether the base rate is stationary — a
rate that drifts across the series (rising with sea level, growing with population) makes a temporal
split carry a systematic shift, which is a property of the phenomenon to document rather than a
construction fault. Prefer a holdout spanning several periods so one anomalous period cannot decide
the result.

**Declarations are claims; recompute them from the rows.** Split windows, boundary strings,
positive counts and clustered event counts recorded in a manifest are all assertions, and the two
false passes that matter most look perfect in every declaration:

- **Evaluation rows that fall inside the training period.** The declared windows are clean and
disjoint; the eval file simply contains rows from the training years. Only the data exposes it, so
compare the actual minimum and maximum of each split's time column pairwise for overlap, and check
every row against the window it claims to belong to.
- **An evaluation split with no negatives** (or no positives). A single-class eval split scores a
  meaningless AUC however carefully its counts are declared. Count both classes from the label
  column and refuse a split that is uniform, and require minimum positive *and* independent-event
  counts for eval and holdout.

So the manifest must carry machine-readable windows and an explicit event key (the column whose
distinct dates define an independent event), and the checker must recompute every declared count
from the data and fail when the two disagree — an undeclared field must fail closed rather than
pass silently.

**Check identifier overlap and identifier repetition as two separate properties.** An identifier
present in two *different* splits is leakage. The same identifier appearing twice *inside* one split
is the source's grain, not leakage — and a checker that reports both down one path refuses a usable
extract with a message naming the same split on both sides (`<id> in train and train`), which is how
the defect hides: the failure looks like a bug in the checker, so the natural next move is to delete
the check. Split them into three:

- cross-split overlap — hard failure, always;
- a repeat inside one split — refused unless the descriptor pins the known count as a measured
tolerance, so the build states its expectation and a regression shows up as a count above the
declaration instead of as silence;
- a repeated identifier carrying *both* labels — **a defect only when the descriptor claims the
  identifier is a unique entity key** (`id_columns_are_entity_keys`). That claim is what makes
  "one label per identifier" follow, and where it is made a contradiction is label noise that must
  fail. Where it is not made, the identifier is merely reused and the measured disagreement is
  recorded in the report rather than refused. Do not assert the claim on the source's behalf —
  read the rows. A repeated identifier whose two rows sit hours apart with different categories,
  sectors and priorities is two different events sharing a number, not one entity with two labels;
  a checker that assumes otherwise refuses a usable extract for a property nothing ever claimed,
  and the failure message names the same split twice, which reads as a bug in the checker and
  invites deleting the check instead of questioning its premise.

When the entity column is not unique, a temporal split becomes a hazard as well: two rows of one
entity can fall on opposite sides of the boundary, and the cross-split check is precisely what
catches it. So do not "fix" a repeat by dropping the overlap check.

## Report shape

A shortlist table: candidate id, domain, measured scale (stating what was measured), license with
its evidence, status. Then **the lead choice and the reason**, the runner-up with what blocks it,
and each candidate's open question. Rank the shortlist for variety across domains — a shortlist of
five sensor feeds proves less than four unrelated mechanisms.

Never report a score, base rate, AUC or headroom figure that was not measured. "No baseline
measured yet" is a complete and acceptable statement.

## Pitfalls

- **Judging a source from search snippets.** A result description is not the schema; open the
  metadata endpoint before writing a candidate record.
- **Downloading the dataset "to check it".** The coordinator is small and the full extract is the
  worker's job; metadata, aggregates and a two-row sample answer almost every vetting question.
- **Treating a community-created view as the official dataset.** Socrata portals carry both, often
  with identical columns; note the official id and prefer it, since the view can be filtered,
  renamed or dropped by its author.
- **A field name is not its semantics.** Confirm units and derivation from the column docs before
  building on a derived column such as a response time.
- **Comparing a threshold to a series measured in a different reference frame.** A published
  threshold and the series you test it against can come from the same API and still sit in different
  frames — vertical datum, sea level versus station datum, local versus UTC day — and the metadata
  frequently declares nothing. The failure is silent and one-directional: every comparison comes out
  below or above the threshold, so the measurement says "no positives at all" rather than erroring.
  Settle the frame with the known-event check above before measuring a rate, and write the required
  frame into the recipe so the next session cannot repeat it.
- **Inferring a license from an absence.** Thousands of rows and a clean schema say nothing about
  redistribution rights.
- **Recording a negative finding from a rejected query.** "The product does not exist" is a claim
  about the publisher, and it is frequently a claim about your parameter name: an API that rejects an
  unknown parameter usually answers with the list of valid ones, and that list is the finding. Read
  the error body before writing anything down, and re-probe with the exact name it returned - a
  wrong-name probe recorded as an absence sends the next session down an expensive route to
  rediscover something the publisher had documented all along.
- **Quoting a count without its extraction time.** Datasets that update in place return different
  numbers minutes apart; record when the count was taken.
- **Confusing popularity with novelty.** A dataset that every tutorial already uses is not a
  discovery, whatever its licence says.
- **A scan that is linear on the sample and quadratic on the data.** Building per-level statistics
  inside the per-row loop costs `rows x group-size` — invisible at a thousand rows, fatal at a
  million. Build the level table in one pass and score the rows in a second. Read splits
  column-wise (`{column: [values]}`) rather than as a list of row dictionaries: a dict per row is
  roughly a kilobyte, so a full extract costs hundreds of megabytes that a columnar read does not.
  Size performance claims against the full row count, never against the fixture.
- **Paging with an offset over a non-unique sort key.** `$order=<col>&$offset=<n>` where `<col>`
  repeats leaves the tied rows in whatever order the backend prefers, and that order is not
  guaranteed to be the same between requests — so a page boundary can repeat or skip rows, silently,
  in the built file only. Confirm the key is unique per row before paging on it (`count(*)` against
  `count(DISTINCT <col>)`, one cheap aggregate) and give the order a unique tiebreaker; on Socrata
  the `:id` row identifier is unique per row and `$order=<col>,:id` is accepted and returns identical
  results across repeated calls. Without that check, a page-boundary duplicate is indistinguishable
  from a duplicated source record — and the source record is the innocent explanation you will reach
  for first.
- **Settling a trap without writing it down as a test.** When a known-event check fixes a reference
  frame, a unit or a field mapping, land it in the repository as a checked-in fixture plus an
  offline assertion: the recorded values, the expected verdict against the threshold, and the
  required frame as a named constant. The trap is silent and one-directional, so the next session has
  no way to know which frame is correct from the data alone; the fixture is what makes it
  unrepeatable, for the cost of one small file and one test. Then keep that assertion honest:
  - **Run the suite as a different machine would.** `env -u PYTHONDONTWRITEBYTECODE TZ=Asia/Tokyo
    python3 -m unittest discover -s tests` — a host that sets `PYTHONDONTWRITEBYTECODE` hides a
    loader that writes `__pycache__` into the fixture directory, and a host at UTC hides a check
    that parses a timezone-free timestamp through the local clock. A green run on your machine is
    weaker evidence than it looks. Load fixture modules with
    `exec(compile(path.read_bytes(), str(path), "exec"), ns.__dict__)` so the test cannot
    contaminate the directory it is asserting on.
  - **Size the fixture to reach the branch you are testing.** Below roughly ten rows per split every
    column is unique enough to be classified as an identifier, so the categorical path never runs
    and the assertion passes without exercising anything. Give each level of each categorical
    column at least five rows, and assert that the intended branch executed.
  - **Deletions are explicit and owned.** Enumerate first and delete exact paths; a wide
    `rm -rf <dir>` removes the directory rather than the caches in it, and a careless cleanup pass
    has deleted whole source trees. Commit before a cleanup pass so a mistake costs a checkout,
    not the work. The same rule governs the construction script: never recurse over whatever path
    was passed as the output argument. Refuse a protected path, a directory containing `.git`, and
    a non-empty directory that lacks an ownership marker the script writes on creation; then clear
    an owned directory entry by entry through an explicit list, so an unrelated file sitting beside
    the output survives the rebuild.

## References

- `references/api-recipes.md` — working catalog, metadata, aggregate and sample queries for Socrata,
  OpenDataSoft, NOAA CO-OPS and USGS NWIS, the derived summary products that cross-check a
  recomputed measurement, the limits each API imposes on bulk retrieval, and the three probes that fix
  a candidate's task shape (grain, target set-structure, headroom) from counts alone.
- `references/discovery-coverage.md` - making discovery international by measurement: the required
  `jurisdiction` block, the coverage report and its exit code, deterministic regional rotation, and
  the order to backfill and gate existing records.
- `references/novelty-check.md` — the mirror check before building: the catalog and preprint-index
  sweep endpoints, the verdict vocabulary, what "what is ours" has to state, and where in the stage
  ladder the gate belongs.
- `references/artifact-qualification.md` — the checklist for the files construction produced:
  leakage scan, row-based split checks, acceptance by content hash, running the gate on the remote
  machine, and packaging the gate so the agent can load it.
- `references/release-packaging.md` — turning a qualified artifact into a reviewable publication
  package: the document set, generating identity from recorded evidence, the decisions to surface
  rather than make, and plan-only publish tooling.
