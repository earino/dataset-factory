# eccc-hydrometric-daily-flows

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: Canada)

Publisher: Environment and Climate Change Canada - Water Survey of Canada.

### Probes run (commands and results)

- `python3 .factory/ca_probe_catalog.py` -> open.canada.ca CKAN package_search
  'hydrometric' (anonymous HTTP 200, 54 results): ECCC records include
  'Environment Canada Hydrometric stations and network information, 1850-'
  (0b30719a-f7a6-4f3c-ae37-000acfe9f5a3), 'Environment Canada Water Level Data,
  1850-' (9128b287-7659-49d9-8445-7d69fd5a2d77), 'Real Time Hydrometric Data
  Tool' (ef2161a8-b01d-4dfb-ad00-1a70f7c4073b), 'Hydrometric Monitoring, Oil
  Sands Region' (0c4b0757-8e20-4f7d-b8fb-7df8ae5d93f5), all license_id=ca-ogl-lgo.
- Web search (queries: 'CAMELS-Canada hydrometeorological dataset streamflow
  Canadian basins benchmark'):
  - CAMELS-SPAT (FRDR 9ca63670-9e40-477c-a8a8-30f61205d668 and
    fef15147-940a-4a7d-86c3-373ec7d67ec4): "Streamflow observations, forcing data
    and geospatial data for 1426 streamflow measurement stations located across
    the United States and Canada" - daily AND hourly streamflow at basin outlets,
    4 meteorological forcing sets, 11 geospatial sets, catchment attributes
    (Knoben et al., doi:10.5194/egusphere-2025-893). A 2025 preprint already
    benchmarks deep-learning hydrologic models across 921 North American catchments
    on CAMELS-SPAT.
  - HYSETS (Arsenault et al., Earth Syst. Sci. Data 12, 2020): 14,000+ North
    American basins including Canada, daily streamflow + forcings, built for ML.

### Decision

REJECT as a mirror, before measuring extraction cost on purpose: the task this
source would carry (Canadian station-level streamflow forecasting / flow
exceedance) is already downloadable in ML-ready form with forcings and static
attributes (CAMELS-SPAT covers the Canadian stations; HYSETS covers more). The
task family is also already live in this bench (malaysia-river-danger-exceedance).
HYDAT bulk download was deliberately NOT probed further - the mirror verdict does
not depend on access cost, and the prior art has already paid the extraction cost
for the same data.

Novelty check recorded: `python3 scripts/check-novelty.py eccc-hydrometric-daily-flows
--verdict mirror ...` (exit 3 = the script's expected refusal of a mirror; verdict
and prior art written to the record).
