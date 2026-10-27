# malaysia-river-danger-exceedance - probe evidence (2026-10-20, all anonymous)

## Current-conditions pages (working)
    curl "https://publicinfobanjir.water.gov.my/?lang=en"          -> 200, 93,377 bytes
    curl ".../aras-air/data-paras-air/?state=KEL&lang=en"         -> 200, 76,926 bytes
       - per-station rows with 'Danger Level:' / 'Warning Level:' / 'Alert Level:' /
         'Normal Level.' threshold columns (grep-measured)
       - 15 state options: PLS, KDH, PNG, PRK, SEL, WLH, PTJ, NSN, MLK, JHR, PHG, TRG, KEL, SRK, SAB, WLP
    Station codes seen in the KEL page HTML: AAAG9200, CC2127, FBC002, FF0084, FF7300, OY416.

## Historical trend endpoints (extracted from the trend page JS, lines 1300/1409/2752/3327)
    /wp-content/themes/enlighten/query/searchresulttrenddata1hour.php?lang=en&state=<S>&district=<D>&station=<ST>&from=<F>&to=<T>&datafreq=<FREQ>
    /wp-content/themes/enlighten/query/searchresultwaterleveldtlead_rptdb.php?station=<ST>&from=<F>&to=<T>&datafreq=<FREQ>
    /wp-content/themes/enlighten/query/searchresulttrenddata15min.php, searchresultrainfalldthourlylead_rptdb.php, searchresulttrendlead.php
    helpers: searchdistricttrend.php?name=, searchstationTrend.php?lang=en&name=

## Historical probes (failed this session - the park reason)
    searchresulttrenddata1hour.php?lang=en&state=KEL                      -> "Tiada data / No data"
    searchstationTrend.php?lang=en&name=KEL                               -> only "Choose Station"/ALL placeholder
    searchdistricttrend.php?name=KEL                                      -> only "Pilih Daerah"/ALL placeholder
    searchresultwaterleveldtlead_rptdb.php?station=CC2127&from=2026-07-01&to=2026-07-03&datafreq=60
       (and 01/07/2026-03/07/2026 variants, and station=ALL)              -> {"count":,]}No result
    latestreadingstrendabc.json at /, /api/, /wp-content/themes/enlighten/ -> 404
    Endpoints are alive and anonymous; the exact parameter contract (district/station keys,
    date format) was not captured. Unpark step: real-browser capture of the trend page XHR.

## Licence
    grep of home/state/trend HTML for copyright|hak cipta|terms|privacy: no licence text found.
    data.gov.my homepage (fetched, 140,945 bytes) advertises 'flood-warning' and 'rainfall'
    catalog categories, but dataset pages load client-side; entry not located this session.

## Prior art checked (2026-10-20)
    Caravan (arXiv 2212.00719) - global river DISCHARGE regression benchmark; Google Flood Hub -
    operational forecasts, not a dataset; FloodCastBench (2025) - coastal; Wupper/LamaH-CE
    studies - discharge regression. No packaged official-threshold EXCEEDANCE classification
    task on this publisher's telemetry found.

## 2026-10-28 session (regional tick: South & South-East Asia): portal redesigned; access contract resolved; history window is 7 days only

The recorded unpark step 1 (real-browser capture of the OLD trend-page XHR) is now
OBSOLETE: the portal was rebuilt between 2026-10-20 and 2026-10-28.

    curl -sL https://publicinfobanjir.water.gov.my/                          -> 200, 45,868 bytes (home; was 93,377 bytes on 2026-10-20)
    curl -sL https://publicinfobanjir.water.gov.my/trend-hujan-aras-air?lang=en -> 404 (old trend page gone)
    curl .../wp-content/themes/enlighten/query/searchresultwaterleveldtlead_rptdb.php?station=... -> 404
    curl .../wp-content/themes/enlighten/query/searchdistricttrend.php?name=kelantan -> 200 but body is a "Notis Gangguan" maintenance image (320 bytes)

New structure: /rainfall and /waterlevel live dashboards; /waterleveldata/<State> per-state
tables; state JPS subdomains infobanjirjps<state>.water.gov.my for per-station graphs.

New JSON API (Laravel), anonymous; a public bearer token is embedded in every portal page
(measured in kelantan_wl.html inline JS): /api/district, /api/station, /api/detailstation,
each POST with {"state":..., "district":..., "station_name":..., "parameter":"waterlevel"}.

    curl -X POST -H "Authorization: Bearer <page token>" -d '{"state":"Kelantan",...}' \
         https://publicinfobanjir.water.gov.my/api/detailstation
    -> 200, 12,620 bytes, 29 stations; per station: station_id, station_name, district,
       basins, last_update, water_level, normal, alert, warning, danger (official
       thresholds), trend, wl_severity, graph_url. The label definition (official Danger
       Level) is carried per station by the publisher itself.

Per-station graph data (the only historical series on the public web):

    curl https://infobanjirjpskelantan.water.gov.my/WaterLevel/GetWaterLevelGraph/101
    -> 200, 95,195 bytes, 2,068 points at 5-min cadence covering EXACTLY the trailing
       7 days (2026-10-21T00:00 -> 2026-10-28T04:15), plus stationName, district, state,
       and the four set points. Date-range query params (startDate/endDate, from/to)
       are IGNORED: same 7-day window every time (measured twice). Old WP endpoints that
       accepted arbitrary from/to ranges are gone. -> NO multi-year history is anonymously
       obtainable from the public web any more.

National extraction cost measured (coordinator network, 2026-10-28, one request per state;
candidates/malaysia-river-danger-exceedance/ has no probe script - the loop was run inline
with urllib; script preserved at probe/poll_states.py in this directory):
    15 states -> 563 water-level stations, 241,534 bytes total, 43.6 s wall clock.
    Largest: Sarawak 121 st/51,099 B; Selangor 86; Johor 58; Kedah 50.

Other history paths measured:
    - data.gov.my current catalogue enumerated (storage.data.gov.my/metrics/dataset_list.csv,
      355 datasets): NO river-level telemetry. Closest: water_pollution_basin (yearly
      aggregate pollution classes). The CC BY 4.0 licence measured for PriceCatcher
      (my-pricecatcher-weekly-increase, class A) does NOT carry to this telemetry.
    - archive.data.gov.my (holds aras-air-sungai-malaysia.csv = the official threshold
      table, per search index) is UNREACHABLE from the coordinator: connection timeout,
      HTTP 000 after 25 s / 60 s (two attempts). Access failure, not absence.
    - mywater.gov.my Telemetri module (DID Hydrological Station Inventory): loads
      anonymously, Excel export of the station inventory; historical series are NOT
      exposed there. JPS's own FAQ (jpsweb.terengganu.gov.my, mywater.gov.my): historical
      hydrological data are provided on application (SPRHIN, sprhin.water.gov.my), free
      for government/academic use, charged for private projects, approval required -> a
      permission model, not an open-data channel.
    - Portal HTML (home, waterlevel, rainfall, Kelantan state page) grepped for
      copyright|hak cipta|terms|syarat|privacy|privasi|lesen|license: only a "Privasi"
      (privacy) link; still NO licence or terms text anywhere.

## Decision 2026-10-28

Stays PARKED, but the blocker has changed: it is no longer "XHR contract unknown" (that is
solved and documented above); it is "no multi-year history on the anonymous public web, and
no licence statement anywhere on the portal". The only viable task design on this source is
a FORWARD-COLLECTION COHORT: a scheduled poll (e.g. daily; the 7-day graph window gives
poll slack) of /api/detailstation plus per-station GetWaterLevelGraph, accumulating a
station-hour panel; label = any reading in (H, H+24] above the station's official Danger
Level; features from trailing levels/rainfall only. The northeast monsoon (Nov-Mar) is the
positive-generating season; starting a loop before it begins would capture the first
usable season within months.

That loop is an infrastructure commitment and the licence question is unresolved
(portal silent; telemetry absent from the national open-data catalogue; historical data
application-gated): BOTH are operator decisions. Per the standing class-C policy no
written permission will be solicited by Scout unprompted, and no existing operator risk
acceptance extends to this candidate. Reopen triggers:
  (a) operator authorizes the collection loop (licence then resolved before publication
      by publisher terms or an explicit operator risk acceptance);
  (b) the portal or data.gov.my publishes terms permitting redistribution of derived rows;
  (c) the telemetry appears in the data.gov.my catalogue under CC BY 4.0.
