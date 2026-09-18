# Austin 911 response time — prediction dataset

A leakage-checked, time-split prediction dataset built from the City of Austin's public
`APD 911 Calls for Service 2023-2026` records. The task is to predict, **at the moment a call
is dispatched**, whether the first police unit will reach the caller later than a fixed
threshold.

- **Version:** `2026.09` (artifact version `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`)
- **Rows:** 1,049,636 across three time-separated splits
- **Licence of the data:** Public Domain (City of Austin)
- **Status:** prepared for review. Not published, and no agent/harness comparison has been run.

This dataset is one product of the Dataset Factory pipeline. The construction code, the
qualification gate that gated it and the full record of what was measured live in the private
factory repository; **nothing in this repository requires that repository to use the dataset.**

---

## Task

**Prediction question.** For a dispatched Austin police 911 call, will a patrol unit reach the
caller more than 20 minutes after the call was dispatched?

**Unit of observation.** One row is one dispatched call record from the source catalogue.

**Target.** `late` — a 0/1 column derived from the portal's own `response_time` field, which is
an integer number of seconds:

```
late = 1  if  response_time > 1200     # 1200 s = 20 minutes
```

The threshold is **fixed at 20 minutes and frozen before any row was scored**. It was chosen by
binary search on the *training window only* so that the training positive rate sits just at or
above 0.40 — 0.4008 measured, against 0.3938 over the full series. It is a physically
meaningful cut (20 minutes is a long wait for an emergency response), not a quantile that moves
with the data.

**Prediction time.** The moment the 911 call-taker's dispatch screen opens, recorded as
`response_datetime`. Everything a model may use must be known at that instant. In particular
`response_time` itself — the source of the label — is **never shipped in any split file**.

**Population and dates.** All rows the catalogue returns for the dataset's own coverage,
2023-01-01 through 2026-09-18 (the extraction date). Rows whose `response_time` is null are
dropped rather than imputed.

**What the outcome means in practice.** A positive row is a call where the caller waited more
than 20 minutes for a unit to arrive. The dataset is useful for asking which *dispatch-time*
signal — call type, sector, hour of day, free-text problem description — carries information
about that wait. It is not a model of demand, of unit availability, or of whether the response
was appropriate.

## Source and permissions

| | |
|---|---|
| Source | Austin Open Data — *APD 911 Calls for Service 2023-2026* |
| Landing page | https://datahub.austintexas.gov/d/e687-fx2y |
| API | https://datahub.austintexas.gov/resource/e687-fx2y.json |
| Dataset id | `e687-fx2y` |
| Owner | City of Austin (Austin Police Department) |
| Access | anonymous Socrata API, no key, offset-paginated; last verified live 2026-09-18 |
| Accessed | 2026-09-18 |
| **Data licence** | **Public Domain** |
| Construction code | see the licence section below |

**Licence evidence, quoted from the source rather than asserted:**

- The Socrata catalogue entry for `e687-fx2y` reports `license = "Public Domain"`
  (catalogue API v1, queried 2026-09-18).
- Re-confirmed the same day directly from
  `GET https://datahub.austintexas.gov/api/views/e687-fx2y.json`, which returns
  `"license": {"name": "Public Domain"}` for the view named *APD 911 Calls for Service
  2023-2026*.

Redistribution of the source data is therefore permitted. Attribution to the City of Austin is
given here regardless.

**Transformations applied.** Row selection (the catalogue's full coverage), a derived binary
label, and temporal partition into three splits. No row is edited, imputed, reweighted or
synthesised, and no source field is recoded except the label. Column exclusions are listed in
`DATA_DICTIONARY.md` and are additions to the *feature* set, not deletions from the source.

## Download this version

Release assets are the five files that make up the qualified artifact, in the runner's layout:

```
task/meta.json
task/public/train.csv
task/public/eval.csv
task/private/holdout.csv
task/quality.json
```

`MANIFEST.json` records each file's size and SHA-256, the artifact version, and the commit that
produced it. `SHA256SUMS` is the same information in `sha256sum` format.

**Verify before use:**

```bash
sha256sum -c SHA256SUMS
```

**Row counts and positive rates, measured:**

| split | period | rows | positives | positive rate |
|---|---|---|---|---|
| `public/train.csv` | before 2025-01-01 | 572,180 | 231,025 | 0.403763 |
| `public/eval.csv` | 2025 | 285,665 | 109,860 | 0.384576 |
| `private/holdout.csv` | 2026-01-01 onward | 191,791 | 72,450 | 0.377755 |
| **total** | | **1,049,636** | | |

The split is **temporal and never random**: a model is trained on the past, selected on 2025,
and scored on 2026 onward. Row counts equal the source's per-year counts exactly, so no row was
lost or duplicated in extraction.

`meta.json` carries the machine-readable task description (`target`, `positive_label`,
`id_columns`, `columns`, `rows`, `positive_rate`, `split`, `description`) and the prediction
time and threshold. `quality.json` is the descriptor the qualification gate validated the rows
against, including the excluded post-hoc columns and the measured source properties.

**The holdout may be downloaded, but must stay out of an evaluated agent's workspace during a
benchmark run.** It is labelled, so exposing it to an agent being scored would defeat the
evaluation. Its presence here is for reproducibility and independent scoring, not for training.

Categorical treatment: object-dtype columns are categorical. `train.py` in the benchmark
treats string columns with more than 1000 levels as too high-cardinality for its baseline and
drops them, so `geoid` and `blkgpnm` are dropped by that baseline even though they ship in the
data. That is the runner's documented behaviour, not a property of the dataset.

## Reproduce and evaluate

The dataset is reproducible **without the private factory repository**: `build.py` is
stdlib-only Python, fetches the public API anonymously, and is pinned to the commit that
produced this artifact.

```bash
# 1. fetch the construction script at the pinned revision
#    repository: earino/dataset-factory (private); commit pin:
#    06d7002bc01933e4c094bbe84e4d9899572a893f
# 2. run it, pinning the recorded build timestamp so meta.json reproduces exactly
python3 build.py --out /tmp/extract --built-at 2026-09-18T19:36:55.770697+00:00
# 3. verify
sha256sum -c SHA256SUMS
```

**Measured resource needs.** The full build plus its qualification gate ran on a 2-vCPU /
2 GB worker and took **353.7 s** wall clock, using about 136 MB of output. The extraction makes
roughly 53 paginated API requests of 20,000 rows and needs no credential.

**Dependency versions.** The construction script uses the Python standard library only
(Python 3.13). The baseline uses the benchmark's own ranges: `pandas>=2.2,<3`, `numpy>=1.26`,
`xgboost>=3.0`, `scikit-learn>=1.5`. The exact versions resolved in the recorded run are in
`REPRODUCE.md`.

**Checks run before this version was accepted.** The `dataset-qualification` gate
(version 1.3.0) ran on the worker over the full artifact and **passed all 33 checks**, covering:

- *Leakage* — every shipped column declared; no answer source or post-hoc column shipped; no
  single shipped column separates the classes on its own; high-cardinality columns declared.
- *Prediction timing* — the prediction instant declared; no feature documented as post-hoc; the
  label source is not a feature; every feature documented as available at prediction time.
- *Splits* — files present and non-empty; both classes in eval and holdout; declared positive
  counts recomputed from the rows; clustered event counts recomputed; **no identifier spans two
  splits**; repeated identifiers within a split measured against the declared count; rates not
  uniform; actual row ranges disjoint and inside the declared windows; enough independent
  positive events to score.
- *Runner compatibility* — the holdout is private and train/eval public; `meta.json` carries
  every key the runner reads and agrees with the files; identifiers are not also features.

**Duplicate, boundary and missing-value findings.** These are measured and stated rather than
hidden:

- `incident_number` is **not unique in the source**: 1,049,636 rows carry 1,049,612 distinct
  values, so 24 incident numbers appear twice. All 24 pairs fall inside a single split, so
  nothing spans a boundary. The 24 are declared (`expected_duplicate_ids`).
- **4 of those 24 pairs carry different labels**, because they are *different events that
  happened to share a number* — e.g. `230990471` is an "Alarms"/Baker call at 07:33 with a
  618-second response **and** an "Other"/Frank call at 16:38 with a 6,164-second response. This
  is recorded as a source property, and the descriptor deliberately makes no claim that the
  identifier names one entity. Impact: 4 rows of 1,049,636.
- Rows with a null `response_time` cannot be labelled and are dropped; the count is recorded in
  each split's entry in the build manifest.
- Paging uses a **total** order (`incident_number,:id`), because the first version ordered by
  `incident_number` alone and the order among tied rows is not guaranteed stable across
  requests, which can repeat or skip rows under offset pagination.

**Measured baselines.** Two, and they are floors rather than headline results:

| baseline | eval AUC | what it is |
|---|---|---|
| single-feature (`initial_problem_category`) | **0.627031** | shipped in the extract's `manifest.json` |
| the benchmark's own `train.py`, unmodified | see `REPRODUCE.md` | one run through the runner's training/validation contract |

**No agent or harness comparison has been run on this dataset.** That is outside this
publication milestone, so no statement here compares harnesses, and none should be inferred.

## Findings and limitations

**What the task measures.** How much information about a long wait is available at dispatch
time, and how much of the apparent difficulty is structural (call type, geography, hour) versus
irreducible.

**Known weaknesses, stated plainly.**

- The label comes from the portal's `response_time`, which **begins when the call was answered**
  and therefore starts slightly *before* `response_datetime` — measured median offset −58 s,
  range −561 s to +6,287 s, with 48 of 2,000 sampled rows within one second. The window between
  the prediction instant and the start of the measured clock is small but not exactly zero.
- The source is a live catalogue that the City updates; a rebuild after 2026-09-18 will not
  reproduce this artifact byte-for-byte, because later rows and revisions enter the series. The
  artifact hashes, not the source URL, define this version.
- Class balance is a consequence of the physical threshold (~38–40% positive), not a target.
  The threshold was deliberately **not** tuned to balance classes.
- 4 rows carry a contradictory label for a repeated incident number. This is visible in the
  gate report and is immaterial at 0.0004% of rows, but it is real.
- `priority_level` and `mental_health_flag` are excluded as post-hoc even though they look
  useful: both are determined after the prediction instant, and a model allowed to see them
  would report performance it could not achieve in deployment.

**Attribution and citation.** Data: City of Austin, *APD 911 Calls for Service 2023-2026*,
Austin Open Data, Public Domain, accessed 2026-09-18.

**Versioning and corrections.** Releases are versioned `YYYY.MM`. A corrected rebuild gets a new
version and a changelog entry; previous versions and their hashes are kept rather than
overwritten, so a published result always names the artifact version it used.
