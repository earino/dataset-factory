# notes — unhcr-refugee-data-finder (opened 2026-10-20)

Verdict: PARK. Access/automation blocker, not a licence blocker. The datasets are CC BY 4.0
(granted on the methodology page, quoted below), but no machine-fetchable bulk path could
be found: the host is WAF-gated, exports are interactive-app-only, and the full series is
not mirrored anywhere with a stable URL.

## Access probes (2026-10-20, coordinator)

```
curl https://www.unhcr.org/refugee-statistics/                -> HTTP 403, 182,520 B (challenge page)
real browser, same URL                                        -> loads (title: "Refugee Data Finder - Key Indicators")
in-page same-origin fetch of ?v2url=dc36b6 deep link         -> HTTP 403, 222,964 B (fetch() is WAF-distinguished)
real-tab navigation to the deep link                         -> opens the interactive Data Finder app (view selector, not a file)
programmatic click of the app's "Download" control            -> no file landed in the browser download dir (JS-driven dialog form)
curl http://popstats.unhcr.org/en/overview                    -> HTTP 000 (host gone)
curl https://data.unhcr.org/en/index                         -> HTTP 404 (old portal path dead)
curl https://data.humdata.org/api/3/action/package_search... -> HTTP 200 (CKAN API fine; but no full-series mirror)
```

The RDF app is a Symfony/UX live-component application (turbo/stimulus bundles,
`data_finder_controller-*.js` submits a FormData via Turbo POST; no API route appears in
the controller source or the page's network entries). The homepage's export deep links:

```
population by country of origin   https://www.unhcr.org/refugee-statistics/download/?v2url=dc36b6
population by host country        https://www.unhcr.org/refugee-statistics/download/?v2url=bd1059
demographics of refugees          https://www.unhcr.org/refugee-statistics/download/?v2url=d3e49d
solutions 2015-2024               https://www.unhcr.org/refugee-statistics/download/?v2url=d63e73
new asylum applications 2024      https://www.unhcr.org/refugee-statistics/download/?v2url=1e3087
```

...are view selectors into the app, not stable file URLs.

## Licence (read 2026-10-20, real browser)

- Methodology page, "Data terms and conditions of usage": **"Except where otherwise
  indicated, the datasets made available by UNHCR on UNHCR Refugee Population Statistics
  Database are licensed under the Creative Commons Attribution 4.0 International Public
  License."** — a clear CC BY 4.0 grant for the data.
- Site-wide website terms (https://www.unhcr.org/contact-us/terms-and-conditions-use):
  extracts may be reproduced "for research or private study but not for sale"; "Any use
  other than for personal or educational purposes, including reproduction, scraping by
  artificial intelligence (AI), or translation of substantial portions of the Content of
  the UNHCR website, requires the express prior written permission of UNHCR."
- Reading: the dataset-specific CC BY 4.0 grant governs the statistics; the website ToU is
  the default for website Content. The explicit AI-scraping clause in the ToU is recorded
  because it shows this publisher's posture, and it would apply to any scraping that
  works around the WAF rather than using the granted datasets. Tension flagged for the
  operator if unparked.

## HDX check (does a mirror unblock the data?)

HDX (OCHA Centre for Humanitarian Data) hosts UNHCR datasets with CC BY / CC BY-IGO
metadata, but the full origin-year population series is NOT there — only per-country
extracts (afg/bgd "forcibly displaced population by origin", updated 2026-08-17), the
situations CSV, reference GIS layers, and yearbook archives. So no stable anonymous
mirror of the full series exists.

## Recency (the series itself is fine)

The homepage reports end-2025 global figures (117.8M forcibly displaced; charts 2000-2025),
so the annual series is maintained and current. The blocker is purely the export channel.

## Task shapes this source would support (for whoever unparks)

1. Situation growth (annual): origin-country-year refugee/IPTC population; will it grow
   >25% in D+1? Label from the D+1 row (documented process: UNHCR's compiled statistics).
2. Asylum applications (monthly): applications by origin × country of asylum; will
   applications exceed a threshold next month? Higher grain, same access problem.
   Prior art to check before building either: UNHCR Innovation Service "Project Jetson"
   (internal forecasting of new arrivals), displacement-forecasting literature, and the
   old Kaggle UNHCR mirrors.

## Unpark question

Can the RDF population/asylum CSVs be fetched by a non-interactive client from a
datacenter IP — a documented export URL, an API, or written guidance from UNHCR's data
team (RDF feedback form)? Failing that, does the operator accept a once-per-release
browser-captured export as provenance? Until one of those, the thinner annual alternative
is UNICEF's SDMX republishing of the refugee-by-origin counts (different publisher; see
unicef-sdmx-* candidate if opened).

## What NOT to redo next session

- popstats.unhcr.org and data.unhcr.org/en/index are dead; don't re-probe.
- curl/fetch of www.unhcr.org is 403 by design; only real-browser navigation passes. The
  403 is a WAF, not a missing page — this note exists so the next session doesn't misread
  the site as "down" or the terms page as unreadable.
- HDX does not mirror the full population series; that search is done.
