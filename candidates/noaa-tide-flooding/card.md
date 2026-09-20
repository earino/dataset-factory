---
license: cc0-1.0
language:
  - en
pretty_name: NOAA Tide Flooding Prediction
size_categories:
  - 1M<n<10M
task_categories:
  - tabular-classification
tags:
  - tabular
  - climate
  - oceanography
  - time-series
  - temporal-split
  - station-disjoint-split
configs:
  - config_name: temporal
    data_files:
      - split: train
        path: temporal/public/train.csv
      - split: eval
        path: temporal/public/eval.csv
      - split: holdout
        path: temporal/private/holdout.csv
  - config_name: station_disjoint
    data_files:
      - split: train
        path: station_disjoint/public/train.csv
      - split: eval
        path: station_disjoint/public/eval.csv
      - split: holdout
        path: station_disjoint/private/holdout.csv
---

# NOAA Tide Flooding Prediction ({RELEASE_TAG})

**Status: {STATUS_LINE}**

Will a tide gauge's daily maximum observed water level exceed its published **minor flood threshold**
tomorrow? 122 NOAA NOS stations, 2006-2025, 2,440 station-years, one row per station-day.

- **Artifact version:** `{ARTIFACT_VERSION}`
- **Version tag:** `{RELEASE_TAG}` (use this revision for reproducibility)
- **GitHub counterpart:** {GITHUB_REPOSITORY}
- **Rows:** {ROWS_TOTAL} across two levels

**This is a derived dataset and not an official NOAA, NOS or NWS product.** The source is NOAA CO-OPS
public-domain data.

## Loading

Version-pinned. `revision` is the tag, not a branch, so the bytes cannot change under you. There are
**two configs**, one per level, because each is a complete task instance.

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", "temporal", revision="{RELEASE_TAG}"{TOKEN_ARG})
print(ds)
# DatasetDict({
#     train: Dataset({features: [...], num_rows: ...}),
#     eval: Dataset({features: [...], num_rows: ...}),
#     holdout: Dataset({features: [...], num_rows: ...})
# })

# the label is `late`: 1 when the target day exceeded the station's threshold
print(ds["train"].features["late"])
```

{LOADING_NOTE}

```python
ds = load_dataset("{REPO_ID}", "station_disjoint", revision="{RELEASE_TAG}"{TOKEN_ARG})
```

The files are also plain CSVs, so they can be used without `datasets`:

```bash
hf download {REPO_ID} --repo-type dataset --revision {RELEASE_TAG} \
    --include "temporal/*" --local-dir ./noaa
```

`temporal/` and `station_disjoint/` mirror the GitHub release layout exactly:
`public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`, `quality.json`.

## The two levels

| config | train | eval | holdout | what it asks |
| --- | --- | --- | --- | --- |
| `temporal` | 2006-2021, all 122 stations | 2022-2023 | 2024-2025 | the benchmark-typical panel split |
| `station_disjoint` | 2006-2021, 81 stations | 2022-2023, **41 unseen stations** | 2024-2025, the same 41 | whether a model learned something transferable rather than one station's local behaviour |

The station-disjoint level is why this dataset exists. NOAA publishes the observations, the verified
maxima and the annual counts, so **access is not the contribution**. A frozen multi-station panel, an
observations-only feature contract, a station-disjoint generalisation split and a leakage gate around
all of it are not things NOAA's products package.

## The label

`late` is the binary target: `1` when the station's daily maximum observed water level exceeded its
published **`nos_minor`** threshold on the target day, `0` otherwise.

- The label comes from **NOAA's own minor-flood days** (the HTF daily product's `minFlag`). Our own
  reduction of the 6-minute maxima overcounted flood days by about 20% against NOAA's counts on a
  year with real signal (113-114 against 94 over four stations, 2024), while NOAA's flags matched
  exactly, station by station. A label that disagrees with the publisher's own product has to be
  justified, and there is no reason to ship one.
- The threshold is the **physical published value on station datum (`STND`)**. It is not a quantile
  chosen to balance the classes. Comparing MLLW-referenced heights against it silently yields zero
  positives at every station - a trap this dataset documents in `meta.json` and measures.
- **Prediction time is the end of the previous local day.** Features are observations only, with
  trailing windows, so the future cannot leak into a feature. NOAA tide predictions and model
  guidance are excluded: they are model output, and including them would hand the task over.

**Only about 2% of station-days are positive.** A constant "no flood" answer agrees with the label
roughly 96% of the time. Score **AUC**, not accuracy.

## Results, including the uncomfortable one

Baseline through the benchmark's own `train.py`/`validate.py`, copied verbatim into the GitHub
counterpart:

| level | recorded | independent reproduction |
| --- | --- | --- |
| `temporal` | **0.8638** | 0.8651 |
| `station_disjoint` | **0.8688** | 0.8687 |

The runner's training is not bit-reproducible (xgboost, default threading, identical bytes), so the
last decimal moves between runs. Treat both columns as the same result; the digests do not move.

The station-disjoint level scores the same on **stations the model never saw**, so the signal is not
station-specific memorisation.

**And the floor, measured without training:** a single stock feature - yesterday's maximum against
the station's own threshold - already reaches **0.8265** (temporal) and **0.8454** (station-disjoint).
The trained model's real headroom is **+0.0373** and **+0.0234**. The headroom is narrow, and it is
stated here rather than discovered by a reviewer. The full measurement is in the GitHub
counterpart's `measurements.json`.

## Licence

- **This compilation** (frozen station list, row selection, derived label, both partitions, feature
  construction): **{DATA_LICENSE}**.
- **Code and documentation:** **{CODE_LICENSE}**.
- **NOAA's data**: {SOURCE_LICENSE} (US Government work), preserved unchanged.

{SOURCE_ATTRIBUTION}

NOAA's constraint - modified content must not be presented as official government material - is
honoured: this dataset is labelled as derived everywhere it appears.