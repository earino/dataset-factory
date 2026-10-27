# ns-bwa-advisory-lift-duration — discovery notes (2026-10-27, Canada tick)

Lead origin: the regional sweep for the Canada tick (open.canada.ca CKAN, "boil water
advisory" queries) surfaced the provincial municipal-water channel that the dropped
`isc-ltdwa-advisory-lift-timing` record named as its reopening condition. Per that
record's instruction ("If a per-advisory machine-readable advisory register WITH lift
dates appears (provincial municipal-water channel...), open a new candidate for the
duration-to-resolution task and cite this record for the formulation"), this candidate
was opened. It is a NEW candidate, not a reopening of the ISC record: the population
(NS public registered and municipal supplies, not First Nations systems) and publisher
differ.

## Commands and results (all anonymous, run 2026-10-27 from the hosted coordinator)

Probe scripts are retained in this directory; JSON outputs of the aggregate probes
are retained beside them. `python3 -m factory candidate create ns-bwa-advisory-lift-duration`
created the record; all field values in `record.json` trace to the commands below.

1. `probe_bwa_portal.py` — open.canada.ca CKAN `package_search`/`package_show`
   (package cc06d839-c26a-19f1-2428-4b5464670f8a): org ns-ne, licence ns-oglns,
   resources CSV/TSV/RDF/RSS/XML from data.novascotia.ca. Notes document per-advisory
   grain: "Site Name, County, Date Boil Advisory Issued, Date Boil Advisory Removed,
   Facility Type (Registered or Municipal), Length of Advisory in Days, Reason for
   the Report... from 2006 - current."
2. `probe_ns_aggregates.py` — Socrata SoQL against
   `https://data.novascotia.ca/resource/7t68-9xmm.json`:
   - total count: 2,649
   - by issue year: 2008:3 ... 2024:220, 2025:208, 2026:71 (+30 unparseable)
   - resolved (lift date present): 2,576; active/censored: 73
   - distinct site names: 1,116
   - reasons mix (variants incl. "E. Coli Present" 83 / "E.Coli Present" 52)
   - facility types: Registered 2,491 / Municipal 101 / missing 57
   - per-window labeled counts + lift14/lift30 base rates (train 2008-2017:
     1,069 labeled, lift14 45.09%, lift30 66.88%; eval 2018-2020: 372, 39.52%,
     60.48%; holdout 2021-2024: 886, 39.95%, 58.24%)
   - distinct sites per window: 586 / 286 / 551
   - censored by issue year (mostly 2024-2026: 5/11/19)
   - duration by issue year: mean 47-65 d for 2009-2018, 218 d in 2020, 143 d in
     2021, 101 d in 2022, 64 d in 2023 — a measured regime shift straddled by the
     holdout window.
3. `probe_ns_csv_verify.py` — full-file cross-check: one GET of
   `https://data.novascotia.ca/api/views/7t68-9xmm/rows.csv?accessType=DOWNLOAD`
   (283,987 bytes; sha256 60f77ac4945ca824700f5bcd3eaf564f4e5c5d4ec3f08496e8dd796e7184a30a;
   CSV Last-Modified header "Tue, 16 Jun 2026 13:58:42 GMT"). Local parse of all
   2,649 rows reproduced every SoQL number exactly (row count, per-window labeled
   and censored counts, base rates, distinct sites). CSV dates are month-name text
   ("October 02 2025"), not ISO. Duration range -52 .. 1,668 days. 3 negative-duration
   rows, 5 zero-duration rows, 30 rows without a parseable issue date, 57 missing
   facility type, 5 missing reason.
4. Licences and dataset page read via the extraction backend (novascotia.ca direct
   fetches time out from this coordinator; recorded as coordinator-side network
   behaviour, and the licence text was read, not assumed):
   - `https://novascotia.ca/opendata/licence.asp` — OGL-NS v1.1, class A, required
     attribution statement quoted in record.json license_evidence.
   - `https://data.novascotia.ca/datasets/7t68-9xmm` — publisher metadata: 2,649
     rows / 7 columns (matches the fetched CSV exactly), Quarterly frequency,
     coverage 2006-01-01 to present, Department "Environment and Climate Change",
     Usage Considerations quote (blanks = not available; values not provided for
     advisories currently in effect), changelog full refresh 2026-06-16
     ("Inserted 2649 rows, Deleted 0").
5. Sibling channels (measured negatives, same tick):
   - NL "Boil Water Advisories" (opendata.gov.nl.ca filedownload/?file-id=17146,
     nl-oglnl, 53,342 bytes; bounded 6 KiB range read of header+rows): has
     BOIL_ADVISORY_ISSUE_DATE + rich system features (SUPPLY_TYPE, SOURCE_TYPE,
     NUM_OF_WELLS, CHLORINATION, POPULATION_SERVICED, REGION_*), NO lift/rescinded
     date column. Cannot support the duration task.
   - Manitoba "Current BWAPWS" (mb-omb): current advisories only (no lift dates).
   - Quebec (qc-cc-by): City of Repentigny only.
   - ECCC/CESI "Boil water advisories" (ca-ogl-lgo): aggregate indicator CSVs only
     (causes, community-size percentages) — the ECCC feed named by the ISC record
     has NOT gained event grain.

## Dated example (America/Halifax)

- Prediction instant: 2024-08-31 (calendar day; register stores dates without times).
- Subject row (verified in the pinned CSV): Maple Meadows Campground Inc,
  INVERNESS COUNTY, Registered, "Total Coliform Present", issued August 31 2024.
- Feature event window: register rows with issue date < 2024-08-31 only (the same
  site had an earlier 2023 advisory of 258 days — a legitimate as-of feature row).
- First-available version of all fields: the single pinned vintage (content current
  as of 2026-06-16; fetched 2026-10-27; sha256 above).
- Eligibility cutoff: issue date <= 2026-05-17 (vintage minus 30 days).
- Target window: the 30 days following 2024-08-31 (through 2024-09-30); no part of
  it precedes the instant.
- Observed outcome: Date Advisory Removed July 04 2025 → 307 days → lift30 NEGATIVE.
- Positive-class fixture: Canning, NS (Municipal, Total Coliform Present), issued
  October 02 2025, removed October 03 2025, 1 day → lift30 POSITIVE.

## Duplicates and hazards (verified in-file, for construction to handle)

- PID 50323732 has TWO rows with issue October 13 2023 and different removals
  (May 28 2024 / 228 d with blank county; August 22 2023 / -52 d with county
  Inverness) — a duplicate-row + negative-duration hazard in one site identity.
- Negative durations: McIntyre's H. Cottages (Baddeck) -1 (2021); PID 50323732 -52
  (2023); Naugler's Ultramar - Italy Cross -7 (2025). Naugler's also shows repeat
  advisories across 2022-2025 (site-repeat example).
- Reason label variants must be normalised ("E. Coli Present" vs "E.Coli Present").

## Novelty searches (2026-10-27)

- "boil water advisory duration prediction machine learning lift rescind" —
  operational FAQ pages only (several US agencies: duration "impossible to
  predict").
- "\"boil water\" advisory duration days statistical model predict study water
  system" — descriptive/epidemiological prior art only: PLOS Water 2024 (Texas
  Winter Storm Uri geospatial correlates of duration), J Water Health 19(5) 2021
  (Norway descriptive series; median 6 d, n=522 lift-dated), MDPI Water 2025 (West
  Virginia; duration as an explanatory variable for utility costs), one referenced
  decision-tree study predicting advisory ISSUANCE (not duration). No predictive
  benchmark, no ML-ready dataset, no scored contract. Verdict: no_precedent
  (recorded via scripts/check-novelty.py).

## Decisions

- Verdict: ready (go) — all five contracts have recorded evidence; licence class A
  with the OGL-NS attribution statement to be carried into LICENSE.md at release.
- Advancement owns construction per record.construction_handoff. No rows were
  constructed, qualified or scored in this session.
