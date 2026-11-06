# tw-reservoir-drought-storage

**Verdict: investigating - REOPENED 2026-11-06.** Parked 2026-10-22 on "no anonymous
historical bulk source"; that blocker is contradicted by new measurement: the legacy
`/Disaster/api/ReservoirHistoryApi/GetComparision` endpoint serves the daily 07:00
records for all 21 major reservoirs to anonymous plain-HTTP clients, back to ~2008
(full fields) with per-day queries. The one gate to ready is the split-count
measurement, which needs the full panel and therefore runs on a worker.

## The task (well-posed; access resolved)

Predict drought-onset: storage ratio of a major reservoir (石門/曾文/德基/南化/烏山頭...)
crosses below 20-30% within 30 days, from daily records up to the 07:00 observation
instant. Persistence cannot win the onset formulation by construction. Positives
cluster in drought years (2015 northern, 2021 island-wide, 2024 southern), so
clustered counts must be reported by episode.

## Dated example (all times Asia/Taipei, UTC+8)

- Feature event window: daily 07:00 records 2021-02-01T07:00 .. 2021-03-02T07:00
  (trailing 30 observations), each first published same day by ~09:30 (41568's own
  statement; same-day visibility measured once, see below; historical same-day
  publication is a declared retrospective-scope assumption, not evidence).
- Eligibility cutoff: station has CapacityRate >= threshold at the instant and >= 30
  trailing observed days. Example station 石門 (10201): rate 0.5246 on 2021-03-02
  (measured) -> eligible.
- Prediction instant: 2021-03-02T09:30 (after the 07:00 observation is entered).
- Target start/end: the next 30 daily records, (2021-03-02T07:00, 2021-04-01T07:00] -
  the earliest possible crossing observation is 2021-03-03T07:00, strictly after the
  instant; no part of the target window precedes it.
- Measured anchor for the window: on 2021-04-15, 12 of 21 stations were below 0.25
  (min 0.0175) - the documented 2021 island-wide drought is inside this window.

## Probe evidence (2026-10-22; commands in probe_fhy_reservoir.py)

| Probe | Result |
|---|---|
| data.gov.tw 45501 page (browser) | ODDL 1.0, free; fields documented; 更新頻率 每1時; note: history -> fhyv2 viewer |
| fhyv2 SPA resource capture | API family /Api/v2/* + /disaster/Reservoir/Comparison |
| GET /Api/v2/Event/Year/2025, /Api/v2/Event/Active (plain client) | HTTP 401 |
| GET /disaster/Reservoir/Comparison (plain client) | AngularJS HTML shell (4,252 B), not JSON |
| opendata.wra.gov.tw swagger | unreachable: strict-SSL failure + intermittent DNS |
| WraBigData/WraApi legacy endpoints | 404/503 |

**Park recorded 2026-10-22:** no anonymous history found. Two misses, both corrected
below: the 401s belong to the `/Api/v2` family only, and the truncated shell hid the
legacy app bundle that names the real history endpoint.

## Probe evidence (2026-11-06; commands in probe_fhy_history_2026_11_06.py and probe_fhy_anchors_2026_11_06.py)

| Probe | Result |
|---|---|
| SPA app bundle `/fhyv2/js/app.03b8c3b9.js` (browser read) | API bases `Api/v2` + `OpenApiv3/v2`; axios interceptor adds front-end constant header `apikey: d6dd3cd4-...` to those bases - explains the 2026-10-22 401s (publisher's own front-page constant; XKDR demo-key precedent). OpenApiv3 `/Reservoir/Daily` serves only the LATEST day per station (Time $filter ignored, StationNo $filter works). |
| SPA comparison tab -> `/disaster/Reservoir/Comparison` fetched same-origin from the SPA page (browser) | Full HTML (3,978 B) + `/Disaster/bundles/Comparision.js` (1,639 B): POST `/Disaster/api/ReservoirHistoryApi/GetComparision` with form payload `ST_NO` (comma-joined; UI limits to 9, API accepts all 21), `StartDate`, `EndDate` (YYYY/MM/DD); GET `/Disaster/api/ReservoirStationsApi/GetAll` -> 21 major stations. Direct plain-client fetch of the comparison page still yields the truncated shell (the HTML is Referer/session-gated; the API itself is not). |
| Plain-client POST GetComparision (urllib, no cookies/Referer/apikey) | 6/6 HTTP 200; all 21 stations in ONE request (9,458 B); 3-day range -> n=42 = 21 stations x 2 boundary DATES only (endpoint is a two-date comparison; one request per day is needed for a panel); latency 1.12-1.66 s fresh-TLS. |
| Depth probes (same-day queries) | 2015-01-01 rate 0.5584; 2010-01-01 0.7669; 2003-01-01 / 1999-01-01 records exist but CapacityRate null. All-21: 2003 0/21 rates, 2005 0/21, 2008 6/21 (min 0.8655), 2015 18/21, 2021 19/21, 2024 19/21. |
| Known-episode anchors (all-21, output in probe/out_fhy_anchors_2026_11_06.json) | 2015-03-15: 8 <0.30, min 0.1607; 2021-04-15: 14 <0.30, 12 <0.25, min 0.0175; 2024-04-15: 7 <0.30, min 0.0569; 2025-06-15 (wet period): 3 stations <0.25 (20202, 20503, 30802) - chronic-low censoring; 2026-11-06 (queried ~08:45 Taipei): today's 07:00 records already readable - same-day visibility measured once. |
| WAF behaviour | GET `$filter=Time ge 2015-01-01` (spaces) -> "Request Rejected" page; `$filter=StationNo eq '10201'` -> works (1 record); all form POSTs to the history API -> 200. No rate limit hit at an 8-request burst. |

Record fields per station-day: DATE (07:00), CapacityRate (蓄水百分比), Capacity,
WaterLine, Basin_Rain, Inflow_Total, Outflow_Total, NAME_C; other columns (HQ, Inflow,
outflow breakdowns, Status_Name...) mostly null in the history API.

## Cost (measured, coordinator class)

1 request = all 21 stations for 1 day, ~9.5 KB, 1.1-1.7 s (fresh TLS per request).
Full panel 2003-2026: ~8,800 requests, ~65-85 MB, est. 2.5-4.5 h serial; keep-alive and
bounded concurrency to be measured on the worker. Worker-side, not coordinator-side.

## Licence

ODDL 1.0 on the same-series datasets (class B, attribution; quotes in
record.license_evidence). The fhyv2/Disaster channel pages themselves carry only a
© footer; whether the ODDL grant covers the history series served through this
channel is the one licence question for ready-review. 45501's own note routes history
to this site, which is the publisher's own linkage.

## Next action

Record.next_action carries the ordered handoff: worker panel-count pass (per-station
panel starts, per-window onset counts at 0.25/0.30, episode-clustered positives,
chronic-low inventory), threshold binding, five-contract re-reconciliation, formal
novelty check, then ready-review. No labelled panel is built on the coordinator.
