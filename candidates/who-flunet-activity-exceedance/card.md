---
license: cc-by-nc-sa-3.0
license_name: cc-by-nc-sa-3.0-igo
license_link: https://creativecommons.org/licenses/by-nc-sa/3.0/igo/
language:
  - en
pretty_name: WHO FluNet Influenza Positivity Exceedance
size_categories:
  - 10K<n<100K
task_categories:
  - tabular-classification
tags:
  - tabular
  - public-health
  - influenza
  - surveillance
  - epidemiology
  - temporal-split
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/public-train.csv
      - split: eval
        path: data/public-eval.csv
      - split: holdout
        path: data/private-holdout.csv
---

# WHO FluNet Influenza Positivity Exceedance ({RELEASE_TAG})

**Status: {STATUS_LINE}**

For a WHO FluNet reporting country with systematic weekly negative reporting, will influenza test
positivity in ISO week **W+4** exceed **10% of processed specimens**, given that country's weekly
laboratory series through ISO week **W**? One row per (country, prediction week); the label is
computed from week W+4's row only.

The prediction instant is **the Sunday that closes week W**. Every feature is derived from weekly
counts published for weeks <= W: the week's own specimen and detection counts, lagged positivity
and counts for W-1..W-4, and an eight-week rolling summary. Week W+4's laboratory counts, and the
positivity derived from them, never ship - only the binary label does.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **Rows:** {ROWS_TOTAL} country-weeks across three disjoint temporal splits
- **GitHub counterpart:** {GITHUB_REPOSITORY}

## Splits

| split | rows | window (prediction week) | positive rate | distinct country-years |
| --- | ---: | --- | ---: | ---: |
| `train` | 5,779 | <= 2019-12-30 | 59.2% | 235 |
| `eval` | 6,831 | 2019-12-30 .. 2023-01-02 | 23.9% | 257 |
| `holdout` | 13,483 | 2023-01-02 onward | 40.7% | 422 |

The splits are temporal and disjoint on the prediction week. The base rate moves because the
phenomenon moved: eval covers the COVID-era collapse in influenza circulation and its recovery,
and negative reporting becomes systematic only in later years. That is a documented property of
the series, not a sampling choice.

Positives cluster by country-season. The effective sample size is the **distinct country-year**
count, not the row count: quote uncertainty against those figures.

## Rows are gated, not a census

A row ships only when the prediction week has at least 50 specimens, the target week exists with
at least 50 specimens, and the target country-year reports negatives systematically (at least 4
specimen-bearing weeks, at least 50% with `INF_NEGATIVE >= 1`). That last rule removes a measured
trap: before ~2015 most FluNet rows lack `INF_NEGATIVE`, so positivity computed from them is 100%
by construction. The 1995-2004 window measures 931/931 positive before the rule and 14 rows after
it.

## Loading

Version-pinned. `revision` is the tag, not a branch, so the bytes cannot change under you.

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", revision="{RELEASE_TAG}"{TOKEN_ARG})
```

{LOADING_NOTE}

The files are plain CSVs too:

```bash
hf download {REPO_ID} --repo-type dataset --revision {RELEASE_TAG} \
    --include "data/*.csv" --local-dir ./flunet
```

The GitHub counterpart carries the identical files and digests: {GITHUB_REPOSITORY}, with
`MANIFEST.json`, `SHA256SUMS` and `get_dataset.py`.

## Baseline

Through the benchmark's own `train.py` / `validate.sh` on the exact published bytes (fetched and
digest-verified, not rebuilt), and a standard-library reference measured at construction:

- runner-contract XGBoost baseline: see `VERIFICATION.md` and `MANIFEST.json`'s `baseline` block;
- **persistence** (score = week W's own positivity): **0.8929 AUC on eval**, **0.8745 on holdout**;
- rolling-8-week mean positivity: 0.8281 eval, 0.7683 holdout.

Persistence is a strong floor. A solution that cannot beat it is not interesting on this task.
Scope: baselines only, through the runner's contract. No agent or harness comparison was run.

## Qualification

- Gate **1.3.0** over the full artifact on the worker: `ok: true`, 0 failed checks (leakage,
  prediction timing, units and frames, temporal splits, runner contract), re-accepted on the
  coordinator with `--accept` against the same artifact digest.
- Timing self-check: 201 rows recomputed against a series physically truncated at week W, 0
  mismatches; 0 duplicate row ids.
- Known-event fixture (France 2024-25): blended peak positivity 0.2379 in the week of 2025-01-27,
  off-season maximum 0.0071 - the fixture pins the 10% threshold and the 4-week lead with margin.

## Provenance

- Source: World Health Organization, FluNet (Global Influenza Surveillance and Response System),
  https://www.who.int/tools/flunet; full table at
  `https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv`, one anonymous request,
  32,246,617 bytes, sha256 `5695e5d2...`, retrieved 2026-10-20.
- Column meanings are the publisher's own `VIW_FLU_METADATA` view (53 documented fields).
- FluNet is a live weekly register: a rebuild after 2026-10-20 will pick up later weeks and will
  not reproduce these digests. The published artifact is the 2026-10-20 vintage.

## Licence and attribution

| | |
| --- | --- |
| Source data (WHO) | **{SOURCE_LICENSE}** - attribution, non-commercial, share-alike carried through unchanged |
| Our rights in this derived compilation | **{DATA_LICENSE}** - no separate dedication; no CC0 claim |
| Code and documentation in the GitHub counterpart | **{CODE_LICENSE}** |

**Attribution.** {SOURCE_ATTRIBUTION}

This dataset is **derived** from WHO FluNet and is labelled as derived; it is **not an official
WHO product**, has not been reviewed by WHO, and carries no endorsement. The label is ours: WHO
publishes laboratory counts, not this exceedance target.

## Limitations

- Test positivity depends on who is tested: sentinel-based and non-sentinel streams are summed,
  which blends two sampling regimes.
- Country reporting practice changes over time and differs by country; the systematic-negative
  rule mitigates the largest known break (missing negatives before ~2015) but is not a guarantee.
- The label's 10% threshold is a fixed activity level, not a country-specific epidemic threshold.
- No agent or harness comparison was run on this artifact, and none is implied.