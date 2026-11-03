# npri-facility-reporting-exit

## 2026-11-03 discovery session (regional focus: Canada) - reconciliation to ready

Recorded the stale status (`investigating` since 2026-10-19 with a `go` verdict) as
`ready` after reconciling all five contracts; probe retained at
`probe/probe_2026_11_03.py`, output at `probe/out/probe_2026_11_03.json`. Bulk
CSVs in `/opt/data/cache/scratch/ca_npri_2026_11_03/` left to the 24h sweep.

### Fresh measurement + dated example (command: `python3 candidates/npri-facility-reporting-exit/probe/probe_2026_11_03.py`)

- 2 GETs, 79,162,819 bytes, ~43 s: 2023 single-year CSV (40,400,423 B, sha256
  0e8c04a9...), 2024 (38,762,396 B, 7648e67f...). Both byte-size-identical to
  the 2026-10-19 ranged measurements -> files stable across the 15-day gap.
- 2023->2024 exit pair (third full-population measurement): 7,986 -> 7,738
  facilities, exits 1,063 (**13.311%**), entrants 815. Recent era now
  12.32% / 10.84% / 13.31%.
- Provincial clustering of exits: AB 588 (55.3%), SK 262 (24.7%), ON 82, BC 80,
  QC 32, MB 11, NS 4, NB 2, YT 1, NL 1 - oil-and-gas provinces dominate.
- POSITIVE example: NPRI ID 10033 "Hagersville Agg" (Lafarge Canada Inc. -
  EAST), Hagersville ON, NAICS 2123, 3 substance rows in 2023, ABSENT from the
  2024 file -> label 1.
- NEGATIVE example: NPRI ID 1 Alberta-Pacific Forest Industries Inc. (County
  of Athabasca AB, NAICS 3221), 102 substance rows in 2023, present in both
  files -> label 0.
- Encoding: both files cp1252; headers are BILINGUAL ("ID INRP / NPRI ID",
  "Nom de l'installation / Facility Name", "Ville / City") - construction must
  match columns bilingually (a naive exact-name lookup returns None).

### Timing evidence (as-of; 2026-11-03)

- Publisher FAQ (canada.ca NPRI reporting-requirements FAQ, read via search):
  "the reporting deadline is 11:59 p.m. Eastern Daylight Time (EDT) on June 1",
  extended to the next business day when June 1 falls on a weekend.
- The 2021-2023 Canada Gazette notice names the adjusted dates: reports due
  "June 1, 2023, June 3, 2024 and June 2, 2025" (2024-06-01 was a Saturday,
  2025-06-01 a Sunday - verified with `date -d`). So the year-2023 instant is
  2024-06-03 23:59 America/Toronto; the year-2024 target deadline
  (2025-06-02) is strictly after it.
- open.canada.ca single-year package was re-created 2026-04-30 (portal dates
  prove nothing about first publication); both files byte-size-stable between
  the 2026-10-19 and 2026-11-03 reads. Current-vintage posture, no
  historical-vintage claim.
- DATED EXAMPLE (America/Toronto): Hagersville Agg (ID 10033) - feature
  window = reporting history through year 2023; instant T = 2024-06-03 23:59
  EDT; target = no 2024 report, due 2025-06-02 23:59 EDT; label revealed with
  the 2024 single-year publication; measured label 1.

### DNMC label nuance (publisher's reporting guide, read via search)

"A facility that submitted a report in the previous year but no longer meets
NPRI reporting criteria for the current year, is required to submit a 'Does
Not Meet Criteria (DNMC) report' by the reporting deadline." Construction must
measure whether DNMC submissions appear in the published year files (e.g.
zero-quantity rows) and state which side of the presence/absence label they
fall on. The mechanical label is unaffected; the limitation must be explicit.

## 2026-10-19 discovery session (regional focus: Canada)


Anonymous probes from the coordinator; probe scripts (`.factory/probe_ca_npri*.py`)
deleted after use; single-year CSVs downloaded to `/opt/data/cache/scratch/ca_npri/`
and deleted after measurement.

### File location (CKAN metadata is stale - measured)

- CKAN package_show 40e01423 (bulk) and 348504f1 (single-year): both OGL-Canada, org `ec`.
  The `data-donnees.ec.gc.ca/data/...` download URLs in CKAN serve a 2,200-byte HTML SPA.
- Measured working path: `https://data-donnees.az.ec.gc.ca/api/file?path=<percent-encoded
  path>` - answers ranged GET with 206 + real bytes. Bulk Releases 1993-present CSV:
  content-range total **393,281,064 bytes**. Single-year CSVs: 2021 36,460,887 B;
  2022 39,154,265 B; 2023 40,400,423 B; 2024 38,762,396 B.
- Bulk list format header (19 cols): Reporting_Year, NPRI_ID, Company_Name,
  Facility_Name, NAICS(+titles), PROVINCE, CAS_Number, Substance Name EN/FR, Group
  (Releases to Air/Water/Land), Category (Stack/Fugitive/Spills/...), Quantity, Units,
  Estimation_Method. Single-year wide format: 77 cols incl. geolocation (lat/lon, CSD,
  CMA, ecozone, watershed), NAICS 4/6, per-media release columns.

### Exit rates and shape (full single-year files, `probe_ca_npri_measure.py`)

| year | rows | facilities (distinct NPRI_ID) | spill facility-years |
|---|---|---|---|
| 2021 | 56,115 | 7,322 | 110 (1.50%) |
| 2022 | 60,202 | 7,521 | 114 (1.51%) |
| 2023 | 62,125 | 7,986 | 149 (1.87%) |

- exit 2021->2022: 902/7,322 absent (**12.32%**), 1,101 entrants
- exit 2022->2023: 815/7,521 absent (**10.84%**), 1,280 entrants
- NPRI_ID is stable across years (facility 1 = Al-Pac in every file read).
- Files decode as cp1252, not UTF-8.

### Units/reference-frame warning (measured)

Quantities arrive in mixed units per row: 2023 file measured `tonnes` 57,570 rows,
`kg` 4,221, `grams` 167, `g TEQ` 167. Any cross-row aggregation or threshold MUST
normalize by the Units column first; construction must pin a cross-check against the
publisher's own provincial/sector summary tables (a known-event fixture for the
qualification gate).

### Cost (measured)

Three single-year CSVs (116 MB total) downloaded + fully parsed with csv module in
183 s single-process on the coordinator (~0.64 MB/s effective). A 1993-2023 bulk build
is a modest worker job (~400 MB releases + other bulk files, estimate).

### Decision

Spill-year alternative measured and dropped (see candidates/npri-facility-spill-year):
1.5-1.9% base rate, too thin for a scored holdout. Reporting-exit is the primary task.
Novelty recorded by scripts/check-novelty.py as differentiated: ECCC's own scoping
review (canada.ca "NPRI use in environmental research", 225 articles) shows NPRI used
as *input* to exposure/air-quality models, not as a prediction target; US TRI
literature is adjacent (PEMS real-time stack emissions, EPA data-standardization work)
but nothing ships a next-year reporting-outcome task with splits on this or an
equivalent source.
