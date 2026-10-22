# wb-ieg-project-outcome — discovery notes (2026-10-22)

World Bank IEG World Bank Project Performance Ratings as an approval-instant
project-outcome prediction task. All commands run from the coordinator
unless stated. Bulk probe CSV kept at scratch only; deleted at session end,
never committed.

## Licence (triaged first, minutes)

- Data Catalog dataset page 0038059 fetched:
  `curl -sL 'https://datacatalog.worldbank.org/search/dataset/0038059/ieg-world-bank-project-performance-ratings'`
  -> page JSON-LD: `"license":{"@type":"CreativeWork","name":"Creative Commons Attribution 4.0..."}`
  page text: "This dataset is licensed under Creative Commons Attribution 4.0" / "classified as Public".
- Dataset metadata API:
  `curl -s 'https://datacatalogapi.worldbank.org/dexapps/fone/api/metadata?assetId=DS00053'`
  -> `"license": "Creative Commons Attribution 4.0 International"`, `"data_classification_name": "Public"`,
  `"update_frequency": "Quarterly"`, `"row_count": 12629`, `"column_count": 21`, `"data_as_of": "2026-10-20"`,
  `"last_updated": "2026-10-22T05:49:57Z"`.
- Standing licence: https://datacatalog.worldbank.org/public-licenses — CC BY 4.0 is the default for
  Bank-produced datasets; the "additional terms" are a mediation/arbitration dispute procedure, not a use
  restriction. Class A.

## Bulk access (measured)

```
curl -s 'https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00053&resourceId=RS00055&top=20000&type=csv'
-> HTTP 200, 3,340,648 bytes, 12,629 data rows, ONE request, ~4 s
```

Schema (21 cols): agreement_type, approval_fy, as_of_date, bank_performance, country,
country_fcs_lending_group, country_fcs_status, country_lending_group, evaluation_fy, evaluation_type,
final_closing_fy, global_practice, lending_instrument_type, me_quality, outcome, practice_group,
project_id, project_name, quality_at_entry, quality_of_supervision, wb_region.

## Row-level probes

`python3 candidates/wb-ieg-project-outcome/probe_ieg_stats.py <scratch>/ieg_test.csv`

```
rows: 12629
distinct project_id: 12628  duplicated_ids: 1      -> P122764 (eval_fy 2023 AND 2026, both ICRR, both MS)
outcome mix: Satisfactory 5639, ModSat 3153, Unsat 1870, ModUnsat 1224, HighlySat 398, HighlyUnsat 194, Not Rated 151
MS+ share over rated rows: 0.7365
approval->evaluation lag: min=1 median=8 max=31
approval_fy range 1956..2024 (present on all rows)
window MS+ rates: 1960-1995 0.6999 (n=5805) / 1996-2005 0.7199 (n=2710) / 2006-2012 0.7465 (n=2134)
                  / 2013-2016 0.7980 (n=1079) / 2017-2030 0.8009 (n=899)
evaluation_type mix: ICRR 6909, PPAR 3713, PCR 1482, EVM 487, PCN 35, PCM 2, CSSR 1
missing: final_closing_fy 35.8%, global_practice 36.1%, country_lending_group 0.77%
country-approvalFY clusters: 4695, with >=1 positive: 4020
```

`python3 candidates/wb-ieg-project-outcome/probe_join.py <scratch>/ieg_test.csv`

```
duplicated project_id P122764: two ICRR rows (eval_fy 2023, 2026) - dedupe keeping latest
(country,approval_fy) cells with >1 distinct fcs_status: 165/4695; 51/187 countries >1 value
  e.g. Cameroon FY1995: P038801 eval 1997 -> non-FCS, P000216 eval 2008 -> FCS
  => country_fcs_status / country_lending_group are evaluation-vintage, NOT approval-time: excluded from features
projects API id-lookup (search.worldbank.org/api/v2/projects?format=json&id=...): HTTP 200, 3/3 returned
full record has 50 fields incl. approvalfy, board_approval_month, boardapprovaldate, lendprojectcost,
  ibrdcommamt, idacommamt, lendinginstr, prodline, sector1-3 (with Percent), themes, countryname, regionname
```

Split windows for the record (recomputed):

```
train  1956-2009: n=9741 pos=6891 neg=2850 msplus=0.7074 countries=179
eval   2010-2014: n=1488 pos=1174 neg=314  msplus=0.7890 countries=142
holdout 2015-2019: n=1097 pos=885  neg=212  msplus=0.8067 countries=133
stream MS+: ICRR 0.7605 (n=6828) / PPAR 0.7266 (n=3705) / PCR 0.6853 (n=1465) / EVM 0.6373 (n=466)
```

## Projects API cost

```
curl -s 'https://search.worldbank.org/api/v2/projects?format=json&rows=10000&fl=...' 
-> HTTP 200, 1,193,063 bytes, but returns 1,000 keys (page cap), 1.14 s
total projects: 22,729  -> 23 requests, ~27 MB total (estimate)
```

## Prior art found (web, 2026-10-22)

- Kraay & Tawara, World Bank Policy Research Working Paper 7001 — the Bank's own model predicting IEG
  ratings for active projects (2,729 IPF ops, 1995-2012); strongest predictors are TTL track record and
  CPIA during project life, both post-approval. Models in a working paper, no public splits/contract.
- Goldemberg/Jordan/Kenyon WPS 10532 (2023) — ML on WB project documents, predicts contribution to
  sector outcomes, explicitly not ratings.
- Hugging Face `lukesjordan/worldbank-project-documents` — 15.7k project documents, card states
  "no leaderboard yet" and "we have not done a train test split"; used by others "to predict project
  outcomes" but no packaged task exists.
- No Kaggle/HF/Zenodo ML-ready World Bank outcome-rating benchmark found (see novelty_check in record.json).

## Verdict

go — licence class A (CC BY 4.0), anonymous one-request bulk access, quarterly republication,
documented label process (IEG evaluation, six-point outcome scale), 12.5k rated projects with both
classes in every candidate window, clean approval-instant prediction timing after excluding the
measured evaluation-vintage columns. Headroom risk recorded: approval-time-only signal is unmeasured
and the Bank's own internal model leaned on post-approval features — the baseline triad decides at
construction whether this is a benchmark or a negative result.

## Construction session (2026-10-22, scheduled advancement tick)

Constructed, gate-qualified and re-accepted the approval-instant panel. All
commands from the repo root unless stated; scratch files deleted afterwards.

### Pre-construction probes (coordinator, bounded)

- `python3 .factory/wb_probe_fields.py` - pinned the exact outcome vocabulary
  (`Highly Satisfactory`, `Satisfactory`, `Moderately Satisfactory`,
  `Moderately Unsatisfactory`, `Unsatisfactory`, `Highly Unsatisfactory`,
  `Not Rated`), the 7-stream evaluation_type mix, and the projects API's
  full 50-field record on six spanning ids (1958/1972/1990/2005/2015/2019).
  Old projects ARE served (P009598, Calcutta Port, FY1958, amounts present).
- `python3 .factory/wb_probe_page2.py` - offset paging confirmed
  (`os=1000` returns exactly 1,000 records of 22,729); closing-year MS+
  shares computed for the RAP cross-check.
- RAP 2024 Figure O.3 (MS+ % by closing FY) extracted from
  `https://documents1.worldbank.org/curated/en/099845103072525633/pdf/SECBOS-e45e1b2e-4fff-4e52-8d27-c33709508fe8.pdf`:
  71 (FY13) -> 91 (FY23). Reconciliation probes
  (`wb_probe_rap_ipf.py`, `wb_probe_rap_cohort.py`): the panel runs 3-7
  points below the published series under every plausible cohort
  restriction (all-instruments / IPF-only / ICRR+EVM-only), same trend; the
  build therefore asserts the published TREND (FY13 at least 10 points
  below FY23; measured gap 18.5), not the level, and records the series.
- `python3 .factory/wb_probe_paged_shape.py` - **measured API quirk**: the
  paged query IGNORES `fl` for field selection; with `fl` it serves a
  search-result record (id, project_name, url, project_abstract only) and
  without `fl` it serves the full structured approval record (approvalfy,
  board_approval_month, boardapprovaldate, amounts, lendinginstr, prodline,
  sector dicts, mjsector/mjtheme lists) WITHOUT the fat abstract. The
  id-lookup path serves full records either way. The first dry run joined
  empty features for exactly this reason - caught by inspecting the written
  rows before any worker spend.

### Build (dry run then worker)

- Full local dry run with live fetches:
  `python3 -u candidates/wb-ieg-project-outcome/source/build.py --out <scratch> --work-dir <scratch>`
  - exit 0; gate run locally: 38/38 checks green (gate 1.4.0).
  - Inspection caught the empty-API-join bug above (all amounts missing,
    no approval months) and the `country[:10]` event-key truncation effect
    (83 "Republic of ..." borrowers share one prefix; 179 distinct countries
    -> 81 distinct prefixes in train). Kept `country` as the event key: the
    truncation is conservative (undercounts clusters), passes the gate with
    wide margin (eval 57 / holdout 55 distinct positive clusters vs minimum
    20), and both counts are recorded in summary.json and quality.json.
  - GE trust-fund records carry no approval metadata in the API (measured on
    samples: approvalfy/board_approval_month/boardapprovaldate all null) -
    approval_month_num=0 and amounts_missing=1 are genuine source gaps, not
    parse failures.
- Worker: `python3 scripts/assemble-job.py wb-ieg-project-outcome` (bundle
  declared in `source/bundle.json`), then plan (EUR 0.04 reservation),
  launch, collect, destroy:
  - wb-001 succeeded, exit 0, 385.3 s elapsed (worker 171926570, destroyed
    2026-10-22T22:26:31Z). Sources: 1 IEG CSV request (3,340,648 bytes,
    1.3 s) + 24 projects-API requests (23 pages + 2 supplementary
    id-lookup batches, +25 records; 54,486,121-byte merged JSON,
    22,636 records).
  - Gate 1.4.0 on the worker: 38/38 checks green, artifact
    b8345bcb5769e422... (full digest in the record).
  - Uploaded to staging release 421262457 (12 assets); fetched back via the
    asset API (octet-stream; the draft-release `browser_download_url` 404s -
    measured), all 11 manifest digests verified, and
    `qualify_dataset.py --accept` ACCEPTED on the coordinator.

### Panel facts (from the worker's summary.json, not restated by hand)

- train 9,598 rows / 6,891 positives (0.7180); eval 1,479 / 1,173 (0.7931);
  holdout 1,097 / 885 (0.8067). Positives match discovery exactly after the
  P122764 dedupe (discovery's eval n=1,488/pos=1,174 counted the duplicate
  row and included 9 Not Rated rows; the build's counts are the deduped,
  rated-only ones).
- Unobserved accounting: 151 Not Rated; 303 approved FY2020+;
  not-yet-evaluated (API-only, approved <=FY2019): train 1,724 / eval 719 /
  holdout 637 - the right-censoring is material in the recent windows and is
  now quantified; 2 ids not served by the API at all (P072979, P113625);
  1,215 rows with no amounts (mostly GE records).
- IEG-vs-API approval FY mismatches: 729 rows (+-1 FY convention; IEG CSV is
  canon, counted in summary).
- Reference baselines (stdlib, train-estimated): majority-class 0.717962;
  identity-only (country) AUC 0.6003 eval / 0.4909 holdout; calendar-only
  (country x approval_fy) the same (every eval/holdout cell unseen in train
  falls back to identity); agreement-type 0.5407/0.4844; practice-group
  0.5497/0.4948. No persistence leg exists at project grain.

### Baseline (full model, runner contract)

- wb-baseline-001 launched on worker 171927514 (EUR 0.06 reservation): fetch
  the five accepted files from staging release 421262457, re-accept through
  the gate, materialize the runner workdir, run the benchmark's own
  train.py + validate.sh verbatim. Result recorded in the record when
  collected.
