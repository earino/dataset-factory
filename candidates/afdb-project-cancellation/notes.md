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
