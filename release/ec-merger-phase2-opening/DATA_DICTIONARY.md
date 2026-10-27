# Data dictionary

One row per merger case notified to the European Commission under the EU Merger
Regulation (caseType `Merger` with a recorded `caseNotificationDate`), as carried by
the DG COMP machine-readable case register (open-data bulk feed `case-data-M.json`,
vintage of 2026-10-27). 10,091 shipped rows of 10,125 eligible; 33 pending cases
(no terminal decision yet: 29 with no decisions at all, 3 Art. 9(3) partial referrals,
1 Art. 4(4) partial referral) are censored out and counted, never labelled.

## Columns

| Column | Role | Definition |
| --- | --- | --- |
| `case_number` | id | The register's case number (e.g. `M.10188`), one row per case. |
| `phase2_opened` | **target** | 1 if the case carries at least one `Art. 6(1)(c)` decision adopted on or after the notification date (ever-adopted; a later withdrawal does not undo the opener; `'Withdrawal of Art. 6(1)(c)'` decisions never match), else 0. Positive rate: train 4.01%, eval 2.60%, holdout 1.58%. |
| `notification_date` | time column | The case's notification date (`caseNotificationDate`, date-only precision, Brussels local). The prediction instant: every feature is fixed when the file is registered. |
| `notification_year` | feature | Calendar year of the notification date. |
| `notification_month` | feature | Calendar month (1-12) of the notification date. |
| `regulation` | feature | The applicable merger regulation: `4064/89` or `139/2004` (`caseRegulation`). |
| `sector_divisions` | feature | Sorted set of NACE division labels for the parties' activities, `'\|'`-joined, or `NONE` when the register carries no sectors (79 cases measured). Derived from `caseSectors`; division = first two components of the label's code part (e.g. `C.20.5 - ...` -> `C.20`). Register coding is the current-vintage NACE Rev 2 taxonomy (see the vintage note in the README). |
| `sector_count` | feature | Number of `caseSectors` entries on the case. |
| `has_sectors` | feature | 1 when the case carries sectors, 0 for the `NONE` cases. |
| `party_count` | feature | Number of segments of the case title split on `/` with optional surrounding whitespace. |
| `title_has_jv` | feature | 1 when the title carries a `JV` token (joint ventures). |
| `case_title` | feature | The case title (`caseTitle`): the merging parties as named by the register, an immutable historical fact (the OJ prior notice for M.4731 GOOGLE/DOUBLECLICK documents the parties and their activities at notification). High-cardinality free text. |

## Excluded by construction (never shipped)

`caseSimplified` (upgrade leak: a simplified filing upgraded to Normal during review
would make the current value post-hoc), and the post-hoc / mutable / non-pinned fields
`caseInvestigationPhase`, `caseDeadlineDate`, `caseLastDecisionDate`, `caseLinks`,
`caseCourtCases`, `caseRenotificationDate`, `caseInitiationDate`, `caseAttachments`.
The label source - the case's `decisions[]` block (decision types, adoption dates) -
is excluded wholesale from the shipped columns.

## Splits

Temporal on `notification_year`: train 1990-2013 (5,406 rows / 217 positives),
eval 2014-2018 (1,770 / 46), holdout 2019-snapshot (2,915 / 46). Distinct positive
notification dates: 45 in eval, 44 in holdout. The register's coverage starts
November 1990.
