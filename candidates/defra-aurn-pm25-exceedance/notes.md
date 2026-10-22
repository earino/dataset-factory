# defra-aurn-pm25-exceedance — probe notes

Discovery session 2026-10-22 (UK-regional tick). Scratch probes
(`.factory/probe_fsa_defra3.py`, `probe_fsa_defra4.py`, plus an inline OpenAQ
check) deleted after the session.

## Triage

Defra was on this tick's named publisher list, so the task shape was evaluated
against the bench's own precedents before spending anything on access:

- `eccc-hydrometric-daily-flows` (dropped): day-ahead station-level
  sensor exceedance/forecasting is recorded as "the canonical
  streamflow-forecasting task", rejected before construction. The air-quality
  twin of that verdict is day-ahead pollutant concentration/exceedance from
  hourly history.
- `cpcb-aqi-exceedance` (dropped): India PM2.5 next-day exceedance, closed.
- `air4thai-pm25-exceedance` (parked): Thailand PM2.5 next-day exceedance,
  parked; its next_action already says "a second air-quality task must argue
  why it is differentiated".
- AURN publishes hourly gas/particulate concentrations at automatic monitoring
  stations — the only prediction tasks it carries are day-ahead
  concentration/exceedance forecasting. A UK instance would be a geographic
  mirror of a twice-declined shape.

## Commands and results (measured, not assumed)

1. `probe_fsa_defra3.py` — `uk-air.defra.gov.uk/data/open-data` and
   `uk-air.defra.gov.uk/` both returned HTTP 200 with **2,038-char** bodies.
2. `probe_fsa_defra4.py` — the 2,038-char body is a WSP
   "Website Temporarily Unavailable" maintenance page ("security updates are
   applied in response to recently disclosed PHP vulnerabilities
   CVE-2026-109618 and CVE-2026-109619"). Identical for:
   - plain UA and browser UA,
   - `/data/open-data`, `/data/automated-monitoring`,
     `/data/site-info?site_id=ABD`, and `/`.
   So the whole publisher site is in a maintenance outage (2026-10-22); its
   licence text could not be read this session. This is an infrastructure
   condition, recorded as measured context — it is NOT the reason for the
   verdict, and per AGENTS.md an infrastructure failure does not prove a
   dataset unsuitable.
3. Inline OpenAQ check — v2 API retired (HTTP 410 "Gone"), v3 requires an API
   key (HTTP 401), so third-party redistribution of UK AURN data could not be
   verified anonymously; no mirror claim is made in the record.

## Verdict: reject (dropped)

Canonical task shape, already declined twice on this bench
(cpcb-aqi-exceedance closed, air4thai-pm25-exceedance parked; eccc-hydrometric
records the same verdict for the sensor-forecasting family). The site outage
blocked the licence read but did not decide the verdict. Recorded 2026-10-22.

What would reopen: a genuinely different task formulation on AURN data (not
day-ahead concentration/exceedance), with the site back online and its licence
read from the publisher's own instrument.
