# nrw-historic-flood-warnings — probe notes

Discovery session 2026-10-22 (UK-regional tick). Found during the EA candidate's
CKAN searches (probe_ea_flood1.py / probe_ea_flood14.py output); recorded here so
the Welsh twin is not re-investigated.

## Commands and results

1. `.factory/probe_nrw_flood1.py` — CKAN
   `package_show?id=historic-flood-warnings-and-flood-alerts2`:
   - title "Historic Flood Warnings and Flood Alerts", org Natural Resources
     Wales, metadata_modified 2026-09-16.
   - notes: "all messages issued for flooding from rivers or the sea in Wales
     since 2006", three flood warning codes, EA Wales provided data until
     1 April (NRW's creation).
   - frequency-of-update: quarterly (same schedule as the EA file).
   - access_constraints: "There are no access restrictions on this data. NRW
     may release, publish or disseminate it freely." / "© CNC/NRW. Data may be
     re-used under the terms of the Open Government Licence providing it is
     done so, acknowledging both the source and NRW's copyright." → OGL with
     attribution, class A.
   - One resource: "Download Data and Web Service" →
     `https://datamap.gov.wales/documents/2644` (not downloaded).

## Verdict: reject (task-shape duplicate)

The Welsh twin of `ea-flood-alert-escalation` (opened the same day, go) on the
same stream family. Per the efsa-one-health-sample-prevalence precedent, the
duplicate is rejected with its ids pinned for a fresh candidate ONLY after the
England task ships and a second instance is wanted. No data was downloaded;
probing was record-level only. Recorded 2026-10-22.
