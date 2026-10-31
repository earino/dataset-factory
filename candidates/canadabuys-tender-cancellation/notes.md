# canadabuys-tender-cancellation — discovery notes

Opened 2026-10-31 (scheduled discovery session, regional focus Canada). All probes run
2026-10-31 from the coordinator, anonymous HTTPS, bounded. Bulk CSV samples stayed in
`/opt/data/cache/scratch/cb/` (scratch, not committed) and are re-fetchable from the
recorded URLs; the probe scripts are retained in `probe/`.

## Source identification

```
curl -sS "https://open.canada.ca/data/en/api/3/action/package_search?q=CanadaBuys%20tender&rows=20" -o ckan_tender.json
```

- CanadaBuys tender notices: dataset `6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2`, org pwgsc-tpsgc,
  license_id `ca-ogl-lgo`. Files: complete (2022-08-08 onwards), legacy 2009-2022, per-FY
  2022-23..2026-27, new/open snapshots.
- CanadaBuys award notices: dataset `a1acb126-9ce8-40a9-b889-5da2b1dd20cb`, same licence.
- CanadaBuys contract history: dataset `4fe645a1-...` (same licence; not used by the primary
  task — a post-award contract-amendment task on contract history is a family duplicate of
  `austender-contract-amendment-occurrence` (status ready) and was NOT opened for that reason).

Bulk file sizes (HEAD, 2026-10-31):

```
for u in ...; do curl -sSI "https://canadabuys.canada.ca/opendata/pub/$u" | grep -iE "^(HTTP|content-length|last-modified)"; done
```

- tenderNoticeComplete 188,290,269 B; 2009-2022 tenderNoticeHistorical 558,413,231 B;
  awardNoticeComplete 104,817,598 B; 2012-2022 awardNoticeHistorical 270,603,514 B;
  per-FY tender 2022-23..2026-27: 48.0 / 45.3 / 40.2 / 41.5 / 23.2 MB;
  per-FY award 2022-23..2025-26: 19.9 / 19.7 / 24.0 / 29.2 MB.
- FY2026-27 tender file Last-Modified: Sat, 31 Oct 2026 10:30:31 GMT (daily refresh measured).

## Licence (class A)

- OGL-Canada 2.0 text read 2026-10-31 at https://open.canada.ca/en/open-government-licence-canada
  (quotes in `record.json license_evidence`). Attribution statement required:
  "Contains information licensed under the Open Government Licence – Canada."
- Dataset-level instrument: license_id `ca-ogl-lgo` on the open.canada.ca package records above.

## Column documentation (read in full, publisher's own instrument)

```
curl -sS "https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/achatscanada-canadabuys-dd.xml" -o canadabuys-dd.xml   # 60,478 B
python3 parse_dd.py   # prints all 67 documented fields
```

Decisive documented semantics (verbatim quotes in `record.json`):
- `tenderStatus`: "Open (ie: accepting bids), Expired (no longer accepting bids) or Cancelled".
- `tenderClosingDate`: all times "in UTC-0500 ... EASTERN STANDARD TIME".
- `amendmentNumber`: "The number of amendments against a tender notice and/or a related awarded
  contract" — a running counter, not an event list; excluded from features (post-instant).
- Publisher support page (https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/soutien-support-eng.html,
  fetched 2026-10-31): the files "include information on new, open, cancelled and expired notices
  that are published on the CanadaBuys website"; "Active" renamed to "Open"; per-FY files bucketed
  by publication date; closing times UTC-0500.

## Row-level probes

### FY2023-24 panel (whole-FY bounded sample, 45.3 MB, ~8 s)

```
curl -sS -o 2023-2024-TenderNotice-AvisAppelOffres.csv "https://canadabuys.canada.ca/opendata/pub/2023-2024-TenderNotice-AvisAppelOffres.csv"
curl -sS -o 2023-2024-awardNotice-avisAttribution.csv   "https://canadabuys.canada.ca/opendata/pub/2023-2024-awardNotice-avisAttribution.csv"
curl -sS -o 2024-2025-awardNotice-avisAttribution.csv   "https://canadabuys.canada.ca/opendata/pub/2024-2025-awardNotice-avisAttribution.csv"
python3 probe/probe_fy2023_24_panel.py
```

Output (2026-10-31): 7,430 rows, 6,829 distinct solicitationNumbers; publication dates
2023-04-01..2024-03-29; status mix Expired 6,414 / Cancelled 415 / Open 0; closing date present
6,829/6,829; pub->close median 26 d (p10 14, p90 53). Notice-type mix and per-type cancellation
counts, procurement-method mix, award-notice join (46.07% overall; Expired 48.1% vs Cancelled
14.5%; RFI 3.2%) — full numbers in `record.json measurements.provenance_mix_2026_10_31` and
`award_join_2026_10_31`. RFP-like population (RFP, RFP-SA, RFSO, RFSA, ITQ): 5,749 with 397
Cancelled = 6.90%.

### Row model (amendment rows vs original rows)

```
python3 probe/probe_row_model.py
```

Output: 499 solicitations with >1 row; amendment rows carry their own later publication dates;
144 multi-row solicitations show differing status across rows; 81 where the amendment-000 row is
not the earliest-published row; 12 rows with 'Cancelled-' title prefix (legacy-era convention,
also measured in the 2009-2022 archive). Consequence: features from the earliest-published row;
solicitation-level label precedence any-row-Cancelled, verified at construction against notice
pages (bounded sample).

### Legacy archive coverage (bounded 400 KB range slices, no bulk download)

```
python3 probe/probe_legacy_slices.py    # HTTP Range fetches at byte offsets 3M/150M/330M/520M
```

Output: identical 67-column schema in the 2009-2022 legacy file; tenderStatus populated in every
slice; Cancelled rows present in the 2017/2018 region (Parks Canada 5P420-17-5210/A, pub
2017-07-17, close 2017-08-08T16:00:00) and the 2021 region (PWGSC WS3010378161, NRCan
NRCan-5000059348/B); slices span publication years 2012-2022. Note: plain `urllib` gets HTTP 403
from the CDN without a User-Agent header; curl and UA-header requests both succeed.

### Bulk file headers (bounded 0.2-0.4 MB range fetches)

```
python3 probe/probe_bulk_file_headers.py
```

Output: legacy and complete files share the FY-file header exactly (67 cols); complete file
carries live Open rows (sample: pub 2026-01-23, close 2029-03-31).

## Dated examples (closing times are published in UTC-0500/EST per the data dictionary)

- CANCELLED: WS3864736193, PWGSC, "RFP - HVAC Maintenance Services Contract - Connaught Range
  a[nd...]", published 2023-04-14, closing 2023-04-17T14:00:00 (EST display) -> terminal status
  Cancelled. Instant = 2023-04-14; posting duration 3 days; every shipped feature is fixed at the
  instant; the cancellation is a state change strictly after it.
- CANCELLED: WS3765771658, PWGSC, "EV385-231411. Loading Docks Assessment and Repair, Prince[...]",
  published 2023-04-20, closing 2023-05-16T14:00:00 -> Cancelled.
- Negative class: BPM020594/25224, Shared Services Canada, published 2024-01-22, closing
  2024-02-06T14:00:00 -> Expired (closed normally).
- Legacy: 5P420-17-5210/A, Parks Canada, published 2017-07-17, closing 2017-08-08T16:00:00 ->
  Cancelled.

## Five contracts (reconciled; details in record.json review)

1. Redistribution: SUPPORTED (OGL-Canada 2.0, class A, attribution carried).
2. Prediction timing: SUPPORTED with recorded limitation (terminal-state label from pinned
   current archive; cancellation dates not in bulk data; Open rows censored; bounded
   notice-page verification at construction).
3. Target: SUPPORTED (documented status column; Expired = observed absence; eligibility fixed at
   the instant).
4. Split capacity: PARTIALLY MEASURED — whole-FY2023-24 measured; legacy label presence shown by
   slices; per-window exact counts REQUIRE the ~746 MB bulk download = worker job (prerequisite to
   `ready`, never extrapolated).
5. Not a mirror: DIFFERENTIATED (mechanical sweep recorded by check-novelty.py; nearest prior art
   is EU TED outcome-prediction literature on different targets/jurisdiction, not ML-ready;
   bench sibling austender is a different task contract).

## Decision

Status `investigating` (not `ready`): contract 4's full-window counts and the notice-page
verification are bulk work that belongs on a worker. Exact acceptance criteria for the
ready/drop flip are in `record.json next_action`.
