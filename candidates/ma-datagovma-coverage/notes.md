# ma-datagovma-coverage — notes

Country-coverage record for Morocco: a census of the national open-data portal
data.gov.ma (live, CKAN, ODbL on all 697 datasets) that found no unit-level ongoing
series to build a task on. Opened and parked in the 2026-10-23 Africa discovery tick.
All probes anonymous from the coordinator.

## Probes (2026-10-23)

- CKAN API `https://www.data.gov.ma/data/api/3/action/package_list` — 697 datasets.
  `package_search?rows=0&facet.field=[...]` — license_id facet: **odc-odbl, 697/697**;
  formats: XLSX 524, XLS 102, DOCX 38, PDF 17, CSV 10.
- Licence instrument (the publisher's own FAQ, https://www.data.gov.ma/fr/faq):
  datasets on www.data.gov.ma are "soumises aux conditions de la licence ODbL (Open
  Database Licence)" — copy/distribute/use, produce creations, adapt/modify/build,
  subject to attribution and share-alike. Class B; conditions carry into LICENSE.md.
- Publisher census (titles via package_search per organization):
  - Ministry of Justice (84): annual court-activity tables (Cours d'appel, tribunaux
    de commerce/administratifs/premiere instance) for 2021, 2022, 2023 + a
    quinquennat 2017-2021 file. Annual grain, ~3-5 periods -> too few for splits.
  - HCP (79): national accounts / CPI / IPP / labour aggregates (annual and quarterly,
    old bases) — conceptually mirrored by WDI and the electricsheepafrica HF mirrors.
  - Economie et Finances (75), Commune d'Ait Melloul (27): not title-censused this
    tick beyond counts (recorded as census limitation; same annual-table pattern in
    formats).
  - MATNUHPV housing ministry (61): regional construction-materials price indices
    2005-2022, agent fees / rents / deposits 2001-2022 (12 regions), housing units
    started/completed 2016-2023, cement consumption. Regional annual tables ending
    2019-2022 — no ongoing unit-level series.
  - Bank Al-Maghrib (43): monetary / credit / patrimoine aggregates, most series
    running dec-2001 to sept-2023 — aggregate macro.
  - mjcc youth/culture (41): static facility inventories (centres, festivals, sites).
  - ACAPS insurance/social-security regulator (34): sector indicators 2012-2023 —
    annual sector aggregates.
  - INPPLC anti-corruption (15): mostly THIRD-PARTY governance indices (Basel AML,
    WJP, BTI, TRACE, V-Dem, Mo Ibrahim, OBI) + annual corruption-complaint counts —
    mirrored indices, not Moroccan unit-level data.
  - AMMC capital-markets regulator (11): weekly OPCVM statistics 2016-2026. Granularity
    check by downloading four 2025 files (39-55 KB each): sheets are "Actif net par
    categorie OPCVM" with 6 categories (Actions, Diversifies, Monetaire, Obligations
    CT/MLT, Contractuel) + performance indices — **category-level aggregates, not
    per-fund rows**. Not viable as a task.
  - CNSS (12), ANRT (16): annual declarant/telecom tables.

## Verdict (2026-10-23)

PARK — coverage, not a task defect. The portal is one of the cleanest licence channels
in Africa (ODbL everywhere, anonymous API, machine-readable files); the census found no
unit-level ongoing series to carry a task. Nothing cheap remains unprobed for the
current catalogue. Re-census only when the count moves materially above 697 or a new
publisher org appears; probe for unit-level/event-level streams (procurement,
inspections, licences, per-establishment series). Do not re-verify the ODbL licence.

## Reproducing the probes

`probe_portal_census.py` in this directory re-runs the CKAN enumeration (package list,
facets, per-org title census) and the AMMC file granularity check. Run:
`python3 probe_portal_census.py`.

## Reopen-condition check (2026-10-27)

One CKAN call, exactly as the reopen condition specifies:
`curl -s "https://www.data.gov.ma/data/api/3/action/package_search?rows=0"` ->
`{"success": true, "result": {"count": 695, ...}}`.

Count is 695, BELOW the 697 threshold (and below the 697 recorded on 2026-10-23);
no new publisher org was observed. Reopen condition NOT met - stays parked, no
further probes spent.
