# za-dws-dam-storage-exceedance — notes

Dam-level weekly storage exceedance (drought early warning) on the South African
Department of Water and Sanitation's national reservoir reporting. Opened and parked
in the 2026-10-23 Africa discovery tick. All probes anonymous from the coordinator.

## Probes (2026-10-23)

- `https://www.dws.gov.za/Disclaimer.aspx` and
  `https://www.dws.gov.za/Hydrology/Weekly/WeeklyBulletins.aspx` — **HTTP 403 Forbidden**
  to a plain HTTP client AND inside a real browser (same 403 page both ways). The site
  is network-blocked from this coordinator: inaccessible evidence, not proof of absent
  data or absent terms.
- `https://niwis.dws.gov.za/niwis2/` — connection timeout. Legacy
  `http://www.dwa.gov.za/...` — NXDOMAIN. `https://data.gov.za/` — DNS
  "Temporary failure in name resolution" (the national open-data portal that would carry
  per-dataset licences is gone, same failure class as open.data.go.ke).
- Wayback Machine: `web.archive.org/web/2026/https://www.dws.gov.za/Disclaimer.aspx` —
  "The Wayback Machine has not archived that URL". CDX API
  (`web.archive.org/cdx/search/cdx?url=dws.gov.za/Hydrology/Weekly/WeeklyBulletins.aspx`)
  — zero captures. Domain-level CDX: only a 2016 302 and 2025 warc/revisit scanner-noise
  entries (garbage URLs, statuscode "-"). No readable archived DWS page exists.
- `https://www.capetown.gov.za/.../this-weeks-dam-levels/` — HTTP 200, readable: daily
  levels table + weekly PDF ("Dam Levels Report: 19 October 2026", ~2.5 MB); six major
  dams 48.3–100.2%, total 74.0% storage. City of Cape Town Open Data Portal
  (odp-cctwdesa.opendata.arcgis.com) also HTTP 200 — but the Cape-Town-only variant was
  rejected (single supply system; drought positives clustered in the 2017-18 "Day Zero"
  episode; existing Day Zero forecasting literature + Kaggle raw mirrors). Not probed
  further — see record.json cape_town_variant_assessment.

## Third-party attribution used only because the publisher is unreachable

reservoirs.earth/transparency-index/south-africa (read 2026-10-23): ~250 covered dams,
weekly Tue/Wed HTML bulletins + PDFs, NIWIS manual CSV/Excel export (~5 years of weekly
series), "No API". DWS media releases on gov.za confirm the weekly State of Reservoirs
cadence. Every one of these facts must be re-measured from dws.gov.za before any ready
verdict; none is first-hand.

## Verdict (2026-10-23)

PARK on two measured blockers: (1) publisher unreachable from the coordinator (403 /
timeout, plain + real browser), so schema, history depth and terms could not be
measured; (2) no licence instrument readable (site blocked, data.gov.za gone, no
Wayback capture). Access failure is not a scientific rejection. Cheap decisive probes
are named in record.json next_action: a ~2-minute worker-side access test (does the 403
repeat from the Hetzner network?), then read + quote the terms instrument if reachable,
classify, and only then consider novelty (Cape Town Day Zero papers, Kaggle dam-level
mirrors). Do not spend further coordinator-side ticks on it.

## Reproducing the probes

`probe_access_licence.py` in this directory re-runs every probe above (DWS endpoints,
NIWIS, legacy host, data.gov.za, Cape Town page, Wayback CDX queries) and prints the
same evidence. Run: `python3 probe_access_licence.py`.
