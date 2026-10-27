# imd-station-observation-series - probe evidence (2026-10-20)

## Network probes (measured, from the coordinator)
    curl -L "https://mausam.imd.gov.in/"  -> HTTP 000 (connection failure)
    curl -L "https://dps.imd.gov.in/"      -> HTTP 000 (connection failure)
    Two attempts each, 2026-10-20. Possibly network/geo filtering of this host; a worker in
    another region may see otherwise (recorded as infrastructure, per AGENTS.md, not as a
    source judgement).

## Portal policy (read via web search of dsp.imdpune.gov.in pages, 2026-10-20)
    - "IMD Free Data Access" (home_freedataaccess.php) lists AGGREGATE products only:
      All-India monthly and seasonal mean temperature series, All-India monthly and seasonal
      rainfall, cyclonic-system frequencies, gridded climatological data, climate tables.
    - "The Version 4.0, is operational from 27th July 2020 / launched 16th August 2021 ...
      Henceforth, the account-login enrolment process is introduced for the procurement of
      data." + "Estimate of Data Charges can be checked (for those who are not under MoES
      organisation)" - station-level series are enrolment-gated and chargeable.
    - Data types offered through supply: hourly/daily/monthly rainfall, temperature, RH,
      wind, pressure, clouds - i.e. exactly the series a station-level task needs.

## Verdict basis
    Access blocker (registration + network), not a data judgement. Unpark = probe from a
    worker in another region; enumerate free products; ask the operator about enrolment.
    Any gridded free product would need its own novelty check first (monsoon/rainfall
    prediction literature is enormous - not checked this session because the hypothetical
    task was not advanced).

## 2026-10-28 session (regional tick: South & South-East Asia): network blocker resolved from the coordinator; free inventory enumerated - no free station-level series

The 2026-10-20 HTTP 000 findings are stale: both hosts answer from the coordinator now.

    curl -sk https://mausam.imd.gov.in/     -> HTTP 200, 229,231 bytes, 2.2 s
    curl -sk https://dsp.imdpune.gov.in/     -> HTTP 200 (home_freedataaccess.php: 200, 45,490 bytes, 2.0 s)

Free Data Access page read from the publisher's own instrument (not via search this time):

    curl -sk https://dsp.imdpune.gov.in/home_freedataaccess.php
    -> "IMD Free Data Access" lists exactly THREE products: (1) All India Monthly and
       Seasonal Mean Temperature Series, (2) All India Monthly and Seasonal Rainfall,
       (3) Frequency of Cyclonic Systems in Indian Ocean Region. It states the same
       information "is also available on Open Government Data Platform
       (https://data.gov.in/)". No station-level product. Page footer: "Copyright
       (c) India Meteorological Department 2019"; Version 4.0 note repeats the
       account-login enrolment for data procurement; Data Delivery Report table shows
       monthly request volumes (Oct 2026: 322 requests received / 250 completed).

mausam.imd.gov.in enumerated (home + section pages): forecast/bulletin/GIS portal only -
district nowcast GIS, warnings, seasonal forecasts, radar, satellite, cyclone info,
monsoon info, flash-flood bulletins. The station-rainfall page
(responsive/rainfall_page_station_rainfall.php, 53,057 bytes) is a static shell with no
data form and no inline AJAX endpoint (only a Google search box and amcharts/map JS);
climate_services.php is likewise informational (links out to internal.imd.gov.in city
pages, nwp.imd.gov.in model outputs, srf.tropmet.res.in). No downloadable station
observation archive on any public page measured.

## Decision 2026-10-28

Stays PARKED; the access blocker is now fully measured: station-level historical series
remain enrolment-gated and chargeable on the publisher's own Data Supply Portal, and the
complete free inventory (three national aggregate series + cyclonic-system counts)
cannot carry a station-level task. The unpark is no longer a probe question but an
operator decision on paid enrolment. Cheap watch trigger for a future tick: one request
to https://dsp.imdpune.gov.in/home_freedataaccess.php - reopen only if a station-level
product appears in the free list (then licence terms must be read before any advance).
