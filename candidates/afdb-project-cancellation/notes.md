# afdb-project-cancellation — discovery notes

Opened 2026-11-04 by the Africa discovery tick (operator regional focus). The tick's named
publishers were triaged licence-first; this is the one named publisher with an un-probed
row-level, class-A product. See the tick STATE.md entry for the full regional sweep.

## Why this source

The tick named "African Development Bank". The old AfDB data portal domain data.afdb.org is
NXDOMAIN (Cloudflare DoH status 0, no A record; probe 01). The current products are:
- MapAfrica (mapafrica.afdb.org) — the publisher's own dashboard; API + downloads sit behind a
  Cloudflare challenge (403 "Just a moment..." to plain clients, probes 05/06); the supported
  browser passes.
- The AIH country portals (africadata.org / *.opendataforafrica.org, Knoema platform) —
  aggregate indicator panels; dataportal.opendataforafrica.org is Cloudflare-challenged too;
  treated as the aggregate platform it is (StatCan precedent: aggregate-only = weak task value).
- AfDB's IATI publication — 57 registry datasets, IATI 2.03 XML, full project history
  (cancelled approvals back to 1969-07-24). This is the bulk instrument.

## Licence (read before task probing; class A)

- MapAfrica "About this data" modal (browser, 2026-11-04): "Data provided under Creative
  Commons Attribution licence." + footer anchor "Creative Commons Attribution" ->
  https://creativecommons.org/licenses/by/4.0/deed.en
- IATI Registry: `curl -s 'https://iatiregistry.org/api/3/action/package_show?id=afdb-saotome'`
  -> `"license_id":"cc-by"`, organization "African Development Bank" (afdb).
  `package_search?fq=organization:afdb&rows=100` -> 57 datasets, license_id cc-by on 57/57.
- Registry HTML pages 404 on old slugs; the CKAN compat API works (q/fq text search unsupported,
  fq=organization:afdb works).

## Probes (all commands in probe/, raw outputs in probe/out/)

1. Portal reachability (probe 01, out/africa_tick_b1.json): data.afdb.org / projectsportal.afdb.org /
   data.gov.za NXDOMAIN; africadata.org 200; ecastats.uneca.org redirects to /data.
2. MapAfrica schema (probe 05 + browser): `/api/v15/activities?per_page=10` rows carry
   iati_identifier 46002-P-XX-..., activity_status, activity_date_{planned,actual}_{start,end},
   country, sector codes, custom sector/theme, SDG, safeguards, climate, gender, fragility,
   sovereign flags, total_budget/disbursements/commitments.
3. Publisher aggregate (browser, same-origin fetch `/api/v15/stats?currency=xdr`):
   6,000 activities; status {1: 383 Approved, 2: 987 Ongoing, 3: 4400 Completed, 5: 230 Cancelled};
   55 countries, 58 sectors, 16 ADF cycles.
4. Full cancelled population, bounded (browser, 3 pages x 100):
   `/api/v15/activities?status=5&per_page=100&page=1..3&ascending=true&order_by=activity_date_planned_start`
   -> 230 rows (probe/out/afdb_cancelled_sample.json). Approval years 1969..2023, every decade
   carries positives (see record.measurements.cancelled_population_2026_11_04 for the year table);
   49 countries + 29 multinational; actual_start 219/230; actual_end 0/230.
5. IATI registry inventory (probe 11, out/africa_tick_b12.json): 57 datasets, sum activity_count
   5,188; largest afdb-multinational 781, afdb-nonsovereign 402.
6. Datastore cross-check (probes 07/08/10): 5,187 activities; status=3 -> 3,896; status=5 -> 191;
   start-date<1985 -> 610 (deep history is in the published files). DISCREPANCY vs MapAfrica
   (230 cancelled) recorded; construction defines the population from the registry XML only.
7. Raw XML schema (probe 11/12/13, out/africa_tick_b12.json): afdb-saotome file 1,145,985 B in
   one anonymous GET; 42 activities; activity-date types 1,2,3 on 42/42 and type 4 on exactly the
   32 completed; no board-approval-date element; default-finance-type/flow-type present;
   transactions carry afdb:finance-type-id. Overrun check on the 32 completed: actual_end >
   planned_end on 4/32 (12.5%) — planned_end is the revised end in the current vintage, so an
   overrun target is revision-contaminated; cancellation is the clean target.
8. Extraction cost: see record.measurements.extraction_cost_measured_2026_11_04. Bulk ~140 MB is
   an estimate from one measured file; the worker pass measures it. Worker-side (Hetzner)
   reachability of afdb.org static paths is UNTESTED — first prerequisite of the worker job.

## Dated example (Africa/Abidjan timezone note: the IATI dates are day-grain ISO; the bank
approves in board meetings; the instant is the type-1 date)

P-SD-FF0-001 (Sudan, measured in the cancelled fetch): planned start (type 1) 2019-12-18,
actual start 2020-03-05, planned end 2025-12-31, sector 23230 (road transport? construction per
IATI codelist), sovereign, UA 29,020,000. Feature window = at-approval attributes only.
Instant T = 2019-12-18 (approval). Target = terminal status observed at the current coverage
end: activity-status 5 (Cancelled) -> label 1. Negative: 46002-P-ST-K00-012 (Sao Tome), type-1
date 2013-06-17, status 3 (Completed), actual end 2015-12-31 -> label 0.

## Five contracts — state at investigating

- Redistribution: SUPPORTED (class A, two publisher instruments).
- Prediction timing: PARTIAL — instant stateable, current-vintage posture must be declared;
  type-1 vs displayed approval date offset (~1 day on the one observed pair) needs a sample.
- Target: SUPPORTED as derivable + excludable; censoring rule stated; channel gap 230 vs 191
  must be reconciled at construction.
- Split capacity: PARTIAL — measured positives per proposed window (136/36/58); per-window
  denominators and clustered counts unmeasured (first construction measurement, worker).
- Contribution: UNRESOLVED — check-novelty.py + the pre-registered family-risk test
  (two WB at-approval comparators on this bench died on rate/identity priors; the triad is the
  mandatory first scored comparison and a pre-registered drop condition).

## What would close or kill it

Close: worker pass confirms per-window class counts at the measured positive levels and the
triad shows the label carries signal beyond country/sector/decade rate tables.
Kill: triad dominance (third measured instance of the WB family defect), or worker-side
extraction blocked with no clean fallback channel, or the registry population cannot support
the eligibility rule (e.g. the historical backfill proves incomplete against MapAfrica).

## Worker panel probe 2026-11-05 (executed next_action steps 1-3)

Probe recipe: probe/probe_worker_panel_001.py (durable copy), staged at
.factory/job-sources/afdb-panel-probe-001/, job id afdb-panel-probe-001,
cx23/hel1, EUR 0.04 reserved. Result: succeeded exit 0, 20.5 s job wallclock.
Staging release 435425973 (private). Worker destroyed 16:20:10Z with provider
read-back (GET /servers/174640740 -> HTTP 404 not_found; /servers 0; /primary_ips 0).

Measured (all numbers in record.measurements.worker_panel_probe_2026_11_05):

- REACHABILITY: 57/57 afdb.org IATI XML URLs HTTP 200 from the Hetzner worker
  (egress 2.29.159.168). Registry refreshed from the worker: 57 datasets, cc-by
  57/57. Zero failures, zero retries. The dws.gov.za risk (coordinator access
  not proving worker access) is settled affirmatively for this source.
- COST: 172,488,241 B across 57 files in 7.2 s fetch / 20.5 s total; largest file
  afdb-cameroon 3,881,643 B; 62/130 request budget. All 57 sha256 digests recorded
  as the source vintage pin for construction.
- POPULATION: 5,188 activities, 0 duplicate identifiers; status {1:281, 2:819,
  3:3897, 5:191}. RECONCILIATION RESOLVED: registry 191 cancelled = datastore
  191; MapAfrica's 230 is a larger, different population (6,000 activities).
- TERMINAL: 4,088 rows; 0 missing type-1 dates (instant stateable for every scored
  row); 38 missing planned end; 0/191 cancelled carry an actual end.
- TIMING: type-2 follows type-1 by median 75 days (n=5,059; 0 negative offsets).
- CENSORING: 1,100 status-1/2 rows, all approvals 2007+ (min type-1 2007);
  planned_end <=2015: 0, <=2020: 1, <=2026: 271, missing: 173.
- SPLITS: the 2026-11-04 proposal (train <=2000 / eval 2001-2010 / holdout
  2011-2023) measures 121/29/41 positives - eval is ONE SHORT of the gate's 30.
  Re-cut before any score: eval 2001-2011 = 1,126 rows/32 positives/27-29 cells;
  holdout 2012-2023 = 1,118/38/31-33 cells; train unchanged. Every bound clears
  the gate (30 positives, 20 events).
- GRAIN: 13 positive rows carry no recipient-country (multinational); event key
  must be country-or-region x approval year.
- CODELIST: machine-readable ActivityStatus.xml 404; labels used are MapAfrica's
  own (1 Approved, 2 Ongoing, 3 Completed, 5 Cancelled), measured 2026-11-04.

Verdict: READY. The construction-time deciding check stays the pre-registered
rate triad (see record.next_action); neither row-level data nor any score exists
on this host.

## Construction outcome 2026-11-05 (advancement session; jobs afdb-build-001 + afdb-baseline-001)

Executed the record's standing order end-to-end on a worker, in the fixed order,
with no step skipped:

- CONSTRUCTION (afdb-build-001, server 174648468, 30.4 s): all 57 pinned afdb.org
  XMLs fetched, every sha256 matched the afdb-panel-probe-001 vintage pin; the
  terminal panel built exactly to the pre-registered windows - train 1,871/121
  (107 cells), eval 1,126/32 (29 cells), holdout 1,087/38 (31 cells); anchors
  (population 5,188; status histogram {3:3897, 5:191, 2:819, 1:281}; per-year
  table) asserted exactly and all matched.
- QUALIFICATION + ACCEPTANCE: gate 1.5.0 passed 44/44 on the full artifact;
  exact-byte --accept ACCEPTED artifact 7313e7fc6972edfc... (staging release
  435481585, private).
- REFERENCE TRIAD (score.py, post-acceptance, identical 1,126 eval rows, train-only
  estimates): trailing_country_rate 0.5491 (strongest), trailing_sector_decade_rate
  0.4697, global_rate degenerate (Brier 0.0289), supplementary persistence_country_last
  0.5287, majority-class accuracy 0.9716. Prevalence shift 6.47% -> 2.84% recorded;
  eval years 2007/2008 carry zero positives (the outcome-observability selection
  biting as declared).
- FULL MODEL + DECIDING CHECK (afdb-baseline-001, server 174650265, 69.1 s): the
  harness runner baseline (xgboost, unmodified, runner_files.unmodified true)
  scores eval AUC 0.6394 (train.py and validate.py agree to 3.3e-6). Deciding
  check, computed on identical eval rows with per-row model scores via
  validate.py's own code path: beats trailing_sector_decade_rate (CI
  [+0.0124, +0.3231]) and the degenerate global rate (model AUC CI
  [0.5354, 0.7480] above 0.5), but the model-minus-country-prior cluster-aware
  paired bootstrap CI is [-0.0765, +0.2546] - contains zero.

Verdict per the rule written before any score: headroom NOT demonstrated;
the strongest member is not beaten by a meaningful margin, so this is the third
measured instance of the WB at-approval family defect and the candidate DROPS
with the evidence preserved (private staging releases 435481585 and 435496906).
The negative finding does not prove every competent model must lose - eval
carries only 29 independent positive event cells, and the cluster-aware interval
is wide because the positives are that clustered.

Corrections recorded with evidence in record.measurements.construction_2026_11_05:
the split_strategy prose's holdout row count (1,118 -> 1,087, an off-by-a-year
slip in the re-cut arithmetic; windows and 38 positives were always right) and
notes.md's no-country positives figure (13 -> 17; all 564 no-country terminal
rows carry a recipient-region, so no row falls to the MULTINATIONAL bucket).

Both workers destroyed with provider read-back (GET /servers/<id> -> 404).
No holdout figure exists or is implied anywhere; the holdout stays sealed.
