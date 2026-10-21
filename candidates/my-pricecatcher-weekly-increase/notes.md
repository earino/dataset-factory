# my-pricecatcher-weekly-increase — probe notes

Discovery session 2026-10-21 (regional focus: South & South-East Asia). Verdict: **go** (status
ready). All commands run from the repository root on the coordinator unless stated.

## Access probes

- `curl -A "<UA>" -o /dev/null -w ... https://data.gov.my/` → HTTP 200, 142,373 B. Portal live.
- `curl ... https://developer.data.gov.my/` → HTTP 200, 48,218 B. Documents Data Catalogue API,
  OpenDOSM API, Transport API (GTFS/GTFS-R), Weather API. Query params documented: limit, filter
  (contains/icontains/range), sort (-column), date_start/date_end.
- `curl ... "https://api.data.gov.my/data-catalogue/?id=fuelprice&limit=2"` → 200, weekly fuel
  prices JSON (API works with the trailing slash; without it the host 301s to the slash path).
- `curl ... "https://api.data.gov.my/data-catalogue/?id=pricecatcher&limit=6"` → **404**
  `{"status_code": 404, "details": ["The data catalogue (pricecatcher) requested does not exist."]}`
  — pricecatcher is bulk-only by publisher design (stated on the dataset page).
- `curl -I ... https://storage.data.gov.my/pricecatcher/pricecatcher_2026-09.csv` → 200,
  content-length 45,137,790, last-modified Mon, 12 Oct 2026 06:42:57 GMT.
- `.../pricecatcher_2026-10.csv` → 200, content-length 20,407,078, last-modified Wed, 21 Oct 2026
  12:10:13 GMT (current month, filling).
- `.../pricecatcher_2022-01.csv` → 200, content-length 65,359,198 (earliest edition present).
- `.../pricecatcher_2026-09-01.csv` → 404 (name pattern is `pricecatcher_YYYY-MM.csv`).
- `.../lookup_premise.csv` → 200, 486,306 B; `.../lookup_item.csv` → 200, 56,042 B.
- Ranged reads: `curl -r 0-2047 .../pricecatcher_2026-09.csv` → header
  `date,premise_code,item_code,price`, first rows dated 2026-09-01. `curl -r -2048
  .../pricecatcher_2026-10.csv` → tail rows dated 2026-10-21 (same-day freshness, measured).

## Licence (measured)

- `curl ... https://data.gov.my/data-catalogue/pricecatcher` → 200, 84,619 B; page-embedded
  metadata `license_text`: "This data is made open under the Creative Commons Attribution 4.0
  International License (CC BY 4.0). A copy of the license is available Here" (link to
  creativecommons.org/licenses/by/4.0/). Same statement on OpenDOSM's mirror.
- Publisher caveat on the same page: data is collected for price surveillance; "excellent for
  high-frequency analysis of specific items in specific locations"; "Inflation analysis should be
  conducted using DOSM's CPI data".

## Panel and label probes

- Downloaded two month files (bounded sample, deleted after measurement): `pc_2026-08.csv`
  (50,122,871 B) and `pc_2026-09.csv` (45,137,790 B), ~3.7-3.8 s each from the coordinator.
- `python3 .factory/probe/panel_stats3.py` (10% premise subsample, premise_code % 10 == 0, kept
  after the full-panel version OOMed at 1.9 GiB RAM — the coordinator cannot aggregate the full
  3.7M-observation panel in memory; this is a coordinator limit, not a source defect; a worker
  aggregates it trivially):
  - rows/month: 2026-08 = 1,933,285 (29 of 31 days; 2026-08-01..2026-08-30),
    2026-09 = 1,742,320 (28 of 30 days; ..2026-09-29)
  - 0 duplicate (date, premise_code, item_code) rows in both months
  - full-sample panel: 2,158 premises x 343 items; subsample: 216 premises x 326 items
  - 7 weekly transitions (both weeks >= 6 covered days), pairs >= 3 obs/week:
    increase rate 0.2217, 0.1947, 0.1823, 0.1774, 0.1809, 0.1548, 0.1875;
    decrease rate 0.1604, 0.1950, 0.2014, 0.1621, 0.1791, 0.1862, 0.1448;
    flat 0.61-0.67; eligible pairs 3,911-4,031 per transition (subsample);
    items with >=1 increase: 54-58; top-10 items' share of increases: 0.38-0.45.
  - results also saved to `.factory/probe/pc_probe_results.json` (scratch, not committed).
- Item lookup (56,042 B, 797 items, 60 categories) read in full; sugar items identified for the
  2022-11 subsidy-removal fixture: GULA PUTIH BERTAPIS KASAR (1589), GULA PUTIH BERTAPIS HALUS
  (1590), both 1kg.
- Premise lookup schema (ranged read): premise_code, premise, address, premise_type, state,
  district.

## Cross-check against publisher summary

- The Star, 2025-12-04 (parliamentary written reply by minister Armizan), retrieved via search:
  programme covers "2,170 premises and keeps tabs on 316 items across six categories, supported by
  more than 850 price monitoring officers" with "daily, weekly and monthly checks" — corroborates
  the measured panel (2,158 x 343; lookup 797 items of which ~343 actively quoted).
- Publisher data-request ticket log (data.gov.my/data-request, via search): 2026-10-06 ticket
  complaining pricecatcher stale since 24 Sep 2026 — evidence that refreshes can stall >1 week;
  construction must hash file snapshots and record last-modified as observed lag.

## Novelty

`check-novelty.py` verdict `differentiated` recorded 2026-10-21 (3 queries). Prior art is
demand-forecasting (M5, Store Item Demand, Rossmann, Favorita: sales target, price a feature) and
equity price-movement classification; no retail micro-price week-ahead increase task found on
Kaggle/HF/arXiv/web by mechanical search.

## Coordinator-side scratch

`.factory/probe/pc_2026-08.csv`, `pc_2026-09.csv` (95 MB total), probe scripts and results live
under the repository's scratch `.factory/` — never to be committed; delete after the session.
