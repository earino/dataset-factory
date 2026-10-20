# notes — who-flunet-activity-exceedance (opened 2026-10-20)

Verdict: GO (status `ready`). WHO FluNet satisfies all four contracts with measured
evidence: permissive licence posture (CC BY-NC-SA 3.0 IGO general WHO terms; NC/SA carry
through), anonymous publisher-official CSV API, weekly-maintained country-week laboratory
data, derivable target with both classes in disjoint temporal windows, and no ML-ready
equivalent task found (novelty verdict: differentiated, recorded via check-novelty.py).

## Source identity

- Publisher: World Health Organization (WHO), Global Influenza Programme, Geneva.
  FluNet = "a global web-based tool for influenza virological surveillance first launched
  in 1997... The data at country level are publically available and updated weekly."
  (https://www.who.int/tools/flunet, fetched 2026-10-20, HTTP 200, 89,138 B.)
- Data endpoint (the publisher's own "Download the full dataset (CSV)" link, found in the
  page HTML): `https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv`
- Data dictionary (publisher's metadata view, one row per field, 53 fields):
  `https://xmart-api-public.who.int/FLUMART/VIW_FLU_METADATA?$format=csv&$filter=contains(DatasetName,%20%27FluNet%27)`
- Cross-check product (publisher's own charts, for construction-time verification):
  `https://worldhealthorg.shinyapps.io/flunetchart/` (linked from the FluNet page)

## Probes and their results (2026-10-20, coordinator, anonymous, no key)

```
GET .../VIW_FNT?$format=csv                       -> HTTP 200, 30.8 MiB, 189,645 rows, 4.0 s
GET .../VIW_FNT?$format=csv&$filter=ISO_YEAR eq 2026 -> HTTP 200, 1,476 KiB, 9,226 rows, 1.3 s
GET .../VIW_FNT?$format=csv&$filter=ISO_YEAR eq 2010 -> HTTP 200,   926 KiB, 5,276 rows, 0.8 s
GET .../VIW_FNT?$format=csv&$filter=ISO2 eq 'FR'   -> HTTP 200,   304 KiB, 1,693 rows, 2.5 s
   (FR: ISO_YEAR 1997..2026, 30 years of weekly rows, latest week-start 2026-10-05)
GET .../VIW_FLU_METADATA filtered to FluNet       -> HTTP 200, 10 KiB, 53 rows, 0.1 s
```

- Table span: ISO years 1995–2026; latest week-start present 2026-10-19 → updated to the
  current week. Monthly refreshes of a derived task are honest.
- Grain: country × ISO week × ORIGIN_SOURCE (SENTINEL 59,391 / NONSENTINEL 43,366 /
  NOTDEFINED 86,888 rows); 148,355 distinct country-week keys; 189 countries/territories.
  France 2025: 104 rows over 52 distinct weeks = two origin streams. The task grain must
  aggregate or select streams explicitly.
- All 53 columns are documented by the publisher's own metadata view (field name + data
  type + description; key fields: SPEC_PROCESSED_NB, INF_A, INF_B, INF_ALL, INF_NEGATIVE,
  subtype counts AH1/AH3/AH1N12009..., other respiratory viruses, ILI_ACTIVITY, ISO
  week/year and MMWR variants).

## Split capacity (computed from the downloaded table, country-week grain, streams summed)

positivity = INF_ALL / (INF_ALL + INF_NEGATIVE), denominator >= 50:

```
2005-2019 : 14,870 country-weeks, 81.8% positive   (INFLATED — see trap below)
2020-2022 :  8,559 country-weeks, 2,485 positive (29.0%)
2023      :  4,677 country-weeks, 1,984 positive (42.4%)
2024-2026 : 12,707 country-weeks, 6,135 positive (48.3%)
clustered positives (country-years with >=1 positive week): 278 (2020-22), 131 (2023), 400 (2024-26)
```

Both classes present in every recent window. The clustered (country-season) count, not
the row count, is the effective sample size — positives arrive in ~10-20-week seasonal
bursts per country. The 2020–2022 window sits across the COVID base-rate break (near-zero
influenza circulation in 2020-21); that is a property of the phenomenon to document, not
a construction fault.

## The negatives frame trap (recorded as a red flag, resolved by construction rules)

Pre-2015 rows mostly lack INF_NEGATIVE, so a positivity rate computed from them is 100%
by construction: the 1995-2004 window measures 931/931 country-weeks positive — a uniform
result, which is the frame-error signature, not a finding. Recent French off-season rows
show the well-behaved case (INF_ALL 4–7 against SPEC_PROCESSED_NB 126–169, ~3–5%
positivity). Construction must (a) restrict to country-weeks with systematic negative
reporting, (b) land a named known-event fixture (candidate: France 2024-25 season peak
week >40% positive; off-season weeks <10%), and (c) cross-check aggregate positivity
against the publisher's own chart app.

## Licence

- https://www.who.int/tools/flunet states no dataset-specific licence (measured: only a
  site-wide "Terms of use" link).
- WHO copyright policy (read 2026-10-20): "Permission from WHO is not required for the
  use of WHO materials issued under the Creative Commons Attribution-NonCommercial-
  ShareAlike 3.0 Intergovernmental Organization (CC BY-NC-SA 3.0 IGO) licence."
- WHO dataset terms (data.who.int/about/data/terms-and-conditions): "Unless specifically
  indicated otherwise, these Datasets are provided to you under a Creative Commons
  Attribution 4.0 International License (CC BY 4.0)" + mandatory citation + no-emblem.
- Decision: redistribution of derived rows for non-commercial research is permitted with
  attribution; any NC/SA terms carry through unchanged (standing licensing policy). The
  card must label the dataset as derived, cite WHO, and never present it as WHO's official
  product, and the WHO name/emblem restriction is noted for the release documents.

## Novelty (comparison recorded via check-novelty.py; verdict: differentiated)

- The raw FluNet data is mirrored on Kaggle (patricklford/flunet-global-influenza-
  programme-who) — raw CSV mirror, no prediction task, no splits.
- arXiv 2505.10213 (2025): an LLM time-series forecasting experiment on two univariate
  FluNet series (Influenza A/B counts, 2016–2024, MAE/MAPE) — a paper experiment, not a
  released ML-ready task with splits and a scored contract.
- CDC FluSight (US) and ECDC Flusion forecast ILI/hospitalisation indicators on other
  sources (US ILINet, EU) — adjacent in topic, not this source or this target.
- What does not exist: a country-week binary exceedance task on FluNet positivity at a
  stated lead with disjoint temporal splits, a known-event fixture, and a scored contract.
- Ours: the task formulation (threshold + lead + frame), splits, gating, fixtures,
  baselines. Theirs: the surveillance data itself. The easy fetch is the *least* of the
  contribution and is stated as such.

## Also probed this session and set aside (so it is not re-investigated)

The GHO OData API (ghoapi.azureedge.net/api): anonymous, 3,099 indicators, fast; but GHO
is annual country-year panels and several are unmaintained — CHOLERA_0000000001 ("Number
of reported cases of cholera") spans 1949–2016 only (1,341 KiB, 2,469 rows, 161 countries,
ends 2016). A GHO annual-panel task would also compete with the many Kaggle mirrors of GHO
indicators. FluNet (same publisher, weekly grain, maintained) is the better WHO source and
is the one taken forward.

## Next action (construction step, for the advancement session)

Worker job: single-CSV download → country-week aggregation with explicit ORIGIN_SOURCE
handling → restrict to systematic-negative-reporting country-weeks → pin threshold/lead
via the France 2024-25 known-event fixture and publisher chart cross-check → features
from weeks <= W only, INF_ALL/INF_NEGATIVE for the target week excluded from shipped
columns → temporal splits (train <=2019 / eval 2020-22 / holdout 2023+), clustered
country-season counts beside row counts → dataset-qualification on the worker.
