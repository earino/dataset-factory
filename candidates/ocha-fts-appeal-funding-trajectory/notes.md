# ocha-fts-appeal-funding-trajectory — discovery notes

Session: scheduled discovery tick 2026-10-29, regional focus International
organisations. All probes anonymous (coordinator HTTP only, no auth, no
browser login). Every claim below has the probe script that produced it in
this directory; the scripts are runnable as-is (stdlib only).

## Lead

UN OCHA Financial Tracking Service (FTS) — per-plan-year appeal funding
coverage. Prospective user: humanitarian financing analysts and OCHA
resource-mobilization officers; prediction at plan launch of "will this appeal
reach >=50% of its original requirements by year end" enables early
identification of underfunded appeals months before the GHO reports the gap.

## Chronology of probes (2026-10-29, UTC)

1. licence-first: `fts.unocha.org/content/about-fts-using-fts-data` — the
   dataset's own page answers "Can I use and republish the data and
   information published on FTS website/API?" with "Yes" plus a citation
   request; the publisher's HDX record for the identical data
   (`data.humdata.org/api/3/action/package_show?id=global-requirements-and-funding-data`)
   carries `cc-by-igo`. Class A. OCHA site pages 404 for /terms-use and
   /terms-of-use (recorded); the CBPF sibling site footer states CC BY 4.0.
2. API access (no auth):
   - `curl "https://api.hpc.tools/v1/public/fts/flow?year=2023&countryISO3=YEM&groupby=plan"`
     → 200, 5,269 B; report3 gives Yemen HRP 2023 totalFunding 1,774,327,599.
   - `curl "https://api.hpc.tools/v1/public/fts/flow?year=2023&countryISO3=YEM"` (no
     groupby) → 200, 382,997 B, `data.flows` = 200 dated flow records per
     page, meta.count 1,387, nextLink page=2. Flow fields include
     decisionDate (189/200 present), firstReportedDate (200/200), status
     (commitment 125 / paid 75), flowType (Standard 129 / Parked 68 / Pass
     through 2 / Carryover 1). An example multiyear parked flow: decision
     2018-11-22, first reported 2019-04-03, usage years 2019-2023.
   - `flow?planId=1116&year=2023` → 986 flows, incoming.fundingTotal
     1,774,327,599 == HDX CSV row to the dollar. `plan=` and
     `destinationPlanId=` are invalid parameters (HTTP 400 messages read; the
     pager is `page=N`).
   - `api.hpc.tools/v2/public/plan/year/{year}` enumerates plans 2000-2026
     (17-62/year); plan detail has origRequirements, revisedRequirements,
     revisionState, planVersion (dates, isPartOfGHO). No public version
     history endpoint (checked /v2/public/plan/{id}).
3. HDX bulk: downloaded `fts_requirements_funding_global.csv` (1 request,
   279,849 B, 2.0 s). `probe_reqfund_stats.py` / `probe_reqfund_stats2.py`:
   3,874 rows 1999-2031; 2,678 rows without requirements (country rows
   outside appeals); 1,196 rows with id+requirements; 877 distinct plan-years;
   111 distinct countries; published percentFunded median 50 (p25 31, p75 69).
4. grain (`probe_grain_vintage.py`): regional plans appear once per affected
   country with slices; Burundi RRP 2021 slice funding sums to 14,978,233 vs
   API plan total 19,282,778 (0.78) → regional plans excluded from the primary
   population. AFG 2023: single plan id 1117; orig 4,627,363,573; revised
   3,227,372,908.
5. vintage (decisive): `probe_reqfund_vintage.py` on 2016+2023 cohorts — the
   CSV requirements column matches the *revised* value in revised cases
   (2016: orig 21 / revised 14; 2023: orig 23 / revised 15, 8 slice
   mismatches). Full sweep `probe_plan_sweep.py` (877 plan fetches, 0 errors,
   401 s → `plan_orig_sweep.jsonl`, 296 KB): of 836 plans with orig>0,
   286 revised up, 166 down, 384 unchanged. Launch-vintage denominator =
   origRequirements only.
   Dated cross-check fixture: GHO 2023 launched 2022-12-01 (reliefweb press
   release; UNICEF sitrep #12: "US$4.62 billion is required", HRP launch
   "end of December or early January 2023") vs plan origRequirements
   4,627,363,573 → matches. Final funding (flow endpoint, 683 flows)
   1,678,347,238 = 36.3% of orig → label 0. Today's CSV row: requirements
   3,227,372,908, percentFunded 52 → using the CSV column would flip this
   label to 1. Forbidden-column fixture recorded.
6. split counts (`probe_split_counts.py`, launch-vintage denominators,
   >=50% threshold, primary population 782 plan-years):
   - 2000-2013: 347 rows, 237/110 (68.3%), 69 countries
   - 2014-2018: 153 rows, 80/73 (52.3%), 44 countries
   - 2019-2022: 152 rows, 97/55 (63.8%), 52 countries
   - 2023-2025: 106 rows, 45/61 (42.5%), 40 countries
   - 2026 live edge: 24 rows (excluded)
   Concrete 3-way cut: train 2000-2016: 437 (282/155, 64.5%), eval 2017-2020:
   139 (81/58, 58.3%), holdout 2021-2025: 182 (96/86, 52.7%). Clustered count:
   83 country series, max 28 appearances; prevalence drift is a measured
   phenomenon property (GHO coverage 50% in 2022 → 38% in 2023).
7. publisher summary cross-check: GHO 2023 December update — requirements
   $56.7B, funding $21.8B, coverage 38% at 2023-12-31 (launch ask $51.5B on
   2022-12-01). CSV-basis 2023 aggregate here: 55.8B / 25.2B / 45.1% — the
   difference is composition (non-GHO plans + mixed-vintage requirements),
   not a data conflict; per-plan orig + isPartOfGHO reconcile at construction.
8. novelty (mechanical search recorded by check-novelty.py): raw-table
   mirrors exist (HDX global + per-country; HF user mirrors of the same CSVs;
   HAPI funding endpoint), no ML-ready per-plan-year coverage task with an
   instant, splits and a scored contract found. Verdict: differentiated.

## Decisions and residual uncertainty

- Verdict: READY (all five contracts backed; see record.json review field).
- Named risk: the WB instrument-outcome drops (identity/persistence-dominated,
  no headroom) — the prior-year same-country coverage rule is the reference
  that decides this task's value; a negative comparison is a reportable
  result, not a defect.
- origRequirements verified launch-vintage on one external December source
  plus orig/revised separation on 836 plans; construction asserts the GHO
  cross-check on sampled cohorts.
- Decisions recorded: regional plans out of the primary population (measured
  0.78 slice gap); appeal-linked funding only (label single-population);
  2026+ live edge excluded; CSV requirements column forbidden as a feature.
