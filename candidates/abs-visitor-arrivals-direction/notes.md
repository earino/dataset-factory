# abs-visitor-arrivals-direction - row-level notes

Session: scheduled discovery, 2026-10-22 (Oceania tick). Verdict: **go (ready)**, licence class A.

## Source identity

- ABS Data API (SDMX 2.1), dataflow `ABS,OAD_COUNTRY,1.0.0` - "Visitor arrivals and
  resident returns, Selected Countries of Residence/Destinations", monthly.
- Landing page:
  https://www.abs.gov.au/statistics/industry/tourism-and-transport/overseas-arrivals-and-departures-australia/latest-release
  (reference period August 2026, released 13/10/2026, 11:30am AEDT)
- API base: https://data.api.abs.gov.au/rest/ (user guide:
  https://www.abs.gov.au/statistics/application-programming-interfaces-apis/data-api-user-guide)

## Licence triage (first, 2026-10-22)

ABS "Privacy and legals" (https://www.abs.gov.au/privacy-and-legals): "All material
presented on this website is provided under a Creative Commons Attribution 4.0
International licence, with the exception of: the Commonwealth Coat of Arms, the ABS
logo, material protected by a trade mark, unit record data (microdata), content
supplied by third parties." -> class A. No per-dataset exception applies to OAD
aggregate time series.

## Commands and measured results

1. Dataflow inventory: `curl https://data.api.abs.gov.au/rest/dataflow/ABS` ->
   3,230,544 bytes; 1,228 dataflows. Parsed with `.factory/abs_flows.py`:
   OAD_COUNTRY among the tourism/transport flows (also RT "Retail Trade" - which the
   landing page shows CEASED with the June 2025 release, so retail was not taken).

2. Structure (`.factory/abs_structure_dump.py` on
   `data/api.abs.gov.au/rest/dataflow/ABS/OAD_COUNTRY?references=all`,
   100,939 bytes, 2.72 s):
   - CL_OAD_CAT_TRAVEL: `05 = Short-term (less than one year) Residents returning`,
     `06 = Short-term (less than one year) Visitors arriving`
   - CL_OAD_ARRIVALS_COUNTRY: 78 codes (names saved to scratch, e.g. 6203/OT7/TO2)
   - CL_TSEST: 10=Original, 20=Seasonally Adjusted, 30=Trend, 40/50=Sensitivity
   - DSD dimensions: CAT_TRAVELLER, COUNTRY_RESID, TSEST, FREQ
   -> every column's meaning is documented by the publisher; only Original (10) exists
   in this dataflow, so seasonality must be learned (calendar-only baseline is
   meaningful), and no SA column can leak the label.

3. Full panel fetch (`.factory/abs_oad_probe.py`,
   `https://data.api.abs.gov.au/rest/data/ABS,OAD_COUNTRY,1.0.0/all?format=csv&startPeriod=1991-01`):
   - HTTP 200, 3,308,454 bytes, 3.47 s, **1 request** (measured cost of the whole panel)
   - 59,452 observation rows; 428 months 1991-01..2026-08; 77 COUNTRY_RESID;
     2 CAT_TRAVELLER; TSEST=10 only; 0 missing OBS_VALUE
   - CSV columns: DATAFLOW, CAT_TRAVELLER, COUNTRY_RESID, TSEST, FREQ, TIME_PERIOD,
     OBS_VALUE, UNIT_MEASURE (NUM), OBS_STATUS, OBS_COMMENT

4. Label base rates (same probe):
   - MoM direction pairs: 58,082 (up 30,466 / down 30,048 / 568 flat) - near coin-flip,
     so a persistence-of-sign rule cannot dominate
   - YoY direction pairs: 56,843; per-year up/down e.g. 2004: 1,218/424; 2020: 159/1,492
     (pandemic collapse); 2022: 1,645/9 (reopening surge)
   - Split windows on the YoY label (candidate partition):
     train 1991-2014: up=24,166 down=13,575 flat=520; eval 2015-2019: up=5,588
     down=2,630 flat=61; holdout 2022-2026: up=6,167 down=1,533 flat=140.
     All windows carry both classes; every year inside each window has both classes.
   - 2020-2021 sit outside the candidate partition (either dropped as pandemic
     extremes or folded into train; construction decides and documents).

5. Prediction timing (observed release dates from the ABS release pages, read
   2026-10-22):
   - Aug 2026 reference period released 13/10/2026 (43 days after month end)
   - Jul 2026 released 11/09/2026 (42 days); Apr 2026 released 12/06/2026 (43 days)
   - Next-release schedule published: Oct 2026 due 15/12/2026; Nov 2026 due 19/01/2027
   - Note "Caution: Data in Data Explorer is currently released after the 11:30am
     release on the ABS website" (Jul 2026 page) - SDMX/website sync same day.
   -> prediction instant = release of month M; target month M+1 is unpublished at that
   instant; max observed lag 43 days.
   - Revision caveat (methodology History of changes): "March 2026, state or territory
     of stay/residence - Once linked Medicare data became available, the ABS
     reprocessed and revised overseas arrivals and departures data for March 2026,
     which was released in the April 2026 issue". Only the current vintage is
     downloadable; feature values are current-vintage, cutoff documented as an
     assumption (same posture as NHS A&E on this bench).

6. Known-event fixtures, verified directly in the fetched panel: 2020 border closure
   -> YoY down 1,492 vs up 159; 2022 reopening -> YoY up 1,645 vs down 9.

## Novelty

Prior art recorded by scripts/check-novelty.py (see record.json novelty_check):
tourism-forecasting literature and M-competition style series exist; Tourism Research
Australia publishes its own forecasts (a publisher cross-check product); no ML-ready,
publication-lag-gated, country-panel direction benchmark for Australian arrivals was
found. Verdict: differentiated.

## Construction pointer

Fetch panel (1 request), build (06-visitor, country) x month grid, features =
history <= published M + calendar + country identity, label = YoY direction of M+1,
splits per the candidate partition, baseline triad before any headroom claim. All bulk
work on the worker; the coordinator only ever holds the ~3.3 MB probe copy (deleted
after this session).
