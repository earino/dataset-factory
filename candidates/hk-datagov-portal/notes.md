# hk-datagov-portal

**Verdict: park (2026-10-22) - licence and access clean; no novel task family.**

## Probe evidence (2026-10-22; commands in probe_hk_catalog.py)

| Probe | Result |
|---|---|
| CKAN package_list | 3,831 packages |
| Provider prefix counts | censtatd 935, hkma 198, swd 167, lcsd 124, landsd 119, emsd 100, immd 88, dh 81, wsd 72, hko 57, ... |
| package_show samples | license_id None at package level; resources are department CSVs |
| EMSD reported_lift_incidents.csv | 200 OK, 1,580 bytes, 43 rows: Year, Main Cause, Number - annual aggregate, not per-incident |
| WSD burst datasets | annual CSV (burstreport_en.csv) + 'Report of Main Burst Case' as CSDI geoportal layer (per-case, positives-only) |
| Terms page (en/terms-and-conditions) | redistribution + reproduction, commercial and non-commercial, free, with attribution |
| Keyword sweeps (prosecution/enforcement/hospital/rainfall/traffic/cyclone/...) | all hits are Censtatd/HKMA/departmental aggregate tables or existing-family mirrors |

## Mapping to existing bench families

- WSD weekly reservoir storage -> tw-reservoir-drought-storage family (also parked, on history depth)
- HKO TC best track (post analysis) -> TCRISI/TCBench mirror precedent (jma-typhoon-rapid-intensification, dropped)
- Hospital Authority in/outpatient tables -> NHS A&E family (nhs-ae-four-hour-decline, dropped as negative result)
- Censtatd/HKMA statistical tables -> aggregate-series family parked twice (statcan, ons)
