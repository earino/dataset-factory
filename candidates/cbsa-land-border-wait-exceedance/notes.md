# cbsa-land-border-wait-exceedance — discovery notes

Opened 2026-11-05 (Canada discovery tick). All probes run from the coordinator,
anonymous HTTPS, UTC. Scripts that reproduce the aggregate numbers live in
`probe/` (same directory as this file); raw fetch outputs were kept in the
session scratch path, not in the repository (bounded samples only — the full
~190 MB archive is worker work per AGENTS.md).

## 1. Catalogue and licence (2026-11-05)

```
curl -sS "https://open.canada.ca/data/en/api/3/action/package_search?q=border+wait&rows=20"
curl -sS "https://open.canada.ca/data/en/api/3/action/package_show?id=000fe5aa-1d77-42d1-bfe7-458c51dacfef"
curl -sS "https://open.canada.ca/data/en/api/3/action/package_show?id=d4a716f5-a2fc-4c3c-88ed-451fe05900e4"
curl -sSL "https://open.canada.ca/en/open-government-licence-canada"
```

- 4 datasets found: Historical BWT Land (000fe5aa, the task source),
  Current BWT (d4a716f5, live feed), Historical BWT Air (fe8020ad, monthly
  air panel — sibling noted, not opened), one unrelated.
- `license_id: ca-ogl-lgo` on both BWT datasets; OGL-Canada 2.0 text fetched and
  quoted in record.json license_evidence. Class A. Attribution statement
  required: "Contains information licensed under the Open Government Licence –
  Canada."
- Package metadata: created 2016-09-23, metadata_modified 2025-12-18,
  date_published 2014-04-04, claimed "Maintenance and Update Frequency:
  Monthly" (contradicted by measured refresh, see §5).

## 2. Archive structure (2026-11-05)

```
curl -sSL -r 0-60000   https://www.cbsa-asfc.gc.ca/data/bwt-taf-2010-2014-eng.csv   # era slice (head)
curl -sSL -r 30000000-30060000  .../bwt-taf-2010-2014-eng.csv                        # era slice (mid)
curl -sSL -r 65000000-65060000  .../bwt-taf-2010-2014-eng.csv                        # era slice (end)
curl -sSL https://www.cbsa-asfc.gc.ca/data/bwt-taf-2019-07-01--2019-09-30-en.csv     # full quarter
curl -sSL https://www.cbsa-asfc.gc.ca/data/bwt-taf-2020-01-01--2020-03-31-fr.csv     # full quarter (FR)
curl -sSL https://www.cbsa-asfc.gc.ca/data/bwt-taf--ref.odt                          # data dictionary
curl -sSL https://www.cbsa-asfc.gc.ca/data/bwt-taf--changelog.txt                    # changelog
```

- Dictionary (ref.odt, v2017-04-11): `Updated` = reporting-period timestamp;
  flow columns carry minutes or a status; "No delay" = five minutes or less;
  "Closed"; "Not applicable"; "Missed entry".
- Changelog: 2016-07-20 column rename + dictionary added; 2017-09-19 FR
  translation fixes; Known Issues: "duplicate records (same location and
  timestamp) ... with conflicting border wait time values".
- Schema drift across eras: 2010-2014 header `CBSA Office,Location,Updated,
  Commercial Flow,Travellers Flow`; 2019-era header `Custom Office Name,...`;
  FR files cp1252. Case drift: "No Delay" (2010-14) vs "No delay" (2019).
- All 24 EN quarterly URLs HEAD-checked: HTTP 200, including
  `bwt-taf-2020-01-01--2020-03-31-en.csv`, whose CKAN resource entry is
  missing from the package record (do not rely on the CKAN list).
- Boundary overlaps: 2019 Q3 file spans 2019-06-30 21:00 .. 2019-10-01 01:00
  (outside its nominal quarter); the 2010-2014 file contains rows into
  2014-04-04. Cross-file dedupe on (office, UTC hour) is mandatory.

## 3. Measured aggregates (2026-11-05)

`python3 probe/measure_archive.py` (inputs fetched by the commands in §2):

- 2019 Q3 EN: 81,836 rows, 26 offices; 57,434 distinct (office, timestamp)
  keys ≈ 99.8% of the 26 x quarter hourly grid; tz abbrevs measured
  {PDT, EDT, MDT, ADT, CDT}.
- Duplicates: 11,960/57,434 office-hours (20.8%) carry >1 row (max 15; mode
  group size 3); 18,053 rows sit in groups with CONFLICTING values,
  concentrated at Peace Bridge, Queenston-Lewiston, Pacific Highway,
  Douglas/Peace Arch, Rainbow, Aldergrove.
- Traveller base rates (valid cells = minutes or no-delay, 80,630):
  >5 22.6%, >10 14.6%, >15 10.1%, >30 3.79%, >60 0.75%.
- 2020 Q1 FR (cp1252): 80,439 rows, 26 offices, 2019-12-31 23:00 CST ..
  2020-04-01 00:00 EDT. COVID closure fixture (2020-03-21): pre — 77.6%
  no-delay, 14,360 minute-rows, max 298, 566 >30; post — 87.3% no-delay,
  1,015 minute-rows, max 75, 18 >30.

`python3 probe/measure_monthly.py` (input fetched per §5):

- Monthly service-standard panel: 2,054 rows = 26 ports x 79 months
  (2019-04..2025-10), 0 duplicates, pct-met range 59.03..100.00;
  miss base rates <100 65.5% / <95 26.1% / <90 13.8%.

## 4. Service standard — the label's rule (2026-11-05)

```
https://www.cbsa-asfc.gc.ca/services/serving-servir/standards-normes-2026-2027-eng.html   (current)
http://web.archive.org/web/20170719071209/http://www.cbsa-asfc.gc.ca/services/serving-servir/standards-normes-2014-2015-eng.html
http://web.archive.org/web/20170128023922/http://www.cbsa-asfc.gc.ca/services/serving-servir/standards-normes-2016-2017-eng.html
http://web.archive.org/web/20170604062445/http://www.cbsa-asfc.gc.ca/services/serving-servir/standards-normes-2017-2018-eng.html
http://web.archive.org/web/20180728094303/http://www.cbsa-asfc.gc.ca/services/serving-servir/standards-normes-2018-2019-eng.html
```

- FY2014-15 / FY2016-17 / FY2017-18: 10 min weekdays (Mon-Thu), 20 min
  weekends (Fri-Sun) and holidays; target 95% (FY2014-15 result 97.1%).
- FY2018-19 onward: adds "September to June:" + "July to August: 20 minutes
  (7 days a week)". Current pages keep that form (FY2024-25 94.97%,
  FY2025-26 96.9%, FY2020-21 99.35%).
- NOT found this session: FY2015-16 and FY2010-11..FY2013-14 forms — the named
  verification prerequisite for an era-correct label; the core 10/20 rule
  avoids the dependency.

## 5. Era discontinuity and refresh history (2026-11-05)

```
curl -sS "http://web.archive.org/cdx/search/cdx?url=open.canada.ca/data/en/dataset/000fe5aa-1d77-42d1-bfe7-458c51dacfef&..."
# captures 2015..2026; fetched 20201020150220, 20211123022841,
# 20241202212526, 20250117011132, 20260116204938
curl -sSI -L "https://open.canada.ca/data/dataset/000fe5aa-.../download/land-bwt-opengov-en.csv"
# Content-Length 80693, Last-Modified: Tue, 16 Dec 2025 22:29:29 GMT
```

- 2021-11-23 capture: 24 quarterly resources ending 2020-01..2020-03, no
  successor, no monthly file → the hourly series definitively ended.
- Monthly-file range at captures: "to 2024-10-31" (2024-12-02, 2025-01-17),
  "to 2025-10-31" (2026-01-16 and today); blob Last-Modified 2025-12-16.
  Observed refresh ≈ annual despite the CKAN "Monthly" claim → no operational
  monthly task opened.
- Live feed `bwt-eng.csv` (3,270 B, 30 rows): schema drifted (double-semicolon
  columns, both directions, per-row "Last updated"); one row 3 weeks stale.
  Not usable to extend the archive without self-collection (recorded option).

## 6. Novelty (2026-11-05)

```
curl -sS "https://huggingface.co/api/datasets?search=border%20wait&limit=20"      # 0 hits
curl -sS "https://huggingface.co/api/datasets?search=border%20crossing&limit=20" # US BTS volume mirrors only
```

Web searches (queries in record.json novelty_check): no ML-ready task on the
CBSA series. Adjacent prior art — researcher-collected-sensor models at
Niagara Frontier ports (US DOT 50534), Blue Water Bridge ISFC (US DOT 86608),
El Paso CV-data study (Sage 2024), synthetic-data queue framework
(arXiv 2608.27010); CBSA's CanBorder app ships forecasts, not data. Verdict:
differentiated — recorded via scripts/check-novelty.py (see record).

## 7. Open items handed to the next session

1. Worker measurement pass (advancement): exact coverage, per-window label
   counts at candidate thresholds, duplicate-conflict rate per era, and the
   2019-04..2020-03 monthly pct-met cross-check. Acceptance criteria and
   failure modes are in record.json next_action.
2. FY2015-16 and FY2010-11..FY2013-14 service-standard forms (only needed if
   the era-correct label rule is chosen over the core 10/20 rule or a fixed
   threshold).
3. Optional backlog: hourly self-collection of the live feed (~3.3 KB/fetch)
   to build a post-2026 operational tail; not part of this task.
