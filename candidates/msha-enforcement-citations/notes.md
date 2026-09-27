# msha-enforcement-citations

Record dated evidence, decisions, and failed approaches here.

Lead surfaced 2026-09-27 while looking for something better than `chicago-food-inspections` for a
multi-label task. Everything below was measured live from the publisher's own download, not
recalled. The probe scripts live beside this file and are re-runnable:

- `probe_violations.py` - grain, label space, density, co-occurrence (streamed from the zip).
- `probe_splits.py` - per-year counts and whether the proposed windows keep every label.

## Source identity

- Violations Data Set, Mine Safety and Health Administration (US Department of Labor).
  Download `https://arlweb.msha.gov/OpenGovernmentData/DataSets/Violations.zip`
  (120,736,998 bytes; `curl -sSL` took 4.3 s; single member `Violations.txt`, 1,442,221,050 bytes
  uncompressed, `|`-delimited with a header row). Updated every Friday.
- Definition file `https://arlweb.msha.gov/OpenGovernmentData/DataSets/Violations_Definition_File.txt`
  - 50 columns, each with a publisher-written description (the reason this source is usable).
- Linkable companions, keys documented in the same definition files:
  `Inspections.zip` (EVENT_NO - one row per inspection, join key to Violations),
  `Mines.zip` (MINE_ID - mine attributes), `AssessedViolations.zip`,
  `ContestedViolations.zip`, `CivilPenaltyDocketsDecisions.zip`.
- Publisher's own summary products to cross-check against: Mine Data Retrieval System (MDRS),
  the Significant-and-Substantial rate calculator and the Pattern-of-Violations calculator.

## Probes, with the commands that produced them

`python3 probe_violations.py Violations.zip --top 30` (65 s, streamed from the zip; nothing
extracted to disk):

- rows (citations) **3,103,397**; distinct EVENT_NO (inspections) **538,068**; distinct MINE_ID
  **31,444**
- rows with an empty PART_SECTION: **33,782 (1.09%)**
- distinct PART_SECTION labels **5,934**; coal 1,614,873 / metal-nonmetal 1,488,524 citations
- labels per inspection: mean **5.79**, median 2, max 694 (event numbers also cover mine-wide
  audits, so the tail is real and has to be handled, not trimmed silently)
- labels in >= 1% of inspections: **104**; >= 0.5%: **183**; >= 0.1%: **553**
- top sections cited: 75.400 (147,951), 56.14107(a) (120,576), 56.14100(b) (71,917),
  56.12004 (70,111), 75.370(a)(1) (67,025), 75.503 (64,834), 56.14132(a) (57,367)
- co-occurrence is strong and structured, e.g. (75.400, 75.503) 18,490 inspections,
  (75.370(a)(1), 75.400) 17,361, (56.14100(b), 56.14107(a)) 15,169,
  (56.12004, 56.14107(a)) 14,845, (75.202(a), 75.400) 14,100

`python3 probe_splits.py Violations.zip` (31 s):

| window | years | inspections | citations | floor labels present |
| --- | --- | --- | --- | --- |
| train | 2001-2020 | 415,088 | 2,459,741 | 104/104 |
| eval | 2021-2023 | 49,233 | 255,952 | 104/104 |
| holdout | 2024-2025 | 33,576 | 175,151 | 104/104 |

The same run gives the per-year census (2000: 19,640 inspections; peak 2010: 24,951; 2020: 16,508;
2024: 17,212; 2026 partial to date: 12,446). **Note the trap:** the definition file's date range
and the raw `INSPECTION_BEGIN_DT` are `mm/dd/yyyy`, so a string sort of that column is not
chronological - an earlier probe reported the range as ending 12/31/2025 for that reason. The year
census is the authority: the file covers calendar 2000 through 2026-to-date.

## What the label is

`PART_SECTION` is the 30 CFR part/section/suffix cited, in the publisher's format `PPSSSSSXXXX`
(four-digit sections expanded to five with a leading zero). One inspection (EVENT_NO) carries many
citations, therefore many sections - the multi-label target is the **set of sections cited at one
inspection**, and `PART_SECTION` plus every violation-level attribute is excluded from the shipped
features. The raw label space is 5,934; a construction has to declare its label floor (104 at 1%,
183 at 0.5%) and that declaration is part of the contribution, not a detail.

## Prediction instant and features

Instant: **the start of the inspection** (`INSPECTION_BEGIN_DT`, present on every violation row and
on the Inspections table). Everything the inspector learns during the visit is off-limits.

Available before that instant and documented by the publisher:

- from Mines: `COAL_METAL_IND`, `CURRENT_MINE_TYPE`, `CURRENT_MINE_STATUS`, `STATE`,
  `FIPS_CNTY_CD`, `COMPANY_TYPE`, `PRIMARY_SIC`/`PRIMARY_CANVASS` (commodity / industry group),
  `CURRENT_103I` (the five/ten/fifteen-day inspection classification), `NO_EMPLOYEES`,
  `DAYS_PER_WEEK`, `HOURS_PER_SHIFT`, `PROD_SHIFTS_PER_DAY`, `PORTABLE_OPERATION`, coordinates;
- the inspection's own trigger, known when it opens: `ACTIVITY_CODE`/`ACTIVITY` (regular,
  complaint, spot...), `PROGRAM_AREA`, `INSPECT_OFFICE_CD`;
- the mine's **own history** from earlier inspections: its previous inspections and their cited
  sections (label history), which is exactly the structure a pre-inspection task should use.

Post-hoc, therefore excluded - and each of these would leak if it shipped: `SIG_SUB`, `NEGLIGENCE`,
`LIKELIHOOD`, `INJ_ILLNESS`, `NO_AFFECTED`, `ENFORCEMENT_AREA`, `SPECIAL_ASSESS`,
`SECTION_OF_ACT`/`_1`/`_2`, `CIT_ORD_SAFE`, `VIOLATION_NO`, `PART_SECTION`, every date after the
begin date (`VIOLATION_ISSUE_DT`, `ORIG_TERM_DUE_DT`, `LATEST_TERM_DUE_DT`, `TERMINATION_DT`,
`VACATE_DT`, `FINAL_ORDER_ISSUE_DT`), the money fields (`PROPOSED_PENALTY`, `AMOUNT_DUE`,
`AMOUNT_PAID`), the docket/contest fields, and the inspection's end-of-visit counts
(`TOTAL_ON_SITE_HOURS`, `TOTAL_INSP_HOURS`, `SAMPLE_CNT_*`, the area-with-`Y` flags). Whether
`NBR_INSPECTORS` or `ACTIVE_SECTIONS` are known at the instant the inspection opens or only as it
proceeds must be decided at construction; the default is to exclude them.

## Licence

MSHA publishes no licence statement on the data-set pages, and the data.gov catalogue entry carries
`accessLevel: public` with `rights: "true"` rather than named terms. The statutory basis (a work of
the US federal government) is not a licence we can quote, so this is contract #1 unresolved:
**a decision to escalate to the operator before construction**, not an assumption.

There is supporting precedent, and it is only precedent: `emperor-mew/msha-violations` (HF, 2026-05)
dedicates its derived MSHA data to CC0 and asserts the federal works are public domain, and
`FastDOLz/msha-mine-safety-violations-by-operator` (HF + Zenodo, 2026-06) ships a CC-BY-4.0 mirror of
the same source. Two third parties redistributing is evidence a reviewer can weigh; it is not a
grant, so the decision is still the operator's. Compare `chicago-food-inspections`, where the portal
terms are explicit but restrictive.

## Novelty (searched 2026-09-27)

Nothing ML-ready ships this task. What exists is adjacent:

- MSHA's own products: the raw tables, MDRS, dashboards, and the S&S-rate / Pattern-of-Violations
  calculators - all *descriptive*; none is a prediction task with splits.
- Mine-safety ML literature predicts **accidents, injuries, or violation counts**, or **which mines
  to inspect** (binary targeting): "Temporal Machine Learning for Predicting Accidents and
  Violations at Surface Coal Mines" (Univ. of Kentucky thesis), "Machine Learning Classification
  Models for More Effective Mine Safety Inspections", "Identifying hazardous patterns in MSHA data
  using random forests" (Marshall), and the ASCE-ASME J. Risk study on enforcement actions and
  future accidents.
- OSHA-side work is the same shape (which establishments to inspect), not the cited-standard set.

So the verdict recorded in `record.json` is `differentiated`: ours is the multi-label formulation
(set of 30 CFR sections per inspection, label floor declared), the pre-inspection-only feature set
drawn from the Mines table plus the mine's own citation history, and the temporal windows. Theirs is
the raw data, the descriptive calculators, and the accident/count/targeting literature.

### What public catalogues actually hold for MSHA (checked 2026-09-27, by name)

The catalogue search returned two Hugging Face artifacts. Both were opened and read, and neither is
this task:

- `emperor-mew/msha-violations` (created 2026-05-17, 12 downloads, CC0-1.0 tag) is a **card with no
  data files** - it points at a live REST API (`api.ai-analytics.org/api/v1/msha/violations/recent`)
  and a JSON-LD catalogue. It describes citation-level records with S&S flags; it ships no table, no
  splits, no task. Note it claims CC0 for its derived data and cites US federal public-domain
  status - a third-party precedent for the licence question below, not a permission.
- `FastDOLz/msha-mine-safety-violations-by-operator` (2026-06-06, 41 downloads, CC-BY-4.0, mirrored
  on Zenodo, DOI 10.5281/zenodo.20572372) is **operator-level aggregation**: 40,720 operators,
  3,076,282 violations rolled up to the cited entity with penalty totals and cross-agency (OSHA,
  WHD) indicators. A different grain and a descriptive product; its counts also restate the raw
  file (3.08 M violations vs 3.10 M rows here).

So the raw file is mirrored in places, and one mirror is API-shaped - but no package ships the
inspection-level multi-label set of cited sections with a declared prediction instant and splits.
That is what the verdict `differentiated` rests on, and it is now checkable by name.

## Runner-up measured the same day: CMS nursing-home health deficiencies

`https://data.cms.gov/provider-data/api/1/datastore/query/r5ix-sfxw/0` (provider-data datastore,
anonymous, no key). Bounded sample probe (`cms/probe_cms.py`, 12 pages x 1,000 rows spread across
the table, 31 s, three columns requested): **419,479 deficiency rows**; in the 12,000-row sample
2,783 distinct surveys (CCN + survey_date + type), **188 distinct F-tag numbers**, tags per survey
mean **4.31**, median 2, p90 10, max 46; **88 tags at >= 1%** of surveys; top tags 0880 (723), 0812
(621), 0689 (569), 0684 (450), 0656 (385). Every sampled row is `survey_type = Health`, one row per
(survey x deficiency), so the same multi-label shape holds and the prediction instant - the start of
a scheduled health recertification survey - is defensible.

Why MSHA still leads: 538,068 inspections and 3.10 M citations over 26 years against roughly 97,000
surveys here; 104 labels at a 1% floor against 88, with a documented 50-column wire format and the
Mines attribute table to draw features from; a coal / metal-non-metal cut that a mirror dataset
already treats as a first-class split; and a single weekly file with no paging. CMS stays a
perfectly good second lead if the MSHA licence decision goes the wrong way - it is also a
government-published file, so the same licence question applies.

## Comparison with chicago-food-inspections (why this is the better lead)

- licence: MSHA is federal public-domain-by-statute but silent on terms; Chicago is explicit but
  restrictive. Neither is clean - both need a recorded decision. Chicago has a quotable document.
- scale: 538,068 inspections / 3.10 M citations / 31,444 mines over 26 years, against 316,205
  inspections over 16 years.
- label space: 5,934 raw sections (104 at >= 1%, 183 at >= 0.5%) against 61 codes. Larger, and
  hierarchical in a way that makes a declared floor meaningful.
- feature surface: 50 documented violation columns plus fully documented Mines and Inspections
  tables, against 21 columns on a single table.
- novelty: the City of Chicago already **deployed a model on the food-inspection table** (binary
  critical-violation targeting), and mirrors of that table are everywhere; MSHA's citation set has
  no such shipped precedent.
- cost: one 120 MB weekly file (download 4.3 s; streaming probes 65 s and 31 s; no extraction) -
  simpler and cheaper than paged API reads, and the same file is also served through the DOL open
  data API if a request-based fetch is preferred.

## Cost, measured on this machine class

| step | result |
| --- | --- |
| download | 120,736,998 bytes in 4.3 s (`curl -sSL`) |
| member | `Violations.txt`, 1,442,221,050 bytes uncompressed |
| grain/label probe | 65 s, streamed, 0 bytes written outside the zip |
| split probe | 31 s, streamed |
| disk on the coordinator afterwards | zip deleted; nothing extracted |

This is a bounded probe, not a collected dataset: the file was streamed from the zip for
measurement and removed. Construction belongs on a worker.

## Open decisions before construction

1. **Licence** - escalate; the source states no terms.
2. **Label floor** - 104 (>= 1%) or 183 (>= 0.5%); both keep every proposed window.
3. **Event tail** - how to treat mine-wide audit events (up to 694 citations): keep, cap, or a
   separate config.
4. **Coal vs metal/non-metal** - a natural pair of configs (1,614,873 and 1,488,524 citations).
