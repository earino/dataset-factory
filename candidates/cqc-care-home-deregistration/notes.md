# cqc-care-home-deregistration

**UK discovery tick 2026-11-03. Publisher: Care Quality Commission (CQC), England.**
Task: at the production instant of a monthly CQC "HSCA Active Locations" vintage T,
for every care home active at T, predict whether that location's registration ends
(`Location Status` becomes Inactive-Dereg with a `Location HSCA End Date`) within the
following 12 months.

Prospective user / decision: local-authority commissioners and CQC market-oversight
analysts watching care-home market fragility; a useful 12-month early warning supports
capacity planning for displaced residents before a deregistration lands (DHSC/CQC
publish closure-impact guidance; the 2024 BMJ Public Health closure study is the
policy reference). Prediction instant = vintage production date (file name + in-file
"This data was produced on" stamp); features = vintage-visible registration,
service-type, bed, rating and provider columns only; label = register event from the
Deactivated Locations product.

## Licence (class A, publisher's own instruments, quoted 2026-11-03)

- https://www.cqc.org.uk/about-us/transparency/using-cqc-data : "Our data is made
  available under the Open Government Licence [v3]. By using it you are accepting the
  conditions of this licence. If you use our data, you should also acknowledge on your
  site or service that you are using CQC information."
- In-sheet statement inside the Deactivated Locations ODS itself: "the data we have
  provided can be used in accordance with the Open Government Licence for Public
  Sector Information by acknowledging CQC as the data source" (+ disclaimer that CQC
  is not responsible for subsequent analysis and must not be quoted as its source).
- https://www.cqc.org.uk/about-us/our-policies/terms-conditions : CQC copyright
  material "may be used in accordance with the Open Government Licence for Public
  Sector Information".
- No dataset-specific restriction found on any product page; no third-party content
  inside the bulk files (register data only). Attribution carries to any release.

## Sources

1. CQC care directory with filters ("HSCA Active Locations", monthly ODS/XLSX, all
   active locations with care-home beds, service types, service user bands, latest
   rating + publication date, provider attributes incl. Companies House number).
   Current: https://www.cqc.org.uk/system/files/2026-11/02_November_2026_HSCA_Active_Locations.ods
   Archive (Google Drive, year folders 2011-2026, monthly files, anonymous listing via
   embeddedfolderview): drive folder 1Y6V6r-q2l4lJYKuZL0DXw25VDUTH6L4N.
2. CQC Deactivated Locations (monthly ODS, cumulative list of archived locations with
   `Location Status`, `Location HSCA start date`, `Location HSCA End Date`, beds at
   deactivation, latest rating + publication date, provider attributes).
   https://www.cqc.org.uk/system/files/2026-11/02_November_2026_Deactivated_Locations.ods
3. CQC care directory with ratings (monthly ODS, service-level latest ratings; archive
   from 2015; pre-Sep-2023 archive files have missing core-service ratings per the
   publisher) - optional deeper rating history for construction.
4. Weekly locations CSV (no beds/ratings): 28_October_2026_CQC_directory.csv - used
   for the current service-type census only.

## Probes (anonymous, coordinator, 2026-11-03; scripts + outputs in probe/)

| Command | Result |
|---|---|
| `python3 probe/cqc_drive_probe.py` | Drive archive folders anonymous-listable; filters archive = year subfolders 2011-2026; ratings archive 2015-2026; weekly-CSV archive 2012-2026 (old-style folder needs resourcekey; plain listing 401s - recorded, workaround works) |
| `python3 probe/cqc_drive_ls.py <year-folder-id>` | Monthly files per year, e.g. 2019 = 12 files `01 <Month> 2019 HSCA Active Locations.xlsx`; 2024 = 12 ODS; 2026 = 10 ODS to date |
| `python3 probe/cqc_fetch.py` | dir CSV zip 4,401,747 B sha256 81bee6ae...; Deactivated ODS 27,644,723 B sha256 49dc3062... (both from cqc.org.uk) |
| `python3 probe/cqc_fetch_vintage.py` | 05 January 2024 vintage ODS 26,147,266 B sha256 ac40b6f8... (Drive, anonymous `drive.usercontent.google.com/download?id=<fid>&export=download&confirm=t`); current filters ODS 27,677,454 B sha256 94be8a00... |
| `python3 probe/cqc_csv_agg.py` | weekly CSV (produced 28 Oct 2026): 57,123 active locations; Residential homes 10,380 + Nursing homes 4,497 = care-home locations today; all 9 English regions present |
| `python3 probe/cqc_deactivated_agg.py` | Deactivated file (2026-11-02): 65,830 data rows, of which 17,177 `Care home?` = Y; status mix care homes: 17,046 Inactive-Dereg + 131 Removed; HSCA end dates 2010-08-05 .. 2026-10-30 (cumulative history, one file = whole event history); care-home deregistrations by year 2011..2026 = 1656, 1649, 1063, 1227, 1245, 1381, 1352, 970, 949, 822, 967, 803, 827, 768, 801, 697(partial); beds at deactivation small-home-dominated (3-10 top bins); rating at deactivation: Good 5,992 / blank 7,698 / RI 2,318 / Inadequate 1,027 / Outstanding 138 (Inadequate 6.0% of deactivations vs ~2-4% of active stock - signal, see CQC State of Care closure analyses) |
| `python3 probe/cqc_vintage_probe.py` | Jan-2024 vintage header (118 real columns): Location ID, Location HSCA start date, Care home?, Care homes beds, Registered manager, Location Latest Overall Rating, Publication Date, Inherited Rating, geography, Provider Companies House Number / Charity Number / ID / Type-Sector, 32 `Service type - *` Y/N columns incl. 'Care home service with nursing'/'without nursing', 12 `Service user band - *` Y/N columns incl. Dementia/Older People/Learning disabilities. No Location Status column (all rows active by construction). |
| `python3 probe/cqc_example.py` | Join vintage(T=2024-01-05) x deactivated: **14,765 care homes at T; 758 deregister in (T, T+365d] = 5.13% prevalence; 2,076 of the 14,765 deregister by 2026-11-02; 0 rows carry a rating Publication Date after T (as-of holds on the full vintage)**; named rows below |

Extraction cost measured: 4 anonymous GETs for this discovery = 85.9 MB total
(4.4+27.6+26.1+27.7 MB), seconds each from cqc.org.uk / Drive. Construction plan
(January instants, non-overlapping 12-month windows) needs ~10-15 vintage files
(~26 MB each, ~390 MB) + 1 deactivated file: a bounded worker download; vintage
parse measured ~60 s/file on 4 vCPU once page cache is warm (a cold first parse of
the same file ran ~13x slower under I/O contention - worker-sizing note, not a
blocker). Drive per-file IDs must be enumerated via the year-folder listings
(script retained).

## Dated worked example (Europe/London, all values from the named files)

POS: **Park Hills Nursing Home** (Location ID 1-113831768, Oldham, 17 beds, HSCA
start 01/02/2011, latest overall rating Good published 26/08/2022). Feature event
window: registration 01/02/2011, rating publication 26/08/2022 - both strictly
before T. Eligibility: present as `Care home?` = Y in the 05 January 2024 vintage.
Prediction instant T = 2024-01-05 (the vintage's production date, from the file
name; the weekly sibling file states "This data was produced on 28 October 2026",
the same stamping convention). Target window (T, T+365d] = 2024-01-06..2025-01-05.
Label = 1: Location HSCA End Date 01/02/2024 inside the window, status
Inactive-Dereg, read from the Deactivated Locations file (2026-11-02 edition).
Same window, NEG: Henley House (1-10000302982, Suffolk, 66 beds, start 11/12/2020,
Good 20/04/2022) - present at T, absent from the deactivated file as of 2026-11-02
=> label 0. NEG(late, label 0 at T): Options Hazel House (Lincolnshire, 4 beds),
end date 05/03/2025 outside the window. No part of the target window precedes T;
the label event is a register event dated after T by construction.

## Cross-checks against publisher/third-party summaries

- CQC/DHSC "Review into the operational effectiveness of the CQC" (gov.uk, June
  2024 snapshot): 29,108 social care organisation locations; my 28-Oct-2026 CSV:
  57,123 total locations of which residential+nursing homes 15,477 - consistent
  magnitude and mix.
- BMJ Public Health 2024 (Bach-Mortensen et al.): 29,548 care homes existed
  2011-2023 with 8,346 COMPLETE closures; my register events 2011-2023 = 14,911 -
  the gap is their linkage-filtered subset vs raw deregistrations (see framing
  risk below), consistent with their methodology note.
- CQC State of Care 2016 (closures by size): small homes dominate closures; my
  beds-at-deactivation distribution is small-home-dominated.

## Framing risk (recorded, not resolved away)

The register event conflates cessation with re-registration: CQC's own file note
says "In some cases, when a location deactivates, the service continues but under a
new registration due to a legal entity change, address change, or a change in the
provider". BMJ 2024 (8,346 complete closures vs my 14,911 deregistrations 2011-2023)
implies roughly 40-55% of deregistrations are re-registrations/transfer rather than
service cessation. The task must therefore be framed as **12-month deregistration of
the CQC location** (a well-defined, predictable register event - the incumbent legal
entity loses its registration for those beds), with the limitation stated, OR
construction must build successor linkage (same address/UPRN/ODS-code/brand +
adjacent dates; the API carries linked-organisation data but needs developer-portal
auth). A dated decision for advancement; it changes the base rate, not the
constructibility.

## Other recorded risks / open items

- CQC system-migration caveat (publisher, on the data page and inside the files):
  "some updates are currently taking longer than usual to be reflected ... For
  example, the cancellation of provider registrations" - recent-vintage label lag;
  construction should keep the last instant whose 12-month window is fully inside
  the deactivated file's coverage and record a lag check.
- Rating regime change: from the new single-assessment approach (~2024), ASC
  multi-service locations no longer carry a location-level overall rating ("Not
  Rated" in the filters file; service-level ratings live in the ratings file) - an
  era break for rating features; construction must handle it (ratings archive from
  2015 exists).
- "From 1 April 2019" regulatory-history recording change (in-file note): ratings
  inherit across ownership/address changes for applications completed after that
  date - affects `Inherited Rating` features; era note for construction.
- Cross-row exposure: provider-group history features (e.g. sister-location
  deregistrations in the trailing 12 months) read OTHER rows' outcomes - the
  za-statsa/acnc shape; strictly-prior-events-only construction + declared
  restricted protocol (the gate's cross-row audit) if any such feature ships.
- No dormancy flag in the Active Locations file: dormant-but-registered locations
  may sit in the at-T population (CQC publishes no dormant bulk product); recorded
  as a coverage nuance, not measured this session.
- Weekly CSV archive folder needs a resourcekey for anonymous listing (old-style
  Drive folder); workaround recorded in probe script.

## Prior art and what is ours

Named prior art: BMJ Public Health 2024 logistic-regression closure study (they
built their own 2011-2023 dataset from the CQC API; no published ML-ready artifact);
Lancet Healthy Longevity involuntary-closures paper + BenGoodair/Involuntary_care_
home_closures GitHub (Stata/R replication package for the 816 CQC-enforced closure
subset - research data, not a benchmark); NIHR multilevel-logit programme
(25,459 homes 2010-2021); JLTC home-care-agency closure regression; npj Health
Systems US nursing-home-closure ML (16,675 US facilities, AUPRC 0.50 - different
country, regulator and data). Catalogue sweep additions (recorded by
check-novelty.py): Zenodo `cqcpack` (LSE CPEC, doi 10.5281/zenodo.19005825) is an
R data package redistributing CURRENT CQC API snapshots whose own limitation note
states historical/longitudinal data is not accessible from it (its JSON archive
starts 26.10.2026) - an access tool, not a benchmark and not a historical archive;
HF datasets 0 relevant hits; arXiv 0 relevant hits. No scored, temporally-split,
ML-ready benchmark on CQC bulk data found in catalogue or literature searches.
Ours: the vintage-anchored prediction-instant contract (CQC's own 2011-2026 monthly
Drive archive - the asset cqcpack explicitly lacks), temporal splits, reference
triad, gate-qualified artifact - none of which the prior art ships; nobody
redistributes an ML-ready panel (the prior art used the API and bespoke linkage).
