# jp-moe-pollen-exceedance

MOE Hanako-san automatic pollen counter archive (env.go.jp), 2003-2021, as a
retrospective station-day high-pollen exceedance benchmark. East Asia tick,
opened 2026-10-28. All probes ran anonymously from the coordinator.

## s1. Why this source, this tick

East Asia queue check (2026-10-28): every existing JP/KR/TW/HK/SG candidate is
parked on an operator decision or credential (`jma-typhoon-rapid-intensification`
dropped as mirror; `kr-kosis-kma-access`, `singapore-datagov-catalog`,
`hk-datagov-portal`, `hk-red-tide-sighting`, `tw-reservoir-drought-storage`
parked; `tw-typhoon-day-closure` investigating/advancement). JMA's other families
are family-blocked by the recorded note in the jma-typhoon record (earthquake
felt-intensity = bmkg family, river = malaysia-river family; reopening needs an
operator decision naming the family). Taiwan PCC procurement was considered and
rejected without probing: `chilecompra-tender-outcome` (dropped 2026-10-23,
operator-directed, measured no-headroom: model 0.4752 vs unspsc_only 0.5707,
day-clustered CI [-0.1134, -0.0744]) is the family precedent; a second
tender-outcome member is an operator decision, not a discovery probe.

Pollen is a phenomenon no bench candidate covers: the air-quality exceedance
family (cpcb-aqi, defra-aurn, air4thai-parked) is chemical pollutants; this is
a biological allergen with an annual pulse and a health-exposure framing.
Formulation, splits, gating and the retrospective framing are ours.

## s2. Commands and results (reproducible)

Committed probe: `python3 probe_archive.py` (writes `evidence_2026-10-28.json`).
Session-scratch precursors (same logic, kept only here as command history):
`/opt/data/cache/scratch/probe_jp_pollen_1..7.py`, `probe_jp_pollen_7b.py` (deleted at
close-out; the committed script supersedes them).

Measured 2026-10-28, all anonymous HTTP GET, no key:

- Archive page https://www.env.go.jp/page_00209.html -> 200, 57,868 B.
  Two download blocks: 〈花粉データ〉 113 files (2003: 1 region; 2005: 3; 2007: 5;
  2008-2021: 7 region files per season), 〈アメダスデータ〉 110 files (2005-2021).
- Kanto 2021 pollen file /content/000071045.xlsx -> 200, 284,760 B.
  Sheet 時別: 3,602 rows = 2 header + 3,600 hourly rows = 150 days x 24 h,
  first data row 2021-02-01 h01, last 2021-06-30 h24. Columns: 年/月/日/時 then
  one count column per station; 14 station names matched by conservative suffix
  heuristic, 16 station columns visible in the raw header dump (both are lower
  bounds; exact count is a construction-time parse).
- In-header missing-value codes (publisher-documented, in-file):
  `空白:未観測または通信障害による欠測` (blank = unobserved/comms outage),
  `-9998:降雪による欠測` (snow), `-9997:黄砂による欠測` (Asian dust),
  `-9996:その他の欠測(前後の時間や周辺観測値と比較して不自然なデータ)`
  (removed as unnatural vs neighbouring values - proof of post-hoc quality edits,
  i.e. the archive is a cleaned vintage, recorded as a timing caveat).
- National 2021 pollen block: 7 requests, 1,736,797 B, 4.01 s.
  Region files: Hokkaido 116,068 B / Tohoku 207,109 / Kanto 284,760 / Chubu
  298,218 / Kansai 261,551 / Chugoku-Shikoku 299,128 / Kyushu 269,963.
  Station-name estimates (heuristic, undercounts): 1+10+18+20+13+19+13 = 94+.
  Literature: ~120 sites nationally (Kawatsu et al 2019, PMC6685964; NBER w31593:
  120 stations, 2-3 per prefecture; comprehensive since 2008).
- AMEDAS block availability: Range request /content/000071041.xlsx -> HTTP 206,
  content-range total 550,625 B, PK zip magic (valid xlsx). Publisher pairs the
  feature weather data with the label network on the same page.
- Current-era successor (instrument change, NOT this candidate's target):
  https://www.env.go.jp/chemi/anzen/kafun/kakohisan.html -> 200, 42,770 B; annual
  season Excel files for 令和6年 (2024) and 令和7年 (2025), Durham method, 単位:個/cm2,
  sheet 令和7年 日々のスギ花粉の飛散量報告, 36,966 B fetched. Different instrument
  and unit from the KH-3000 era -> regime break; excluded from the target.
- System termination: MOE press 110339 - observation/provision ended
  2021-12-24 (事業終了 noted on the archive page itself). Live pollen feeds are
  now private operators (tenki.jp, Weathernews); not used.
- Licence (publisher's own instrument, read 2026-10-28,
  https://www.env.go.jp/mail.html): PDL 1.0 applies to site content absent a
  rights notice; archive pages carry none. Attribution (出典) required; edited
  content must state the editing. Only extra restriction is Survey Act for GSI
  maps (not these files). Class A.

Extraction cost: one season's pollen block measured 7 req / 1.74 MB / 4.0 s;
full-panel ESTIMATE (arithmetic, labelled): 223 requests, ~55 MB, minutes on
this class; 2008-2016 files are binary .xls (worker-side xlrd needed).

## s3. Dated example (named timezone JST)

Station 東京都多摩小平保健所 (Tokyo Tama-Kodaira public health office, Kanto
2021 file, column T in the header row).

- Feature event window: 2021-02-01 00:00 JST through 2021-03-14 23:59 JST
  (hourly pollen counts at the station + paired AMEDAS hourly weather, all
  timestamps inside the window; the first observation in the file is
  2021-02-01 01:00 JST, row 3 of the sheet).
- First-available timestamps/version: each hourly value was published in real
  time while the system ran (MOE press 4673: hourly-updated display); the
  archive vintage is post-season and includes -9996 post-hoc removals, so the
  task claims no operational availability of the cleaned values.
- Eligibility cutoff: computed from a trailing pre-instant window only
  (e.g. valid observed days in the 14 days ending 2021-03-14), never from
  full-season validity.
- Prediction instant: 2021-03-15 00:00 JST.
- Target window: 2021-03-15 00:00 JST through 2021-03-15 23:59 JST (the
  station's 24 hourly counts for 2021-03-15, none of which exist at the
  instant).
- Target: sum of those 24 hourly counts >= threshold (ours, base rate to be
  measured), with the day excluded if fewer than 20 of 24 hours are valid
  per the in-file codes.

## s4. Five-contract status (2026-10-28)

1. Redistribution: SUPPORTED (PDL 1.0, class A, quoted).
2. Prediction timing: SUPPORTED for a labelled retrospective benchmark; the
   -9996 post-hoc clean-up means no historical-operational-availability claim.
   UNRESOLVED-as-operational by design, and recorded as such.
3. Target: SUPPORTED (daily sum of hourly counts, publisher-documented units
   and missing codes); threshold ours; taxon semantics (sugi vs sugi+hinoki
   for the single count column) to pin from MOE documentation at construction.
4. Split capacity: PARTIALLY measured. 14 national seasons exist; 2021 fully
   enumerated; full per-season station-day and positive counts are the bulk
   measurement prerequisite (not done in this session - no bulk parse here).
   Clustered effective sample = seasons (~14), must be reported with the
   station-day counts.
5. Not a mirror: SUPPORTED (s7 searches); check-novelty.py verdict recorded.

## s5. Failure notes

- First hostname guess `pollen.env.go.jp` did not resolve (DNS NXDOMAIN); the
  archive lives on env.go.jp static pages, not a subdomain. Recorded so the
  dead name is not retried.
- probe 5's 400 KB read of an AMEDAS xlsx failed BadZipFile - truncation by the
  read limit, not an access failure; Range read confirmed the file is a valid
  zip. Recorded to prevent misreading it as a blocked source.
- First block-parse of the archive page walked past the pollen block into the
  AMEDAS block (14 files/season counted as pollen). Fixed by cutting the
  segment at 〈アメダスデータ〉; committed script is the corrected version.

## s6. Regional context recorded per tick policy

Korea (KOSIS/KMA) and Singapore: re-probed 2026-10-20, parked on operator
credential/family decisions; no new evidence this tick, no re-probe spent.
Japan e-Stat: covered this tick in `japan-estat-portal` (dropped, API gate +
aggregate-only). Hong Kong/Taiwan parks unchanged.

## s7. Novelty searches (2026-10-28, from the coordinator)

Queries run (web_search): "pollen prediction machine learning benchmark
dataset public splits"; "Japanese cedar pollen ... Kaggle OR benchmark";
"環境省 花粉観測システム はなこさん 過去データ"; "Japan Ministry of the
Environment pollen observation system hourly data download".

Findings (no packaged, split, scored ML-ready pollen benchmark on this panel
or any national panel):

- Krakow birch/grass category ML (PMC12915917): single city, 1991-2024 data,
  but only a minimal 2022-2023 dataset on OSF (DOI 10.17605/OSF.IO/9YZCF);
  full data by email request to Jagiellonian University. Not a redistributable
  benchmark, one city.
- EUMETNET AutoPollen Munich campaign study: one campaign, 6,220 points,
  low-cost sensor calibration framing.
- Luxembourg PolnPy (data.public.lu): scraped from pollen.lu, daily 1992-2018,
  "License Not Specified" in the catalogue. Not usable, tiny.
- Raleigh NC study: 433 records, one sampler, single location.
- Hanako data in academic use - causal/descriptive only: NBER w31593
  (pollen-accidents, ambulance records), Tohoku DP TUPD-2026-010
  (pollen-suicide panel), Kawatsu et al 2019 (phase synchronisations). None
  ships a prediction task, splits or a scored contract.
- Japan's live pollen forecasts are private operators (pollen is not legally
  weather, so no forecast licence is needed; MOE supplies inputs only -
  watabi.org explainer, cross-checked against MOE pages).
- Pollen AI Atlas (arXiv 2606.17809): microscopy image benchmark, a
  different task entirely (grain recognition, not airborne-count prediction).

Search scope limitation: web search only, English + Japanese query terms; no
guarantee an unindexed private benchmark does not exist. Verdict recorded via
scripts/check-novelty.py: differentiated.

## Count-column taxon pinned + archive format split (2026-10-31, East Asia tick)

- MOE press release 4673 (https://www.env.go.jp/press/4673.html, fetched 2026-10-31)
  documents the Hanako display/download data as "リアルタイムの花粉飛散データ（個数/m³）
  （当分の間 スギ花粉数）" and "過去の花粉飛散データ（個数/m³）（当分の間 スギ花粉数）",
  with per-station "24時間の花粉飛散数" tables and per-day CSV download. So the single
  count column in the archive files is publisher-documented as SUGI (Japanese cedar)
  pollen, grains/m³, hourly -> daily 24-hour sum. Resolves next_action item (2).
  The "当分の間" wording is a publisher caveat that the column may later widen to other
  taxa; the archive terminated 2021-12-24, so for this closed archive the column is sugi.
- Archive file formats measured (worker job east-asia-measure-001 log + magic-byte probe):
  64 of 113 pollen files are OLE2/BIFF .xls (magic d0cf11e0...), covering 2003-2014;
  the 2015-2021 seasons (49 files) are zip .xlsx. The 2026-10-28 probe only parsed a
  2021 xlsx sample, so the "14 seasons with 7 regions" arithmetic over-counted the
  machine-readable (zip) era by 7 seasons: 2008-2014 are .xls. Parsing both eras needs
  xlrd (worker job 002); zip-only parsing would cover 7 seasons (2015-2021).
- 2014 Hokkaido .xls parsed on the coordinator (xlrd, isolated install) as a layout
  fixture: header 年/月/日/時 + station columns (札幌,函館,旭川,帯広,...), 3,600 data
  rows, trailing legend column (-9998:降雪による欠測), station-day counts computed.
