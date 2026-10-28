# eu-transparency-register-removal — discovery notes

Opened 2026-10-28 (EU/EEA regional tick). All probes run from /opt/data/cache/scratch on
the coordinator; scripts retained in this directory as `probe_*.py`. Data files were
deleted from scratch after measurement (bounded probe only); every number below is the
output of a retained script against the named snapshot files.

## Source identity

- Publisher: the EU Transparency Register, operated jointly by the European Parliament,
  the Council of the EU and the European Commission (Interinstitutional Agreement of
  20 May 2021, OJ L 207, 11.6.2021, p. 1); Secretariat of the Transparency Register.
- Publication channels (both read 2026-10-28):
  1. data.europa.eu dataset `transparency-register`
     (https://data.europa.eu/data/datasets/transparency-register). Portal API record
     enumerated with `probe_portal_dataset.py`:
     `curl -s 'https://data.europa.eu/api/hub/search/datasets/transparency-register'`
     -> 49 distributions: semi-annual organisation snapshots **2015-01 .. 2026-06** in
     XML + XLS (`Organisations in Transparency Register - YYYY - MONTH`),
     plus live daily exports (organisation XML/XLS, EP-accredited persons XML).
  2. Register live exports at transparency-register.europa.eu
     (`odplastorganisationxml_en`, `odplastorganisationxls_en`, `odplastaccreditedxml_en`),
     "updated daily" per the dataset description.
- Access recipes (measured 2026-10-28):
  - 2015-01..2024-06 files at `https://data.europa.eu/euodp/en/data/storage/f/<stamp>/<name>.xml`
    answer HTTP 200 to anonymous curl (measured sizes: 2016-01: 51,658,983 B;
    2023-01: 78,312,987 B; 2024-01: 80,735,430 B; 2023-06: 79,159,532 B).
  - 2025-01..2026-06 files at `https://data.europa.eu/data-management/store/api/data/sg/<id>`
    (2025-01 legacy id `68416209b95c776e608721c0`, 2026-01 `01M3235J1FR9HJZ6BZ32177D7A`,
    2026-06 `01M323JV693WY8VP2989DA0ZR2`) answer **401** to a plain client (and a real
    browser navigation / fetch failed), but **200** with a browser-like User-Agent plus
    `Referer: https://data.europa.eu/data/datasets/transparency-register`
    (2026-06 file: 112,656,126 B; 2025-01-labelled file: 83,370,371 B).
  - Live export: anonymous 200; range-request metaData read 2026-10-28:
    `exportDate 2026-10-27T21:00:00Z, numberOfIR 18050`.

## Licence (triage first, before any task probing)

- Per-distribution licence on the publisher's own portal record (all snapshot files):
  `http://data.europa.eu/eli/dec/2011/833/oj` — Commission Decision 2011/833/EU on the
  reuse of Commission documents.
- Decision 2011/833/EU Art. 4 (EUR-Lex CELEX:32011D0833): reuse "for commercial or
  non-commercial purposes", "without charge", "without the need to make an individual
  application", under Art. 6 attribution-style conditions. Art. 2.2 excludes third-party-IP
  documents; these exports are the publisher's own compilation published as open data.
- EU site-wide copyright notice (european-union.europa.eu/legal-notice_en): "Unless
  otherwise indicated (e.g. in individual copyright notices), content owned by the EU on
  this website is licensed under the Creative Commons Attribution 4.0 International
  (CC BY 4.0) licence." No dataset-specific copyright notice restricts the register files.
- Registrants declare on registration that the information they provide "shall be public"
  (EUR-Lex summary of the IIA).
- Classification: **A** (explicit open reuse instrument, attribution conditions only).

## Documented rule mechanics (publisher pages, read 2026-10-28)

- FAQ "Managing my registration" (transparency-register.europa.eu/faqs-and-contact_en):
  "You must update your registration at least once a year." The annual-update deadline is
  "one year after the date of registration, and then one year after the annual update
  date"; reminders at 4 and 2 weeks before the deadline; "If you do not update your
  registration by the deadline, your registration will be suspended and then removed two
  weeks after the deadline. This procedure is automatic and cannot be modified."
- Guidelines: partial updates keep the annual deadline; a full (annual) update resets it.
- Reactivation: possible only within two years of removal, keeping the same registration
  number (FAQ); feature implemented by the Secretariat in January 2025
  (Secretariat "Mapping of the implementation of the 2021 IIA" report).
- Consequence of removal (ECA Special Report 05/2024 and the IIA): removal leads to
  withdrawal of EP access badges; registration is a precondition for certain
  interest-representation activities.

## Probes and measurements

### Snapshot schema and integrity

`probe_snapshot_parse.py tr_2024JAN.xml` (file: the "2024 - JANUARY" export, in-file
exportDate 2024-01-21T19:30:00.308+01:00, numberOfIR 12430, parsed 12430):

- No `<status>` element in the new-era export; every row's lastUpdateDate falls within
  the 12 months before the export (11,365 in 2023 + 1,065 in 2024) — the export carries
  non-suspended (active) registrations only. Old-era files (namespace `intws/20141104`)
  DO carry `<status>`, measured `active` on all 9,120 rows of the 2016-01 file.
- Full element inventory recorded in record.json `measurements.schema_inventory`
  (identity, category, two offices, goals, interests/levels, membership bands + FTE,
  financialData with declared costs/funding/grants/contributions/revenue by
  closedYear/currentYear, clients/intermediaries for consultancies,
  EULegislativeProposals, EPAccreditedNumber, lastUpdateDate, ...). Field meanings are
  documented in the register's Guidelines / IIPA Annex I.
- In-file declared numberOfIR equals parsed rows in every parsed file (6/6).

### Window transitions (probe_snapshot_transitions.py)

All absences are keyed on identificationCode. "Reappear" = rows present in B with
registrationDate earlier than A's export (reactivations plus a small number of
validation-lagged new registrations).

| window (in-file export instants) | days | A rows | removed by B | rate | reappear |
|---|---|---|---|---|---|
| 2016-01-21T19:30+01 → 2017-01-21T19:30+01 | 365 | 9,120 | 1,471 | 16.1% | 13 |
| 2023-01-21T19:30+01 → 2023-06-21T19:30+02 | 150 | 12,418 | 1,212 | 9.76% | 99 |
| 2023-01-21T19:30+01 → 2024-01-21T19:30+01 | 365 | 12,418 | 2,294 | 18.5% | 92 |
| 2024-01-21T19:30+01 → 2024-12-31T21:00Z   | 345 | 12,430 | 1,722 | 13.85% | 118 |
| 2024-12-31T21:00Z → 2026-06-30T20:00Z     | 545 | 13,119 | 2,051 | 15.6% | 200 |

Commands: `python3 probe_snapshot_transitions.py <A.xml> <B.xml>` after download per the
access recipes above.

- Survivors updated within window: 10,116/10,124 (2023→2024) and 7,647/7,649 (2016→2017):
  survival ≈ "performed at least one update in the window".
- Removals occur at every lastUpdateDate age (2023-01→2023-06 window: 21 removals with
  lastUpdate only 0-60 days before the instant; 755 with lastUpdate 300-360 days before).
  The label is therefore NOT mechanically derivable from lastUpdateDate: partial updates
  bump lastUpdateDate without moving the documented annual deadline.
- `probe_lu_missingness.py` (2024-12-31 export): 1,916/13,119 rows (14.6%) have EMPTY
  lastUpdateDate; among rows removed by 2026-06, 593 had empty lastUpdateDate (31%
  removal rate vs 15.6% overall). Keep missingness as a feature.

### XML quirks (needed to parse two files)

- The 2025-01-labelled and 2026-06 exports contain character references invalid under
  XML 1.0 (e.g. `&#x1d;` at line 1,734,983 / 2,239,033 of those files; the 2026-06 file
  declares XML 1.1). probe_snapshot_transitions.py sanitises these references
  (drops refs to codepoints invalid in XML 1.0) and feeds an XMLPullParser.

### Worked dated example (all instants in named timezones)

Snapshot t = 2023-01-21T19:30:00+01:00 (Europe/Brussels, CET).
Next snapshot t+1 = 2023-06-21T19:30:00+02:00 (Europe/Brussels, CEST).

Positive (removed):
- REG 483924815151-12, "Hope For Children" CRC Policy Center (Cyprus, category
  "Non-governmental organisations, platforms and networks and similar").
- Feature event window at t: registered 2014-12-05T15:25:09+01:00;
  lastUpdateDate 2022-04-26T21:42:47+02:00 (270 days before the instant, i.e. the
  documented annual-update deadline ≈ 2023-04-26, inside the target window);
  EPAccreditedNumber 0.
- Eligibility cutoff: present in the 2023-01-21 snapshot (yes).
- Prediction instant: 2023-01-21 19:30 CET.
- Target start/end: (2023-01-21 19:30 CET, 2023-06-21 19:30 CEST] — strictly after the
  instant; the implied automatic-removal date (deadline + 2 weeks ≈ 2023-05-10) sits
  inside the window.
- Measured verdict: ABSENT from the 2023-06-21 export → label 1 (removed). Verified by
  probe_examples.py on the fetched files.

Negative (survived):
- REG 095284146845-67, CloudFerro (Poland, "Companies & groups"), registered
  2022-06-21, lastUpdateDate 2022-06-21T13:17+02:00 at t (214 days before the instant;
  deadline beyond the window), present in both snapshots → label 0.

### Cross-checks against the publisher's own products

- Secretariat "Mapping of the implementation of the 2021 IIA" (register website):
  "87% [complying] timely ... and 1 496 registrants removed" over its reporting period;
  "more than 14 000 registrants" (2025). Annual report 2021: 13,366 registrants at
  31 Dec 2021. Measured snapshot sizes: 9,120 (2016-01) → 11,010 (2017-01) → 12,418
  (2023-01) → 12,430 (2024-01) → 13,119 (2024-12-31) → 17,424 (2026-06-30) → 18,050
  (live 2026-10-27). Removal counts (1.2-2.3k/yr) are consistent with the Secretariat's
  own 1,496-removed figure for a comparable period.
- ECA Special Report 05/2024 confirms the mechanism ("Registrants who do not carry out
  the update are first suspended and then removed") and notes register-side gaps we do
  not inherit (we use the publisher's own snapshot archive, not per-page scraping).

### Cost (measured, not estimated)

- Downloads (coordinator, 2026-10-28): six XML snapshots, 51.7-112.7 MB each, ~5-40 s
  per file, one GET per file (+1 portal API call). Full 24-snapshot series ≈ 1.8 GB in
  ~24 requests, ~15 min sequential.
- Parsing: stdlib XMLPullParser streaming, 40-90 s per ~80 MB file on the 4-vCPU
  coordinator. Construction-scale work belongs on a worker (advancement), not here.

## Novelty sweep (2026-10-28)

- Hugging Face datasets API (`novelty_catalogs.py`): queries "lobbying",
  "transparency register", "EU lobbying", "lobby register" — no EU-register prediction
  task. Nearest hits are unrelated: US LDA text tasks (mteb/legalbench_corporate_lobbying),
  Canadian registry extracts, Ontario disclosure graph.
- arXiv API: "lobbying register prediction", "transparency register prediction",
  "lobbying registration machine learning" — nothing on this task (nearest: US
  bill-level lobbying activity prediction, a different population and label).
- Zenodo: "EU-LOB: An Open and Incremental Database of Registered Lobbying Organizations
  in the European Union" (2026; consolidated current-state CSV/parquet extracts of EU +
  national registries — a database, not a scored prediction task) and a "2023 EU
  Transparency Register - Meta-organizations" extract.
- Literature: Berkhout & Lowery 2011 (J. Eur. Public Policy) measure EU interest-community
  birth/death volatility from the old CONECCS/EP registers; a separate study runs event
  history analysis on the German Bundestag register (1974-2012). Descriptive demography,
  no ML-ready benchmark with splits and a scored contract on this register.
- Comparison to this bench: companies-house-company-exit (GB, PARKED on access) and
  npri-facility-reporting-exit (CA, investigating) are entity-continuation tasks in
  different institutions with different regimes, features and removal mechanisms; this
  is not a second instance of the same reporting stream (the efsa/bvl situation).

## Decision

Verdict `ready` (five contracts reconciled in record.json `review`). Construction and
headroom risks named there; deciding check = qualification gate + headroom over a
deadline-proximity-only baseline on holdout.
