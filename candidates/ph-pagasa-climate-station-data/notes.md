# ph-pagasa-climate-station-data — probe notes

Discovery session 2026-10-21. Verdict: park (request-gated channel, no readable licence).

- getent: philida.pagasa.dost.gov.ph NXDOMAIN; www.pagasa.dost.gov.ph -> 56.11.0.240 /
  18.140.93.223 (AWS ALB, ap-southeast-1).
- First curl to www.pagasa.dost.gov.ph failed DNS transiently; retried before recording the
  negative. https://www.pagasa.dost.gov.ph/climate/climate-data -> 200, 258,361 B, 2.58 s.
- Page text (measured, verbatim excerpts in record.json): raw climatological Excel data via
  CADS-01A (valid ID + accomplished TOU) for agencies/consultants; CADS-02A (school ID, approved
  research proposal, TOU, signed formal letter to the PAGASA Administrator) for students; a
  request-status tracking page exists.
- CliMap (via search): downloads emailed after registration; gridded obs datasets 'currently
  under development'.
- GeoRisk PH ArcGIS REST folder PAGASA (via search): forecast/projection MapServers, anonymous;
  a distinct possible source for a future tick, not probed further.

Region texture: second request-gated national met service in the tick family (IMD is parked the
same way). In South/South-East Asia the open+anonymous weather channels are the aggregated ones
(data.gov.my weather API, Air4Thai, BMKG); national met services keep station archives behind
signed-TOU request forms. No US source substituted for this tick.
