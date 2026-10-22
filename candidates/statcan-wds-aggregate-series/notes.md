# statcan-wds-aggregate-series

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: Canada)

Publisher: Statistics Canada. Probes kept in probe_wds.py.

### Access probes (commands and results)

- `python3 .factory/ca_probe_statcan_hc.py` -> https://www.statcan.gc.ca/en/developers/wds:
  HTTP 200, 22,322 bytes, anonymous. "Our Web Data Service gives developers
  access to Statistics Canada data via the following 15 methods: getChangedSeriesList,
  getChangedCubeList, getCubeMetadata, getSeriesInfoFromCubePidCoord, getSerie..."
  plus "The Statistics Canada SDMX REST web services provide access to the time
  series made available on the Statistics Canada's website". No API key mentioned
  anywhere on the page. Access is clean and anonymous - NOT the blocker.
- https://www150.statcan.gc.ca/n1/en/type/data -> HTTP 200, 135,545 bytes:
  "(13,356) (0 to 10 of 13,356 results)" data tables; example series table
  33-10-0036-01 (daily FX rates, 27 series from 1981); "National Travel Survey
  microdata file Public use microdata: 24-25-0001... Monthly files are available
  back to 2006 and can be directly downloaded. For reference periods prior to
  2006, files are available by request through Statistics Canada's Electronic
  File Transfer (EFT) service..."
- https://www.statcan.gc.ca/en/microdata/index -> HTTP 500 Internal Server Error
  (measured failure on 2026-10-21, recorded; not read as absence of a page).

### Source-class analysis (the verdict)

Everything open falls into two classes:

1. Aggregate time series (the 13,356-table catalogue). The natural task is a
   direction/level forecast on the series' own history - the family served by
   M4/Monash-style macro benchmarks. Same verdict as ONS (ons-la-claimant-count-
   direction, parked 2026-10-21 with the same reasoning).
2. Cross-sectional survey PUMF snapshots (e.g. National Travel Survey 24-25-0001).
   The natural task is same-survey outcome prediction - the census-income family,
   the most mirrored task class in public ML (StatCan's own census PUMFs are among
   the sources of the classic 'adult income' datasets).

Case/event-grain products (UCR incident microdata, RDC research files) are
registration-gated and not redistributable. No further probing was spent after
this class analysis; the park is at class level, before table selection.

### Decision

PARK (source class). Unpark condition recorded in the record's next_action: an
open case/event-grain StatCan release, checkable via the WDS getChangedCubeList
endpoint or the open.canada.ca StatCan feed on a future Canada tick.

## 2026-10-22 discovery session (tick region: Canada) - the unpark checks, run

The record's next_action asked a future Canada tick to check two channels. Both were
checked this tick; the park stands.

- WDS getChangedCubeList (the endpoint named in the unpark condition):
    curl -s -o /dev/null -w "%{http_code}" https://www150.statcan.gc.ca/t1/wds/rest/getChangedCubeList
    -> 404; with ?lang=eng and ?lang=en -> 404 both. The method listed in the WDS
  docs no longer resolves at the documented path (405 from getCubeMetadata for GET
  shows the REST family itself is still mounted, so this is a missing/renamed method,
  not a dead service).
- open.canada.ca StatCan feed: pulled the 100 most-recently-modified OGL packages
  (CKAN package_search?sort=metadata_modified+desc&rows=100 -> HTTP 200, 1,166,356
  bytes). StatCan entries in that window are all aggregate tables of the parked
  class: industrial product price index variants, new housing price index, EI
  beneficiaries by geography, international travellers by mode, FX rates, GoC debt
  securities. No case/event-grain release appeared.
- Also relevant: the 2026-10-22 ISC probe found StatCan tables 34-10-0204..209
  (drinking water advisories by public-owner type) - aggregate counts, same parked
  class, recorded in candidates/isc-ltdwa-advisory-lift-timing.

Conclusion: no event-grain channel appeared on either named path; the park remains
correct and this check need not be repeated before the next Canada tick.

