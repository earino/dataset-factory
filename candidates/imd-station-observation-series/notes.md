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
