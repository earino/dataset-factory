# Data dictionary - ipo-trademark-registration-outcome

One row per distinct domestic UK trade mark application filed 2010-01-01..2016-12-31
(first occurrence per stripped mark-number string; 16,909 duplicate rows removed).
319,436 scored rows: train 106,990 (filings 2010-2012) / eval 97,274 (2013-2014) /
holdout 115,172 (2015-2016). Source: the frozen IPO `opendatadomestic.zip` snapshot of
2018-02-13 (UTF-16LE, pipe-separated, 62 documented columns).

## Identifier

| Column | Type | Meaning |
| --- | --- | --- |
| `tm_number` | string (id) | The mark's application number, e.g. `UK00003041794`. Assigned at filing. Unique per row (declared as the entity key; the gate verified no duplicates and no cross-split reuse). |

## Features (filing-time attributes of the application itself)

| Column | Type | Meaning |
| --- | --- | --- |
| `category` | string | Register category, normalised (3 levels measured). |
| `mark_type` | string | Type of mark (5 levels measured: Word, Device, ...). The strongest single simple reference (train-fitted positive rate per mark type scores eval AUC 0.5650). |
| `series_flag` | integer (0/1) | 1 if the application is part of a series of marks presented and accepted as a series. |
| `series_marks_count` | integer | Number of marks in the series (1 for a non-series application). |
| `nice_class_count` | integer | Number of distinct Nice classes the application covers (derived from the class columns). |
| `class1`..`class45` | integer (0/1) | Whether the application covers Nice class N (the international goods-and-services classification; class 1 = chemicals, 45 = legal services). 45 binary columns. |
| `owner_country` | string | Owner's country as recorded in the snapshot (133 levels measured). Snapshot-vintage: ownership can be assigned after filing. |
| `owner_region` | string | Owner's UK region (empty for non-UK owners). Snapshot-vintage. |
| `mark_text` | string | The mark as filed. High-cardinality (declared, not a leak: the gate scored it as an identifier, not a memorising feature). 94 rows in the source carry embedded pipe characters inside the mark text; these are recovered by right-anchored parsing (asserted in-build, counted). |
| `owner_postcode_area` | string | The owner's UK postcode area (the leading letters), empty for non-UK addresses. High-cardinality, declared. Snapshot-vintage. |
| `filed_date` | date (YYYY-MM-DD) | The application's filing date - the event time of this task. Carried as a feature and used for cohort membership. |

## Target

| Column | Type | Meaning |
| --- | --- | --- |
| `registered` | integer (0/1) | 1 iff the snapshot records a non-empty Registered date (the mark reached registration, whatever its current post-registration status). 0 iff the Registered date is empty AND the status is `Refused` or `Withdrawn`. Applications whose outcome was still unresolved at the snapshot (examination, opposition, appeal, and the undocumented `Deleted` / `Deemed Not Filed` / blank statuses) are **censored** - excluded from scoring and counted per cohort (21 / 172 / 809), never labelled negative. |

## Columns deliberately not shipped

| Source column | Reason |
| --- | --- |
| `Status`, `Published`, `Registered`, `Expired`, `Renewal Due Date` | The label source and its post-filing companions (publication, expiry and renewal all happen after the outcome resolves). `quality.json` records them as `label_source_columns` / `post_hoc_columns` and the gate asserts their absence from every shipped CSV. |
| `Hyperlink` | An Excel formula wrapping the mark number - pure duplication of the id. |
| `Name` (owner name) | Free-text owner identity, excluded by design: removing it also removes the trivial same-owner outcome-rate join a solver could otherwise build. |

Everything else in the 62-column source (owner address parts, representative details,
international-registration fields) is either covered by the shipped owner fields or not
used, per `code/build.py`'s explicit column plan.
