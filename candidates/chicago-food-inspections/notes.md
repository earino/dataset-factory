# chicago-food-inspections

Lead surfaced 2026-09-27 while answering an operator question about multi-label sources. Everything
below was measured live and anonymously against the Socrata API (no key, `User-Agent: scout-verify/1.0`).
Nothing was constructed; this record is the feasibility profile, not a build.

## Source

| | |
|---|---|
| Name | Food Inspections (City of Chicago, Dept. of Public Health) |
| Dataset | `https://data.cityofchicago.org/Health-Human-Services/Food-Inspections/4ijn-s7e5` |
| API | `https://data.cityofchicago.org/resource/4ijn-s7e5.json` (anonymous, no key required) |
| Metadata | `https://data.cityofchicago.org/api/views/4ijn-s7e5.json` - 21 columns, `createdAt` 1312839871 (2011-08-09), `rowsUpdatedAt` 1790500309 |
| Licence field | `{"name": "See Terms of Use"}` - no SPDX designation; attribution "City of Chicago" |
| Terms | Same portal-terms decision as `chicago-doah-adjudication` (`candidates/chicago-doah-adjudication/license.json`, "LicenseRef-CityOfChicago-DataTermsOfUse"). Not CC0-able; no standard open licence may be claimed. |

## Measured evidence

| Probe (anonymous SoQL) | Result |
|---|---|
| `count(*)` | **316,205** rows |
| `count(distinct inspection_id)` | **316,205** - one row per inspection, clean grain, no fan-out |
| `min(inspection_date), max(inspection_date)` | 2010-01-04 to 2026-09-25 (16.7 years, updated weekly) |
| `count(*)` where `violations IS NOT NULL` | 227,036 |
| `results` distribution | Pass 163,683 / Fail 60,869 / Pass w/ Conditions 46,900 / Out of Business 25,886 / No Entry 14,167 / Not Ready 4,604 / Business Not Located 96 |
| `violations IS NOT NULL` by `results` | Pass 122,961 / Fail 57,221 / Pass w/ Conditions 45,951 / No Entry 777 / Not Ready 82 / Out of Business 44 |
| **modelling pool** | result in (Pass, Fail, Pass w/ Conditions) **and** `violations IS NOT NULL` = **226,133** rows |
| `risk` distribution | Risk 1 (High) 235,336 / Risk 2 (Medium) 56,136 / Risk 3 (Low) 24,561 / All 85 |
| `inspection_type` | 40 distinct; Canvass 163,270, License 42,427, Canvass Re-Inspection 35,226, Complaint 29,961, License Re-Inspection 12,829, Complaint Re-Inspection 12,570, Short Form Complaint 9,305 |
| `facility_type` | 40 distinct; Restaurant 214,562, Grocery Store 37,913, School 19,741, Children's Services Facility 7,784, Bakery 4,540 |
| `count(distinct license_)` | 49,145 - about 6.4 inspections per licence, so a facility panel with prior history exists |
| rows with `inspection_date >= '2016-01-01'` / `>= '2021-01-01'` | 197,126 / 101,354 |

### The label: violation codes, parsed from a text blob

`violations` is a single text blob per inspection, one entry per finding:
`"55. PHYSICAL FACILITIES INSTALLED, MAINTAINED & CLEAN - Comments: NOTED DAMAGED WALL..."`. Parsed with
`(?:^|\|)\s*(\d{1,3})\.\s*([^-|]*?)(?:\s*-\s*Comments:|\s*$)`.

- A 40,000-row scan (6 pages `inspection_date DESC` + 2 pages `ASC`, 5,000 per page) yields **61 distinct codes**, 1-70 with gaps.
- Descriptions are canonical: 33 of 61 codes render one way across all 16.7 years; **28 of 61 have more than one rendering** (wording was revised over time, e.g. code 18's rodent-proofing text). Label by **code**, never by description string.
- Density (15,000-row recent sample, `inspection_date DESC`): mean **3.08** codes per inspection, median 2, max 19; **32 codes in >=1% of rows**, 43 in >=0.1%.
- Heaviest codes in the 40k scan: 55 physical facilities (24,342), 38 insects/rodents/animals (12,168), 51 plumbing/backflow (7,447), 10 handwashing sinks (7,641), 56 ventilation & lighting (6,804), 41 wiping cloths (4,837), 58 allergen training (4,664), 37 labelling (4,451), 39 contamination prevention (4,137), 53 toilet facilities (4,114).
- Strong co-occurrence, not independent labels: top pairs in the 15k sample (55,38) 2,350, (51,55) 2,151, (55,56) 2,026, (10,55) 1,688, (55,58) 1,400.
- Density tracks the outcome, so the set carries information a binary outcome does not: mean codes per inspection Pass **2.05**, Pass w/ Conditions **3.70**, Fail **4.85**.

### Two data properties a construction must respect

1. **Comment text is post-prediction.** 14,997 of 15,000 recent blobs carry `- Comments: <narrative>`, written by the inspector during the visit. The blob is the label source and must never ship as a feature.
2. **Non-outcome rows can still carry a blob** (No Entry 777, Not Ready 82, Out of Business 44 - under 0.5% of blob rows). These look like text carried from an earlier visit and must be excluded by `results`, not merely by `violations IS NOT NULL`.

## Prediction framing

- **Prediction instant:** the moment the inspection is opened, before any observation. `inspection_date` is known when a canvass is scheduled or a complaint triggers a visit.
- **Target:** the set of codes in `violations` for that inspection (multi-label over 61 codes).
- **Intended features (all documented by the publisher and available before the visit):** `facility_type`, `risk`, geography (`zip`, `latitude`/`longitude`, ward / community area / census tract computed regions), `inspection_type`, the calendar position of `inspection_date`, and the establishment's **prior** inspections under the same `license_` (their codes, results and dates) - the row's own `violations`, `results` and comment text are excluded.
- **Split:** temporal by `inspection_date`, no random component; the 2021+ window alone holds 101,354 inspections.

## Prior art (searched 2026-09-27)

- **City of Chicago's own `Chicago/food-inspections-evaluation`** - CDPH's deployed forecasting model (2015, R), predicting a **binary** "at least one critical violation" to prioritise canvass scheduling, plus a retrospective evaluation of it. The publisher ships a *different* task; it is the closest thing to a mirror of a naive framing of this source.
- arXiv **1910.04906**, "Hindsight Analysis of the Chicago Food Inspection Forecasting Model" (2019) - evaluates that binary model.
- Kaggle and Socrata mirrors of this same table; a Tennessee restaurant-inspection-score study (PMC3323064); an EJAI paper correlating violations with customer reviews.
- No published ML-ready version of the **multi-label** task - predict the *set* of violation codes at inspection time - was found. That is a search result, not a proof: `scripts/check-novelty.py` must be run with an explicit verdict before this candidate can be promoted to `ready`.

## Superseded as the lead (2026-09-27, same day)

While looking for something better, `candidates/msha-enforcement-citations/` was measured and opened
(`status=ready`). It leads on every axis that matters here - 538,068 inspections and 3.10 M citations
over 26 years against 316,205 rows over 16, 104 sections at a 1% floor against 61 codes, a documented
50-column wire format plus companion tables against 21 columns on one table, and no publisher-deployed
model on the task (CDPH already shipped a binary critical-violation model on this table). The
comparison is in that candidate's notes. **This source stays a valid fallback, not the priority**:
nothing here is dropped, and if the MSHA licence decision goes the wrong way this is the next lead,
with the three open questions below still to clear.

## 2026-09-28 - the three open gates cleared; promoted to `ready`

The record's three open questions are answered. Every claim below has the command that produced it.

### 1. Licence decision recorded against this source id

`candidates/chicago-food-inspections/license.json` (decided 2026-09-28). The City of Chicago
Data Terms of Use posture the operator accepted on 2026-09-26 for `chicago-doah-adjudication`
applies to this source id `4ijn-s7e5`: same publisher, same terms instrument (Socrata
licenseId `SEE_TERMS_OF_USE`), same no-standard-licence posture. Recorded explicitly against
this id rather than inherited silently, as the record's open question 1 required:
`LicenseRef-CityOfChicago-DataTermsOfUse` for the compilation, MIT for our code, the mandatory
derivative disclaimer verbatim, no irrevocable-redistribution claim. The decision states that
if the operator widens or narrows the DOAH decision, this one follows it.

### 2. Novelty verdict recorded (differentiated)

```
python3 scripts/check-novelty.py chicago-food-inspections \
  --query "chicago food inspections" --query "food inspection violations" \
  --query "violation code prediction" --query "multi-label food safety" \
  --query "restaurant inspection forecast" --verdict differentiated ... (recorded_at 2026-09-28T08:02:56+00:00)
```

Hugging Face: 0 hits on all five queries. arXiv surfaces the closest prior art itself -
arXiv 1910.04906, "Hindsight Analysis of the Chicago Food Inspection Forecasting Model" -
which evaluates CDPH's deployed **binary** critical-violation model; "Predicting health
inspection results from online restaurant reviews" is review-text prediction, a different
task. Zenodo's keyword search is noise at these queries (its top hits are unrelated records).
The verdict: `ours` is the multi-label formulation (one row per inspection, target = the *set*
of 61 violation codes, prediction instant at the inspection's opening, prior-history features
under `license_`, temporal windows); `theirs` is the raw table, its mirrors, and the publisher's
own binary model. No ML-ready multi-label package exists. Full evidence in
`record.json novelty_check`.

### 3. Extraction cost measured (probe_cost.py, run on the coordinator)

```
python3 candidates/chicago-food-inspections/probe_cost.py --rows 20000 --page-size 5000
```

- total rows recounted: **316,205** (unchanged from 2026-09-27)
- **measured**: 20,000 rows in 4 pages, **5 requests**, **28,948,432 bytes**, **23.2 s** wall
  clock including the count query; mean **1,447 bytes/row** (the blob dominates)
- **estimate, labelled** (arithmetic in the probe output): full pull ~64 pages + 1 count
  query, ~458 MB, ~366 s on the coordinator class. The full pull runs on the worker.
- Order key `inspection_id` is unique per row (316,205 distinct in 316,205 rows), so it is its
  own tiebreaker - offset paging is stable, per the discovery skill's paging rule.

### 4. Split capacity measured (probe_splits.py, new in this candidate)

```
python3 candidates/chicago-food-inspections/probe_splits.py --json
```

Blob format verified on live rows first: entries are separated by `|` followed by whitespace
and the code (`'30. FOOD...| 32. ...| 33. ...'`), so the regex
`(?:^|\|)\s*(\d{1,3})\.` matches both a leading code and a mid-blob code.

Modelling pool (results in Pass/Fail/Pass w/ Conditions AND violations IS NOT NULL):
**226,133 rows**, census by year 2010 12,469 ... 2016 17,192 ... 2021 11,013 ... 2025 12,963,
2026 partial 7,900.

| window | pool rows | distinct licences | inspections/licence | floor codes present |
|---|---|---|---|---|
| train 2010-01-01..2020-12-31 | 156,853 | 28,930 | 5.42 | 37/37 |
| eval 2021-01-01..2023-12-31 | 35,360 | 12,992 | 2.72 | 37/37 |
| holdout 2024-01-01..2026-09-30 | 33,920 | 12,953 | 2.62 | 37/37 |

Floor re-derived from a fresh 15,000-row recent pool scan: **59 distinct codes, 37 at >=1%**
(the earlier 40,000-row full-range scan found 61; the recent-only scan sees 59 - era
variation, which is why the floor is re-derived at construction time). Per-window presence was
screened with server-side blob matches; construction parses codes exactly.

Probe cost: 122 requests, 185.1 s. A first version of the licence count trusted Socrata's
default cap on grouped queries and reported exactly 1,000 licences in every window - a
measurement artefact, caught and fixed by paging the grouped query explicitly (the corrected
counts above). Recorded here because it is exactly the failure mode the skill warns about: a
uniform number across windows read as a finding.

All four discovery contracts now hold with recorded evidence: redistribution (licence decided),
prediction timing (instant = inspection opening; blob/results/comments excluded), target
(parsable from the blob, label source excludable), split capacity (three disjoint windows,
both classes of the multi-label space present in all three, thousands of independent
licence-entities per window). Novelty verdict `differentiated` recorded. The candidate is
`ready`; construction is the next step, and its open design question (how a 37-target
multi-label task ships through a one-target runner contract) is recorded in `next_action`.
