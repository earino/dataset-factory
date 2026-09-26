---
license: cc0-1.0
language:
  - en
pretty_name: Austin 911 Response Time (2026.09)
size_categories:
  - 1M<n<10M
task_categories:
  - tabular-classification
tags:
  - tabular
  - public-safety
  - emergency-response
  - temporal-split
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train.csv
      - split: eval
        path: data/eval.csv
      - split: holdout
        path: data/holdout.csv
---

# Austin 911 Response Time (2026.09)

**Status: private. Public visibility requires explicit human approval.** Nothing here has been
published.

Predict whether an Austin 911 call for service will have a **late first-unit arrival**: at least
`1200 seconds` between the call being answered and the first unit
arriving. The label and every feature are knowable at prediction time; the label source column is
never shipped.

- **Artifact version:** `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`
- **Version tag:** `v2026.09` (use this revision for reproducibility)
- **GitHub counterpart:** https://github.com/earino/austin-911-response
- **Rows:** 1,049,636 across three disjoint temporal splits

## Loading

Version-pinned. `revision` is the tag, not a branch, so the bytes cannot change under you.

```python
from datasets import load_dataset

ds = load_dataset("{repo_id}", revision="v2026.09")
print(ds)
# DatasetDict({
#     train: Dataset({features: [...], num_rows: 572180}),
#     eval: Dataset({features: [...], num_rows: 285665}),
#     holdout: Dataset({features: [...], num_rows: 191791})
# })

# the label is `late`, a binary target
print(ds["train"].features["late"])
```

For a private repository, pass a token that has access to it (the inference credential does not):

```python
ds = load_dataset("{repo_id}", revision="v2026.09", token=True)
```

The files are also plain CSVs, so they can be used without `datasets`:

```bash
hf download {repo_id} --repo-type dataset --revision v2026.09 \
    --include "data/*.csv" --local-dir ./austin
```

## Splits

Split by `response_datetime`, disjoint and ordered, so no split leaks into another:

| split | rows | positives | positive rate | window |
| --- | --- | --- | --- | --- |
| `train` | 572,180 | 231,025 | 0.4038 | before 2025-01-01 |
| `eval` | 285,665 | 109,860 | 0.3846 | 2025 |
| `holdout` | 191,791 | 72,450 | 0.3778 | 2026 onward |

## The labels

`late` is the binary target: `1` when the first unit arrived `1200` or
more seconds after the call was answered.

The threshold was frozen from the **training window by rule, not by hand** - the largest tested
value whose training-window positive rate stays at or above 0.40, counting only aggregate queries:

- `1200s` gives a training rate of **0.403763**
- `0.390050`
  falls below the target: 0.390050 falls below the 0.40 target

Positive rates differ by split (0.4038 / 0.3846 / 0.3778);
that reflects when the data was collected, not a construction fault.

## The response-time clock (measured, not assumed)

`response_time` is documented as measuring from when the call was **answered**, and no column
records that instant, so the label cannot be recomputed from the shipped fields. Measured over
2000 rows:

- definition: `(first_unit_arrived_datetime - response_datetime) - response_time`
- median **-57.0s**, p05 -206.0s, p95 0.0s,
  range -468.0s to 6041.0s
- 1890 negative / 55 exact zero /
  55 positive rows

Reproduce it with `python3 code/measure_clock_offset.py 2000 --json`.

## Provenance

- Source: Austin Open Data - APD 911 Calls for Service 2023-2026 (dataset `e687-fx2y`), https://datahub.austintexas.gov/d/e687-fx2y
- Licence of the source data: Public Domain, per the publisher's catalogue metadata.
- Extraction: **69 HTTP requests**
  (15 aggregate,
  54 pages), measured
  353.7s on 2 vCPU / 2 GB worker.
- Rebuild: `MANIFEST.json` pins the build timestamp, so a rebuild is byte-identical.

## Licence and attribution

| | |
| --- | --- |
| Source data (City of Austin) | **Public Domain, preserved unchanged** - designation preserved, attribution and citation given below |
| Our rights in this derived compilation | **CC0-1.0** (`LICENSE-CC0-1.0.txt`) |
| Code and documentation in the GitHub counterpart | **MIT** (`LICENSE-MIT.txt`) |

**Scope, stated plainly:** the CC0 dedication covers **our contribution** - the row selection, the
derived binary label, the temporal partition and the packaging. It does **not** cover or relicense
the City of Austin's data, which keeps its own Public Domain designation. This dataset is derived
from the City of Austin's open data and is labelled as derived; it is **not an official City of
Austin product**.

**Attribution.** City of Austin, APD 911 Calls for Service 2023-2026, Austin Open Data, https://datahub.austintexas.gov/d/e687-fx2y, accessed 2026-09-18

**Suggested citation.**

> City of Austin. APD 911 Calls for Service 2023-2026. Austin Open Data. Public Domain. Accessed 2026-09-18. Derived dataset: Austin 911 response time prediction dataset, version 2026.09, artifact e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328.

**Future datasets** in this series choose terms compatible with each source; CC0 here is not a
standing permission to override another source's terms.

## Qualification and baseline

- Gate: **PASSED - 33 checks, 0 failed, on the full 1,049,636-row artifact, on the worker** (gate 1.3.0),
  run over the full artifact on a worker.
- One baseline through the runner's existing training and validation contract:
  **eval AUC not recorded**.
- Scope: One baseline through the runner's training and validation contract. No agent or harness comparison was run and none is implied.

Every number above is measured, with the command that produced it recorded in
`measurements.json`; figures that are estimates are labelled as such.
