# ecdc-atlas-surveillance - discovery notes

Session: 2026-10-21 scheduled discovery tick (EU/EEA regional focus). Terminal record: rejected.

## Probes (`.factory/eu_probe_ecdc.py`, all run 2026-10-21)

1. GET https://atlas.ecdc.europa.eu/public/index.aspx -> HTTP 200, 34,120 B: an interactive
   ASP.NET/JS viewer shell. The historical `?Dataset=27&Output=json` query returns the same
   HTML shell (34,144 B), not JSON - no documented anonymous data API at that pattern, and no
   bulk-download link on the viewer or its landing page.
2. GET https://www.ecdc.europa.eu/en/surveillance-atlas-infectious-diseases -> HTTP 200,
   78,205 B: the anonymous surveillance surfaces linked are the Atlas viewer, annual
   epidemiological reports, weekly threats reports and ERVSS; case-level microdata (TESSy /
   EpiPulse) is behind a data-access request process.
3. GET https://www.ecdc.europa.eu/en/publications-data -> HTTP 200, 88,627 B (sections:
   Surveillance and monitoring / Assessment / Guidance / Operational support).

## Why rejected (mirror + access), with prior art named

- The Atlas data model is country x disease x period surveillance panels (coarser-period
  analogue of WHO FluNet's country-week grain). The only binary task it can carry is
  "will disease activity in country C exceed threshold T next period" - the exact formulation
  already on this bench: who-flunet-activity-exceedance (ready; qualified as flunet-002 on
  2026-10-20, artifact b1323a27). Repeating it on measles/other diseases is the
  "same task, different source" non-discovery the project rule names.
- Even setting novelty aside, an anonymous bulk channel was not found (interactive viewer;
  microdata request-gated), so a construction would depend on undocumented internal endpoints.

Both facts are recorded in rejection_reason so this publisher is not re-opened for this task
shape; a genuinely different ECDC product with its own anonymous bulk channel would be a new
candidate.
