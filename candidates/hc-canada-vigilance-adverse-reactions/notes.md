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

## 2026-10-22 discovery session (tick region: Canada) - the watch, performed

The next_action asked this tick's Canada rotation to watch the Vigilance packages
for a machine-readable resource. Three channels were checked:

- open.canada.ca 100 most-recently-modified packages (package_search?sort=metadata_
  modified+desc&rows=100 -> HTTP 200, 1,166,356 bytes, 2026-10-22): the newest
  Health Canada data package in that window is Cannabis Inspection Data (already
  opened as its own candidate this tick, hc-cannabis-inspection-rating); no
  Vigilance resource appeared.
- 13 keyword package_searches (occurrence, incident, inspection, enforcement,
  violation, conviction, complaint investigation, investigation report,
  enforcement notification, audit finding, test results sample, advisory lifted,
  warnings verification) all returned HTTP 200: no Canada Vigilance CSV/API
  resource appeared in any result set.
- Direct re-probe of the Vigilance packages via package_search 'Canada Vigilance'
  failed twice with the PORTAL's own 504 Gateway Time-out (rows=10, then
  rows=5 with a different query; nginx 504 body captured). Recorded as an
  open.canada.ca infrastructure failure on this date, not as evidence of absence
  (AGENTS.md: infrastructure failures do not prove unsuitability). The two
  successful channels above are the load-bearing ones for the watch.

Conclusion: the watch was performed; no machine-readable Vigilance resource
appeared. The park stands, with the same unpark condition as before.

## 2026-10-27 discovery session (tick region: Canada) - REOPENED on access, then DROPPED (mirror)

The park's unpark condition ("watch the two open.canada.ca packages for a CSV/API
resource appearing") was checked again, this time with package_show against BOTH
package IDs. Result: the condition is met and always had been - the 2026-10-21/22
probes only ever showed 98cad9a3 (the query-form package, 2 HTML resources).

- `probe_extract_channel.py` (retained here): CKAN package_show for
  9cbaef00-b52c-4a70-9fed-d9aa8263ab74 - resources: HTML, JSON, OTHER, XML, ZIP
  (created 2016-09-25; resources dated 2016-12-01/2018-04-13; metadata_modified
  2025-12-19). extract_extrait.zip HEAD: 313,578,432 bytes, Last-Modified
  "Wed, 28 May 2025 17:41:31 GMT", HTTP 200 anonymous. Lookup API
  (health-products.canada.ca/api/canada-vigilance/outcome/) answers 200 (457 B
  code table).
- `probe_extract_zip_tail.py` (retained here): bounded 128 KiB range fetch
  (HTTP 206) of the ZIP tail; central directory lists 13 members under
  cvponline_extract_20241130/: reports.txt 422,306,974 B uncompressed,
  report_drug.txt 953,170,175, reactions.txt 742,284,976,
  report_drug_indication.txt 340,006,407, report_links.txt 66,858,662,
  literature_reference.txt 15,470,173, drug_product_ingredients.txt 34,017,992,
  drug_products.txt 1,930,980 + five *_lx lookups (~2.9 GB uncompressed,
  $-delimited in quotes per the data structure page).
- Extracts page (extraction backend): "updated on a monthly basis", covers
  1965 to 2026-06-30, ZIP ~344 MB (the CKAN resource lags at the 20241130
  vintage). Data structure page (modified 2025-05-29) documents every field,
  including DATINTRECEIVED/DATRECEIVED, VERSION_NO, OUTCOME_CODE, SERIOUSNESS_CODE
  + six criterion flags, REPORTER/SOURCE, MedDRA PT/SOC with version, DRUGINVOLV
  (suspect role), indications, duplicate/linked reports.

So the access blocker in the 2026-10-21 park was factually wrong, and the reopen
was executed. The novelty gate then decided: the natural tasks (report-level
seriousness/outcome prediction; suspect-drug role identification) already exist
published and ML-ready on the open US analogue - GCAP benchmark (Commun Biol
2023, 141,752 drug-ADR interactions, same 7-class seriousness scheme, released
splits), ISPOR 2025 (FAERS serious-outcome classification, identical feature
shape, ROC-AUC 0.916), Kaggle/GitHub FAERS pipelines, openFDA's anonymous
report-level API, and Frontiers Pharmacology 2026 (LLM primary-suspect-drug
identification in FAERS). A Canadian re-issue changes jurisdiction, not the
task - the same standing test that dropped hc-recalls-classification and
hc-cannabis-inspection-rating.

Decision: DROPPED (mirror), with the access evidence corrected in the record so
no future tick re-parks this source on the HTML-only premise. The only reopen
path left is a NEW candidate with a formulation absent from the FAERS ecosystem
(see record next_action: per-version outcome-revision, only if a bounded worker
sample shows reports.txt carries multiple VERSION_NO rows per REPORT_ID - never
measured here because the natural task was decisively mirrored).


