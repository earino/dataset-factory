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
