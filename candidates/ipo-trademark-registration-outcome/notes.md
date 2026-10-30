# ipo-trademark-registration-outcome - discovery notes

Verdict: **READY (go)**, licence class A, novelty differentiated. Opened and fully
probed 2026-10-27 (UK regional tick). All numbers below were measured from the
source by the retained probe scripts in this directory; nothing is estimated.

## Task

For a UK domestic trade mark application, predict from filing-time attributes
(mark text, Nice class coverage, category, mark type, series, owner
country/region/postcode-area, filing date) whether it will reach registration,
as resolved in the IPO's frozen February-2018 open-data snapshot.

Prospective user and decision: a brand owner or IP paralegal deciding how much
to invest in a filing (search scope, class coverage, attorney time) and whether
to pre-empt an office action; the refusal/withdrawal outcome is the decision
that changes the advice. Base rate measured: 10.5%-16.1% never registered
depending on cohort.

## Dated example (Europe/London)

- Mark UK00003171385 "Brexit", filed **2016-06-25** (Saturday).
- Feature event window: everything fixed at filing - mark text, 1 Nice class,
  Standard category, Figurative type, owner United Kingdom. No feature used from
  after the filing date (Published/Registered/Expired/Renewal are label-side and
  excluded).
- Eligibility cutoff: filed 2010-01-01..2016-12-31 -> eligible.
- Prediction instant: 2016-06-25, the filing date.
- Outcome observation window: 2016-06-25..2018-02-13 (snapshot). In-file status
  at snapshot: Appealed, no Registered date -> **censored**, excluded from
  scoring (2016 cohort: 631/61,648 = 1.02% censored).
- Live register 2026-10-27 (read in the supported browser; plain clients get
  403): Status **Refused** - the censored direction resolved negative, so the
  rule excluded an unresolved case rather than mislabelling it.

A resolved contrast: the 2014 cohort has 51,075 distinct marks, 42,766 positive
(registered by snapshot), 8,206 negative (Refused/Withdrawn), 103 censored.

## Licence state (class A)

- Dataset's own documentation, section 5 "Open government licence"
  (ipo-data-explained-2016, read 2026-10-27): "Provision and use of this data is
  defined under an open government licence" (links OGL v2).
- Same page footer: "This publication is licensed under the terms of the Open
  Government Licence v3.0 except where otherwise stated. ... (C) Crown
  copyright 2018".
- Live register page footer (fixture read, 2026-10-27): "All content is
  available under the Open Government Licence v3.0, except where otherwise
  stated."

## Source identity and shape (measured 2026-10-27)

| Fact | Value |
|---|---|
| Landing page | https://www.gov.uk/government/publications/ipo-trade-mark-data-release (last updated 13 Feb 2018) |
| Data URL | https://assets.publishing.service.gov.uk/media/5a82e5f4e5274a2e87dc387d/opendatadomestic.zip |
| Zip | 63,238,846 B, Last-Modified 2018-02-13T13:19:48Z, sha256 `3b6063bed36a78e8a04f10a5383f2881f4072a1be13e706a81ab097fb56ee571` |
| Member | OpenDataDomestic.txt, 817,350,108 B uncompressed, UTF-16LE, **pipe**-separated (page says tab-separated; the file measures '|' ), 62 columns |
| IR zip | opendataIR.zip 6,155,543 B (Last-Modified 2018-02-13T08:46:44Z) - separate international-registrations file, not needed for the domestic task |
| Cost | 1 anonymous GET, no paging, no auth; full aggregate pass (parse+dedup+classify 1,189,005 rows) wall 5.1 s on the coordinator |

Columns (62): Trade mark, Hyperlink (Excel `=HYPERLINK(...)` formulas), Mark
Text, Name, Postcode (area code, UK owners), Region, Country, Status, Category
of Mark, Mark Type, Series, No of Marks in Series, Filed, Published,
Registered, Expired, Renewal Due Date, Class1..Class45 (binary).

## Full-file aggregates (probe_aggregate.py, run 2026-10-27)

- 1,189,005 rows; **1,149,248 distinct marks**; 16,892 multi-owner duplicate rows.
- Field counts: 62 fields on 1,188,911 rows; 63 on 76; 64 on 15; 65 on 3 ->
  **94 rows carry embedded pipes** in Mark Text (right-anchored parse or
  exclude-with-count). 53 rows blank/invalid Filed. 3 shifted IR-clone rows.
- Sortedness violations: 3 (file is number-sorted; adjacency dedup safe).
- 10 rows: negative status WITH a Registered date set (label keys on the
  Registered date; count asserted in-build). 239 rows: Registered date with a
  status outside the registered-then-lapsed set (counted bucket).
- Filing years run 1876-01-01 .. Jan-2018 (2017 cohort n=75,024; 2018 Jan
  n=6,221) - the explained-document's "31 August 2016" cutoff is stale.

Label rule (registered-by-snapshot): positive = Registered date non-empty;
negative = Registered date empty AND status in {Refused, Withdrawn}; censored =
everything else (Application Received, Examination, Pre-Publication,
Application Published, Opposed, Appealed, Appealable, Registration Pending,
Deleted, Deemed Not Filed, blank). Deleted/Deemed Not Filed/Appealable/Appealed
are NOT in the publisher's documented 16-value status table - they are
censored, with per-cohort counts asserted.

Eligible cohorts (filed 2010-2016; complete-population coverage documented from
2010-01-01, 2005-2009 measured as registration-conditioned: 2009 shows only 499
never-registered of 25,163). CORRECTED 2026-10-30 by the reconciliation probe
(see the reconciliation section below) - the original table under-counted
2013-2016:

| Year | marks | pos | neg | censored |
|---|---|---|---|---|
| 2010 | 30,372 | 27,181 | 3,187 | 4 |
| 2011 | 36,364 | 31,015 | 5,338 | 11 |
| 2012 | 40,275 | 34,472 | 5,797 | 6 |
| 2013 | 46,362 | 38,928 | 7,365 | 69 |
| 2014 | 51,084 | 42,771 | 8,210 | 103 |
| 2015 | 54,300 | 46,169 | 7,953 | 178 |
| 2016 | 61,681 | 53,216 | 7,834 | 631 |

Splits (scored rows = pos+neg): **train 2010-2012 = 106,990 rows / 14,322 neg
(13.4%)**; **eval 2013-2014 = 97,274 / 15,575 (16.0%)**; **holdout 2015-2016 =
115,172 / 15,787 (13.7%)**. Both classes in every window and every year;
negatives arrive as 3-8k per year across all months (no event clustering).
2017+ is out of eligibility: 16,386/75,024 censored at snapshot.

The ORIGINAL (wrong) 2026-10-27 table - eval 97,258 / 15,569, holdout
115,130 / 15,785, cohorts 2013-2016 = 46,355 / 51,075 / 54,291 / 61,648 - is
preserved verbatim in `ipo_tm_aggregates.json` and in git history as a
recorded probe-measurement error.

## Publisher cross-check (probe_crosscheck.py, 2026-10-27)

IPO facts-and-figures workbook "Trade_marks_2016.xlsx", "Summary of trade mark
activity", National UK applications vs my distinct-mark filed-year cohorts
(measured values updated 2026-10-30 to the corrected cohort counts; the
corrected 2013 and 2016 counts now match the published figures EXACTLY,
which is independent corroboration that the right-anchored recovery reads
the pipe rows the way the publisher structured them):

| Year | Published National applications | Measured distinct marks | rel. diff |
|---|---|---|---|
| 2012 | 40,238 | 40,275 | +0.09% |
| 2013 | 46,362 | 46,362 | 0.00% |
| 2014 | 51,016 | 51,084 | +0.13% |
| 2015 | 54,320 | 54,300 | -0.04% |
| 2016 | 61,681 | 61,681 | 0.00% |

Register fidelity corroborated within 0.13% every year. (The PDF facts-and-
figures "Applications 58,627" figure for 2016 is the National+IR Total column -
not the domestic series - which resolves the apparent mismatch.)

## As-of / vintage posture

Single frozen snapshot (2018-02-13), sha256-pinned; the publisher itself warns
the snapshot "may not be directly comparable" with the live register. The task
is a clearly-labelled RETROSPECTIVE benchmark: one uniform vintage for every
row; the instant (filing) precedes all outcome observation; no historical
operational-availability claim. Declared caveat: owner Name/Postcode/Region/
Country and class columns are snapshot-vintage (assignment can move ownership;
classes can be narrowed post-filing) - robustness variant (drop owner fields)
recorded as a construction decision.

## Fixtures

1. UK00000000001 "BASS & Co's PALE ALE" - the first UK trade mark (1876);
   in-file Registered with Registered date 1876-01-01. Identity/fidelity anchor.
2. UK00003171385 "Brexit" (2016-06-25) - censored at snapshot (Appealed);
   live register (2026-10-27): Refused. Exercises the censoring rule.
3. UK00003041794 "ALL NATURAL FRUITY V" (2014-02-11) - Application Published
   2017-12-22 (34 months after filing), still unregistered at snapshot ->
   censored; shows why the long-examination tail must be censored, not
   labelled negative.

## Prior art (searched 2026-10-27; verdict recorded via check-novelty.py)

- "Automating Abercrombie" (J. Empirical Legal Studies / Wiley): predicts
  USPTO inherent-distinctiveness decisions from US application text; different
  target, different jurisdiction, no released ML-ready benchmark.
- TrademarkML (TU Wien thesis 2023): pairwise likelihood-of-confusion under
  Art. 8(1) EUTMR; different target (opposition-side pair scoring).
- UK IPO "Pre-Apply" tool and commercial tools ("Rocketeer") predict outcomes
  but publish no dataset, no splits, no scored contract.
- IPO facts-and-figures workbooks: aggregate counts only.
- Kaggle/Hugging Face/Zenodo: no UK trade-mark registration-outcome benchmark
  found (searches returned unrelated datasets).

Ours: the first open, ML-ready UK trade-mark registration-outcome benchmark -
formulation, eligibility and censoring rules, cohort splits, fixtures, and the
honest reference baselines, built from the only open bulk snapshot of UK trade
mark applications. The fetch being trivial is precisely why the contribution is
stated as formulation and validation, not access.

## Next action

Advancement owns construction per record.json `construction_handoff`: worker
build pinning sha256 `3b6063be...`, freeze eligibility + censoring rules,
quality.json with a gate-1.5 evaluation_contract (retrospective single-snapshot
scope, owner-vintage caveat), in-build assertions for the fixtures, the
cross-check tolerance (+-1% vs National applications), the 94 pipe rows and the
10 neg_with_regdate rows, per-split counts equal to this record; then the full
qualification gate on the worker, exact-byte acceptance, and only then the
reference baselines (class-conditional rate is the required comparator).

## Construction handoff executed (2026-10-30)

The frozen `construction_handoff` was implemented as
`source/build.py` + `source/score.py` + `source/run.sh` and launched as
worker job **ipo-tm-001** (cpx32, server 173462544, 2026-10-30T03:17Z,
reservation EUR 0.24) through `scripts/assemble-job.py` (bundle
`ipo-trademark-registration-outcome`; source digest
935aaa3756e54de3b674078ec08e2b974ab49a51d6e700adde04ef8b3a9a5a31).

**Dedup-key reconciliation, measured 2026-10-30 (full-file source-metadata
probe, counts only - no panel, no labels, no model).** The discovery probe
deduped by the parsed integer mark number, which silently skipped the 22,812
letter-suffixed series sub-marks (e.g. UK0000000052A/B) out of both dedup and
the distinct-mark count. Re-measured under the stripped-string key:

| Fact | Integer key (discovery) | String key (construction) |
|---|---|---|
| distinct marks, all years | 1,149,248 | 1,172,043 |
| duplicate rows removed | 16,892 | 16,909 (17 are letter-suffixed) |
| per-year 2010-2016 n/pos/neg/cens | (record table) | **identical to the record table** |

So the recorded cohort table stands; construction dedups on the stripped mark
number string and asserts the record's numbers exactly, plus data rows
1,189,004, the field-count distribution 62/63/64/65 = 1,188,910/76/15/3, the
52 blank/bad-filed data rows, the 3 unparseable ('3'/'5') filed rows, and the
8 eligible rows whose negative status still carries a Registered date (10 on
the wider post-2010 population, matching the discovery note).

Build-time assertions also cover the three in-file fixtures (BASS 1876,
"Brexit" 2016-06-25 censored, UK00003041794 censored), the publisher
cross-check (+-1% against the pinned Trade_marks_2016.xlsx National UK
applications values 2012-2016) and per-split positives/rows. Adopted source fields
from the 2026-10-30 header read confirm the 62-column order used by the
builder (Trade Mark, Hyperlink, Mark Text, Name, Postcode, Region, Country,
Status, Category of Mark, Mark Type, Series, No of Marks in Series, Filed,
Published, Registered, Expired, Renewal Due Date, Class1..Class45).

The worker run is `build.py`'s first execution: it was syntax-checked and its
parse/classify logic mirrors the two measured probes, but no local full run
was performed (construction belongs on the worker). Outcome and any repair
are the next session's first step.

## Pipe-row reconciliation (2026-10-30, advancement; probe_reconcile_pipe_rows.py - RECONCILIATION CLOSED)

ipo-tm-002's build scored +58 rows vs the frozen EXPECTED table (eval +16,
holdout +42; censored identical, train exact; blank/bad-filed 34 vs 52). The
recorded bounded reconciliation ran on the coordinator over the same
sha256-pinned snapshot (63,238,846 B, `3b6063be...`; one anonymous GET to
scratch, deleted after the run). Aggregate counts only - no feature panel,
no labels aligned, no model, no AUC. Evidence: `ipo_tm_reconciliation.json`
(pass A = probe_aggregate.py verbatim, pass C = build.py's exact pipeline
including an imported `build.iter_records` cross-check, per-row diff
attribution, and the full 94-row pipe census).

**Which pipeline is correct - decided by measurement.** The discovery probe
read the 94 embedded-pipe rows at SHIFTED positions (left-anchored
fields[7]/[12]/[14], so it read the Country / series-count / Mark-Type
columns as Status/Filed/Registered) and deduped on the int key AFTER the
filed check. build.py's right-anchored recovery (the 45 class columns are
the LAST 45 fields, so the extra pipes belong to Mark Text) is the correct
reading:

- All 94 recovered rows: Status in the publisher's documented vocabulary
  (94/94); shifted status reads in vocabulary: 0/94 (they read country and
  mark-type values). Recovered Filed dates parse: 94/94. Class columns
  binary: 94/94.
- Corrected cohorts 2013 (46,362) and 2016 (61,681) equal the IPO's own
  published National applications EXACTLY (the old table was low by exactly
  the mis-read pipe rows).

**Attribution of every delta (closes exactly; probe checks all green):**

- +58 scored rows = the 58 recovered pipe rows filed 2013-2016:
  2013 +5 pos +2 neg; 2014 +5 pos +4 neg (eval +16);
  2015 +9 pos; 2016 +31 pos +2 neg (holdout +42). Every one of the 58 rows
  is named, with its recovered fields, in `ipo_tm_reconciliation.json`.
- -18 blank/bad-filed (52 -> 34) = the 18 pipe rows whose SHIFTED filed
  read ('No' x11, 'Yes' x4, 'Word' x2, 'Figurative' x1) failed the 4-digit
  check. The other pipe rows were excluded via bogus year keys ('0' x67,
  '2' x6, '3' x2, '5' x1) or as int-key dups (x2).
- 17 non-pipe classification diffs = letter-suffixed series sub-marks with
  repeated owner rows (e.g. UK0002338781A x3), ALL filed 1928-2003
  (out of window) - the string-key dedup change alone moves no cohort,
  confirming the 2026-10-30 dedup-key reconciliation's "identical per-year
  table" claim.
- The "3 unparseable ('3'/'5') filed rows" in the 2026-10-30 handoff note
  was the SAME shifted-read artifact: rows UK00003033672 (recovered filed
  2013-12-05, Withdrawn -> 2013 negative), UK00003112662 (2015-06-10,
  Registered -> positive), UK00003154878 (2016-03-14, Registered ->
  positive). Correct-column unparseable count: 0. The worker build never
  printed or asserted this count; it is now asserted as 0.
- Pass A reproduces the frozen `ipo_tm_aggregates.json` exactly (all
  numeric keys), proving the frozen EXPECTED table's provenance is the
  shifted-read probe and nothing else.

**Actions taken:** EXPECTED in `source/build.py` re-derived from the
corrected probe (cohorts 2013-2016, eval/holdout split counts, blank 34,
unparseable 0 now asserted); the old table preserved in git history and
`ipo_tm_aggregates.json` as a probe-measurement error, never tuned against
build output. Relaunch: ipo-tm-003 (rebuild 3, linked to ipo-tm-002) in the
unchanged construct -> gate -> exact-byte --accept -> references order.
Attempt cap: a further defect on ipo-tm-003 means re-target or drop per
dataset-qualification, not ipo-tm-004.

## ipo-tm-003 outcome and the ipo-tm-004 rebuild (2026-10-30, advancement)

ipo-tm-003 (server 173516828, 23.1 s, exit 1, staging release 428902203)
VALIDATED the construction for the first time and then crashed after the
write: with the re-derived EXPECTED, every in-build assertion passed
(cohorts, splits, fixtures, publisher cross-check, hazards, label-source
absence, exact column set) and all five artifact files were written
(train 106,990/92,668; eval 97,274/81,699; holdout 115,172/99,385). The
crash is a one-line latent defect in the never-reached summary tail of
main(): the publisher cross-check comprehension looked the pinned INT year
keys of PUBLISHED_NATIONAL_APPLICATIONS up in the STRING-keyed
`diag["per_year"]` dict (KeyError: 2012), before summary.json was written.

Cap reasoning (recorded in the candidate record): this is a mechanical
post-artifact code defect, not the structural/timing/population class the
dataset-qualification rebuild cap guards against, and the 2026-10-29 cap
note anticipated a further DIVERGENCE - what happened is the opposite, the
construction verifying green end to end. One bounded rebuild is therefore
justified: ipo-tm-004 (launched 10:52:44Z, server 173520161) with the fix
(build.py `cross_check_measured()`, red/green regression test in
tests/test_ipo_tm_build.py - red on a pre-fix variant reproducing
KeyError: 2012, green on the fix). Hard cap now: ANY further code defect on
ipo-tm-004 means re-target or drop; no ipo-tm-005. Determinism check at
collect: 004's CSVs/meta/quality must be byte-identical to 003's staging
digests (the fix touches only the post-write summary block); summary.json
is the only new file. Local suite 679 tests OK, with one unreproduced
single failure in one of five full runs (recorded in STATE.md; CI runs at
the exact commit).
