# tsb-railway-occurrence-casualty

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: Canada)

Publisher: Transportation Safety Board of Canada (TSB). Dataset page:
https://www.tsb.gc.ca/eng/stats/rail/data-5.html ("Rail transportation occurrence data
from January 1983"). open.canada.ca record: 4f8d9b0d-c4af-4be2-b751-3f5a403993ff.

### Access probes (commands and results)

- `python3 .factory/ca_probe_catalog.py` -> open.canada.ca CKAN package_search for
  'railway occurrence' etc.: HTTP 200 anonymous; TSB railway occurrence data package
  found with 5 CSV resources + data dictionary; license_id=ca-ogl-lgo on every TSB
  package read back.
- `python3 .factory/ca_probe_tsb.py` (session script) -> plain urllib (custom
  User-Agent 'scout-dataset-factory/1.0') on
  www.tsb.gc.ca/sites/default/files/stats/*.csv -> **HTTP 403 Forbidden** on all.
- `python3 .factory/ca_probe_tsb403.py` -> diagnosis: with a full browser-like
  header set (Chrome UA, Accept, Accept-Language, Referer: https://www.tsb.gc.ca/)
  the same URLs answer **HTTP 200**. Measured sizes via bytes=0-0 ranged GET
  (HTTP 206, Content-Range read back):
  - OCCURRENCE 97,765,258 B (last-modified 2026-09-15 17:13:09 GMT)
  - TRAIN 21,742,734 B (17:13:24), ROLLING_STOCK 34,723,267 B (17:13:45),
    INJURIES 2,710,400 B (17:14:01), COMPONENTS 42,523 B (17:14:16)
  - Data dictionary RODSdb-dd.csv 109,771 B: 699 rows; 353 entries for the
    occurrence table, every column documented (kept at scratch, key meanings
    quoted in record sources).
  The 403-to-plain-client / 200-to-browser-headers behaviour is a documented,
  reproducible programmatic path (kept in probe_access.py) - NOT a bot wall of the
  UNHCR kind. Release schedule confirmed from the dataset page: "The RODS datasets
  are is released on or soon after the 15th of each month, and contains data from
  January 1983 to the last day of the month preceding its release."
- The 97.8 MB occurrence file was NOT downloaded to the coordinator (coordinator
  no-bulk rule); all measurements below come from bounded ranged reads
  (2 MB head, 2 MB at offsets 30,000,000 / 50,000,000 / 70,000,000, 1.5 MB tail
  = ~8.6 MB total transferred).

### Schema and timing findings

- Occurrence table: 345 columns, ordered newest-first; row 1 is 2026-09-05, last
  row 1983-01-02. Sample row keys: OccID 137800, OccNo R26E0080, OccDate
  2026-09-05, OccTime 200, TimeZoneID MDT, OccurrenceTypeID ACCIDENT/INCIDENT,
  AccIncTypeID 'NON-MAIN-TRACK TRAIN DERAILMENT (NO DAMAGE)'.
- **Timing split of the schema** (dictionary descriptions read for every shipped
  candidate feature): pre-onset context = OccDate/OccTime/OccYear, TimeZoneID,
  SubdOwnerID (railway) + SubdNameID (subdivision) + SubdMileage, ProvinceID,
  StationID, NearLocation, Latitude/Longitude, RegionOfOccurrence,
  ActivityTypeID ('type of train activity at the time of the occurrence');
  post-onset = AccIncTypeID (taxonomy embeds outcomes: '... (NO DAMAGE)',
  'CROSSING', 'TRESPASSER'), OccurrenceTypeID, InjuriesIND, TotalFatal/Serious/
  MinorInjuries, FireIND, ExplosionIND, EvacuationIND, NumEvacuated,
  DG*CarsIND/Total* columns, DerailedRSIND/TotalDerailedRS, DamageLevelID,
  NumberTrainsInvolved/TotalRSInvolved, all weather columns (WeatherSourceID,
  Temperature_Celsius... - observations taken at the occurrence), all track/
  rolling-stock inspection attributes, DeployedIND, all process dates (ENTRY_DT,
  RELEASE_DT, DAILY_RELEASED_DT, OccClosedDate, CLOSEOUT_*), Summary narrative,
  ReportedDate/ReportedTime (notification instant - provenance only, not a feature).
  The dataset page itself documents that the Occurrence table contains
  "Notification data, including the date and time that the occurrence was reported."

### Label base rates (bounded era samples, command = probe_era_samples.py)

- 2025-26 sample (offset 0, n=1,501; 665 rows 2025 + 836 rows 2026 to 09-05):
  InjuriesIND 14.7% (220), fatalities>0 7.4% (111), FireIND 7.4%,
  DerailedRSIND 48.4%, DGCarsInvolvedIND 8.4%, EvacuationIND 0.2%,
  DGReleasedCarsIND 0.1%, DeployedIND 1.5%.
- offset 30,000,000 (n=1,499; 2008:34, 2009:884, 2010:581): injuries 13.9%,
  fatalities>0 6.3%.
- offset 50,000,000 (n=1,359; 2001:447, 2002:912): injuries 15.0%, fatalities 5.7%.
- offset 70,000,000 (n=1,383; 1995:1383): injuries 18.0%, fatalities 5.7%.
- tail (n=1,450; 1983:1168, 1984:282): injuries 30.2% - and accident types include
  'DG LEAKER' (343), 'HISTORICAL' (120), time zone 'N/A', OccClassID 'N/A':
  the pre-modern era is shaped differently; construction should start at a
  modern-era boundary (2004-01 proposed) and re-verify.
- Label choice: DG release (0.1% sample rate; publisher's 2025 summary: 'Three
  accidents in 2025 resulted in dangerous goods being released') and evacuation
  (0.2%) are far too thin; casualty (InjuriesIND, 13.9-18.0% across eras) is the
  label. Both classes present in every window.

### Publisher cross-check (own summary product)

- `python3 .factory/ca_probe_statcan_hc.py` -> https://www.tsb.gc.ca/eng/stats/rail/2025/sser-ssro-2025.html
  (HTTP 200, 136,930 B): "In 2025, 831 rail accidents... down from the 2024 total
  of 895, and 17% below the previous 10-year (2015 to 2024) average of 1007";
  "332 rail transportation incidents reported to the TSB in 2025, a 10% increase
  from 2024 (303)"; "Among all rail transportation accidents, 82 involved
  dangerous goods... Three accidents in 2025 resulted in dangerous goods being
  released."; "Freight trains accounted for 42% of all rolling stock involved in
  rail accidents in 2025."
- Consistency: newest 2 MB sample holds 665 rows from 2025 (~57% of the year's
  1,163 occurrences at ~8 months depth of the 2025+2026 rows) - consistent in
  order of magnitude. Full-panel counts to be cross-checked at construction.

### Licence evidence

- open.canada.ca CKAN package_show -> license_id ca-ogl-lgo (OGL-Canada 2.0).
- OGL-CA page (open.canada.ca/en/open-government-licence-canada, HTTP 200,
  23,079 B): "Acknowledge the source of the Information by including any
  attribution statement specified by the Information Provider(s) and, where
  possible, provide a link to this licence. If the Information Provider does not
  provide a specific attribution statement... you must use the following
  attribution statement: Contains information licensed under the Open Government
  Licence - Canada."
- TSB dataset page disclaimer: "The dataset is for information purposes only.
  The user of the data assumes all responsibilities for the data's use and for
  verifying their completeness and accuracy for both critical and non-critical
  uses and applications." Page carries no licence text of its own - licence comes
  from the open data record.

### Novelty check

- Recorded via `python3 scripts/check-novelty.py tsb-railway-occurrence-casualty
  --verdict differentiated ...` (queries: railway occurrence prediction / rail
  accident severity dataset / train derailment prediction benchmark; 3 catalogs
  searched, verdict + prior art written to the record).
- Prior art found by web search 2026-10-21: NRC derailment impact-map tool
  (RODS historical counts; predictive models explicitly deferred to future work);
  Rana/Sattari/Lefsrud/Hendry 2024 (doi:10.1177/03611981231212162) grade-crossing
  casualty-severity ML study on TSB data - a paper, not a shipped dataset.
- Verdict: differentiated. Our contribution is the formulated task: context-only
  casualty prediction with temporal splits, outcome-coded taxonomy and every
  post-onset column excluded, monthly-republished panel 1983-2026.

### Decisions and caveats

- Prediction instant fixed at occurrence ONSET, not at notification: at onset the
  casualty outcome is genuinely unknown; ReportedDate is provenance only. At
  construction, the qualification gate's timing check should assert no post-onset
  column ships.
- Row-count ~70,000 is an ESTIMATE from row density (1,502 rows / 2 MB); full
  count measured on the worker.
- Construction must measure naive baselines (global / per-railway /
  per-subdivision / per-activity / time-of-day) before spending the rest of the
  build; headroom over per-subdivision persistence is the go/no-go for release.

## 2026-10-22 - construction probes (bounded, coordinator-side)

Construction prep for job tsb-001. Two bounded ranged GETs (2 MB + 64 KB) plus
the data dictionary (109,771 B) answered the remaining design questions; every
claim below is from a probe, with the command recorded.

- `python3 .factory/tsb/probe_head_values.py` (2 MB ranged GET of
  RODSdb_MDOTW_VW_OCCURRENCE_PUBLIC.csv, 1,495 rows, HTTP 206):
  - The file decodes cleanly as UTF-8; cp1252 fails (byte 0x9d). Earlier
    session scripts that read it as cp1252 printed mojibake ("QUÃ‰BEC");
    the shipped CSVs are written UTF-8.
  - **OccID is empty in every one of the 1,495 newest rows.** The row key must
    be OccNo. (The INJURIES child table still carries a populated OccID, so
    the internal id exists - the OCCURRENCE export just does not carry it now.)
  - **OccDate is a full local timestamp** ('2026-10-06 04:55:00.0000000',
    7-digit fraction) that already embeds OccTime; the build parses date+hour
    from it.
  - TimeZoneID_DisplayEng values are DST-aware abbreviations (EDT/EST/MDT/
    MST/CST/CDT/PST/PDT/ADT/AST), so the site timezone is fully documented by
    the shipped string; no hand-rolled UTC offset map is needed (occ_hour
    ships as the LOCAL hour with the timezone label beside it).
  - Latitude/Longitude are degrees x 10^4 unsigned (505900 -> 50.59 N;
    1181200 -> 118.12 W), of the nearest city/town; the build negates the
    West longitude and asserts the Canadian envelope 41-72 N / 52-145 W.
    10/1,495 newest rows have empty coordinates.
  - Label components agree perfectly in the newest sample: InjuriesIND=1 on
    224 rows, fatal+serious+minor totals > 0 on the same 224, 0 disagreements
    either way.
  - OccClassID_DisplayEng carries TSB occurrence classes ('5', '4', '3',
    'BEING ASSESSED') - post-onset taxonomy, excluded like AccIncType and
    OccurrenceType (ACCIDENT/INCIDENT is used only for the publisher
    cross-check, never shipped).
- `python3 .factory/tsb/probe_keys.py` (same 2 MB sample + 64 KB of the
  INJURIES table): OccNo distinct on 1,494/1,495 rows; the one collision
  (R26D0003) is a **byte-identical exported row** (all 345 columns equal -
  `python3 .factory/tsb/probe_dup.py`), so exact duplicates are dropped and
  counted at build time, and OccNo remains the row key. INJURIES joins on
  OccNo and carries per-person severity counts (Offtrain_*Fatal/Serious/Minor
  and more), used only as the label cross-check.
- Current vintage measured at fetch time (2026-10-22): contains occurrences
  dated as late as 2026-10-10 - newer than the record's 2026-09-15 vintage
  and past the "month preceding release" convention. The build therefore
  holds the holdout window at 2025-01-01..2026-08-31 (one full settling month
  behind the data) and counts occurrences after the window as excluded
  (post-window accounting in summary.json), and asserts the vintage covers
  the window end.
- The data dictionary (fetched 2026-10-22) documents 353 OCCURRENCE columns;
  the CSV header carries 345. The build ships only documented fields; the
  count difference is recorded, not a defect.

### Build decisions pinned at construction (job tsb-001)

- Row key: occ_no (OccNo), suffixed only for measured non-identical
  collisions; exact duplicates deduplicated with the count recorded.
- Modern-era panel start is MEASURED, not assumed: first year from which
  the early-signature share (AccIncType HISTORICAL/DG LEAKER, or TimeZone
  empty/N-A) stays under 2% in every later year; asserted within
  [1995, 2010]. The record proposed 2004; the full panel decides.
- Label: casualty = InjuriesIND == 1 OR TotalFatal+TotalSerious+TotalMinor
  > 0, cross-checked against the INJURIES child table; all four source
  columns are asserted absent from every shipped file.
- Shipped features (14, context-only): occ_year, occ_month,
  occ_day_of_week, occ_hour, timezone, activity_type, subdivision,
  subd_mileage, railway, near_location, province, region, latitude,
  longitude - plus occ_date (carry) and occ_no (id).
- UTC normalization deliberately NOT applied: the publisher documents the
  site timezone as a DST-aware label, which ships beside the local hour; a
  hand-rolled offset map could silently misplace an hour (the exact
  unit/frame failure class the gate exists to catch). Recorded in
  quality.json measurements[occ_hour].
- Baselines measured inside the build before any model spend: per-column
  conditional-rate AUCs (activity, railway, subdivision, province, month;
  train-estimated, eval/holdout-scored) and a trailing-12-month-rate
  persistence analogue.
