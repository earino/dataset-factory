# npri-facility-reporting-exit

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
