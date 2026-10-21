# defra-la-household-recycling-rate

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: United Kingdom) - PARKED on headroom

Publisher: Defra, "Local authority collected waste management - annual results"
(https://www.gov.uk/government/statistics/local-authority-collected-waste-management-annual-results,
older years on env18).

### Commands and measured results

- `curl -s .../local-authority-collected-waste-management-annual-results` ->
  HTTP 200, 99,484 bytes; links the 2024/25 release's
  `LA_and_Regional_Spreadsheet_2024-25.ods` (2.04 MB) and
  `WFH_England_Data_202425.ods` (49 KB).
- `python3 .factory/waste_dump.py` -> downloaded 9 year-files (2016-17..2024-25),
  11,120,901 bytes in 2.3 s. First attempt found no sheets: wrong namespace guess
  (`urn:oasis:names:tc:opendocument:spreadsheet`); ODS uses
  `urn:oasis:names:tc:opendocument:xmlns:{table,text,office}:1.0`. Second attempt
  with the correct namespaces enumerated all sheets.
- `python3 .factory/waste_rows.py` -> Table_1 of the 2024-25 ODS is the FULL
  cumulative panel 2014-15..2024-25 (3,770 rows); numeric cells carry
  `office:value` attributes with no text node, so cell extraction must read the
  attribute (else every rate is empty - that failure was measured and fixed).
- `python3 .factory/waste_panel.py` -> 3,730 LA-years with computable household
  recycling rates; 11 years; 321-352 authorities/year; per-year >=50% positives
  66-84 (21-24%); split windows train/eval/holdout all carry both classes
  (23.2% / 21.9% / 21.3% positive).
- Persistence baseline (label_{Y} = label_{Y-1}), measured year-over-year:
  92.6%, 92.7%, 93.1%, 95.7%, 95.8%, 96.1%, 96.4%, 97.2%, 97.8% accuracy;
  only ~10 authorities cross the 50% line per year.

### Why parked (the measured blocker)

The four contracts mostly pass: licence OGL v3, prediction timing clean
(annual publication lag), label mechanical, splits carry both classes. It
fails the purpose of a scored task: a persistence rule is already 96-98%
accurate and the informative signal is ~10 flips/year, noise-dominated at
annual grain. A y/y-decline variant would have more movement but is an
annual, thin-feature sibling of this session's NHS A&E monthly-decline
candidate. Unpark conditions recorded in record.json next_action.

### Cross-check

Panel-summed national rate (Unitary+Disposal only, per the file's own note):
42.0% (2024-25), 43.8% (2019-20) - consistent with Defra's published England
figures (~41-44% band; release: 41.2% of total LA-collected waste
recycled/composted in 2024/25). England's household recycling rate has been
flat-to-declining since 2016/17, which is why flips are rare.

