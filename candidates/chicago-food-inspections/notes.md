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

## Open questions before construction

1. **Licence reuse.** The portal terms are already decided for DOAH, but redistribution of this table needs the decision recorded against *this* source id, not inherited silently.
2. **Novelty verdict.** Run `scripts/check-novelty.py` and state `ours` against the CDPH binary model.
3. **Extraction cost.** Not yet measured: requests, bytes and wall-clock for a full 316,205-row pull on the worker class. The blob column dominates size and no estimate is recorded here.
