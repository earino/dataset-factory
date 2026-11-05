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


## Unpark-question re-check (2026-11-05, UK discovery tick, read-only)

The recorded unpark condition (1) asked whether Defra's quarterly releases
publish LA breakdowns, naming WasteDataFlow quarterly exports as the channel.

- PUBLISHER'S OWN ANSWER (gov.uk "Local authority collected waste for England:
  quarterly estimates", fetched 2026-11-05): "The regular publication of a
  quarterly statistics release ceased in 2016. Whilst the data continues to be
  collected quarterly, the statistics are now published on an annual basis."
  The historical ENV19 quarterly tables were England/region-grain ("Estimates
  of quarterly waste arisings and management for England", thousand tonnes) -
  never LA breakdowns. One ad-hoc COVID edition (Apr-Jun 2020) only.
- WASTEDATAFLOW (wastedataflow.org, fetched 2026-11-05): the channel DOES exist
  - "the individual questions on waste collected and managed in WasteDataFlow
  can be downloaded by the general public. Questions are completed quarterly
  (annually in Scotland)" and "For English local authorities, past years' data
  can be downloaded from data.gov.uk" - but behind a (free, public)
  registration; not fetched this tick.
- THE PARK STANDS ON ITS MEASURED HEADROOM BLOCKER, which finer time grain does
  not address: the >=50% policy task is solved by persistence at 92.6-97.8%
  accuracy with ~10 threshold-crossing LAs/year, and quarterly grain adds four
  seasonally noisier observations of the same rare crossings rather than new
  signal. The decline variant remains adjacent to the dropped nhs-ae
  persistence-dominated family. Reopening still requires condition (2) (the
  operator wants the annual-grain policy task with the persistence ceiling
  accepted) or condition (3) (cross-sectional joins) - and flip counts would be
  re-measured first either way.
