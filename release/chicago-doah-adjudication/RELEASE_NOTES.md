# Chicago DOAH adjudication outcome — `v2026.09`

First release. A leakage-checked, time-split prediction dataset built from the City of Chicago's
public **Department of Administrative Hearings (DOAH) — Adjudication** records: predict, **at
docketing**, whether the hearing officer will record a `Liable` disposition on at least one charge
of the case.

**53,763 cases**, three time-separated splits, City of Chicago open data. Artifact version
`b71586bf28fa56ebbfaede26c4494d68b166545ac504b2ebd8a52c7f272627ef`. **Published 2026-09-26** —
public on both destinations after explicit operator authorisation; publication changed no data file,
tag or checksum. Also on Hugging Face as `earino/chicago-doah-adjudication`, revision `v2026.09`.

## Get it

```bash
git clone https://github.com/earino/chicago-doah-adjudication.git
cd chicago-doah-adjudication
python3 get_dataset.py --dest ./task        # fetches the release assets, verifies SHA-256
( cd task && sha256sum -c ../SHA256SUMS )   # the published verification command
python3 code/qualify_dataset.py ./task      # the qualification gate, 32 checks
sh baseline/reproduce_baseline.sh ./task    # the recorded baseline
```

## Assets

GitHub does not allow `/` in asset names, so these are flat; `get_dataset.py` restores the layout.

| asset | bytes | becomes |
|---|---|---|
| `train.csv` | 3,751,973 | `public/train.csv` |
| `eval.csv` | 267,311 | `public/eval.csv` |
| `holdout.csv` | 226,237 | `private/holdout.csv` |
| `meta.json` | 2,300 | `meta.json` |
| `quality.json` | 3,803 | `quality.json` |

Verify with `sha256sum -c SHA256SUMS`.

| split | period | cases | positives | rate |
|---|---|---|---|---|
| train | before 2018-01-01 | 47,414 | 29,959 | 0.631860 |
| eval | 2018-01-01 to 2022-01-01 | 3,436 | 3,077 | 0.895518 |
| holdout | 2022-01-01 to 2026-09-01 | 2,913 | 2,715 | 0.932029 |

The holdout is part of the package; it must stay out of an evaluated agent's workspace during a
benchmark run.

## What was checked before this was staged

- **Qualification gate 1.3.0: 32 checks, 0 failures**, on a worker over the full artifact — leakage,
  prediction timing, split capacity and boundary integrity, and the runner's input contract.
- **No leakage:** `case_disposition` (the label's source) is absent from every file, as are
  `hearing_date`, `imposed_fine`, `admin_costs` and `last_modified_date`, all declared and
  excluded as post-hoc rather than merely unused.
- **Splits are temporal and disjoint**, taken over **cases, never over the source's charge rows**;
  no identifier appears in two splits; both classes are present in eval and holdout.
- **Provenance:** the frozen extract fetched **823,955 rows** — exactly the count the source
  reported at freeze time — over 17 pages, and its 130,318 dockets reduce to 53,763 published
  cases. Nothing was lost or duplicated.

## Measured

| | |
|---|---|
| Baseline, the benchmark's own `train.py` unmodified | eval AUC **0.6915** |
| Same, re-scored through `validate.py`'s `predict_proba` | eval AUC **0.6915** |
| Baseline train / score time | 0.2 s / 0.0 s |
| Build | 93.4 s on 4 vCPU / 1.9 GiB (**345 MB peak RSS**), 18 HTTP requests, 4,245,521 bytes out |
| Same build on the qualification worker | 92.6 s on 2 vCPU / 2 GB including the gate |

**Eval's positive rate is 0.8955**, so a constant-`Liable` predictor already scores 89.6% accuracy;
AUC 0.6915 is a floor that actually ranks. Baselines are floors, not results. **No agent or harness
comparison has been run** — a separate milestone, and none should be inferred.

## Known properties, stated rather than hidden

- **The positive rate rises steeply across the periods** (0.632 → 0.896 → 0.932). A model can gain
  on eval and holdout by learning recency alone. This is a property of the City's docket.
- **Decided cases only.** The 74,387 dockets with no disposition on any charge are excluded —
  there is nothing to predict for them. That is a selection on the outcome, and it is declared.
- **No clock-offset measurement is reported.** Unlike a threshold-based task, nothing here turns on
  a label clock: the label is a disposition, not an event time. No number is invented to fill that
  slot.
- **`docket_number` is unique**: 53,763 of 53,763 rows carry a distinct value, and no value appears
  in two splits. Declared in `quality.json`.
- **Blank feature values are shipped as blank** (153 `ward`, 613 `street_type`) and are not
  imputed.
- The source is republished daily by the City, so rebuilding later will not reproduce these bytes.
  The hashes, not the source URL, define this version.

## Licensing

**Code and documentation** in this repository — including the three baseline runner files copied
verbatim from `earino/harness_benchmark` — are released under **MIT** (`LICENSE-MIT.txt`), with
contributor credits preserved: Copyright (c) 2026 E. Arino de la Rubia (earino), with contributors
Claude and Szilard.

**Our rights in the derived compilation** are released under the **City of Chicago Data Terms of
Use**, the source's own terms (`LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md`); the required
disclaimers appear in `LICENSE.md` and in the packaged `meta.json`. This compilation is **not an
official product** of the City of Chicago and is not endorsed by it.

## Citation

> City of Chicago, Department of Administrative Hearings — Adjudication (dataset `6br9-quuz`),
> Chicago Open Data Portal. City of Chicago Data Terms of Use. Accessed 2026-09-26. Derived
> dataset: Chicago DOAH adjudication outcome prediction dataset, version 2026.09, artifact
> `b71586bf28fa56ebbfaede26c4494d68b166545ac504b2ebd8a52c7f272627ef`.
