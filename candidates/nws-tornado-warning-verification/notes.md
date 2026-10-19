# nws-tornado-warning-verification

**Verdict: GO (2026-10-19).** Status `investigating`; novelty search recorded by
`scripts/check-novelty.py` (differentiated). Construction belongs to an advancement session.

## The task

For an NWS tornado warning at the moment it is issued, predict whether it will be
verified - at least one tornado report inside its storm-based polygon during its
valid time. Features are only what the issuance itself carries (WFO, forecaster,
issue time, counties, polygon geometry, tags, optional full product text); the
verification outcome is the label.

## Probes (2026-10-19, anonymous, from the coordinator)

### cow.json contract discovery

| Command | Result |
|---|---|
| `GET https://mesonet.agron.iastate.edu/api/1/cow.json?year=2023&wfo=DMX&phenomena=TO&significance=W` | HTTP 422 `{"detail":[{"type":"missing","loc":["query","begints"]},{"type":"missing","loc":["query","endts"]}]}` - the deployed API requires `begints`/`endts` (ISO8601). The cow HTML page still says "None of the parameters are required"; that text is stale. Read the error text, do not guess. |

### National TOR-year pulls (the whole construction unit)

| Query | Result |
|---|---|
| `begints=2013-01-01T00:00Z&endts=2013-12-31T23:59Z&phenomena=TO&significance=W` | HTTP 200, 19,593,733 bytes, 38.4 s; **1,832 events, 441 verified (0.241)**; 94 WFOs; 411 forecasters; 170 active days; **100 days with >=1 verified warning**; stats FAR[1]=0.759 |
| `begints=2023-01-01T00:00Z&endts=2023-12-31T23:59Z&phenomena=TO&significance=W` | HTTP 200, 28,389,049 bytes, 59.5 s; **2,531 events, 656 verified (0.259)**; 96 WFOs; 514 forecasters; 201 active days; **115 days with >=1 verified warning**; stats FAR[1]=0.741 |

Positives cluster by outbreak day, so 100-115 independent positive days per year is
the split-capacity figure, not 441-656 rows.

### Per-event record (wfo=DMX, 2023, 222,257 bytes)

`events` is a GeoJSON FeatureCollection (the first probe wrongly assumed a list).
Feature properties, verbatim from the probe:

`year, wfo, phenomena, eventid, issue, expire, statuses, fcster, svr_tornado_possible,
significance, hailtag, windtag, carea, ar_ugc, lat0, lon0, perimeter, parea,
sharedborder, product_id, status, stormreports, stormreports_all, verify,
tor_in_svrtorpossible, lead0, areaverify, product_text (URL), link` + MultiPolygon geometry.

- Label source (excluded from shipped features): `verify`, `stormreports`,
  `stormreports_all`, `lead0`, `areaverify`, `statuses`, `status`.
- Features available at issuance: everything else, plus the linked full warning
  text at `product_text` (IBW tornado/damage-threat tags, storm motion).
- Natural key: `(year, wfo, eventid)`; feature id e.g. `2023DMX1TOW1`;
  `product_id` (e.g. `202303311740-KDMX-WFUS53-TORDMX`) ties to the archived text.

### Licence and terms (read 2026-10-19)

- NWS: "The information on National Weather Service (NWS) Web pages are in the
  public domain, unless specifically noted otherwise" - https://www.weather.gov/disclaimer
- IEM: "The materials found on this website are in the public domain and may be used
  freely by anyone for any lawful purpose. Attributing the Iowa Environmental Mesonet
  of Iowa State University would be appreciated." - https://mesonet.agron.iastate.edu/disclaimer.php
- Caveat to carry on any release: "Data presented here is unofficial and should be used
  for educational purposes only." - https://mesonet.agron.iastate.edu/cow/
- Cow's own methodology page documents the buffered-LSR-in-polygon verification;
  NWS Instruction 10-1601 documents the official concept cow reimplements.

### Cross-check against published summary products

- cow FAR[1]: 0.759 (2013), 0.741 (2023).
- Published tornado-warning FAR 2014-2023: 0.69, and tornado emergencies 0.03
  (Keylon 2025, arXiv 2510.25011). DOC OIG: NWS met its GPRA false-alarm-ratio goal
  in 9 of 12 recent fiscal years. Same ballpark; no contradiction.
- Known-event fixture to pin at construction: the 2022-04-16 northern-Arkansas
  nontornadic storm behind all 3 documented tornado-emergency false alarms
  (arXiv 2510.25011) - its repeated TOR warnings must read `verify=false`.

### Costs

Measured: one national TOR-year pull = 20-28 MB / 38-60 s from this host class.
Construction 2008-2024 = 17 such pulls (~500 MB, 12-17 min) - per-year cost measured,
the sum is arithmetic over those measurements; re-measure once on the worker class.
ESTIMATE (labelled): optional per-warning product-text enrichment is one ~2-5 KB
request per warning (~40,000 warnings 2008-2024); measure on a 500-warning sample
before committing to it.

### Novelty (searched 2026-10-19, before any probing of the source)

Prior art found and why this is different:

- NWS/IEM publish *verification statistics* (POD/FAR per WFO) and cow computes the
  per-warning verdict, but neither ships a prediction task.
- NOAA-adjacent ML papers use warnings as *targets* at storm-minute granularity with
  radar/satellite/lightning features (Random-Forest nowcast, MWR 2021; WAFS target
  choice study 2025) - different unit, different features, case-study periods.
- The 2016-18 tornado-warnings study (6,881 warnings) diagnoses warning performance
  from radar rotational velocity + STP - a diagnostic analysis, not a released task.
- arXiv 2510.25011 analyses tornado emergencies 2014-2023 from IEM archives - it uses
  the same archive as a research input, which is precedent for IEM as a source.

Ours: per-warning, issuance-metadata-only prediction, full 2008-2024 history, frozen
temporal splits, shipped as a scored runner contract. Recorded as `differentiated` by
`scripts/check-novelty.py` in the record.
