# ofsted-childrens-home-next-rating — discovery notes

Probed 2026-10-30 (discovery session, UK regional focus). All commands run from the probe/
directory on the coordinator (1.9 GiB class) unless noted. Publisher: Ofsted (England).

## The source family (three overlapping bulk products, all gov.uk, all OGL v3.0)

1. **Quarterly MI series** "Inspection outcomes of children's homes"
   (https://www.gov.uk/government/publications/inspection-outcomes-of-childrens-homes,
   discontinued Jan 2025; files Dec 2014 -> Jun 2024). Each file carries an
   `Inspection_level_data` table: one row per inspection event in the period, with
   Provider URN, provider status, sector, organisation, LA, region, inspection number,
   inspection date, inspection type group, and judgement columns. Readable formats
   measured: CSV Dec 2016 -> Dec 2020 (one tab-separated quirk: 30 June 2019 file is a
   comma-CSV wrapping tab-separated lines), ODS Jun 2021 -> Jun 2024. The 2014-2016
   editions are .xls only (no reader on the coordinator; `xlrd` on a worker reads them).
2. **Annual transparency dataset** "Inspection and regulation of children's social care
   providers" (https://www.gov.uk/government/publications/inspection-and-regulation-of-childrens-social-care-providers;
   2024 and 2025 editions, ODS ~2 MB). `Provider_level_in_year_*` sheet: inspection-level
   events for 1 Apr - 30 Sep of the year; `Provider_level_at_*` sheet: one row per active
   provider with its most recent inspection. Adds per-event `Inspection publication date`.
3. **Annual accredited statistics** "Children's social care in England" SFR
   (2026 edition: https://www.gov.uk/government/statistics/childrens-social-care-in-england-2026,
   underlying data ODS 3.0 MB, published 30 Jul 2026; prior editions 2020-2025 in the
   collection). `Provider_level_in_year` sheet: inspection-level events for the FULL
   regulatory year (1 Apr - 31 Mar), filling the Oct-Mar windows product 2 never publishes.
   The SFR series also carries a time-series sheet and provider joiners/leavers.

## Licence (read 2026-10-30)

Both publication pages carry the GOV.UK footer: "Open Government Licence v3.0" linking to
https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/. OGL v3.0 permits
copying, publication, distribution, transmission, adaptation and commercial use with
attribution. => licence_class A. Verified with: `curl -sS <page> | grep -io "open government
licence[^<]*"` (output: "Open Government Licence v3.0" x2).

## Commands and measured results

### Shape probes (one-time)
- `python3 probe_ods.py ch-2025.ods` — sheet inventory of the 2025 annual file
  (Providers_and_places 6,251 rows; Provider_level_at 6,251; Provider_level_in_year 2,651
  events 1 Apr - 30 Sep 2025; aggregates for applications/unregistered/CSE notifications).
- `python3 verify_dec2019.py` — Dec 2019 quarterly CSV is inspection-level: 1,026 events,
  dates 2019-09-02..2019-12-30, 944 distinct URNs (max 3 events/URN in-quarter),
  full inspections 809, judgements Good 519 / Outstanding 133 / RI 120 / Inadequate 39 /
  blank 104 (monitoring), plus interim-era labels on interim inspections
  ('Sustained/Declined/Improved effectiveness').

### Full-series measurement (source-side aggregates; no panel built)
- `python3 pull_series.py` — downloads the 20 remote quarterly/annual assets + parses the
  2 local annual files; per-file event counts, date ranges, event-type and judgement mixes
  saved to `probe/series_summary.json`. **Measured cost: 22 requests, 7,784,646 bytes,
  5.1-9.5 s wall clock on the coordinator.** All files anonymous GETs.
- `python3 aggregate_years.py` — dedupes full-inspection rows across ALL products by
  inspection number, aggregates per calendar year. **Measured: 23 requests, 7.4 s,
  16,760 deduped children's-home full inspections 2016-2026** (pre-Oct-2016 .xls era not
  read on the coordinator). Dedupe cross-checks: the Jun-2024 quarterly file's 708 full
  inspections are 708/708 already inside the 2024 annual file's Feb-Sep 2024 window; the
  SFR-2026 in-year sheet adds 2,356 new events after deduping 2,084 shared with the 2025
  annual file => the inspection number is a stable cross-product key.

Per-year deduped counts (full inspections; pos = Requires improvement or Inadequate):

| year | events | pos | neg (Good/Outstanding) | ungraded | distinct homes |
|------|--------|-----|------------------------|----------|----------------|
| 2016 | 728  | 25  | 603  | 100 | 724  |
| 2017 | 2122 | 344 | 1613 | 165 | 1883 |
| 2018 | 2195 | 548 | 1647 | 0   | 1909 |
| 2019 | 1206 | 308 | 898  | 0   | 1182 |
| 2020 | 0    | -   | -    | -   | -    (COVID suspension; only monitoring visits published) |
| 2021 | 1466 | 423 | 1043 | 0   | 1436 |
| 2022 | 1302 | 408 | 894  | 0   | 1267 |
| 2023 | 1641 | 379 | 1261 | 1   | 1615 |
| 2024 | 1660 | 393 | 1267 | 0   | 1627 |
| 2025 | 3268 | 676 | 2592 | 0   | 3177 |
| 2026 | 1172 | 127 | 1045 | 0   | 1172 |

Vocabulary era note: 265 events (2016-2017) use the old wording 'Requires Improvement';
the rest use 'Requires improvement to be good'. Construction must map these; 2016-era
'full' rows with blank overall (100) need handling.

Measured split windows (events by inspection year, deduped):
- train 2017-2019: 5,523 full inspections, 1,200 positives (21.7%)
- eval 2021-2023: 4,409, 1,210 positives (27.4%)
- holdout 2024-2026: 6,100, 1,196 positives (19.6%)
- 2020 excluded (no full inspections; COVID). Both classes present in every year.

### Coverage gaps (measured properties, recorded honestly)
- Q1 (Jan-Mar) quarters from 2019 onward are not published in the quarterly MI series
  (releases were Feb + Aug only). Partially recoverable: each product's "most recent
  inspection" sheets carry the latest inspection per home regardless of quarter, and the
  SFR in-year sheets (full 1 Apr - 31 Mar years) close the Oct-Mar gaps for 2025-26 and
  earlier SFR years. Gaps: Q1 2019, Q1 2021, Q1 2022, Q1 2023, Q1 2024 (the 2024 annual
  file's in-year window starts 2024-02-06, so Q1 2024 is largely covered), Oct 2019.
- The 2024 annual file covers 6 Feb - 30 Sep 2024; Oct 2024 - Mar 2025 falls in the
  "Children's social care in England 2025" SFR (published 16 Jul 2025) - not yet pulled;
  same-family file, expected same schema (worker-side pull).
- Pre-Oct-2016 history exists as .xls (Dec 2014 - Sep 2016): readable with xlrd on a
  worker; not needed for split capacity.

### Publication timing (as-of policy inputs)
- 2024+ products carry `Inspection publication date`. Measured lag for children's-home
  events: 2025 annual file min 15 / p50 41 / max 127 days (n=2,399 all event types);
  2024 annual file min 17 / p50 40 / max 133 (n=1,892). SFR-2026 as-at sheet carries
  'Latest full inspection publication date'.
- Pre-2024 quarterly files carry inspection dates only. First bulk availability is
  bounded by each vintage's documented GOV.UK release date (the publication's
  "Updates to this page" log, e.g. "13 February 2020: Uploaded ... inspections carried
  out between 1 September and 31 December 2019"). The prediction contract anchors to
  these vintage release dates, so no per-event publication timestamp is assumed.
- The publisher's own summary cross-check: SFR 2026 main findings state 5,530 full or
  monitoring inspections or assurance visits of 4,350 homes 1 Apr 2025 - 31 Mar 2026,
  with full-inspection judgement mix 11% Outstanding / 71% Good / 13% RI / 5% Inadequate
  (4,430 full inspections of homes of all types). My deduped count over the same window
  (3,268 + 1,172 = 4,440 children's-home full inspections Apr 2025 - Mar 2026) is within
  10 events (0.2%) of the publisher's denominator - close agreement, not exact; resolve
  the residual in construction (window-edge and provision-type coding differences).
- Amendment precedent: the SFR-series "Regulatory activity" sibling had figures corrected
  post-release (24 Apr 2025 update) => vintage immutability must not be assumed; pin
  exact asset digests at construction time (the ipo-trademark candidate's pinned-source
  pattern).

## Prediction contract (dated example, Europe/London throughout)

- Population: children's homes registered in England (provision type children's home,
  incl. short-break-only and multi-building), Active or Suspended as of the prediction
  instant, with at least one prior graded full inspection available in a published
  vintage.
- Prediction instant T: the documented GOV.UK release date of a bulk vintage (e.g.
  T = 13 Feb 2020, the release date logged for the Dec-2019 MI file). Features are
  everything visible in vintages released <= T: prior inspection history (dates, types,
  overall + domain judgements), registry attributes (registration date, sector, LA,
  region, places, organisation), provider-organisation aggregates computed from the same
  vintage (number of homes, share of homes last rated below Good).
- Target: the overall judgement of the home's NEXT full inspection dated after T
  (binary: below Good = Requires improvement or Inadequate). Label source column:
  'Overall Effectiveness' (2016-2023 files) / 'Overall experiences and progress of
  children and young people' (2024+ files); excluded from shipped features.
- Dated example: home URN SC000803 (Pear Tree Projects Limited, Darlington, registered
  02/05/2008, Private). Feature event window: its full inspection 25/09/2019 rated Good
  (event 10095322), first available in bulk at the Dec-2019 vintage released T = 13 Feb
  2020 00:00 Europe/London. Eligibility cutoff: home Active in the Dec-2019 vintage.
  Prediction instant: T = 13/02/2020 (Europe/London). Target: overall judgement of the
  home's next full inspection with inspection date > 13/02/2020; window ends 4 quarters
  after T (13/02/2021) or at the inspection, whichever first; the label is read from the
  first vintage released after that inspection date. No part of the target window precedes
  the prediction instant.
- Censoring: homes that deregister (status Resigned/Cancelled/Closed in a later vintage)
  before their next full inspection are censored, not labelled negative; policy decided
  in construction.

## Novelty probes (2026-10-30)

- Web: QMUL EMAP working paper (2025) predicts Ofsted SCHOOL inspection outcomes for
  state secondary schools from DfE attainment data - different population, features and
  product. No children's-home ML prediction task found.
- Web: 'Outsourcing and children's social care' (PubMed 36201866, 2022) assembled a
  longitudinal dataset of 13,000+ children's home inspections 2014-2021 for EXPLANATORY
  regression analysis of ownership vs quality - not a prediction benchmark, no splits,
  no scored contract, dataset not released ML-ready. Confirms assemblability; not a mirror.
- Mechanical search recorded by scripts/check-novelty.py (see record.json novelty_check).

## Risks to carry into advancement (named now, measured there)

1. **Persistence-baseline headroom** (the defra-recycling / nhs-ae failure mode): homes
   rated below Good are re-inspected sooner and may persist below Good; the first
   construction measurement must be the last-rating -> next-rating transition table and
   the persistence reference, before any model figure is quoted.
2. Judgement vocabulary and framework eras (2016-2017 'Requires Improvement'; interim-era
   effectiveness labels on non-full inspections; 2020 suspension) need an explicit mapping
   table in construction.
3. Q1-quarter gaps pre-SFR: eligibility for "next inspection" targets must not condition
   on gap-quarter events (use inspection dates, not file windows, for target assignment;
   only feature availability is vintage-anchored).
4. Vintage immutability is NOT assumed (documented post-release correction in the sibling
   series); pin per-asset digests (sha256) at fetch time, record them in the artifact.
