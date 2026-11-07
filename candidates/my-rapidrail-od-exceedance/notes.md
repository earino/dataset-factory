# my-rapidrail-od-exceedance — discovery notes

Opened 2026-11-07 (South & South-East Asia discovery tick). All probes read-only,
anonymous HTTP from the coordinator vantage; no bulk download; no construction.

## Lead origin

Regional tick named India/Indonesia/Philippines/Thailand/Vietnam/Malaysia. Existing
regional records cover the named institutions (CPCB packaged; IMD, data.gov.in, BPS,
PSA, PCD/air4thai, OJK, BMKG, PAGASA, Vietnam NSO, Singapore catalog all parked or
dropped with recorded blockers). New ground this session: the relaunched Malaysian
national open-data platform (data.gov.my, built by Jabatan Digital Negara; the same
platform that produced our published my-pricecatcher-weekly-increase), enumerated in
full. Its catalogue is overwhelmingly DOSM aggregate time series (inventory retained:
`references/catalogue_inventory_2026-11-07.txt`, 355 slugs). The event-derived panels
are the rail ridership origin-destination sets, published from anonymous tap-in/tap-out
gate transactions, with frozen annual editions and a documented daily publication
calendar. Rapid Rail (KV) daily OD was selected over the KTMB Komuter hourly variant
because measured Komuter pair-hour counts are tiny (sampled p50 = 2, p90 = 9 riders —
a threshold label at that scale is noise-dominated), while Rapid Rail pair-day counts
carry real signal (sampled p50 = 20, p90 = 3,240; complete pair-year series p50 90-4,374).

## Licence (checked first)

Class A. The dataset page's embedded metadata carries, verbatim (read 2026-11-07 from
`https://data.gov.my/data-catalogue/ridership_od_rapidrail_daily` `__NEXT_DATA__`,
i18n key `catalogue.license_text`):

> "This data is made open under the Creative Commons Attribution 4.0 International
> License (CC BY 4.0). A copy of the license is available Here"

Same instrument as `candidates/my-pricecatcher-weekly-increase/license.json` (the
published candidate from this platform). Developer portal footer (developer.data.gov.my,
read 2026-11-07): "License: CC BY 4.0" → creativecommons.org/licenses/by/4.0/.
Storage host serves the bulk files anonymously with no additional terms.

## Prediction contract — dated worked example (Asia/Kuala_Lumpur, UTC+8, no DST)

- Target day T: Tuesday 2026-11-10, 00:00–23:59 (+08).
- Prediction instant: 2026-11-10 07:00 +08 (before the operating day begins).
- Feature event window: all OD rows dated 2023-01-01 through 2026-11-08 (= T−2).
- First-available evidence for the last feature day (2026-11-08): the current-year
  edition file written on 2026-11-09 (observed write times 08:03Z; scheduled refresh
  22:00 +08 per the dataset page's `next_update`), i.e. available well before the
  instant. Day T−1 (2026-11-09) data is NOT available at the instant — measured
  publication lag is one day (see below), so features are honestly lag-2.
- Eligibility cutoff: pair active in the training window (has rows; excluding
  A0 pseudo-station rows and PYL05+ destinations).
- Label window: entirely after the instant (the whole of day T). No part of the
  target precedes the instant.
- Version policy: feature rows for completed years come from that year's frozen
  edition (2023/2024/2025); current-year rows from the digest-pinned build snapshot.
  The 2026 edition file observed on 2026-11-07 08:03:16 GMT carries `data_as_of`
  2026-11-06 23:59 as its last row — the one-day lag that forces the T−2 feature
  cutoff is measured, not assumed.

## Measured probes (commands runnable from the candidate dir)

- `python3 probe/edition_head_inventory_2026_11_07.py` — HEAD every edition
  (parquet + CSV, rapidrail + komuter). Rapid Rail results (2026-11-07):
  2023 csv 374,488,341 B / parquet 5,719,014 B, Last-Modified 2026-09-21;
  2024 csv 375,944,306 B / parquet 6,099,463 B, 2026-09-23;
  2025 csv 309,579,953 B / parquet 5,491,753 B, 2026-04-02;
  2026 csv 318,772,855 B / parquet 5,370,277 B, 2026-11-07 08:03 (daily).
  komuter_2020/2021/2022.parquet → 404 (page metadata lists them; they do not exist).
- `python3 probe/edition_head_tail_2026_11_07.py` — head/tail rows per edition:
  identical header `origin,destination,date,ridership`; date format drift
  ("2023-01-01 00:00:00" in 2023/2024 vs "2025-01-01" in 2025/2026 — normalize);
  2023 file opens with the `A0: All Stations,AG01: Sentul Timur` block; every
  edition tail is the `SP31: Putra Heights,SP31: Putra Heights` block; the 2026
  tail ends at 2026-11-06.
- `python3 probe/range_sample_2026_11_07.py` — bounded ~1.5 MB Range samples:
  2024 rapidrail: 26,708 sampled rows, 366 distinct dates present, 71 distinct
  station codes in sample, 17.5% zero-ridership rows; komuter_2024: p50=2.
- `python3 probe/extract_pair_blocks_2026_11_07.py` — the file is sorted
  (origin, destination, date): binary-searches each pair's contiguous block and
  extracts the COMPLETE pair-year series. 5 pairs, each 366/366 days, 0 missing
  dates: results summarised in record.measurements.pair_year_series_2024; full
  series in `probe/pair_blocks_2024.json`. Cost: 150 requests, 744,161 bytes,
  86.0 s wall. This is also the proof that per-pair absence is published as
  explicit zero rows (a sampled Saturday slice shows 29.3% zero pair-rows).
- `python3 probe/dump_catalogue_2026_11_07.py` — full platform catalogue dump
  (from the data-catalogue page's `__NEXT_DATA__`), retained at
  `references/catalogue_inventory_2026-11-07.txt`.

Also measured: the OpenAPI does NOT serve this dataset
(`api.data.gov.my/data-catalogue?id=ridership_od_rapidrail_daily` → 404 with
`"The data catalogue (ridership_od_rapidrail_daily) requested does not exist."`;
page metadata `exclude_openapi: true`). Bulk files are the documented channel.

## Known data-quality constraints (design inputs, recorded before construction)

1. `A0: All Stations` pseudo-station rows exist in BOTH directions at
   station-scale magnitudes (A0→AG01 p50 4,374/day). Excluded from the pair
   panel; whether they are station aggregates or unknown-tap censored rows is
   an explicit construction-time verification (compare against station sums),
   not an assumption.
2. Putrajaya Line destination censoring: 32/34 PYL codes never appear as
   destinations. Public data-request thread id 216 (2026-10-24, Universiti
   Malaya PhD candidate) documents it for the 2025/2026 releases; my own
   sampling of the frozen 2024 edition independently confirms (only PYL03 and
   PYL04 appear as destinations). Pairs into PYL05+ are excluded from the
   population; PYL origins are present and usable.
3. Edition date-format drift (see above).
4. 2023/2024 editions were regenerated in 2026-09: completed-year editions are
   the publisher's current published form, not archival vintages → the task is a
   current-compilation retrospective (evaluation_contract states this; no
   operational point-in-time claim), matching the ab-wildfire posture.
5. Network non-stationarity inside the window: the MRT Putrajaya Line phase 2
   opened during 2023 (new stations appear mid-2023); train-year 2023 contains
   the opening shock. Temporal splits carry this; record it in limitations.

## Five contracts (reconciled 2026-11-07)

- Redistribution: SUPPORTED — CC BY 4.0 on the publisher's own per-dataset
  instrument + platform developer portal; identical to the published PriceCatcher
  precedent. Class A.
- Prediction timing: SUPPORTED — instant statable (07:00 +08 on day T); every
  feature column individually documented by the publisher; one-day publication
  lag measured (file written 2026-11-07 carries data through 2026-11-06), so the
  T−2 feature cutoff is enforced by evidence, not convention; calendar features
  complete. Current-compilation vintage limitation recorded (no per-row
  historical vintages; retrospective, no operational-availability claim).
- Obtainable target: SUPPORTED — label is the day-T value of the same published
  `ridership` column; zeros published explicitly; label source excludable;
  censoring (PYL05+, A0) measured and excluded by rule.
- Split capacity: SUPPORTED with a named prerequisite — four editions spanning
  2023-2026; panel ~5.4M rows/year measured by size; disjoint year windows with
  both classes guaranteed by measured pair-year distributions; full counts
  (incl. day-clustered positives) are the first worker step, never presented as
  already computed.
- Not a mirror: SUPPORTED (novelty check recorded) — no public ML-ready Klang
  Valley rail benchmark exists; the metro-flow literature (SHMetro/HZMetro,
  SHMOD/HZMOD, MTA OD) covers other cities, finer time grids, regression
  targets, and researcher-hosted snapshots; contribution = new task family for
  the bench (urban transit demand), new geography, day-ahead pair-level
  exceedance contract on a maintained government platform.

## Uncertainties handed to construction

- Full split counts and day-clustered positive counts (first worker step).
- A0-row semantics (aggregate vs censored) — verify against station sums.
- Threshold choice: pair-relative (p90/p95 from training window) vs absolute;
  freeze before any baseline runs. Persistence-at-lag-2 will be a strong
  reference on commuter pairs; the pre-registered triad must measure headroom
  over it honestly (ab-wildfire precedent: full model did not beat persistence
  under day-cluster bootstrap).
- Re-HEAD the 2026 edition at build to record the digest-pinned snapshot; the
  publisher's frozen 2026 edition (~early 2027, judging by 2025's 2026-04-02
  freeze) is the durable re-verification target for the holdout.

## What this session did NOT do

No construction, no worker job, no labelled example derivation, no bulk download
through the coordinator, no qualification, no scoring. The five pair-year series
retained in probe/ are aggregate-count series extracted by bounded read-only
requests — discovery evidence, not a constructed dataset.
