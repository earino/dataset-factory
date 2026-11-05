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

## 2026-11-05 session (regional tick: South & South-East Asia) - steps 1-4 of the reopen next_action EXECUTED; full-panel daily counts measured, splits re-cut on a measured 2025 export hole, threshold bound, fixture confirmed; status -> READY

### XKDR channel, measured (all anonymous; scripts probe/probe_cpcb_full_window_2026_11_05.py + probe_sea_watch_triggers_2026_11_05.py)
- Transient 401 window 20:33-20:44Z: every request (incl. /v1/meta) answered 401 with the same
  front-page demo key that returned 200 before and after; no rotation (page byte-identical), no
  cookies involved. Separately and standing: Cloudflare 403 "error code: 1010" for the literal
  'Python-urllib' UA only - curl, curl-UA-urllib, custom UA and the browser all pass.
- Demo-tier boundary is /v1/files, not /v1/measurements:
    GET /v1/files/v1/measurements/year=2019/month=01/data.parquet  (Range 0-1023) -> 403
    GET /v1/files/v1/measurements/year=2024/month=11/data.parquet (Range 0-1023) -> 206
    GET /v1/files -> 200: 207 monthly parquets, 409,568,028 B / 196,521,834 rows, plus
    v1/stations.parquet (27,232 B), v1/parameters.parquet (1,366 B)
    GET /v1/measurements?...start=2019-01-01&end=2019-01-31&agg=monthly -> 200, x-tier: demo,
    x-truncated: false, 144 station-months -> the front-page "2024 bulk files only" prose
    describes /v1/files; full-history QUERY access is anonymous at the demo tier.
- FULL-PANEL RUN (84 months x 2 station-batches, agg=daily, PM2.5, cpcb_caaqm only): 166 requests,
  ~500 s wall on the 4-vCPU coordinator, 716,750 station-days streamed, zero truncated responses.
  One fetch defect fixed mid-run: hardcoded Feb-29 produced end=2019-02-29 -> HTTP 400
  {"error":"request_error","detail":"end must be YYYY-MM-DD"} (the first 'transient 400'
  diagnosis was wrong - it was this bug; replaced with calendar.monthrange).
  Output: probe/out/xkdr_daily_counts_2019_2025_2026_11_05.json (per-month, state-month triples,
  both window cuts). The earlier zero-count artifact from the 401 window was deleted, not kept
  as evidence (its content is this paragraph).

### The 2025 export hole -> one re-cut BEFORE any score (measured, both cuts preserved)
- Monthly all-station queries (parameter=PM2.5&agg=monthly): 2025-01 -> 5 rows, 2025-03 -> 4,
  2025-10 -> 2, 2025-12 -> 2, 2026-01 -> 2 (the 2-5 rows are the 5 us_embassy monitors - the
  cpcb stream has none). Panel months present: 2025-04..2025-08 (~320 stations, 9.2-9.7k
  station-days/month) plus ONE day 2025-09-01 (294 station-days). NO cpcb pm25 rows for
  2025-01..03 or 2025-10..12. The 2026-11-04 "stream effectively ends 2025-12" reading was wrong
  in both directions: it ends 2025-09-01 AND Jan-Mar 2025 is missing.
- Consequence: the proposed holdout-2025 would be a winter-free 1.74%-prevalence tail.
  RE-CUT (the afdb no-score precedent): train 2019-2022 / eval 2023 / holdout 2024.
  Measured: train 339,557 station-days / 63,735 positives (18.77%) / 390 stations / 85 state-x-season
  cells / 1,267 positive days; eval 2023 154,003 / 20,773 (13.49%) / 511 / 90 / 357;
  holdout 2024 175,624 / 19,254 (10.96%) / 529 / 92 / 358. Excluded tail 2025-04..09:
  47,566 / 829 (1.74%) / 329 stations - counted, declared, never scored.

### Threshold bound to the publisher's instrument + fixture confirmed on both sides
- CPCB 'About National Air Quality Index' PDF (cpcb.gov.in/displaypdf.php?id=bmF0aW9uYWwtYWly
  LXF1YWxpdHktaW5kZXgvQWJvdXRfQVFJLnBkZg==, 298,817 B, retained probe/out/about_aqi.pdf):
  PM2.5 24-hourly breakpoints Moderately Polluted (101-200) 61-90 ug/m3; Poor (201-300) 91-120;
  Very Poor 121-250; Severe 250+. Corroborated by CPCB's AQI-Calculator.xlsx
  (app.cpcbccr.com/ccr_docs/AQI-Calculator.xlsx): 61.0-90.0 -> 101-200; 91.0-120.0 -> 201-300.
- CPCB Daily AQI Bulletin 2024-11-18 (cpcb.gov.in/upload/Downloads/AQI_Bulletin_20241118.pdf,
  52,671 B, retained): Delhi Severe 494, prominent pollutant PM2.5, 36/39 stations; Bahadurgarh
  453, Bhiwadi 447, Dharuhera 447, Ghaziabad 438, Bhiwani 429, Churu 401 Severe; Faridabad 367
  Very Poor. MEASURED from the panel rows: 38 Delhi cpcb station-days on 2024-11-18; all 36
  complete ones (n>=18h) label TRUE (means 235.7-731.5 ug/m3); the 2 exceptions are incomplete
  days (n=11, n=9) - matching the bulletin's 36/39 participating stations. Caveat recorded: the
  bulletin averages 4PM-4PM and takes the worst sub-index - a category-level cross-check, not a
  numeric reproduction. Bulletin 2024-11-17 retained alongside.

### OpenAQ archive enumerated (anonymous) - decisive 2023-2024 gap
- Wayback capture 20230425092626id_ of api.openaq.org/v2/locations?limit=10000&country=IN
  (3,459,137 B valid JSON; the plain fetch returns a 9,058 B wrapper - the id_ modifier is
  required): 1,765 IN locations; 989 government; 978 source 'Central Pollution Control Board'
  (312 also 'data.gov.in'); 937 with pm25 (ids 13..363603); the 5 embassy monitors appear as
  'U.S. Department of State India - *' (corroborating the us_embassy exclusion); meta license
  'CC BY 4.0d'.
- S3 year-dir enumeration of all 937 (one LIST each): 447 have any archive. Per-year location
  counts 2015:7 2016:40 2017:40 2018:182 2019:203 2020:270 2021:324 2022:365 2023:0 2024:0
  2025:332 2026:327; 316 follow 2022 -> (gap) -> 2025; ZERO have any 2023/2024 files.
  => OpenAQ's India ingestion stopped ~Oct 2022 and resumed 2025; it cannot carry eval-2023 or
  holdout-2024 and has no 2023 at all. XKDR is the only channel carrying all three re-cut
  windows. Evidence: probe/out/{openaq_in_locations_2023_04_25_compact.json,
  openaq_cpcb_937_year_coverage_2026_11_05.json}; scripts probe/probe_openaq_*_2026_11_05.py.

### Full free XKDR key - MISSING ACCESS (operator)
- Signup page read in the supported browser: EMAIL (required), NAME (required), affiliation and
  purpose (optional), accept_terms checkbox ('I will credit the data sources (CPCB and the US
  Department of State) and XKDR Forum in any publication' - consistent with our attribution
  practice), Cloudflare Turnstile; 'Free and instant... your key appears on the next page.'
- No project email identity exists on this host (himalaya not configured; no recorded convention
  for third-party signups), so the key was not obtainable this session. Options recorded for the
  operator: (a) supply/authorize an email for the signup, (b) provide a full key directly, or
  (c) leave construction on the anonymous measurements-API batching path (viable and measured).

### Regional watch triggers (probe/probe_sea_watch_triggers_2026_11_05.py, all anonymous)
- IMD free list (dsp.imdpune.gov.in/home_freedataaccess.php): HTTP 200, 45,487 B; 'station' and
  'gridded' absent from the free list - aggregate products only; park stands.
- BMKG repogempa.bmkg.go.id/eventcatalog and data.bmkg.go.id: HTTP 200 both; no new anonymous
  bulk historical channel evident; park stands (operator options a/b/c unchanged).
- data.gov.vn / www.data.gov.vn: getent rc=2 both - still dark in DNS; park stands.
- data.gov.in: www 503, api TCP-refused (Errno 111) - unchanged from 2026-11-04; the operator's
  worker-location decision is the only unlock; park stands.
- BPS and PSA OpenSTAT: NOT re-probed - both carry recorded steady-state task-shape drops
  (aggregate-only statistics publishers) with reopen conditions that have not fired.
- Singapore data.gov.sg catalog diff: NOT run this tick (the recorded quarterly enumeration is
  ~467 requests and the last full enumeration is recent); unpark trigger unchanged.

Five contracts reconciled in record.review; status investigating -> ready (the buffer's ready
candidate for this region). Construction handoff order in record.next_action.

## 2026-11-05 (late) - advancement session: construction design finalized pre-launch; build.py drafted (UNTESTED - no dry run yet, no worker launched, no gate run, nothing scored)

Primary candidate chosen per the 2026-11-05 21:55Z STATE next_action (advancement
owns the cpcb-aqi-exceedance construction). No actionable packaged release exists
(cqc, za-cct-substation, ns-bwa all carry awaiting_operator: true - human waits,
untouched). Job ledger reconciled: no running or pending jobs (dvsa-mot-build-001
collected+destroyed 19:52Z; afdb-build-001 succeeded 17:01Z today and is the freshest
proven gate-1.5 worker template - its source/ is the structural pattern used here).

### Preflight measurements (this session, anonymous demo key, bounded - 4 requests;
### retained: probe/out/preflight_build_design_2026_11_05.json)

- /v1/meta vintage-pin field confirmed: exported_at = "2026-09-30T11:25:11+00:00",
  measurements.rows = 196,521,834. Both are now hard anchors in build.py (a re-export
  refuses the build).
- cpcb_caaqm PM2.5 station count re-confirmed: 549 (anchor).
- Delhi 2024-11-18 severe-day fixture RE-VERIFIED on the label side: 38 station-days,
  36 complete (n>=18), 36/36 mean > 90 ug/m3. Asserted exactly in build.py.
- Monsoon negative-control day measured: 2023-08-15 all-India: 425 station-days,
  389 complete, 1 exceed. Pre-registered as a TROUGH BOUND (>= 300 complete,
  <= 4 exceed) in build.py - an all-or-nothing "0 positives" fixture would be wrong
  (the record's own seasonal proxy says ~0.4% of monsoon station-days still exceed).

### Design finalized BEFORE any score (pre-registration; no score, gate or
### acceptance has ever existed for this candidate)

- Layout/identity (za-cct precedent, gate-1.5-proven): id_columns = [station_day]
  (station_id|date, unique); station_id and date ship as declared
  high_cardinality FEATURES (station identity is hidden from the runner otherwise,
  and state_name enables the pre-registered state-x-season climatology reference to
  be computed from shipped columns); event_key_column = date (the clustered event =
  the winter day; matches the record's distinct_positive_days counts);
  expected_duplicate_ids = 0; id_columns_are_entity_keys = true.
- Splits by prediction instant D: train 2019-2022 / eval 2023 / holdout 2024;
  2025-04..09 tail excluded+counted; 2025 hole months asserted empty.
- Row = station-day with n_hours(D) >= 18 AND labelable D+1 (row present, n >= 18);
  unlabelable excluded AND counted per split AND per month (exclusion seasonality
  recorded in summary.json - the monsoon co-movement of thin D+1 days is a declared,
  measurable limitation, not a hidden one).
- Label: D+1 24-hr mean > 90 ug/m3 (strict; CPCB Poor-band lower edge).
- Features (21): station_id, state_name, date, day_of_week, month, doy_sin, doy_cos,
  pm25_mean/max/min, n_hours, pm25_mean_lag1..3, pm25_mean_7d + pm25_days_valid_7d,
  pm25_mean_30d + pm25_days_valid_30d, pm25_hist_mean_90d, days_since_gt90,
  exceed_count_30d. Missing policy: -1.0 sentinels + explicit count columns; rolling
  windows require 4/10/30 valid days. All features are functions of hourly readings
  through day D only. NOTE: this adds station_id + state_name (coarse identity,
  knowable at prediction time) to the discovery tick's "trailing stats + calendar
  only" summary - a pre-launch design finalization, recorded here BEFORE any score,
  with the reason (identity enables the pre-registered climatology reference; the
  prediction question's "the station's own history" is unchanged - identity is the
  station's own metadata).
- Timing: kind=event_time, 23:59 IST on day D; administrative_record source_kind;
  day-D trailing completeness at the instant is the DECLARED ASSUMPTION (CPCB
  intraday latency unmeasured; the publisher's 4 PM bulletin shows incomplete
  station participation). evaluation_contract: use=retrospective_research,
  access=isolated_rows, training_label_timing=unverified, vintage=current_snapshot
  (single 2026-09-30 export pinned), selection=prediction_time with the
  outcome-observability D+1 rule declared and its seasonality recorded.
- Cross-row exposure declared + probed (gate 1.5 reverse-history): entity
  station_id, offset 1 day, left=pm25_mean, gt 90 - row D+1's pm25_mean IS row D's
  label operand; trailing-aggregate exposure (D+2..D+91) declared in probes_note.
- Hard panel anchors asserted exactly (from record window_counts_2026_11_05):
  716,750 fetched rows; 339,557/154,003/175,624/47,566 per window; 63,735/20,773/
  19,254/829 valid-day positives per window; 549 stations; Delhi fixture; monsoon
  bound. Any drift refuses the build loudly (one worker cycle at risk, accepted).
- Channel: anonymous demo-key /v1/measurements batching (84 months x 2 batches,
  ~168 requests, X-Truncated asserted false per batch). Demo-key rotation fallback:
  re-read the front-page constant once on auth refusal (rotation observed once;
  the key is the publisher's own published anonymous constant, not a credential).
- Job sizing planned: cpx32/hel1, timeout 100 min, lifetime 140 (reservation 0.32
  EUR), memory 8192 MB, max_artifact_mb 300 (shipped extract estimated 100-150 MB
  from ~550-610k eligible rows x 23 columns), max_disk 30000.

### Handoff - exact remaining steps for a fresh session (in order)

1. Read this note + record.next_action; the design above is final pre-registration.
2. Write source/score.py (adapt afdb-project-cancellation/source/score.py): triad on
   EVAL rows only = station persistence (score = pm25_mean, the most recent observed
   daily value; report binary [pm25_mean>90] agreement as supplementary),
   state-x-season climatology (train-estimated rate per state_name x season(D+1);
   state rate then global train rate fallbacks), majority/global_rate (constant;
   AUC null, accuracy + brier). Supplementary: station_train_rate. Station-clustered
   paired bootstrap (cluster = station_id, 1000 resamples, fixed seed), per-month
   AUC/Brier within eval 2023, per-split + per-month prevalence. Holdout never read.
   DECIDING RULE (pre-registered, before any score): headroom ONLY if the full model
   beats EVERY triad member on identical eval rows with a station-clustered paired
   bootstrap 95% CI excluding zero in the model's favour AND the model's own
   cluster-bootstrap AUC CI lies above 0.5 (degenerate constant member). Triad
   dominance -> recorded defect; drop or re-target (the skill's
   persistence-dominance rule).
3. Write source/run.sh (fixed order: build -> qualify -> accept -> score, mirroring
   dvsa-mot's run.sh), source/job.json (id cpcb-aqi-build-001, image
   python:3.13-slim, sh /workspace/run.sh, cpx32/hel1, cpus 4, memory_mb 8192,
   timeout_minutes 100, lifetime_minutes 140, max_disk_mb 30000, max_artifact_mb
   300), source/bundle.json (files: build.py, run.sh, score.py, qualify_dataset.py
   from skills/dataset-qualification/scripts/; overrides matching job.json).
4. LOCAL DRY RUN first (no worker money): python3 source/build.py --synthetic
   --out <scratch>/extract --work-dir <scratch>/work; then the REAL gate:
   python3 skills/dataset-qualification/scripts/qualify_dataset.py <extract> --json
   --report <scratch>/qualification.json; then --accept; then score.py against the
   synthetic extract. Fix anything the dry run catches BEFORE launch (dvsa's dry
   run caught two descriptor defects pre-launch; this build.py is UNTESTED - expect
   the dry run to find something).
5. Record this design block in record.json (construction pre-registration; keep
   check-candidate green) - or confirm the next_action already covers it.
6. python3 scripts/assemble-job.py <bundle>; sh scripts/scout-factory worker plan;
   launch. Collect, then the standing order (gate 1.5 full artifact on worker ->
   exact-byte --accept -> triad -> report; holdout sealed).

Build script: candidates/cpcb-aqi-exceedance/source/build.py exists but is UNTESTED
(no synthetic dry run was run - the session hit its wall-clock budget first). Treat
step 4 as mandatory before launch. Nothing was launched, scored, gated or accepted
this session; no EUR was spent.
