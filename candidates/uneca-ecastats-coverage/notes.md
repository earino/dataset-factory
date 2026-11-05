# uneca-ecastats-coverage - discovery notes

Opened and closed 2026-11-05 by the Africa discovery tick (operator named UNECA in the
regional focus). UNECA had no candidate record before this session; the 2026-11-04 Africa
tick had only touched ecastats.uneca.org at reachability level (probe 01: 200, redirects
to /data). This session measured the portal end-to-end and closed it on task shape.

## Probes (anonymous, plain HTTP, from the coordinator, 2026-11-05)

1. Portal shell: `https://ecastats.uneca.org/data/` -> 200, Vue SPA
   ("ECAStats: The ECA statistical data portal"); no data links in the HTML.
   `https://data.uneca.org/` -> no DNS; `https://www.uneca.org/data` -> 404.
2. Backing API found in the SPA bundle `/data/assets/index-B9a3nMaS.js`
   (189,533 bytes): base URL literal `https://ecastats.uneca.org/ecastats.api/api`,
   plus a chatbot endpoint. Bundle strings carry the footer vocabulary
   {termsOfUse, privacy, copyright: "© Copyright {year}"} and NO licence grant.
3. OpenAPI spec: `GET https://ecastats.uneca.org/ecastats.api/swagger/v1/swagger.json`
   -> 200, OpenAPI 3.0.1, title "ACS ECAStats API", description "An API for accessing
   country profiles, indicators, and time series data". ~100 paths enumerated: ALL
   country/subregion/theme/indicator/time-series/chart/subscription/search surfaces
   (sample: /api/SubIndicator/timeSeries/{rootIndicatorId},
   /api/country-profile/{countryId}/{themeId}, /api/data-viz/visualizations,
   /api/subscribe/*). No event-grain, unit-grain, project, register or listing
   endpoint exists in the spec.
4. Live JSON calls (all 200, anonymous):
   - `/api/data-products` -> 27 products, all theme-level indicator collections
     (first: Health, 28 indicators / 115 sub-indicators / 112,711 data points,
     coverage 54 countries / 14 subregions, 1990-2025).
   - `/api/general/summary` -> 7,390 indicators, 2,955,076 data points,
     min year 1970, max year 2028, 54 countries, 15 subregions.
   - `/api/datasources` -> 66 datasources, predominantly OTHER publishers:
     World Bank (data.worldbank.org), IMF, FAO (FAOSTAT), UNDP, national sources.
   - `/api/topics` -> 25 topics (SDGs 5,329 sub-indicators / 804,895 data points,
     Climate change 140 / 81,706, ...).
   - `/api/countries` -> 54 payload rows (Algeria DZA first, unCode 12).
5. Licence: no open-licence instrument anywhere in the API or the bundle; the only
   rights string is the footer copyright line. `/data/terms` and `/data/about` return
   the SPA shell to a plain client (client-side routes), so no terms text was read.
   NOT chased in the supported browser: the task-shape blocker is decisive without it.

Probe scripts (durable copies): probe/probe_01_portal_reachability.py and
probe/probe_02_api_surface.py. Session raw outputs (pruned with scratch):
/opt/data/cache/scratch/africa_tick_2026_11_05_region_probes.json and
/opt/data/cache/scratch/uneca_api_probe.json; the numbers they contained are in
record.measurements.

## Decision

DROP, task shape (measured), licence unstated (secondary). ECAStats is a redistribution
gateway for aggregate indicator series that belong mostly to other publishers - the same
measured family defect as the statcan-wds park (aggregate-only = weak task value), plus
mirror risk since the primary series are already open at their own publishers
(World Bank, IMF, FAO). Reopen conditions in record.next_action. This says nothing about
UNECA's reports or other products; it is about the ECAStats portal surface enumerated
2026-11-05.
