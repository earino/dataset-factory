# Data dictionary

Every file in every split has the same 11 columns, in this order.

| # | column | role | available at prediction time? | notes |
|---|---|---|---|---|
| 1 | `docket_number` | identifier (carry) | yes | The City's case number, as recorded (`08BN00002A`). One row is one case, so it is unique here — **53,763 of 53,763 rows** carry a distinct value. Never a feature. |
| 2 | `violation_date` | date (carry) | yes | `YYYY-MM-DD`. The notice date of the case's **lead charge** — its earliest recorded violation — which is what places the case in a split. Known at docketing: it is on the notice. 4,624 distinct values, 2008-01-01 to 2026-05-15. Declared high-cardinality; never a feature of the packaged baseline. |
| 3 | `violation_code` | feature | yes | Ordinance code of the lead charge, exactly as published (`000001`, `001002FR`). 544 levels. |
| 4 | `ward` | feature | yes | The City's ward, as published — a string, because `0` appears as an "unassigned" value. 52 levels; 153 rows (0.28%) blank. |
| 5 | `street_direction` | feature | yes | Street direction of the property: `E`, `N`, `S`, `W`. 4 levels, no blanks. |
| 6 | `street_type` | feature | yes | Street type of the property (`AVE`, `BLVD`, `ST`). 18 levels; 613 rows (1.14%) blank. |
| 7 | `latitude` | feature | yes | Decimal degrees, WGS84 (EPSG:4326), as published. 41.644713 to 42.022686; 41,389 distinct. |
| 8 | `longitude` | feature | yes | Decimal degrees, WGS84 (EPSG:4326), as published. −87.911367 to −87.524679. |
| 9 | `charge_count` | feature | yes | How many violation charges the City publishes against this docket number, every disposition included. 1 to 144. |
| 10 | `distinct_code_count` | feature | yes | How many distinct `violation_code` values the case carries. 1 to 65. |
| 11 | `outcome` | **target** | — | `Liable` if the hearing officer recorded a Liable disposition on **at least one** charge of the case; otherwise `Not Liable`. |

`case_disposition` — the source column the label is read from — is **deliberately absent from
every split file**. It is the answer, so shipping it would hand the model the label.

## Excluded columns: present in the source, absent from every file

| column | why it is excluded |
|---|---|
| `case_disposition` | The label's source: the disposition the hearing officer recorded for the case. |
| `hearing_date` | Post-hoc for a decided case. The City documents it as the date of the **most recent** hearing, which on a decided case *is* the hearing at which the disposition was recorded. A feature derived from it separates the classes on its own, so it is excluded outright — not merely left out of the feature list. |
| `imposed_fine` | Recorded when liability is decided. |
| `admin_costs` | Recorded when liability is decided. |
| `last_modified_date` | Changes after the outcome; a row-update timestamp, not a property of the case at docketing. |

These are excluded because they are post-hoc, **not** because they are uninformative — several
are strongly predictive, which is exactly why they must not be features.

### The source's text fields, and what happens to them

The source table also carries prose and identifier fields. None of them is shipped, and they are
excluded for three different reasons — worth stating separately, because "not shipped" is not the
same claim as "carries nothing":

| column | what it holds | why it is not shipped |
|---|---|---|
| `violation_description` | The charge's wording, e.g. `Arrange for inspection of premises. (13-12-100)` | It is a fixed rendering of `violation_code`, not additional information: the source's 1,260 distinct codes carry only 1,266 distinct code+description pairs, so six codes have any variant wording at all. The code ships as a feature; the sentence that restates it does not. |
| `respondents` | Named parties and their representatives, e.g. `PULLMAN STATION LLC C/O BRETT SECHRIST` | Named-person text. It plays no part in the task and is not redistributed: this release publishes case outcomes, not a list of the people and firms charged. Excluding it is a publication decision, not a judgement that it is uninformative. |
| `address`, `street_number`, `street_name` | The property address as text | The location signal ships as the published `latitude`/`longitude`, and `street_direction`/`street_type` are already features; the address string restates them. |
| `nov_number` | The City's notice number for the charge | A per-notice publication identifier, like `id`. The case is the unit of this task, so an identifier at charge grain is not a feature; no claim is made about it as a predictor. |
| `location` | The source's point geometry | The same point the shipped `latitude`/`longitude` carry. |

Verified against the source's live schema (`data.cityofchicago.org`, resource `6br9-quuz`) on
2026-09-27; the code↔description ratio is the source's own aggregate, not a sample.

**All other source columns are absent by construction**, because the file is not a projection of
the source table: it is one row per case, aggregated from that case's charge rows. Charges other
than the lead charge are represented only by `charge_count` and `distinct_code_count`.

## Splits

Temporal, by `violation_date`, with no random component. **A case is placed by its earliest
recorded violation date, and the split is taken over cases, never over source rows** — the source
publishes one row per charge, so splitting the source rows would put charges of one case on both
sides of a boundary.

| split | file | predicate |
|---|---|---|
| train | `public/train.csv` | `violation_date < '2018-01-01'` |
| eval | `public/eval.csv` | `>= '2018-01-01'` and `< '2022-01-01'` |
| holdout | `private/holdout.csv` | `>= '2022-01-01'` and `< '2026-09-01'` |

| split | period | cases | Liable | positive rate |
|---|---|---|---|---|
| `public/train.csv` | before 2018-01-01 | 47,414 | 29,959 | 0.631860 |
| `public/eval.csv` | 2018-01-01 to 2022-01-01 | 3,436 | 3,077 | 0.895518 |
| `private/holdout.csv` | 2022-01-01 to 2026-09-01 | 2,913 | 2,715 | 0.932029 |
| **total** | | **53,763** | **35,751** | 0.664970 |

## Known data properties

- **The positive rate rises steeply over time** (0.632 → 0.896 → 0.932). This is a property of the
  City's docket, not of the split: `Not Liable` dispositions are concentrated in the earlier
  period. A model that learns "recent cases are liable more often" will score well on eval and
  holdout without learning anything about the charge. Read any eval AUC against the split's own
  baseline, not against 0.5.
- **The three periods are unequal in size and that is not adjusted.** eval and holdout are small
  relative to train because the earlier period is long (2008 onward) and the filtered population
  is thin in decisions. Nothing is reweighted or resampled.
- **Blank feature values are left as they are.** `ward` is blank in 153 rows, `street_type` in 613;
  the benchmark's `train.py` maps unseen categorical levels to NaN and does not impute.
- **`violation_code` is a string, not a number.** Codes such as `001002FR` and `0006014` exist, so
  leading zeros and suffixes are significant; it is treated as categorical.
- **No imputation, no synthesis, no recoding.** The only derived column is the target. The
  case-level reduction reads the case's own published charge rows and selects, as the lead charge,
  the earliest recorded violation, tie-broken deterministically by (violation date, violation code,
  row identifier) — see `code/build.py`.
- **The source is republished daily by the City.** This version is defined by the hashes in
  `MANIFEST.json` and the row counts recorded in `measurements.json`, not by the live endpoint.
