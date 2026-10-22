# nz-ea-wholesale-price-exceedance - row-level notes

Session: scheduled discovery, 2026-10-22 (Oceania tick). Verdict: **go (ready)**,
licence class A (CC BY 4.0).

## Source identity

- Electricity Authority (NZ), EMI dataset "Final energy prices" under
  Real-time dispatch and pricing. Landing page:
  https://www.ea.govt.nz/data-and-insights/datasets/wholesale/dispatch-and-pricing/
  ("Real-time pricing was introduced in the wholesale electricity market on
  1 November 2022, replacing the ex-post pricing regime in place from the time the
  market started on 1 October 1996. ... interim prices will be declared to be final
  prices by 2pm the following business day.")
- Programmatic channel (anonymous, documented by the publisher's forum thread
  "New access arrangements to EMI datasets (retirement of anonymous FTP)"):
  Azure blob container
  `https://emidatasets.blob.core.windows.net/publicdata?restype=container&comp=list`
  with `prefix=Datasets/Wholesale/DispatchAndPricing/FinalEnergyPrices/`.

## Licence triage (first, 2026-10-22)

- EMI LegalInformation (read first-hand): "Unless indicated otherwise for specific
  items or collections of content ..., this copyright material is licensed for re-use
  under the Creative Commons Attribution (CC-BY) 4.0 international licence. In essence,
  you are free to copy, store, distribute and adapt the material..." Restricted
  material: emblems/trademarks, EMI tools/models, third-party works, s46 request
  responses. The price datasets are Authority content -> class A.
- Successor hub (https://www.ea.govt.nz/copyright-disclaimer-transparency/): same CC BY
  4.0 "owned by the Electricity Authority on behalf of the Crown".
- EMI retirement notice (https://www.emi.ea.govt.nz/): the Data & insights hub "will
  replace EMI". Migration risk recorded (pin URLs + digests at construction); the
  datasets are already catalogued on the hub, licence unchanged.

## Commands and measured results

1. Inventory (1 request, 2.80 s, 460,102 bytes):
   `curl "https://emidatasets.blob.core.windows.net/publicdata?restype=container&comp=list&prefix=Datasets/Wholesale/DispatchAndPricing/FinalEnergyPrices/&maxresults=5000"`
   -> parsed by `.factory/nz_listing_stats.py`:
   - 728 files: 360 monthly files `YYYYMM_FinalEnergyPrices.csv` 199610..202609
     (min 8,245,783 / median 10,012,278 / max 10,894,850 bytes; total 3,594.6 MB,
     no naming gaps) + 368 daily files `YYYYMMDD_...` 20251021..20261021
     (~312,808-348,002 bytes; total 119.7 MB). Grand total 3,714.3 MB.
   - Publication lag, Last-Modified minus trade date (all 368 daily files):
     min 0.75 d, p50 1.80 d, p90 3.80 d, max 5.80 d.
   - Note: `.factory/nz_ea_probe.py` (v1) crashed parsing the 1996 monthly file name
     as a daily date; diagnosed (name shape YYYYMM_), fixed, not a source problem.

2. File schema (ranged GET + whole-file reads):
   columns `TradingDate,TradingPeriod,PointOfConnection,DollarsPerMegawattHour`;
   48 trading periods/day; monthly files 346,392-370,512 rows; POC counts 238 (1997),
   249 (2008), 241 (2020, 2024).

3. Region mapping (publisher-published):
   `NetworkSupplyPointsTable/20261021_NetworkSupplyPointsTable.csv` (424,502 bytes,
   2,633 rows) columns include `POC code`, `Network reporting region ID`,
   `Network reporting region`, `Island`, `Start date`, `End date` -> island- and
   region-grain aggregation supported, with POC validity dates for point-in-time joins.

4. Era/event sample (4 whole monthly files + 12 daily files, 19 requests, 45.1 MB,
   75.1 s; market daily-mean $/MWh = mean over POCs x trading periods):
   - 199701: min 26 / p25 37 / median 42 / p75 46 / max 50; 0 days >$100
   - 200807: min 41 / median 135 / max 306; >100: 19, >150: 13, >200: 9, >300: 1
     (highest days 2008-07-01 $306, 07-07 $294, 07-09 $278)
   - 202006: min 72 / median 145 / max 287; >100: 28, >150: 12, >200: 5
     (mid-month event: 06-14..06-18 means $237-$287)
   - 202408: min 4 / median 436 / p75 757 / max 884; >200: 25 of 31 days, >300: 22
     (2024-08-05..08-08 means $815-$884 - the dry-year episode)
   - recent era, 12 days spread over 2025-10..2026-10: median 32 / max 165; 1 day >$100

5. Split capacity: candidate windows train 1996-10..2015-12 / eval 2016-01..2020-12 /
   holdout 2021-01..2026-10 each contain at least one measured high-price episode
   (2008-07 in train; 2020-06 in eval; 2024-08 in holdout) plus quiet periods
   (measured: 1997-01 in train; recent-era sampled days in holdout). Positives cluster
   into multi-day storage/weather episodes; exact per-window counts are computed at
   construction from the full files - the numbers above are sampled, measured, and
   labelled as samples.

## Prediction-timing evidence

- Documented instrument (publisher's dispatch-and-pricing page, read 2026-10-22):
  "At the end of the trading period, interim prices ... will be calculated ... If no
  pricing error claims are subsequently lodged, interim prices will be declared to be
  final prices by 2pm the following business day."
- Measured on the files: daily-file availability lag p50 1.80 d, max 5.80 d after the
  trade date. -> prediction instant = final-price publication for day D; features =
  published prices only; target = day D+k (k ~ 7) with the label source excluded.
- Vintage caveat: the Authority states it "may change information ... without notice"
  and historically regenerates file sets (forum thread: "we may infrequently regenerate
  entire sets of files"); monthly files' Last-Modified reflects regeneration, so only
  the current vintage is available - same current-vintage posture as the ABS/NHS
  candidates; documented as an assumption.

## Novelty

Prior art: Lago et al. EPF benchmark (five Northern-Hemisphere markets, day-ahead
*level* regression, no NZ); an AUT study "Electricity price forecasting in New Zealand"
(GARCH/SV vs ML on daily *levels* 2014-2022, five regions, no published artifact);
github.com/SoyeonIm/nz-electricity-market-analytics (single node OTA2201, level MAE,
no benchmark contract). None is an ML-ready exceedance task with splits and a scored
contract. Mechanical search results recorded by scripts/check-novelty.py in
record.json. Verdict: differentiated.

## Construction pointer

See record.json next_action. Bulk download is worker-scale (728 files, 3.7 GB
ESTIMATE from measured sizes); the coordinator only held a 45 MB sample, deleted
after this session.
