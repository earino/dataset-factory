# notes — unicef-sdmx-refugee-origin-growth (opened 2026-10-20)

Verdict: PARK. Access and licence are both good (recorded so they are never re-probed);
the park is on split capacity: the clustered effective sample (22 distinct surging origins
in the eval window, 34 positive rows) is too thin to carry a scored binary eval, and the
series is UNHCR-derived, so it adds no genuinely new data to the bench beyond the richer
parent record that is access-parked (`unhcr-refugee-data-finder`).

## Probes (2026-10-20, coordinator, anonymous)

```
GET https://sdmx.data.unicef.org/ws/public/sdmxapi/rest/data/UNICEF,MG,1.0/.MG_RFGS_CNTRY_ORIGIN.?format=csv
  -> HTTP 200, 4,967 KiB, 12,452 rows, 0.5 s, text/csv
GET https://data.humdata.org/api/3/action/package_show?id=unicef-mg-rfgs-cntry-origin
  -> HTTP 200; license_title "CC BY 3.0 IGO"
```

Found via the HDX CKAN search for "refugees country of origin" (the dataset is listed with
its SDMX resource URL). The SDMX API is anonymous, documented by the SDMX standard, and
returns the full indicator in one request — an access path the UNHCR RDF itself does not
offer.

## Table shape (measured)

- 12,452 rows = 364 REF_AREAs × years 2001–2025 × AGE split.
- AGE=_T (total): 8,475 rows usable. AGE=Y0T17 (children): 3,977 rows, **all OBS_STATUS
  'MD'** — the child-age disaggregation is missing in this pull; do not build on it.
- 155 REF_AREAs are regional/global aggregates (UNICEF_WCA, WPP_GLOBAL, AU_AFRICA,
  UNSDG_REGION_GLOBAL, FAO_LIFDC, WB_LI...) — excluded, leaving 209 country origins.
- Every row's DATA_SOURCE: "United Nations High Commissioner for Refugeers, Global
  Trends: Forced Displacement in 2025. UNHCR, 2026." and SOURCE_LINK:
  https://www.unhcr.org/refugee-statistics/download/ — i.e. this series is UNICEF's
  republishing of the UNHCR RDF data. Attribution in any release must name both.

## Split capacity (country-only, AGE=_T, base >= 1,000, growth > 25% into D+1)

```
train 2001-2015 : 1,356 origin-years, 155 positives (11.4%), 72 distinct surging origins
eval   2016-2019:   378 origin-years,  34 positives ( 9.0%), 22 distinct surging origins
hold   2020-2024:   485 origin-years,  72 positives (14.8%), 44 distinct surging origins
```

Both classes exist in every window, so the gate's uniform-split check would pass — but the
effective sample is the clustered count: a surge is a *situation* (Afghanistan mid-2000s,
Syria 2012-15, Ukraine 2022, Sudan 2023-24...), and the eval window holds only 22 of them.
That is the number a confidence interval would be computed on, and it is too small for a
stable eval AUC.

## Licence

CC BY 3.0 IGO (HDX dataset record, maintained by UNICEF's own HDX organisation account).
Attribution-only; redistribution of derived rows permitted with citation to UNICEF Data
and Analytics and to the underlying UNHCR Global Trends statistics.

## Prior-art comparison (recorded; check-novelty.py not run because status is parked)

- UNHCR Innovation Service "Project Jetson" — internal forecasts of new arrivals in
  specific situations; not a public ML-ready benchmark, and different grain (arrivals,
  not origin-year populations).
- Kaggle hosts raw UNHCR refugee mirrors (e.g. 2010-2016 vintages) — data mirrors, no
  prediction task with splits.
- Displacement-forecasting papers exist (arrival forecasting, conflict-driven movement);
  none publishes an ML-ready benchmark with disjoint splits and a scored contract on
  origin-year refugee populations.
- Conclusion on novelty: a task here would be *differentiated*, not a mirror — but novelty
  does not rescue the sample size, which is why the verdict is park and the novelty check
  was not mechanically recorded.

## Unpark condition

A machine-fetchable richer grain of the same phenomenon: UNHCR RDF's monthly asylum
applications or host-country × origin populations. That is exactly the unpark question on
`unhcr-refugee-data-finder`; if UNHCR unblocks, build the task there, not on this annual
derivative. Only reopen this record if the operator explicitly wants the thin annual
task.
