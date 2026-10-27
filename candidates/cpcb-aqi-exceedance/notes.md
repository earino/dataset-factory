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
