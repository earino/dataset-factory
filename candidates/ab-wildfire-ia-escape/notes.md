# ab-wildfire-ia-escape - discovery notes

Discovered and probed 2026-11-06 (Canada-focus scheduled discovery session).
All commands run on the coordinator from the repo root; the source CSV is the
pinned copy described below (the portal blocks plain HTTP clients).

## The task in one sentence

At Alberta Wildfire's initial assessment of a newly discovered wildfire in the
Forest Protection Area - the moment the Incident Commander's assessment is
recorded - predict from the crew-observed assessment record (size, rate of
spread, fire behaviour, slope position, in-situ weather, fuel type, detection
channel, season, elapsed time since report/ignition) whether the fire will
escape initial attack (final area burned >= 100 ha) and/or remain uncontained
longer than 72 hours - the resource-prioritization decision airtanker groups
and incident commanders actually face, on a 20-year regulator record.

## Source and pinned inputs

- CSV: fp-historical-wildfire-data-2006-2025.csv, 10,400,030 B,
  sha256 8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72.
  URL: https://open.alberta.ca/dataset/a221e7a0-4f46-4be7-9c5a-e29de9a3447e/resource/80480824-0c50-456c-9723-f9d4fc136141/download/fp-historical-wildfire-data-2006-2025.csv
  Licence: Open Government Licence - Alberta v2.2 (quoted in record.json).
- Data dictionary PDF: fp-historical-wildfire-data-dictionary-2006-2025.pdf,
  192,870 B, sha256 bfff81c0d0e4b5cb0684180a53ddab4da54ddb5dd63f0c0f9497fa67f2334cdf.
  No text layer (16 scanned pages); rendered at 150 dpi and transcribed
  verbatim into references/data-dictionary-transcript.md (every field this
  task ships or excludes, with page cites).
- Access path measured: open.alberta.ca sits behind a Cloudflare managed
  challenge for plain HTTP clients (curl 403, cf-mitigated: challenge, both
  with a bare and a full Chrome UA). The supported browser loads the dataset
  page and serves both files 200 (Content-Length measured 10,400,030 and
  192,870); both files were fetched through the cleared page context and
  byte-verified. The open.canada.ca CKAN mirror
  (package_show id=a221e7a0-4f46-4be7-9c5a-e29de9a3447e, read 2026-11-06)
  federates the same two resources but redirects downloads back to
  open.alberta.ca, so the browser path is the only anonymous bulk channel.
  CONSTRUCTION PREREQUISITE: a worker fetching the CSV with plain curl will
  hit the same challenge; ship the sha256-pinned 10.4 MB CSV inside the job
  bundle or re-fetch via the recorded browser procedure, and assert the
  digest in-build.
- Older eras exist as separate CSVs (1961-1982, 1983-1995, 1996-2005, seen in
  the portal listing and open.canada.ca federation); different schema
  generations - not needed for the task; noted as extenders only.

## Dated example (named timezone: America/Edmonton; CSV datetimes carry no
timezone and are recorded by the publisher in local Alberta operational time -
ASSUMPTION, to be confirmed at construction against a fire with a
publicly documented UTC timestamp)

Worked from the pinned CSV row YEAR=2023, FIRE_NUMBER=HWF036 (Long Lake
Complex, the second-largest holdout fire):

- Feature event window (all at or before the instant): fire_start_date
  2023-05-03 16:21 (estimated ignition), reported_date 2023-05-03 16:26,
  detection unplanned/public; at the assessment instant 2023-05-03 16:26
  America/Edmonton (MDT, = 2023-05-03 22:26 UTC): assessment_hectares 4,
  fire_spread_rate 2 m/min, fire_type Surface, position Flat, weather Clear,
  temperature 25 C, relative_humidity 15%, wind W 30 km/h, fuel_type O1a
  (matted grass), lat/lon 58.4906/-119.4031.
- Eligibility: every wildfire in the dataset is assessed (100%); no
  outcome-conditioned selection - the row is eligible because it was
  discovered and assessed, not because it grew.
- Prediction instant: assessment_datetime 2023-05-03 16:26 America/Edmonton.
- Target start/end: the remainder of the incident (assessment instant -> under
  control). First under control 2024-01-30 10:35 (241 days after assessment);
  extinguished 2024-07-29 8:30; final area burned 203,022 ha (size class E).
- Observed outcome: escape label (final >= 100 ha) = 1; containment label
  (first under control more than 72 h after assessment) = 1.
- No part of the target precedes the instant: the fire's growth happens after
  16:26; first_bh/first_uc/first_ex and the revised final size are all
  post-instant milestones and are label sources only.

Negative example from the same season: LWF002 2023 - start 2023-04-07 16:15,
reported 16:39, assessed 2023-04-08 10:35 at 0.01 ha, spread rate 0, RH 51%,
wind 5 km/h, fuel O1a, ground fire; under control at the same instant
(duration 0 h -> containment label 0), extinguished 2023-05-03, final 0.01 ha
(escape label 0).

## Population and provenance mix

All wildfires with a point of origin inside Alberta's Forest Protection Area
("wildfires have a point of origin inside the Forest Protection Area - either
provincial lands or federal lands covered by agreement with the province";
mutual-aid fires outside the FPA are excluded by the publisher). 27,828 rows
2006-2025, one row per wildfire: (YEAR, FIRE_NUMBER) is unique (0 duplicates
measured). Detection channel mix drifts across years (provenance, not
population): lookouts 34% of 2006 fires -> 21% of 2025; unplanned (public
reports) 42% -> 59% (full per-year mixes in
probe_escape_base_rates_result.json). The population is stable; the mix is a
recorded distribution shift, shipped as a feature (det_agent_type).

## Commands and measurements (reproducible)

```
python3 candidates/ab-wildfire-ia-escape/probe_escape_base_rates.py \
    <pinned-csv> candidates/ab-wildfire-ia-escape/probe_escape_base_rates_result.json
python3 candidates/ab-wildfire-ia-escape/probe_publisher_crosscheck.py \
    <pinned-csv> candidates/ab-wildfire-ia-escape/probe_publisher_crosscheck_result.json
```

Measured results (full JSON next to the scripts):

1. Per-year counts 2006-2025: 723 (2020) to 1,954 (2006); 1,011-1,342/yr in
   2019-2025. Total 27,828.
2. Prediction-instant ordering (vs assessment_datetime): reported_date at or
   before for 27,828/27,828; discovered_date 21,977/21,977 (5,851 missing);
   fire_start_date 27,109/27,109 (719 missing); dispatch_date at or before for
   27,143/27,813 (2.41% after - dispatch fields excluded from features on this
   mixed ordering evidence); start_for_fire_date 96.44% at or before (same
   treatment). Zero unparsed datetimes across all timestamp columns.
3. Feature coverage by window (train 2006-2015 / eval 2016-2020 /
   holdout 2021-2025): assessment_datetime and assessment_hectares 100% in all
   three; weather block 88.8/86.4/94.0%; fire_spread_rate 88.9/86.7/94.6%;
   fuel_type 68.8/71.1/81.6%; fire_type 89.2/88.0/96.0%;
   discovered_date 88.8/72.4/59.9% (its dictionary note explains the
   unplanned-detection blanks; reported_date 100% is the always-available
   pre-assessment timestamp).
4. Escape base rates (final area burned >= threshold), per window:
   - >= 100 ha: train 297/15,944 (1.86%), eval 104/5,627 (1.85%),
     holdout 257/6,257 (4.11%).
   - >= 200 ha (publisher's size class E): 235 (1.47%) / 76 (1.35%) /
     217 (3.47%).
   - >= 4 ha: 1,167 (7.32%) / 433 (7.70%) / 705 (11.27%).
   Both classes present in every window at every threshold. The holdout rate is
   higher because 2021-2025 contains the 2023 record season - real
   non-stationarity, recorded as a task property (see fixtures below).
5. Clustered positives (independence scale): escapes arrive on the same
   extreme-weather days. Distinct assessment dates of >=100 ha positives:
   train 156, eval 79, holdout 128 (vs 297/104/257 positives). Report and
   score at the fire grain but treat same-day fires as the cluster; put
   intervals on clustered counts.
6. Containment label (assessment -> first under control): median 0.4 h,
   p90 24.4 h; > 72 h for 4.72% overall - per window 514 (3.2%) / 189 (3.4%) /
   611 (9.8%). 11,688/27,828 fires (42.0%) were already under control at the
   assessment instant (assessment == first under control) - a degenerate
   label-0 stratum the construction decision must handle explicitly (exclude
   or keep, and declare in quality.json.evaluation_contract). Escape is the
   primary label; containment is the secondary formulation.
7. Publisher cross-check (probe_publisher_crosscheck.py): CSV hectares vs
   Alberta Wildfire's published season totals: 2020 3,274 vs 3,269; 2021
   54,089 vs 54,047; 2022 131,272 vs 130,858; 2023 2,217,295 vs 2,211,900;
   2024 714,874 vs 708,528 (all within 1%); 2019 791,838 vs 883,411
   (-10.4%) - consistent with the dictionary's statement that area burned is
   revised downward the following spring when aerial-photography
   interpretation removes waterbodies and unburnt islands. Fire counts differ
   from published season totals because the CSV is year-round (winter
   wildfires included; e.g. 31 new wildfires Nov-Dec 2025 per the 2025 season
   PDF) while the published season runs March 1 - October 31.
8. Revision/label-flip sensitivity: fires within +-20% of the 100 ha
   threshold: 89 (0.32% of all rows); of 40 ha: 146; of 10 ha: 260; of 4 ha:
   383. Post-hoc area revision can flip a threshold label only for this small
   band; per-fire historical vintages are NOT recoverable from this single
   current compilation (see the vintage section).
9. Data-quality probes: 0 duplicate (YEAR, FIRE_NUMBER); 0 SIZE_CLASS vs
   CURRENT_SIZE threshold inconsistencies; 0 rows with CURRENT_SIZE 0; 0
   unparseable timestamps. Cause-family fields are post-investigation
   (dictionary: "under investigation" temporary cause; "true_cause"
   52.5% filled vs 100% for general_cause) and are excluded from features.
   No personal names ship: assessment_resource is a 5-value position
   category, dispatched_resource and initial_action_by are resource codes
   (measured distinct values; the OGL personal-information exemption is not
   engaged by the shipped columns).
10. Extraction cost, measured on this coordinator (4 vCPU container):
    one 10.4 MB CSV + one 193 KB PDF through the cleared browser context,
    ~12 s of transfer + ~25 s chunked export; the probe scripts then run in
    ~3 s over the full 27,828-row CSV locally. Construction on a worker is
    one CSV parse of 10.4 MB - minutes, not hours; no bulk transfer beyond
    the source file itself.

## Known-event fixtures (per split window)

- Train: 2011 Richardson Fire (MWF007) final 577,646.8 ha - escape positive;
  2012 Zama Complex (HWF106) 134,603 ha; 2011 Utikuma Complex (SWF057)
  87,659.4 ha. All publicly documented (Alberta 2011 review, season reports).
- Eval: 2016 Horse River Fire / Fort McMurray (MWF009) final 485,123.6 ha;
  2019 Chuckegg Creek Fire (HWF042) 334,772.6 ha; 2019 McMillan Complex
  (SWF049) 222,837.2 ha. Note: the commonly quoted ~589,000 ha Horse River
  figure is a multi-jurisdiction accounting; the publisher's own final area
  burned for the Alberta wildfire record is 485,123.6 ha - fixtures compare
  against the publisher's numbers, not third-party figures.
- Holdout: 2023 Basset Fire (HWF058) 234,061 ha; Long Lake Complex (HWF036)
  203,022 ha; Pembina Complex (EWF031) 201,913 ha - the 2023 record season
  that raises the holdout base rate.
- Negative base: the 42% already-controlled-at-assessment stratum, e.g.
  LWF002 2023 (0.01 ha, duration 0 h) above.

## The five discovery contracts (reconciled)

1. Redistribution - SUPPORTED. Open Government Licence - Alberta v2.2,
   read from open.alberta.ca/licence 2026-11-06 (quoted in record.json):
   "worldwide, royalty-free, perpetual, non-exclusive licence to use the
   Information, including for commercial purposes"; free to "Copy, modify,
   publish, translate, adapt, distribute or otherwise use the Information in
   any medium, mode or format for any lawful purpose"; condition:
   "Acknowledge the source of the Information by including any attribution
   statement specified by the Information Provider(s)" with the default
   "Contains information licensed under the Open Government Licence -
   Alberta." Attribution wording carried verbatim into LICENSE.md at
   packaging; non-endorsement clause matches our standing derived-not-official
   labeling. Exemptions (personal information, third-party rights, official
   symbols) verified not engaged by the shipped columns.
2. Prediction timing - SUPPORTED (documented instant, documented features).
   The instant is assessment_datetime, "the date and time the wildfire was
   originally assessed". Every intended feature's meaning is documented by the
   publisher at that instant (assessment_hectares, fire_spread_rate,
   fire_type, fire_position_on_slope, the five weather fields, fuel_type all
   say "at the time of initial assessment"; reported/discovered/start/detection
   are pre-instant). Cause-family and suppression/milestone fields are
   documented as post-instant and are excluded. Measured ordering supports
   the instant (reported/discovered/start never after assessment). One
   declared assumption: timestamps carry no timezone and are read as local
   Alberta operational time (America/Edmonton).
3. Target - SUPPORTED. Labels derive from the record's own post-instant
   fields: current_size (final area burned) for escape; first_uc_date for
   containment. Both source columns are excludable from what ships (they are
   label sources; no shipped feature is derived from them). Eligibility is
   assessment-based, not outcome-based: every discovered wildfire in the FPA
   is assessed (100% coverage measured), so the row set is not selected on
   outcome. No censoring: every row has a terminal status (first_ex 99.9%,
   the remainder extinguished/TO pending in the compiled archive - checked at
   construction).
4. Split capacity - SUPPORTED, measured. Three disjoint year windows
   (train 2006-2015, eval 2016-2020, holdout 2021-2025) each carry both
   classes for both labels with 1.9-4.1% escape and 3.2-9.8% containment
   positives; clustered (same-day) positive counts recorded per window.
   Independence scale: the extreme fire-weather day (positives cluster on
   79-156 distinct assessment dates per window).
5. Not a mirror - SUPPORTED, differentiated (novelty check recorded by
   script). The IA-escape/IA-failure family is precedented and crowded:
   WildfireIA (US national benchmark from discovery-time public geodata for
   naturally-caused fires, its own motivation noting operational "response
   records" are non-public); Mesogeos (Mediterranean burned-area at ignition);
   Zong et al. 2026 Alberta POWERLINE-caused subset (294 kB CSV, environmental
   covariates, ignition-day 2 ha rule); Korkola et al. 2024 Ontario
   (non-public records); the UAlberta initial-attack-difficulty study (no
   published task). None ships this task's defining asset: the regulator's
   own per-incident initial-ASSESSMENT observations (crew-measured spread
   rate, fire behaviour, in-situ weather over the fire, assessment size,
   FBP fuel type) for ALL causes over 20 years, with containment-milestone
   labels and a publisher cross-checked revision record. A consumer cannot
   download an assessment-instant all-cause escape/containment task for any
   jurisdiction today.

## Vintage / as-of policy (explicit limitations, not silent assumptions)

This is a CURRENT-COMPILATION RETROSPECTIVE task, and the record says so:

- The archive is one living compilation (portal "Updated February 17, 2026";
  covers through 2025). Per-fire historical vintages are NOT published and
   NOT recoverable: the dictionary documents in-place revision of area burned
  (spring aerial-photography interpretation), cause (under-investigation ->
  final), and location (assessment GPS -> confirmed ignition area). The
  publisher's own 2019 season total (883,411 ha as published) vs the current
  archive (791,838 ha) measures that revision happening at aggregate scale.
- Therefore the task cannot claim operational point-in-time reproducibility of
  historical feature values. What it CAN claim, and what
  quality.json.evaluation_contract must state: (a) every feature is
  documented by the publisher as recorded at/before the assessment instant;
  (b) labels are the current final values; (c) threshold-flip exposure is
  bounded by the measured +-20% band (89 fires at 100 ha); (d) the assessment
  fields' semantic availability at the instant is the publisher's own
  operational design, not an inference.
- features that could be revised post-hoc with unknown direction (estimated
  start time, location refinement) are flagged in the evaluation contract
  rather than dropped - they are the operational estimates the IC held.

## What construction must decide (handoff)

Worker build (advancement owns it), then full-artifact qualification ->
exact-byte acceptance -> baseline triad before any number is quoted:

1. Fetch: browser-channel fetch or bundle-shipped pinned CSV; assert sha256
   8b6ed447... in-build; freeze and record.
2. Eligibility: all assessed wildfires (the full population); optionally
   restrict to fire season rows - decide once, declare.
3. Labels: primary escape (final >= 100 ha; report >= 200 ha and >= 4 ha
   variants too); secondary containment (first under control > 72 h after
   assessment) with an explicit decision on the 42% already-controlled
   stratum.
4. Features: the assessment block + pre-instant timing/detection fields +
   calendar/geography; EXCLUDE cause-family (general_cause, true_cause,
   industry_identifier, responsible_group, activity_class), dispatch block
   (mixed ordering measured), all suppression/milestone fields
   (initial_action_by, ia_*, fire_fighting_start_*, bucketing, first_*),
   and the label sources (current_size, size_class).
5. Timezone: confirm the America/Edmonton reading against a publicly
   documented timestamp (e.g. the Horse River 2016 report timeline) and
   declare it in the evaluation contract.
6. Splits by year: train 2006-2015 / eval 2016-2020 / holdout 2021-2025
   (both classes measured present); document the 2023-season base-rate shift
   in the dataset card.
7. Leakage probes at gate 1.5: assert no shipped column is derived from
   post-instant fields; assert (YEAR, FIRE_NUMBER) uniqueness; run the
   reverse-history join probes on the exact artifact.
8. Fixtures asserted in-build: the named fires above at their final sizes;
   the already-controlled stratum for the containment label.
9. LICENSE.md: MIT for our code; CC0 for our compilation rights; Alberta's
   terms preserved with the required attribution sentence; derived-work
   labeling per the non-endorsement clause.

## Construction (abwildfire-build-001, 2026-11-06) - COMPLETE

Full worker order construct -> qualify -> exact-byte accept -> pre-registered
references, exit 0 in 102.1 s (cx23 hel1, server 174889543, destroyed after
verified collection). Record status: qualified.

- Source channel: the pinned CSV was staged in the private staging repo
  (source-abwildfire-001, release 437116894, asset 718748383 - stage_source_
  2026_11_06.py, digest re-verified on redownload) because open.alberta.ca
  Cloudflare-challenges plain clients; the executor fetched it with sha256
  verification and build.py asserted the digest again.
- Population: all 27,828 assessed FPA wildfires; winter rows kept (587
  Nov-Feb); eligibility assessment-based, no outcome-conditioned rule.
- Splits follow the ASSESSMENT instant's calendar year (the time column):
  train 15,864 / eval 5,707 / holdout 6,257. 356 winter carryover fires
  move with their assessment year; every label-side count (positives
  297/104/257, distinct positive dates 156/79/128, containment>72h
  514/189/611, already-controlled 11,688) is identical under either rule.
- Shipped label: escape only (final area burned >= 100 ha). The containment
  formulation needs its own stratum decision and would be a separate task
  instance; its per-window measurements are in build-summary-abwildfire-
  build-001.json.
- Column policy enforced in code and asserted on the written headers: cause
  family, dispatch block (2.41% mixed ordering), suppression/milestone
  fields, fire_name (post-hoc, outcome-revealing), fire_origin (no publisher
  definition transcribed), discovered_size and detection_agent excluded.
- Timezone confirmed: the official 2016 Horse River review states
  detection at 16:03h MDT 2016-05-01 - the record's naive local 16:03 -
  and its under-control (2016-07-04) / extinguished (2017-08-02) dates
  match the record's milestones.
- Gate 1.5.0 on the FULL artifact, on the worker: ALL CHECKS GREEN
  (failed_checks []), artifact_version c2c8ceb56c7ff52aaf748473e1251725c4e
  86912edb9b17387e6b44d0e43da2; exact-byte --accept re-verified on the
  worker. The local dry run produced byte-identical files (same digest).
- Reference triad on eval 2016-2020 (5,707 rows, 104 positives), computed
  post-acceptance, holdout never opened: majority constant AUC 0.5
  (accuracy 0.9818); persistence analogue (assessment_hectares) 0.9096;
  calendar/identity prior 0.7130; full-feature L2 logistic 0.9206.
  Paired day-cluster bootstrap (500 resamples): full - persistence
  +0.0111 [-0.0292, +0.0514] INCONCLUSIVE (interval contains zero);
  full - calendar +0.2077 [+0.1551, +0.2644]; persistence - calendar
  +0.1966 [+0.1371, +0.2694]. Any quoted AUC must carry this comparison;
  no label, threshold, window or feature may be changed to widen the gap.
- Full extract (runner layout) preserved in staging draft release 437132110
  (job-abwildfire-build-001); compact reports committed beside this file
  (qualification-, references-, build-summary-abwildfire-build-001.json).
