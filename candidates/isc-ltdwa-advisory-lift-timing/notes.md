# isc-ltdwa-advisory-lift-timing

Record dated evidence, decisions, and failed approaches here.

## Row-level probes (2026-10-22)

All probes run on the hosted coordinator, anonymous, scratch files under /opt/data/cache/scratch.
Sizes are curl's own %{size_download}.

### 1. Licence triage (first, per standing order)

CKAN search for the LTDWA series on the federal portal (the ECCC CESI indicator republishes
the same ISC series, so its licence statement covers the content family):

    curl -s -o isc_dwa.json -w "isc_dwa %{http_code} %{size_download}\n" \
      "https://open.canada.ca/data/en/api/3/action/package_search?q=drinking+water+advisories&rows=20"
    -> isc_dwa 200 137619

Parsed:
- "Long-term drinking water advisories affecting First Nations water systems – Progress on
  the..." | org=Environment and Climate Change Canada | license_title "Open Government Licence -
  Canada" (CSV under canada.ca/content/dam/eccc/documents/csv/cesindicators/number-lt-dwa-first-nations/).
- Also surfaced: StatCan tables 34-10-0204..209 "Public owners of potable water assets by
  drinking water advisories issued..." (OGL-Canada, CSV zips) - aggregate counts, the parked
  direction-forecast family.

licence_class A: OGL-Canada 2.0 permits redistribution and derivatives with attribution +
no-endorsement conditions, to be restated in LICENSE.md if ever built. Licence was not the blocker.

### 2. The machine-readable advisory export (the "Download map data" file)

Map page:
    curl -s -L -o isc_map.html -w "isc_map %{http_code} %{size_download}\n" \
      "https://www.isc-sac.gc.ca/eng/1620925418298/1620925434679"
    -> isc_map 200 118470

The page's "Download map data" link is client-side only:
    grep -o "[Dd]ownload.{0,120}" isc_map.html
    -> <a href="#" id="linkDownloadData">Download map data </a>
    -> App.ExportCSV("water_advisory_map_data_<date>.csv", App.ListLTDWAs)

The list is fetched by AJAX from App.Config.LinkAjaxSource:
    grep -o "LinkAjaxSource[^,]*" isc_map.html
    -> "LinkAjaxSource": "/DAM/DAM-ISC-SAC/DAM-WTR/STAGING/texte-text/lTDWA_map_data_1572010201618_eng.txt"

Data export:
    curl -s -L -o isc_ltdwa.txt -w "isc_dam %{http_code} %{size_download}\n" \
      "https://www.isc-sac.gc.ca/DAM/DAM-ISC-SAC/DAM-WTR/STAGING/texte-text/lTDWA_map_data_1572010201618_eng.txt"
    -> isc_dam 200 2715200   (GenerateDate inside: 2026-10-20)

First record (verbatim excerpt): {"data":[{"ID":"1","CommunityNum":"001",
"CommunityName":"Abegweit",..., "LTDWACurrent":[],"LTDWALifted":[{"AdvisoryID":"1711",
"Region":"ATLANTIC","WaterSystemName":"Morell Public Water System ","AdvisoryType":"Boil water
advisory","DateSet":"2009-04-29","DateLTDWASet":"2010-04-29","DateExpected":"2015-11-17",...}]}...

### 3. Measured shape (script since deleted)

- communities: 755; lifted advisories: 158; current advisories: 39 => 197 events total.
- lifted advisory fields (verbatim keys): AdvisoryID, AdvisoryType, CategoryID, CommunityName,
  CommunityNum, CorrectiveMeasure, DateExpected, DateLTDWASet, DateSet, Lattitude, LattitudeSTR,
  LongPhase, LongPhaseCode, Longitude, LongitudeSTR, PopulatioEstimated, RecommendedEPHO,
  RecommendedEPHODate, RecommendedEPHOIND, Region, RegionAcronym, WaterSystemName.
  NO DateLifted / end-date field. Same field set on current advisories.
- The export's own display labels DO include the column:
    grep -o "\"Key\":\"[^\"]*[Ll]ift[^\"]*\"" isc_ltdwa.txt | sort | uniq -c
    -> "Key":"AdvisoryLiftedDate"  (value "Date Advisory Lifted")
  i.e. the table intends a lift-date column the published data does not carry.
- DateSet year mix over all 197 events: 1995:1, 1997:7, 1999:5, 2001:5, 2002:3, 2003:4, 2004:14,
  2005:6, 2006:6, 2007:2, 2008:15, 2009:5, 2010:1, 2011:7, 2012:5, 2013:8, 2014:9, 2015:11,
  2016:13, 2017:10, 2018:6, 2019:13, 2020:7, 2021:6, 2022:3, 2023:6, 2024:11, 2025:8.
- AdvisoryType: Boil water advisory 182, Do not consume advisory 15.
- Region: ON 110, SK 30, MB 22, BC 20, ATL 8, AB 4, QC 3.

### 4. Where lift dates actually live (label-source check)

Per-advisory lift dates exist only in narrative HTML (located by web search 2026-10-22):
- "Long-term drinking water advisories on water systems not financially supported by ISC"
  (isc.gc.ca/eng/1516134315897/1533663683531) - per-advisory tables with "Date set (YYYY/MM/DD)"
  and "Date revoked (YYYY/MM/DD)" (non-ISC-funded systems only).
- "Ending long-term drinking water advisories" (sac-isc.gc.ca/eng/1506514143353/1533317130660) -
  "Recently lifted" narrative entries ("Slate Falls Nation as of September 4, 2026", ...).
- Site narrative totals as of 2026-09-10: "158 long-term drinking water advisories lifted since
  November 2015", "38 active-long-term advisories affect 5,457 homes and 334 community buildings"
  (sac-isc.gc.ca/eng/1614387410146/1614387435325, fetched: HTTP 200, 60,753 bytes).

### 5. Split capacity arithmetic

- Positive events since the Nov 2015 baseline: 158 lifts (~14/year over 11 years).
- Clustered by one program's capital-project pipeline and by region (ON = 56% of events).
- Right-censored active: 39 in the export (38 per the site narrative of 2026-09-10).
- Bench anchor: candidates/npri-facility-spill-year was DROPPED on measured split capacity with
  110-149 positives PER YEAR; this source offers ~14 per year. Verdict: reject.
- The task TYPE (duration-to-resolution of an ongoing infrastructure advisory) is unrepresented
  on the bench; the rejection is capacity/label, not novelty. A future per-advisory machine-
  readable register WITH lift dates at municipal scale could carry the same formulation.

### Cleanup

Scratch files (isc_map.html, isc_ltdwa.txt, isc_active.html, isc_dwa.json) under
/opt/data/cache/scratch (auto-pruned); measurement scripts (.factory/isc_extract.py,
isc_fetch.py, isc_measure.py) deleted after use. No bulk data entered the repository.

## 2026-10-27 discovery session (tick region: Canada) - the reopen condition fired

This record's next_action named the reopen path: "If a per-advisory machine-readable
advisory register WITH lift dates appears (provincial municipal-water channel, or
ECCC's boil-water-advisory feed gaining event grain), open a new candidate for the
duration-to-resolution task and cite this record for the formulation."

That check ran this tick via the open.canada.ca CKAN ("boil water advisory" package
searches, package_show on every hit):

- Nova Scotia "Boil Water Advisories" (data.novascotia.ca Socrata 7t68-9xmm, OGL-NS
  v1.1): per-advisory register, 2006-current, with Date Advisory Issued, Date
  Advisory Removed, Length of Advisory in Days, Facility Type, Reason - 2,649
  advisories, 2,576 with lift dates. The condition IS met by this channel.
- NEW candidate opened per this record's instruction:
  candidates/ns-bwa-advisory-lift-duration (status ready 2026-10-27). It executes
  the duration-to-resolution formulation recorded here, on the NS municipal/
  registered-supply population (a different population from ISC's First Nations
  systems - the ISC record itself stays dropped on its measured ~14 lifts/year).
- Measured negatives on the same condition: Newfoundland & Labrador's register
  (opendata.gov.nl.ca file-id=17146) has issue dates and rich system features but
  NO lift/rescinded date column; Manitoba's "Current BWAPWS" is current-only;
  Quebec's federated package is one city (Repentigny); ECCC's CESI "Boil water
  advisories" remains aggregate indicator CSVs - the ECCC feed has NOT gained
  event grain.

No ISC product was re-probed; this record remains dropped for its own reason.

