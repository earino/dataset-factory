# za-cct-substation-evening-peak-exceedance — notes

Africa tick 2026-11-01. Opened from the recorded handoff on
za-capetown-odp-coverage ("probe them in a later Africa tick before opening
new portals"). The named series resolved as recorded in that record's update
this session; the Hub search API then exposed an electricity family the DCAT
census missed, and its strongest member became this candidate.

## Commands behind the measurements (all 2026-11-01, anonymous, from the coordinator)

- Hub search API (the DCAT-US feed does NOT index this family — method gap
  recorded on the coverage record):
  `curl -sS 'https://odp-cctegis.opendata.arcgis.com/api/search/v1/collections/dataset/items?q=voltage&limit=10'`
  → Switching Substation Load Profile, Prepaid Electricity by Suburbs and
  Tariffs, Loadshedding schedule, Distribution/Transmission Capacity, etc.
- Item resolution:
  `https://www.arcgis.com/sharing/rest/content/items/bebf20c25bfa4ffaa7fc07a1a94ba287?f=json`
  → type Feature Service, url services6.arcgis.com/.../Switching_Substation_Load_Profile/FeatureServer,
  created 1772281773000 (2026-02-28), modified 1772446733000 (2026-03-02),
  access public, size 25,444,352; licenseInfo links the Open Data terms.
  Description quoted in record.measurements.publisher_caveat.
- Row count: `<FeatureServer>/0/query?where=1=1&returnCountOnly=true&f=json`
  → 52,608. outStatistics is advertised (supportsStatistics: true) but every
  outStatistics call returns 400 "Invalid outStatistics" on this service, so
  aggregates require paged reads — this is why the full scan (below) is the
  cheapest aggregate path.
- Full scan + streaming reduce: `python3 probe_fullscan.py`
  → 53 GETs (resultOffset paging, 1,000 rows), 70,086,470 bytes, 54.1 s;
  1,096 days each with exactly 48 half-hours; ts range 2022-01-01 00:00 ..
  2024-12-31 23:30 SAST; 41 double columns fully non-null (52,608/52,608);
  Triangle_132kV string-typed and empty; Morgen_Gronde_132kV string-typed,
  numeric-as-text. Raw pages are not stored; reduced aggregates
  (per-station-day day-peak and evening-peak matrices) are written to scratch.
- Label / split / cluster / fixture computation: `python3 probe_cluster.py`
  → labels by year (1,539/13,735; 1,256/14,965; 1,382/15,006), clustered
  distinct-day counts (227/246/247), monthly seasonality table, per-station
  winter/summer ratios, dated worked example (Grassy Park 66kV 2024-07-15:
  150.38 MVA > p95 146.82 → positive).
- Prepaid sibling probe (same services org; recorded on the coverage record,
  not opened): FeatureServer table fields = Suburb, units_per_Suburb,
  txmonth, number_in_Suburb, tariff; monthly, Jan 2024..Sep 2026 per the
  item title; sample rows show a `\\N` Suburb bucket.

## Provenance and population

- One provenance stream: the City's own telemetry export, one reading per
  substation per half-hour. No mixture risk. Two string-typed columns are a
  schema artifact (one empty, one numeric-as-text).
- Population: the City's 33kV/66kV/132kV switching stations as published
  (columns are the stations). Censoring: none — the grid is gapless, so
  observed absence of an exceedance is a true negative, not a missing label.

## Five-contract reconciliation (discovery evidence, 2026-11-01)

1. Redistribution: SUPPORTED. Class A — item licenseInfo + portal Terms of
   Use (disclaimer-only) + Council Open Data Policy 27781 ("freely used,
   shared and built-on by anyone, anywhere, for any purpose"). Instruments
   quoted in license_evidence; same publisher instruments already accepted
   on za-cct-c3-service-request-surge (ready).
2. Prediction timing: SUPPORTED WITHIN-ARTIFACT (retrospective). Every
   feature's meaning is documented by the publisher (half-hourly MVA per
   named substation; caveat quoted). Instant 06:00 SAST, target window
   entirely after. The table itself was published 2026-02..03 as a closed
   window: availability at any historical instant OUTSIDE the artifact is
   unverified → use = retrospective_research, label timing unverified,
   no operational-forecasting claim (docs/PREDICTION-CONTRACT.md).
3. Target: SUPPORTED. Label derivable from the same table; label-source
   columns (target evening readings) sealable and excludable from every
   shipped frame; eligibility decidable at the instant (>= 30 prior
   evenings). No external threshold reference — the baseline is internal
   (trailing p95), so no units/frame ambiguity beyond MVA, which the
   publisher states.
4. Split capacity: SUPPORTED, measured. Train 2022 / eval 2023 / holdout
   2024, both classes in each, positives clustered on 227/246/247 distinct
   days.
5. Not a mirror: SUPPORTED (differentiated) — prior art is regression /
   probabilistic load-forecasting benchmarks on EU/US/AU public data
   (KIT-IAI 2026; Rolle/EPFL 2019; Ausgrid zone-substation data; Liander
   2024 HF benchmark; Fraunhofer 25-dataset survey). None is African, none
   is a within-day exceedance classification with a sealed evening-label
   contract. Recorded by scripts/check-novelty.py.

## What advancement owns (construction handoff)

- Worker-side re-fetch of all 52,608 rows, sha256 pinned; build station-day
  rows with features <= 06:00 instant; sealed evening label matrix; splits
  2022/2023/2024; full-artifact qualification + exact-byte acceptance before
  any number is quoted; cross-row probes (the abs-visitor-arrivals defect
  pattern: a later row of the same station carries this row's evening
  readings in its feature window — enforce isolated_rows prediction and
  keep the evening readings out of all solver-visible frames); reference
  baselines (always-true/always-false at the ~9-11% base rate, prior-evening
  exceedance persistence, calendar/climatology controls) before model
  comparison.
- Open question, non-blocking: whether the publisher extends the series
  (2025+). The sibling prepaid item IS extended monthly, but this item is
  static since 2026-03 and hasStaticData. v1 holds on the closed window; if
  the publisher extends, later windows can widen the holdout in a v2.
