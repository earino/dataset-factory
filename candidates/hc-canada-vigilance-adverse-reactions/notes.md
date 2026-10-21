# hc-canada-vigilance-adverse-reactions

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: Canada)

Publisher: Health Canada - MedEffect Canada / Canada Vigilance Program.

### Probes run (commands and results)

- `python3 .factory/ca_probe_catalog.py` -> open.canada.ca CKAN package_search
  'adverse drug reaction' (anonymous HTTP 200, 53 results): Health Canada
  packages include 'Canada Vigilance Adverse Reaction Online Database'
  (9cbaef00-b52c-4a70-9fed-d9aa8263ab74), 'Canada Vigilance adverse reaction
  online database' (98cad9a3-5b61-4c1e-965d-531804542560), 'Adverse Reaction
  Information' (26390dfa), 'Instructions for the Canada Vigilance Adverse Reaction
  Online Database' (4468c43f), 'Data on cannabis adverse reactions' (371d84b2).
- `python3 .factory/ca_probe_packages.py` -> package_show for 98cad9a3: resources
  are TWO HTML links only (the English and French database pages). No CSV, no
  API, no bulk resource on the record.
- `python3 .factory/ca_probe_rods_eras.py` (Health Canada section) ->
  package_show for 371d84b2 ('Data on cannabis adverse reactions'): all 12
  resources are PDF annual reports (rept_ocss-2020..2024-annual-report.pdf,
  en+fr). The 'data' package is PDFs, not data.
- Direct fetch of
  https://www.canada.ca/en/health-canada/services/drugs-health-products/medeffect-canada/adverse-reaction-database.html
  -> read timeout (90 s) on BOTH attempts from this coordinator (2026-10-21).
  Recorded as coordinator-side network behaviour. The CKAN resource lists are
  sufficient evidence for the access verdict, so the page fetch is not load-bearing.

### Task-family comparison

The US counterpart (FDA FAERS via openFDA) ships event-level ADR data through a
documented anonymous API; ADR-outcome prediction on FAERS is a heavily published
literature. Even with a bulk channel, a Canadian ADR task's differentiation would
rest on the Canadian reporting population alone - a thin contribution.

### Decision

PARK on access: HTML query-form + PDF reports only; no machine-readable bulk
channel exists on any of the packages. Assembling a panel would require
undocumented scripted scraping of an interactive form, which this pipeline does
not treat as acceptable provenance (same posture as the UNHCR park,
unhcr-refugee-data-finder). Unpark condition in the record's next_action: watch
the two Vigilance packages for a CSV/API resource appearing (next Canada tick),
or an operator risk-acceptance for a browser-captured export.
