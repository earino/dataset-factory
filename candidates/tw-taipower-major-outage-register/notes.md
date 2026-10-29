# tw-taipower-major-outage-register

East Asia tick 2026-10-29. First utility-outage register assessed on the bench;
new task family for the region (per-incident outage restoration duration). Parked
on measured content depth + family crowding after the probes below. No worker was
launched; all probes ran from the coordinator (1 quality-mirror request) and the
supported browser.

## The task shape considered

For a major distribution outage in the Taipower flash-report register at occurrence
time t (Asia/Taipei), predict whether restoration takes > 60 min. Event grain with
both datetimes published - the cleanest utility-incident grain found in the region.

## Probe 1 - find the register (browser; portal is a Nuxt SPA)

- Plain HTTP to data.gov.tw search URLs -> HTTP 500 Nuxt shell (curl and first
  browser load). Not evidence of absent content: the homepage loads and the site's
  own search works.
- Keyword suggestion endpoint observed in page resources:
  `https://data.gov.tw/api/front/search/history/query/suggest?q=停電` -> 200.
- Site search navigates to `https://data.gov.tw/datasets/search?p=1&size=10&s=_score_desc&rft=停電事故`
  -> 2 results: dataset 166643 (annual PDF report) and dataset 122741 (the register).
  `rft=事故停電` returns 122741 only; `rft=台電事故` nothing further; `rft=速報`
  returns unrelated water-quality 速報 datasets - no sibling per-incident outage
  register exists on the portal.
- Dataset metadata API (anonymous, from page context):
  `https://data.gov.tw/api/front/dataset/detail?nid=122741` -> 200, 5,351 bytes:
  licence 政府資料開放授權條款-第1版, 免費, updatefreq 每1年, resource CSV
  vid 16112372 amount 102, url service.taipower.com.tw/.../d077011/001.csv,
  last_update_time 2025-06-16 13:02:39 Asia/Taipei.

## Probe 2 - fetch the register (1 request, coordinator)

- `service.taipower.com.tw` does NOT resolve from the coordinator (NXDOMAIN for
  all *.taipower.com.tw; measured with getent and gethostbyname_ex 2026-10-29).
  Recorded as a host constraint, not a source failure.
- The data.gov.tw quality mirror (found in the dataset page's Nuxt payload)
  resolves and serves the file anonymously:

```
curl 'https://quality.data.gov.tw/dq_download_csv.php?nid=122741&md5_url=8f7d7b0af4d16c3074393c7afba36244'
  -> HTTP 200, 9,559 bytes, 1.00 s (timed re-fetch)
```

- Schema (5 columns, documented on the dataset page): 項次 item no; 發生時間
  occurrence datetime (2024 vintage format `20241225T232700`); 事故名稱 incident
  name; 停電戶數 households affected (comma-grouped numerals); 復電時間
  restoration datetime.
- Publisher's inclusion criteria for 重大 (major) cases, quoted from the dataset
  note: (1) outage at key/important facility users or important assembly public
  places; (2) science parks / export processing zones / industrial zones /
  corporate HQ outage or curtailment; (3) secondary-substation incidents causing
  customer outage/curtailment; (4) planned-work outage exceeding 1 h with
  >= 1,000 households.

## Probe 3 - measured content (scripts: probe_fetch_and_stats.py)

Live register fetched 2026-10-29:

- 102 rows, every 發生時間 within 2024. Not multi-year.
- 0 missing occurrence/restoration, 0 negative durations, households 1..22,421
  (median 1,153), all 12 months present, September max (17).
- Duration minutes: min 0, p25 15, median 59, p75 108, max 2,427.
  >30 min 70.6%; >60 min 49.0%; >120 min 22.5%; >240 min 7.8%.
- Category mix by incident-name keywords: substation/feeder 60, water-utility 16,
  park/industrial 13, hospital 6, transport 3, other 4.

## Probe 4 - is there history anywhere? (Wayback CDX, the decisive probe)

```
curl 'http://web.archive.org/cdx/search/cdx?url=service.taipower.com.tw/data/opendata/apply/file/d077011*&output=json'
  -> 3 captures: 20241004143131, 20241004144522 (same day), 20260929233634
```

- 20241004143131 vintage (8,847 bytes): 91 rows, ALL 2023, ISO datetimes
  (`2023-12-30T06:18:00`). >60 min 51/91 (56.0%); all 12 months present.
  DATA DEFECT measured: 6/91 rows have 復電時間 BEFORE 發生時間, all same-date
  ~11-12 h apart (rows 65-69, 74 of that file; e.g. occurrence
  `2023-06-04T16:27:00`, restoration `2023-06-04T04:28:00`) - systematic 12-hour
  clock misentries in the publisher's register, not parse artifacts (both formats
  parse cleanly).
- 20260929233634 vintage (9,665 bytes): 102 rows, ALL 2024 - identical coverage
  to the live file. So as of 2026-09-29 the 2025 update had NOT landed: the
  yearly channel has slipped >= 15 months past year end. (Live resource
  last_update_time 2025-06-16.)
- CDX has no capture before 2024-10 at this URL. The publisher's 2022 reply said
  the file then contained 2019-2021; those vintages are not archived and the
  current file REPLACES yearly rather than accumulating. Measured obtainable
  history: 2 years, 193 events (91 + 102).
- Related dataset 166643 台灣電力公司配電線路事故分析 is a single annual PDF
  (its file-listing CSV fetched via the quality mirror: one row -> 001.pdf; the
  PDF has no Wayback capture). No multi-year per-incident sibling on the portal.

## Probe 5 - licence and publisher posture (dataset page, browser)

- 授權方式: 政府資料開放授權條款-第1版 (ODDL 1.0); 計費方式: 免費 -> class B.
- Publisher replies on the dataset page (their own words, translated):
  - 2026-era reply: "考慮停電事故資訊恐遭有心人士不當引用或作為商業應用...
    故目前採每年更新前1年度資料辦理" - the register is deliberately published
    once a year, prior year only, to limit misuse. This is the decisive timing
    fact: no operational/real-time channel exists for these events.
  - 2022-03-11 reply: the 2021-05-13 Xingda plant trip is generation-system and
    this register covers distribution-system cases only.
  - 2021-07-21 reply: an upload interruption had silently broken the 2020/2021
    update once before - the channel has failed before, and it has now slipped
    again.

## Probe 6 - novelty (web search, 2 queries)

Query 1: "power outage restoration time prediction dataset benchmark machine
learning" - active family: EAGLE-I county-level outage records 2014-2024 (ORNL,
used for county-hourly outage prediction, arXiv:2512.22699); Turkish-utility
outage-duration classification 95,454 events XGBoost (PMC11244009, 2024); NY
6-year utility restoration-time study, 16,000 outages (arXiv:2112.11374); ETR
prediction with longitudinal tabular transformers, 34,000 storm outages
(arXiv:2505.00225); public US datasets: Purdue-style major-outages register
(1,534 events, 57 columns), PG&E Q4-2019 outage scrape.

Query 2: "Taiwan Taipower outage dataset 停電 machine learning prediction" -
Taipower itself ran the 打造韌性城市之停電預測挑戰賽 (2018): village-level
typhoon outage counts 2014-2016 from the 停電通報系統, held-out targets
(Megi/Nesat/Haitang); public participant code github.com/frankbrkao/PFPC (pole
coordinates data.gov.tw 33305, village population 32973, Taipower sales data).
Taipower's own smart-grid pages (service.taipower.com.tw, reached via search
cache) claim 186 open datasets as of 2026-04-09.

Verdict: `differentiated` for this exact register/task (no packaged ML-ready
benchmark on it), but the occurrence direction already ran as a public Taiwan
challenge and the duration direction is a crowded literature family - see
record.json novelty_check and rejection_reason.

## Five contracts (reconciled)

1. Redistribution: SUPPORTED - ODDL 1.0 (class B), quoted; free.
2. Prediction timing: UNSUPPORTED operationally - yearly, prior-year-only
   publication by stated policy; channel already slipped 15 months. Retrospective
   formulation stateable (instant = occurrence; target window = (occ,
   restoration]; features are final-register vintage values with a documented
   caveat).
3. Target: DERIVABLE (restoration datetime), with measured defects (6/91
   negative-duration rows in the 2023 vintage, 0 in 2024) and censored negatives
   (four inclusion criteria; non-major outages unobserved).
4. Split capacity: FAILS on measured content - 193 events over 2 years,
   September/October clustering, future years dependent on the slipped channel.
5. Not a mirror: SUPPORTED for this exact task; family crowded (probe 6).

## Decision

PARK. Not a licence or access or schema rejection - a content-depth blocker plus
family crowding. Reopen paths in record.json next_action: (a) standing monthly
vintage collector into private staging (the file replaces yearly, so a skipped
vintage is lost permanently); ready-review at >= 4 distinct vintages; (b) worker-side
enumeration of service.taipower.com.tw open data (~186 datasets) for a richer
per-incident channel; (c) operator decision required for the family question either
way.

## Failure notes

- First fetch attempt of the original URL died on coordinator DNS (NXDOMAIN);
  the quality mirror is the documented fallback and is the channel the record
  pins.
- The portal's search URLs 500 for plain clients (Nuxt SPA). The homepage +
  in-page search + `/api/front/dataset/detail` are the working anonymous paths;
  do not re-try the CKAN-style `/api/3/action/package_search` (404 - this portal
  is not CKAN).
- The first `檢視資料` (view data) click hit the chatbot helper instead of the
  resource preview; the mirror URL in the Nuxt payload is the reliable route.
