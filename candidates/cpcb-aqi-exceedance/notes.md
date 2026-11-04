# cpcb-aqi-exceedance - probe evidence (2026-10-20, all anonymous unless stated)

## XKDR meta
    curl -H "Authorization: Bearer aqi_demo_..." https://airquality.xkdr.org/v1/meta
    -> HTTP 200; 196,521,834 measurements over 207 months (2009-01..2026-03), 558 stations,
       15 parameters; collected_at is naive IST; demo tier: 10,000 rows/query, 30 s timeout.
       (Demo key is published on the site's own front page.)

## XKDR measured sample (Delhi, Q1-2024, daily aggregate)
    curl -H "Authorization: Bearer aqi_demo_..." \
      "https://airquality.xkdr.org/v1/measurements?city=Delhi&parameter=PM2.5&start=2024-01-01&end=2024-03-31&agg=daily&format=csv"
    -> HTTP 200, 252,729 bytes, 3,384 data rows, 39 distinct station_ids; header:
       station_id,parameter_name,unit,period_start,mean,min,max,n
       site_103,PM2.5,µg/m³,2024-01-01 00:00:00,133.0733333333333,103.91,191.43,24
    Base rate at the proposed 90 µg/m³ threshold, computed with awk over that CSV:
       rows=3384 positive=1993 rate=0.5889 (Delhi winter - worst season; annual rate TBD at construction)

## OpenAQ archive (alternative, fully anonymous bulk channel)
    curl "https://openaq-data-archive.s3.amazonaws.com/?list-type=2&delimiter=%2F&max-keys=100"
    -> HTTP 200, single top-level prefix `records/`
    curl ".../?list-type=2&prefix=real-cpcb-gov-in/2024/&delimiter=%2F"
    -> KeyCount 0 (guessed provider-prefix layout absent; the documented layout is
       records/csv.gz/locationid=<id>/year=YYYY/month=MM/location-<id>-YYYYMMDD.csv.gz)
    Layout and licence read from docs.openaq.org (search reads of /aws/about, /about/terms,
    /about/faq, /resources/licenses): CC BY 4.0 per dataset, attribution + redistribution allowed,
    OpenAQ only ingests CC0/CC-BY data. CPCB locationids NOT enumerated this session (v3
    locations API needs a key) - first construction step.

## Official channels (negative probes)
    curl "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69?format=csv&limit=5"
    -> HTTP 000 (connection failure) from the coordinator, twice, 2026-10-20.
    CPCB CCR portal bulk: registration-gated (not probed anonymously).

## Novelty search (2026-10-20)
Queries: "CPCB AQI station-level prediction benchmark dataset splits", "CPCB PM2.5
exceedance prediction task dataset". Found: research papers with private splits
(arXiv 2404.08702 22-station study; Discover AI 2026 hybrid DL; city-level studies),
Kaggle data mirrors (2010-2023 CC BY-SA, 487 MB), OpenAQ/XKDR archives, Vayuayan archive.
No packaged train/eval/holdout task with a scored contract -> differentiated.

## 2026-10-28 observation (regional tick: South & South-East Asia)

No reopening: CPCB's own terms remain unread. api.data.gov.in is still TCP-refused from
the coordinator (re-measured today, HTTP 000), so the GODL-India claim recorded as
"unverified-from-here" cannot be read from this network. The prepared worker probe
candidates/india-datagovin-portal/probe/ (india-portal-probe-001, currently blocked by the
release-work guard, see that record) would read api.data.gov.in from hel1 and settle
this evidence if launched. Status unchanged: dropped, licence_class C.

## 2026-11-04 session (regional tick: South & South-East Asia) - LICENCE EVIDENCE READ; reopened from dropped

The drop's recorded blocker was "the publisher's own terms were never read; the only redistribution
evidence is a republisher's." This session read the publisher's instruments. Result: the drop's
reopen condition ("CPCB publishes its own explicit reuse licence") is met through the Government of
India's own open-data instrument. Status: dropped -> investigating. Drop history (verbatim):
"License not clean: the only redistribution evidence is a republisher's, and the publisher's own
terms were never read. Under the standing policy (2026-10-21) a source whose license we cannot
establish is not pursued, so this is closed rather than parked."

### CPCB's own site instrument (read live, 2026-11-04)
    curl -sS https://cpcb.gov.in/copyright-policy/   -> HTTP 200, 314,761 B
    Quote: "Material on this site is subject to copyright protection unless otherwise indicated.
    The material may be downloaded to file or printer without requiring specific prior permission.
    Any other proposed use of the material is subject to the approval of competent authority of
    CPCB. Application for obtaining permission should be made to mail id (ccb.cpcb@nic.in)"
    => restrictive-by-default with an explicit "unless otherwise indicated" carve-out.
    https://cpcb.gov.in/terms-condition/ -> HTTP 200 (third-party copyright, linked-site caveats).

### The indicated licence: GODL-India on the data.gov.in platform publication
Live portal unreachable (see india-datagovin-portal notes for the 2026-11-04 reachability
measurements), so the resource page was read from Wayback snapshot 20251231005230:
    https://web.archive.org/web/20251231005230/https://www.data.gov.in/resource/real-time-air-quality-index-various-locations
    -> HTTP 200, 137,370 B compressed capture; page title "Real time Air Quality Index from
    various locations | Open Government Data (OGD) Platform India"
    - contributor: "Ministry of Environment, Forest and Climate Change / Central Pollution
      Control Board"; Published On 04/08/2016, Updated On 31/12/2025
    - resource id on page: 3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69 (matches this record's resource)
    - platform instrument: "The content published on data.gov.in is owned by the respective
      Ministry/State/Department/Organization and licensed under the Government Open Data License -
      India" + "GOVERNMENT OF INDIA All rights reserved except published datasets/resources and
      metadata."
    Extracts: probe/out/wayback_resource_page_lic_extracts_20261104.txt
Independent live corroboration (readable without the blocked route), 2026-11-04:
    https://aikosh.indiaai.gov.in/home/datasets/details/real_time_air_quality_index_from_various_locations.html
    -> HTTP 200; "License: GODL license"; Source Organisation: MoEFCC, Central Pollution Control
    Board; Visibility Open; redirected to the OGD Platform.

### GODL-India v1.0 terms (read via Wayback 20170328213105 of data.gov.in's licence page)
    Section 3: "worldwide, royalty-free, non-exclusive license to use, adapt, publish (either in
    original, or in adapted and/or derivative forms), translate, display, add value, and create
    derivative works (including products and services), for all lawful commercial and
    non-commercial purposes"
    Conditions: attribution (named template, section 5), attribution of multiple data,
    non-endorsement, no warranty, continuity. NO share-alike clause anywhere in the text
    (grep over the full page: zero hits for share-alike / copyleft / "same license").
    => attribution-only open licence; class A. Carried into any release LICENSE.md with CPCB
    attribution and the source's designation preserved.

### XKDR access + compilation licence re-measured (2026-11-04)
    Front page demo key (published on the page itself): aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe
    (the 2026-10-20 key is rotated/revoked - API answers invalid_api_key for it).
    GET /v1/meta -> 196,521,834 rows, 207 months 2009-01..2026-03, 558 stations, 15 parameters,
    export stamped 2026-09-30T11:25:11+00:00; tier demo, 10,000 rows/query, 30 s timeout,
    "can only read the 2024 bulk files" (front-page statement; confirmed by the successful 2024
    monthly query below; full-history passes need the free signup key behind a Cloudflare human
    check, or the OpenAQ archive).
    GET /v1/stations (210,164 B) -> 558 = 553 cpcb_caaqm + 5 us_embassy (DS1010001..5: New Delhi,
    Mumbai, Chennai, Hyderabad, Kolkata); 549 of the 553 CPCB stations list PM2.5.
    -> task population = cpcb_caaqm stream only (embassy monitors are different instrumentation
    with different upstream terms, US DoS via AirNow; recorded as the provenance-mix decision).
    XKDR compilation licence (GitHub README, raw.githubusercontent.com/xKDR/Air-Quality-Database/
    main/README.md, read 2026-11-04): CC BY 4.0, credit "India Air Quality Database, XKDR Forum"
    + CPCB (CAAQM network) + US DoS via AirNow; values "as reported", "no gap filling",
    "preliminary and not fully validated" - vintage/revision posture recorded as open item (3).

### Eval-window (2024) coverage + seasonal class proxy (measured 2026-11-04)
    GET /v1/measurements?parameter=PM2.5&agg=monthly&start=2024-01-01&end=2024-12-31
    -> 988,061 B, 6,084 station-month rows, 5.63 s; 534 distinct stations, of which the 5
    embassy monitors contribute 59 station-month rows; cpcb stream 6,025 rows; 466 stations with all 12 months;
    per-month station counts 504/500/498/500/501/495/497/503/501/515/519/517.
    Monthly-mean >90 ug/m3 share of cpcb station-months (proxy for the daily label):
    Jan .317, Feb .131, Mar .032, Apr .044, May .062, Jun .018, Jul .004, Aug .004, Sep .004,
    Oct .091, Nov .308, Dec .203; annual 619/6025 = .1027.
    Winter-dominant positives => clustered counts (season x state) required at construction.

### Station coverage depth (from /v1/stations first_seen/last_seen, 2026-11-04)
    PM2.5 cpcb stations by last_seen year: 2016:2, 2019:1, 2020:2, 2021:1, 2022:3, 2023:5,
    2024:205, 2025:330, 2026:0 -> the PM2.5 stream effectively ends 2025-12 (the table-level
    last_month 2026-03 notwithstanding); proposed holdout shrinks to 2025.
    By first_seen year: 2009:15, 2010:6, 2011:3, 2012:1, 2015:6, 2016:14, 2017:42, 2018:48,
    2019:66, 2020:55, 2021:66, 2022:75, 2023:127, 2024:22, 2025:3 -> 135 stations started
    <= 2019-01 (train-era depth).

### Open items to ready (record.next_action has the ordered list)
    (1) exact per-window DAILY class + clustered counts (full key or OpenAQ; demo tier is
    2024-files-only); (2) NAAQS 90 ug/m3 threshold citation + known-event fixture from CPCB's own
    Daily AQI Bulletin; (3) vintage/revision policy statement; (4) cross-row self-answer design
    input (a scored day-D row's D+1 mean appears in D+2..D+91 trailing features - za-cct-style
    bounded exposure + gate reverse-history probe); (5) five-contract reconciliation in review.

Probe outputs retained: probe/out/{xkdr_meta_2026_11_04.json, xkdr_stations_2026_11_04.json,
pm25_cpcb_stations_2026_11_04.json, xkdr_pm25_monthly_2024_2026_11_04.json,
wayback_resource_page_lic_extracts_20261104.txt}; script: probe/probe_cpcb_reopen_2026_11_04.py.
