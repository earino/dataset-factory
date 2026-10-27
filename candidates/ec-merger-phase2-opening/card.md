---
license: other
license_name: cc-by-4.0-source-plus-cc0-compilation
language:
  - en
pretty_name: EU Merger Phase II Opening (European Commission)
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - tabular
  - competition-law
  - mergers
  - antitrust
  - european-union
  - regulatory
  - temporal-split
  - event-outcome
configs:
{CONFIGS_BLOCK}
---

# EU Merger Phase II Opening ({RELEASE_TAG})

**Status: {STATUS_LINE}**

A concentration is notified to the European Commission under the EU Merger
Regulation. The Commission's case file is registered that day with a fixed set of
attributes: the merging parties (the case title), the NACE sectors of their
activities, the regulation in force, and the notification date itself.
**At the notification date, from those registration-day attributes only, will the
Commission open an in-depth Phase II investigation (adopt an Art. 6(1)(c)
decision) in this case?** One row per notified merger case; the label is the
procedure outcome, which unfolds over the following weeks (302 of 309 openers
arrive within two months of notification).

Everything the register records during or after review is excluded by
construction and never ships: the decisions block (the label source, including
all Art. 6(1)(a)/(b) and Art. 8 outcomes and their adoption dates),
caseInvestigationPhase, deadlines, last-decision dates, court cases, renotification
and initiation dates, attachments, and caseSimplified (a simplified filing upgraded
to Normal during review would make its current value post-hoc). The shipped
features are the registration-day facts: `case_title`, `sector_divisions` (the
case's NACE divisions), `sector_count`, `has_sectors`, `party_count`,
`title_has_jv`, `regulation`, and calendar decompositions of the notification
date. The qualification gate verifies over the shipped columns that no column
determines the label and that the label source is absent from every file.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} notified merger cases across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | notification years | positive rate |
| --- | ---: | --- | ---: |
| `train` | 5,406 | 1990-2013 | 4.01% |
| `eval` | 1,770 | 2014-2018 | 2.60% |
| `holdout` | 2,915 | 2019-2026 (snapshot) | 1.58% |

The splits are temporal on the notification year and disjoint, with both classes
in every window and every year (309 positives overall: 217 / 46 / 46). Positives
cluster by enforcement era and sector acquisition waves, so the gate's clustered
unit is the notification day (45 distinct positive dates in eval, 44 in holdout)
and per-notification-year counts (1-22, median about 8) are reported beside
every score. The positive rate falls 4.01% -> 2.60% -> 1.58% across the splits -
a prevalence shift recorded as a property of the enforcement regime, so the eval
and holdout windows are partly out-of-distribution tests. 33 pending cases (no
opener and no terminal decision at the snapshot, overwhelmingly live 2020s
filings) are censored and counted per split, never labelled: their outcomes are
unobserved, not negative.

## Reference points

Measured on the identical 1,770 eval rows, after gate acceptance, through the
benchmark's unmodified runner (`train.py` + `validate.sh`, digests verbatim):

| Reference / model | Eval AUC | Brier |
| --- | ---: | ---: |
| Full model (stock XGBoost baseline) | 0.6973 | 0.025343 |
| Sector-division prior (train rate per NACE division) - the required comparator | **0.7679** | 0.025008 |
| Sector-combination prior (train rate per exact division set) | 0.7051 | 0.026192 |
| Title-token prior (train rate per party-name token) | 0.6644 | 0.026111 |
| Calendar/identity prior (train rate per regulation x month) | 0.5606 | 0.025295 |
| Recent-era constant (last three train years) | 0.5000 | 0.025314 |

Paired row-bootstrap differences (1000 resamples): full model - sector prior
**-0.0706** [-0.1558, +0.0168] - the interval contains zero and the observed gap
is negative: the stock baseline trails the sector prior, recorded as a finding
rather than repaired. The model beats the calendar/identity prior (+0.1367
[0.0419, 0.2321]) and the recent-era constant (+0.1973 [0.1068, 0.2745]), so the
task is not solved by calendar and identity alone; against title tokens the
difference is inconclusive (+0.0329 [-0.0770, +0.1367]). Majority-class accuracy
on this split is 0.9740 at a 2.60% base rate - uninformative; AUC is the metric.
Persistence is inapplicable: each row is a newly notified case with no prior
same-entity observation at the instant. Per-year eval AUC (7-12 positives per
year, noisy) is reported in `RELEASE_NOTES.md`.

Headroom above the sector prior is **not demonstrated** by this package; equally,
one stock model trailing it does not establish that none can beat it. The holdout
was never scored by anything and stays sealed; the benchmark's own score is
holdout AUC.

## Timing, honestly stated

The prediction instant is the notification event itself (an administrative
record: the file is registered with these attributes on that day, date-only,
Brussels local), so no publication-lag observations apply to the features. The
label event - an Art. 6(1)(c) opener - is adopted after notification by
construction, and the one pre-notification opener in the register (M.3333, a
re-notification carrying its annulled procedure's 2004 opener) is excluded from
the label by rule. The register publishes a single current snapshot (bulk feed
since 2025-03-18; no historical vintages are retained), so the evaluation
contract is **retrospective research over the pinned vintage**: feature values
are stated as current-vintage register values, with notification-era fidelity
fixture-verified at three cross-era cases (M.877 1997 against the Commission's
own decision PDF, M.4731 2007 against its OJ prior notice, M.10188 2021 against
press releases) - not a verified point-in-time reconstruction, and the sector
taxonomy is the register's current-vintage NACE Rev 2 coding across all eras.

## Source and provenance

- European Commission, Directorate-General for Competition - "EU Competition:
  Merger case publications" open data (machine-readable case register, coverage
  from November 1990, updated daily), fetched as one anonymous bulk GET
  (`case-data-M.json`, 42,034,960 B, pinned 2026-10-27 vintage; sha256 in
  `MANIFEST.json`).
- Construction: `code/build.py`, executed by worker job `ec-merger-003`;
  qualification gate 1.5.0, 46/46 checks on the full artifact, exact-byte
  acceptance before any figure was computed; baseline job
  `ec-merger-baseline-001` through the unmodified runner contract. Two earlier
  attempts (ec-merger-001, ec-merger-002) are preserved as failure records.
- Known-event fixtures verified in-file: M.877 BOEING/McDONNELL DOUGLAS,
  M.4731 GOOGLE/DOUBLECLICK and M.10188 ILLUMINA/GRAIL all reproduce external
  notification-era sources exactly.

## Licence

The source is Commission-owned content under **CC BY 4.0** (European Commission
reuse notice; DG COMP released the machine-readable case data under it for any
processing with acknowledgement). Attribution carries through to every copy of
the derived data. Our contribution to the derived compilation is dedicated
**CC0-1.0**; our code is **MIT**. This is a derived research dataset, **not**
the Commission's official product, and the Commission has not reviewed or
endorsed it. See `LICENSE.md` for the full terms, attribution and citation.

## Use with the runner

```bash
python3 get_dataset.py --dest ./task
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```
