Bridge build-9 worker outcome (2026-11-08T22:59Z). Failure.json exported
verbatim from staging release 438580452 (asset 725466617).

WORKER: failed, exit 1, 38.8 s; collected 22:59:03, deleted 22:59:16.
Worker-scope failure 3 of 5 (build-6, build-8, build-9).

MAJOR PROGRESS - the 3b0ca2e access-research fix worked end to end:
the renamed archive stem (<YEAR>hwybronefiledel) downloaded
successfully (zip fetched, member 2018HwyBridgesDelimitedAllStates.txt
selected, 137 headers observed). Access is SOLVED.

REMAINING FAILURE - header-item check only: "2018 delimited header
carries the required NBI items" reports missing field names
['inspection_date']. Every actual required NBI item header IS present
in the file (STATE_CODE_001, STRUCTURE_NUMBER_008, RECORD_TYPE_005A,
YEAR_BUILT_027, DECK_COND_058, SUPERSTRUCTURE_COND_059,
SUBSTRUCTURE_COND_060, CHANNEL_COND_061, CULVERT_COND_062,
DATE_OF_INSPECT_090). The check expects the code's own derived column
name 'inspection_date' among the RAW file headers - a one-name mapping
defect between the code's expected field name and the real NBI header
(DATE_OF_INSPECT_090). Smallest-component repair: fix the check to use
the actual NBI header names.

No manual edits; the ordinary bounded repair consumes this diagnostic
next. Parallel state: source-16 (Federal Register finalization) and
source-17 continue their own retry cycles under the single worker slot.
