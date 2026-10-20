# Dashboard: executive and operational views

Status: **P0 shipped 2026-10-20.** Exec, Cost and Reliability are live at
https://earino.github.io/dataset-factory-dashboard/. P1 and P2 below are not built.

The pipeline produces a lot of state that currently reaches the operator as chat prose: eight
candidates in flight, a worker ledger, six cron jobs, a token budget, four published releases with
226 assets each. Prose is a bad index. This replaces it with a generated dashboard that answers the
same questions continuously, and reserves chat for exceptions.

## The constraint that shapes the design

This instance has no inbound network. The only service reachable from the internet is the bundled
Hermes dashboard, which is platform-managed and not ours to extend safely. So the dashboard is
**static HTML generated from repo state and published on the existing GitHub Pages site**, not a live
server:

- Generator: `scripts/build-dashboard.py`, stdlib only, deterministic (same inputs -> byte-identical
  output apart from a timestamp).
- Output: one `dashboard.json` snapshot plus static pages (`index.html`, `cost.html`,
  `reliability.html`, `style.css`).
- Publish: the hourly job commits them to **`earino/dataset-factory-dashboard`**, served from that
  repository root at **https://earino.github.io/dataset-factory-dashboard/**.
- Refresh: every hour at `:50`, after the discovery tick, via `scout-dashboard-refresh`
  (job `4d8053a69ed2`, script-only, output kept local so it cannot spam chat).
- It lives in **its own repository, not under `/dashboard/` on the catalogue site**: the catalogue is
  deployed by a reviewed workflow that builds `_site` from `.dataset-site/` and only triggers on
  that path. Adding a second publisher to it would either bypass that review or teach the reviewed
  builder about a directory it does not own. A separate Pages repo keeps the catalogue's
  publication semantics intact.
- The generator is `scripts/build-dashboard.py` (`--publish`), the scheduler entry point is
  `/opt/data/scripts/scout_dashboard.py`, and the anonymous read-back is built in: a publish that
  does not appear publicly is recorded as a failure, not a success.

Consequence to be explicit about: freshness is a first-class number on every page ("state as of
12:20 UTC, 4 minutes ago"), because a static page that silently ages is worse than no page.

## Audiences and the one-screen rule

Two readers, two densities:

- **Executive** (`/dashboard/`): does the pipeline produce publishable datasets faster than it
  consumes them, and at what cost. Nine tiles, no scrolling on a laptop, each tile clickable into
  its operational page.
- **Operational** (the five detail pages): what is running, what is queued, what is stuck, what is
  about to break.

## Views

### 1. Executive — `/dashboard/`

| Panel | Question | Source |
|---|---|---|
| Funnel | sources opened -> verdicts -> investigating -> qualified -> built -> published, 30-day and all-time | `candidates/*/record.json` history fields, `candidates/*/verdict.json` |
| Publishing pulse | datasets published in the last 30 days, and days since last publication | `release/*/MANIFEST.json` (`published_at`) |
| Throughput vs capacity | publishes/week against worker-hours available; backlog age in days | funnel + `.factory/` ledger |
| Spend | tokens this week vs 40M ceiling; worker euros this month vs 20 | `scripts/research-budget.py --json`, worker accounting |
| Cost per published dataset | worker euros + estimated tokens / datasets published this quarter, trend | derived |
| Coverage | live candidates by jurisdiction, non-US share vs the 50% goal | `scripts/discovery-coverage.py` |
| Health | latest test count, `check-candidate --all` results, last CI status, anonymous verification of the newest release (pass/fail, no credentials) | CI API, release verification log |
| Pipeline alarms | at most five lines, each with an owner action | derived rules below |

Executive page carries no tables longer than five rows. Everything else is a link.

### 2. Discovery — `/dashboard/discovery/`

- Tick table, last 48: fire time, region in focus, sources opened, verdicts (`go`/`park`/`reject`),
  quota satisfied (>=3 verdicts, >=2 non-US), duration, tokens, exit status.
- Verdict ledger, last 90 days: candidate, publisher, country, verdict, one-line reason, novelty
  check result. Filterable by region and verdict.
- Region rotation strip: the nine regions, when each was last focused, how many verdicts it produced
  (this exposes a region that keeps returning nothing so it can be retargeted rather than repeated).
- Quota compliance trend: sessions meeting both quotas, as a percentage.
- Rejections with reasons grouped by class (no label, licence unreadable, novelty collision, dead
  source) — the only reliable signal for choosing the next region.

### 3. Construction — `/dashboard/construction/`

- Queue: candidates with a GO verdict, in order, with waiting time and what each needs (download
  volume, estimated worker minutes).
- Worker timeline (Gantt, one lane per job, last 14 days): provision -> run -> upload -> destroy,
  coloured by outcome. Makes serialization visible — the point of the one-worker rule.
- Job table: id, candidate, server type, minutes, euro cost, peak disk, artifact MB, exit class,
  retries. Failure classes grouped so a repeated cause is obvious.
- Build stages per candidate (pull / normalise / split / features / baseline / package), which one is
  current, and how long each took. Answers "why is Chicago still not published".
- WIP line: active worker jobs (must be 0 or 1), candidates claimed by a running advancement session.

### 4. Releases — `/dashboard/releases/`

- One card per published dataset: version, publication date, three destinations with their status and
  last verification time, asset count, total bytes.
- **Byte-level trust panel**: assets re-hashed against `MANIFEST.json`, matched/total, and when the
  check last ran with no credentials. This is the number that says whether the public record is true.
- Freshness: days since the source was last refreshed, and whether a newer source release exists.
- Per-release drilldown: splits, configs, columns, licence posture (including "licence unstated by
  publisher, operator risk acceptance on record"), and the exact attribution string shipped.

### 5. Quality / outcome — `/dashboard/quality/`

Process is not outcome: this page is whether the datasets are any good as benchmarks.

- Baseline vs persistence, per dataset and per config, with the gap. A config whose model barely
  beats persistence is a weak target and should be visible, not buried in a report.
- Split sizes and label balance over time; schema drift (column added/dropped/retyped since the last
  release).
- Known defects register (leading-zero loss, `test_id` duplication, absent 2020 slice) with status.
- Difficulty spread: for each dataset, the distribution of per-config baseline AUC, so a dataset
  that is trivially easy across the board is flagged.

### 6. Cost — `/dashboard/cost/`

- Tokens: this week vs 40M, by source (`scout-research`, `scout-discovery`, interactive), with the
  sessions counted against the 200/week cap.
- Worker euros: month to date vs 20, projected month end, per-job breakdown.
- Unit economics: tokens per verdict, euros per built candidate, euros per published dataset.
- Waste: failed or retried jobs and their cost; verdicts that produced no construction.

### 7. Candidate drilldown — `/dashboard/candidate/<id>/`

One page per candidate, the thing to open when deciding. Identity (publisher, jurisdiction, source
URLs), verdict and novelty reasoning, licence posture and its evidence chain, the measured facts
(rows, columns, label rate, time coverage), construction state, release state if published, and a
chronological event log assembled from `record.json`, job records and session reports. This is the
page that replaces "explain more" in chat.

## Metrics dictionary (so the tiles cannot drift)

- **Verdict**: a recorded `go`/`park`/`reject` with reasoning. Not a source that was opened.
- **Live candidate**: status `investigating` or `qualified`.
- **Published**: a release whose three destinations are verified *anonymously*; a pushed commit is not
  a publication.
- **Cycle time**: first verdict -> publication, median and p90.
- **Conversion**: verdicts -> qualified -> built -> published, as three separate rates; combining them
  hides where the funnel actually leaks.
- **Cost per published dataset**: (worker euros + estimated tokens at the recorded rate) / publishes,
  quarter to date. Labelled *estimated*, never presented as billing.
- **Non-US share**: live candidates by publisher jurisdiction, `unknown` counted and shown, never
  guessed or silently dropped.

## Honesty rules for the generator (non-negotiable)

1. Every figure renders with its `as_of` and its source path. No number appears without one.
2. Missing input shows **"no data"** with the expected path, never `0`, never a carry-forward.
3. A panel whose data is older than its freshness SLA is greyed and labelled STALE, and the page
   banner says which panels are stale. A stale dashboard must not look healthy.
4. No secrets, no token values, no session contents. Only counts, statuses and identifiers.
5. The generator refuses to publish if `dashboard.json` fails its own schema check, so a broken build
   leaves the previous good page up rather than a blank one.
6. The build is reproducible: same repo state -> same output. The timestamp is the only difference,
   and it is injected last.

## Alerting rule (this is the point of the exercise)

The dashboard is the default reporting channel. Chat is for exceptions only, and only these:

- a worker job fails, or a launch is refused;
- a publication completes (one short line with the link);
- a gate fails (tests, `check-candidate`, verification, coverage);
- budget crosses 80% of either ceiling;
- a scheduled job misses its window or exits non-zero twice in a row.

Everything else — progress, discoveries, verdicts, queue depth, "how are we doing" — is answered by
the dashboard, and the answer to "how are we doing" becomes a link rather than a paragraph.

## Build plan

**P0 — shipped 2026-10-20.** `scripts/build-dashboard.py` renders the executive page, the cost page
and the reliability page from files that already exist; `scout-dashboard-refresh` publishes hourly
at :50 and verifies the public page without credentials. Nine dashboard tests guard the honesty
rules (missing input renders "no data", an aged panel is stale, a true zero stays zero, an empty
table says so, and a token in any page aborts the build). What P0 does *not* yet show: worker-job
timings and euro spend (the per-job ledger is not written), the verdict ledger, and any history or
sparklines — those are P1/P2.

**P1 — one day.** Discovery, construction and releases pages; candidate drilldowns; the verdict
ledger; the byte-level trust panel.

**P2 — half day.** Quality page (baseline-vs-persistence, drift, defects), 30-day sparklines from
snapshotted `dashboard.json` history committed daily, and region-rotation analytics.

**P3 — optional.** A JSON endpoint per page (`/dashboard/data/<view>.json`) so other tools can consume
the same snapshot, and a local `--serve` mode for reading it inside the container without publishing.

## Decisions taken here (not put back to the operator)

- **Public URL, unlisted, not authenticated.** Pages cannot enforce auth without a server we do not
  have. The earlier justification ("everything shown is already public") was wrong: candidate names,
  statuses and next actions come from the *private* factory repository. So the pages carry
  `noindex,nofollow` and a `robots.txt` that disallows everything, and rule 4 is enforced in code:
  no credentials, no session transcripts, no staging URLs, and no full budget config — only the
  ceilings the page displays. If this is not acceptable, the alternative is a local `--serve` view
  and no public site.
- **Hourly, offset from the discovery tick**, so one build reflects a finished tick rather than racing
  it.
- **Static, not a live console.** If truly live numbers are ever needed, the correct route is a Hermes
  dashboard plugin on the platform-managed host, not opening a port here; that coupling is not worth
  it for state that changes hourly.
- **The dashboard does not replace the repo as the record.** It renders the repo; when they disagree,
  the repo wins and the generator is wrong.
