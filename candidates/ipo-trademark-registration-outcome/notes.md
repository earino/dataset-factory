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
never-registered of 25,163):

| Year | marks | pos | neg | censored |
|---|---|---|---|---|
| 2010 | 30,372 | 27,181 | 3,187 | 4 |
| 2011 | 36,364 | 31,015 | 5,338 | 11 |
| 2012 | 40,275 | 34,472 | 5,797 | 6 |
| 2013 | 46,355 | 38,923 | 7,363 | 69 |
| 2014 | 51,075 | 42,766 | 8,206 | 103 |
| 2015 | 54,291 | 46,160 | 7,953 | 178 |
| 2016 | 61,648 | 53,185 | 7,832 | 631 |

Splits (scored rows = pos+neg): **train 2010-2012 = 106,990 rows / 14,322 neg
(13.4%)**; **eval 2013-2014 = 97,258 / 15,569 (16.0%)**; **holdout 2015-2016 =
115,130 / 15,785 (13.7%)**. Both classes in every window and every year;
negatives arrive as 3-8k per year across all months (no event clustering).
2017+ is out of eligibility: 16,386/75,024 censored at snapshot.

## Publisher cross-check (probe_crosscheck.py, 2026-10-27)

IPO facts-and-figures workbook "Trade_marks_2016.xlsx", "Summary of trade mark
activity", National UK applications vs my distinct-mark filed-year cohorts:

| Year | Published National applications | Measured distinct marks | rel. diff |
|---|---|---|---|
| 2012 | 40,238 | 40,275 | +0.09% |
| 2013 | 46,362 | 46,355 | -0.02% |
| 2014 | 51,016 | 51,075 | +0.12% |
| 2015 | 54,320 | 54,291 | -0.05% |
| 2016 | 61,681 | 61,648 | -0.05% |

Register fidelity corroborated within 0.12% every year. (The PDF facts-and-
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
