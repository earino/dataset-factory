---
license: cc0-1.0
language:
  - en
pretty_name: MSHA Enforcement Citations
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-classification
tags:
  - tabular
  - mining
  - safety
  - regulation
  - time-series
  - temporal-split
  - multi-label
configs:
{CONFIGS_BLOCK}
---

# MSHA Enforcement Citations ({RELEASE_TAG})

**Status: {STATUS_LINE}**

Will a US mine safety inspection cite a given **30 CFR section**? One binary task instance per
section, {N_CONFIGS} of them, over the same {ROWS_TOTAL} pooled inspections and the same
time-ordered splits. Every instance carries 25 columns: an event id, the mine and inspection
attributes recorded before or at the visit, five prior-behaviour features from that mine's
strictly-earlier inspections, a per-section persistence feature, and the label.

The source is the Mine Safety and Health Administration's published enforcement record: violations,
inspections and mines, 2000 onward, covering coal and metal/non-metal operations. The task asks what
an inspector was about to find, using only what was knowable when the visit began.

## The task

For config `sec_56_12004`, the target is "this inspection will cite 30 CFR 56.12004". The label is
`1` when the inspection's violation rows include that exact `PART_SECTION` value, `0` otherwise. The
prediction instant is the inspection's `INSPECTION_BEGIN_DT`; nothing recorded after the visit
begins is a feature.

Rows and splits are identical in every config, by design — the configs are alternative binary
targets over one panel, not different populations:

- **train** 2001–2020 — 415,088 inspections
- **eval** 2021–2023 — 49,233 inspections
- **holdout** 2024–2025 — 33,576 inspections

**Rows:** {ROWS_TOTAL} inspections. Total across the three splits; every config carries the same rows. Split boundaries are calendar dates, so the eval and holdout windows are
later in time than training; no inspection appears in more than one split.

Each config also ships `meta.json` (feature list, label definition, provenance, split windows) and
`quality.json` (per-split missingness, cardinality and prevalence). The extract root carries
`labels.csv`: one row per pooled inspection, one column per shipped section, so the joint
multi-label problem can be reconstructed from the same bytes.

## Choosing a config

Each config is a complete, independently scoreable binary task with its own train/eval/holdout
files. `sec_56_12004` is the calibrated reference point: the shipped baseline scores **0.8036** eval
AUC on it. Prevalence varies by section and by window (0.0886 / 0.1063 / 0.0996 on the reference
config), so compare a model across configs by AUC, not accuracy.

## Baseline

One baseline was measured on `sec_56_12004` through the runner's own training and validation
contract, on the exact bytes in this release (fetched from staging, not rebuilt):

- eval AUC **0.8036**, identical from the training path and an independent validation re-run;
  train AUC 0.8036; `CONTRACT OK`
- persistence reference — the same model using only `prev_target_cited` — **0.5831**, so the
  24-feature model clears the section's own persistence by **0.2205**

Scope of these numbers: one baseline through the runner's contract. No agent or harness comparison
was run and none is implied.

## Loading

{LOADING_NOTE}

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", "sec_56_12004", revision="{RELEASE_TAG}"{TOKEN_ARG})
# every config is loaded the same way; the config must be named
```

The GitHub counterpart carries the identical files and digests:
{GITHUB_REPOSITORY}, with `MANIFEST.json`, `SHA256SUMS` and `get_dataset.py`.

## Provenance and licence

Source data: MSHA, US Department of Labor — public domain by statute (17 USC 105); the publisher
states no terms. {SOURCE_ATTRIBUTION}

Our contribution — row selection, the derived section targets, the declared prediction instant,
the temporal partitions, the features and this packaging — is dedicated to the public domain
under **{DATA_LICENSE}**. Code is **{CODE_LICENSE}**. The dedication covers our contribution only
and does not relicense the source rows.

## Limitations

- The label is the set of sections the inspector cited, which is an enforcement outcome, not an
  underlying hazard measurement. Mines with more inspections generate more citations.
- Prior-behaviour features are computed from the mine's earlier inspections only, but a mine is the
  same entity across splits by design — the task is about a mine's future, so entity overlap is the
  point, and the temporal split is what prevents leakage.
- Sections cited in fewer than 1% of pooled inspections are not shipped as configs, so this is not a
  census of the 30 CFR part.
- No agent or harness comparison was run on this artifact and none is implied.
