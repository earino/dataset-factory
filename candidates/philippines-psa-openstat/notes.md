# notes — philippines-psa-openstat (opened 2026-10-20)

Verdict: REJECT on task grounds. The portal is reachable (in a real browser) and has a
documented API, but everything it publishes is aggregate statistical tables.

## Probes (2026-10-20)

```
curl https://openstat.psa.gov.ph/                          -> HTTP 403, 5,548 B, Cloudflare "Just a moment..."
curl https://openstat.psa.gov.ph/api/3/action/site_status  -> HTTP 403, 5,641 B (same challenge)
```

Real browser session (browser-use Chromium): the challenge cleared after ~12 s and the
portal rendered ("PSA OpenSTAT > Home"). Legacy CKAN API gone:
`/api/3/action/package_list`, `/api/3/action/package_search` -> 404 HTML pages.

Homepage link tree (extracted in-browser): Database sections are statistical domains —
Population and Vital Statistics, Labor and Employment, Income and Consumption, Poverty,
Education, Health, Human Settlements and Housing, Economic Accounts, Services,
Agriculture-Forestry-Fisheries, Trade, Prices, Mining-Manufacturing-Construction,
Labor Cost, Environment, Information Society, Energy, Digital Connectivity,
Decent Work, SDGs, Gender — plus an "API Documentation" link.

Drill-down: /Database/Demographic-and-Social-Statistics/Population-and-Vital-Statistics
lists PXWeb table trees: Projected Population (2020 census-based), 2015/2020/2024
Census of Population, "Birth Statistics ... including demographic" characteristics,
"Marriage Statistics ...". PXWeb paths like /PXWeb/pxweb/en/DB/DB__1A__VS__BI/.

API documentation page (read in-browser): "The OpenSTAT API provides programmatic
access to official Philippine statistics ... Retrieve datasets in real time from
official Philippine statistical databases ... Access statistical metadata including
variables, classifications, and table structures."

## Task assessment

A statistics-agency table database: count/index tables by period and region. No
event-level or per-entity outcomes with documented labels, so no prediction task.
Same verdict shape as indonesia-bps-webapi; recorded separately because the operator
named PSA in the tick brief.

## Licence

Not captured: headless fetches are Cloudflare-blocked and the browser pass was spent
enumerating content. Moot — no task exists to publish.
