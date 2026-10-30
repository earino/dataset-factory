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

## 2026-10-30 — recorded unpark probe run (negative on the GeoRisk channel)

Exact commands retained: probe/probe_georisk_2026-10-30.sh,
probe/probe_georisk_services_2026-10-30.sh, probe/probe_georisk_layers_2026-10-30.sh.

- getent ahosts philida.pagasa.dost.gov.ph -> no A record; dns.google resolve -> Status 3
  (NXDOMAIN), SOA pagasa.dost.gov.ph (ns-1663.awsdns-15.co.uk). PhilDA has not relaunched.
- https://portal.georisk.gov.ph/arcgis/rest/services?f=json -> HTTP 200; folders BFP, DA,
  DENR, DEPED, DND, DOE, DOH, DSWD, Hosted, MGB, OCD, PAGASA, PHIVOLCS, PSA, Utilities.
- /arcgis/rest/services/PAGASA?f=json -> 9 services; Rainfall_Forecast_Observed is a MapServer.
- /PAGASA/Rainfall_Forecast_Observed/MapServer?f=json -> HTTP 200, 3,208 B; serviceDescription ""
  and copyrightText ""; five Feature Layers: 'Rainfall Forecast Observed (January)' ... '(May)'.
- /MapServer/0?f=json -> HTTP 200, 6,350 B; fields: objectid (OID), id (Integer), gridcode
  (Integer), shape (Geometry), st_area(shape), st_length(shape). No year, no station id, no
  time field.

Verdict: the GeoRisk PAGASA folder carries forecast-visualisation polygons, not station
observations; no readable terms on the service (class C posture). Recorded unpark question is
answered negatively; candidate stays parked. Both probe scripts kept in probe/.
