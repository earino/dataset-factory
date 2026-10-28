# oecd-sdmx-aggregate-family — discovery notes (2026-10-22)

OECD statistical catalogue triaged as a source family. Licence clean (class A); rejected on task
shape after four measured probes.

## Licence (read first)

- OECD Terms and Conditions, www.oecd.org/en/about/terms-conditions.html (read via search
  2026-10-22): "you can extract from, download, copy, adapt, print, distribute, share and embed
  Data for any purpose, even for commercial use. You must give appropriate credit to the OECD by
  using the citation associated with the relevant Data". Per-dataset third-party-ownership caveat.
- OECD Open Access Policy: CC BY 4.0 default for content published since 1 July 2024.
- Class A. Not the blocker.

## Catalogue inventory (measured)

```
curl -s 'https://sdmx.oecd.org/public/rest/dataflow/all'   -> 200, 8,936,572 B XML
grep/parse: 1,550 <structure:Dataflow> elements, 53 agencies
agency mix (top): OECD.CTP.TPS 212, OECD.SDD.NAD 187, OECD.CFE.EDS 133, OECD.EDU.IMEP 127,
                  OECD.SDD.TPS 117, OECD.ELS.HD 86, ... + IAEG-SDGs 2, ESTAT 1
flow names sampled: air emissions accounts, SDG global, climate projections by scenario 2030-2060,
                    coastal flooding / drought / wildfires (cities & FUAs), population, internet speed
```

## Grain probes (three flagship families, one-period windows)

```
QNA  2024-Q3  (OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA,1.1):     21,779 rows, 11.5 MB
      -> every row: country x transaction x measure x quarter (REF_AREA=KOR/GBR/...)
KEI  2026-01  (OECD.SDD.STES,DSD_KEI@DF_KEI,4.0):         1,469 rows, 422 KB
      -> every row: country x measure x month (e.g. HUN retail trade volume growth)
FUA  2020     (OECD.CFE.EDS,DSD_FUA_LAB@DF_LABOUR,1.1):   4,759 rows, 1.1 MB
      -> every row: city/FUA x measure x year (e.g. Greater Sydney labour force)
```

Entity grain in all three: a geographic unit observed at aggregate level. No row-level events,
cases or transactions anywhere in the sample.

## Why rejected (the reasoning, with bench evidence)

- Level target on a persistent aggregate = the nhs-ae-four-hour-decline defect, measured on this
  bench: persistence 0.5758 beat the shipped baseline 0.5511 (operator drop decision 2026-10-21).
- Change target on annual country panels: positives cluster into a handful of global shock years
  (one recession marks most countries in one period) - few independent positives.
- Mirror texture: OECD republishes indicators whose primary publishers are national statistical
  offices; the inventory itself carries ESTAT and IAEG-SDGs flows; WDI/FRED/Eurostat republish
  overlapping series.
- The OECD's one row-level public product, recalls.oecd.org, aggregates member-state recall
  datasets - the bench already holds hc-recalls-classification (Health Canada) and US recall
  candidates, so that channel is a mirror.

## Cost of this verdict

Four HTTP requests (~13 MB total, all deleted from scratch). Total catalogue access verified
anonymous, documented, no key - recorded as clean so a future session does not re-derive it.

## 2026-10-28 — reopen-condition re-check (International-organisations tick)

The record's reopen condition was "the OECD ships a row-level product that is neither an aggregate
panel nor a mirror of national datasets". Re-checked this session (bounded catalogue/news read,
no data pulled):

- oecd.org/en/data/datasets.html (read 2026-10-28): 1,521 datasets, described as "Discover and
  access the OECD's datasets"; the Data Explorer (data-explorer.oecd.org) is "the organisation's
  data warehouse, providing access to all OECD statistical data" - the statistical-aggregate
  catalogue already measured in this record.
- OECD Data Explorer platform-status news, 2025 through 2026-10 (read 2026-10-28): infrastructure
  upgrades, search/navigation improvements, Euro-area (21 countries) code changes, cloud-replica
  availability changes for CRS/TiVA - no new row-level or event-level release.
- recalls.oecd.org remains, as far as this bounded check shows, the only row-level public product
  and it mirrors national recall datasets already on the bench.

Verdict: reopen condition NOT met as of 2026-10-28. This is a bounded catalogue check recorded for
coverage, not a claim that no row-level product exists anywhere on OECD properties. Cost: 2 web reads.

