# malaysia-river-danger-exceedance - probe evidence (2026-10-20, all anonymous)

## Current-conditions pages (working)
    curl "https://publicinfobanjir.water.gov.my/?lang=en"          -> 200, 93,377 bytes
    curl ".../aras-air/data-paras-air/?state=KEL&lang=en"         -> 200, 76,926 bytes
       - per-station rows with 'Danger Level:' / 'Warning Level:' / 'Alert Level:' /
         'Normal Level.' threshold columns (grep-measured)
       - 15 state options: PLS, KDH, PNG, PRK, SEL, WLH, PTJ, NSN, MLK, JHR, PHG, TRG, KEL, SRK, SAB, WLP
    Station codes seen in the KEL page HTML: AAAG9200, CC2127, FBC002, FF0084, FF7300, OY416.

## Historical trend endpoints (extracted from the trend page JS, lines 1300/1409/2752/3327)
    /wp-content/themes/enlighten/query/searchresulttrenddata1hour.php?lang=en&state=<S>&district=<D>&station=<ST>&from=<F>&to=<T>&datafreq=<FREQ>
    /wp-content/themes/enlighten/query/searchresultwaterleveldtlead_rptdb.php?station=<ST>&from=<F>&to=<T>&datafreq=<FREQ>
    /wp-content/themes/enlighten/query/searchresulttrenddata15min.php, searchresultrainfalldthourlylead_rptdb.php, searchresulttrendlead.php
    helpers: searchdistricttrend.php?name=, searchstationTrend.php?lang=en&name=

## Historical probes (failed this session - the park reason)
    searchresulttrenddata1hour.php?lang=en&state=KEL                      -> "Tiada data / No data"
    searchstationTrend.php?lang=en&name=KEL                               -> only "Choose Station"/ALL placeholder
    searchdistricttrend.php?name=KEL                                      -> only "Pilih Daerah"/ALL placeholder
    searchresultwaterleveldtlead_rptdb.php?station=CC2127&from=2026-07-01&to=2026-07-03&datafreq=60
       (and 01/07/2026-03/07/2026 variants, and station=ALL)              -> {"count":,]}No result
    latestreadingstrendabc.json at /, /api/, /wp-content/themes/enlighten/ -> 404
    Endpoints are alive and anonymous; the exact parameter contract (district/station keys,
    date format) was not captured. Unpark step: real-browser capture of the trend page XHR.

## Licence
    grep of home/state/trend HTML for copyright|hak cipta|terms|privacy: no licence text found.
    data.gov.my homepage (fetched, 140,945 bytes) advertises 'flood-warning' and 'rainfall'
    catalog categories, but dataset pages load client-side; entry not located this session.

## Prior art checked (2026-10-20)
    Caravan (arXiv 2212.00719) - global river DISCHARGE regression benchmark; Google Flood Hub -
    operational forecasts, not a dataset; FloodCastBench (2025) - coastal; Wupper/LamaH-CE
    studies - discharge regression. No packaged official-threshold EXCEEDANCE classification
    task on this publisher's telemetry found.
