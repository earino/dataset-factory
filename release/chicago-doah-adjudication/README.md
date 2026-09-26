# Chicago Department of Administrative Hearings — adjudication outcome

A benchmark task built from the City of Chicago's **Department of Administrative Hearings
(DOAH) — Adjudication** dataset: given a case the City has docketed for an ordinance-violation
hearing, predict whether the hearing officer will record a **Liable** disposition on at least one
charge.

- **Version:** 2026.09 (`artifact_version` `b71586bf28fa56ebbfaede26c4494d68b166545ac504b2ebd8a52c7f272627ef`)
- **Rows:** 53,763 cases — 47,414 train, 3,436 eval, 2,913 private holdout
- **Source:** `https://data.cityofchicago.org/resource/6br9-quuz.json` — frozen at build time (2026-09-01), read anonymously
- **Code:** MIT. **Data compilation:** City of Chicago Data Terms of Use (see `LICENSE.md`)

## The task

**Given** a docketed administrative-hearing case — its lead violation's ordinance code and
location, its ward, and how many charges it carries — **predict** whether the officer records a
`Liable` disposition on at least one charge.

- **Unit:** one row = one case (`docket_number`). The source publishes one row per *charge*; the
  case-level reduction is part of the builder.
- **Target:** `outcome` ∈ {`Liable`, `Not Liable`}. `Liable` iff ≥1 charge of the case was disposed
  `Liable`; the source's other dispositions (`Non-Suit`, `Default`, `Continuance`, …) are not the
  positive class — they are folded into `Not Liable`.
- **Prediction time:** at docketing, before any hearing. Every shipped feature is on the notice:
  the charge and its location, not the hearing.
- **Population:** cases **with at least one decided charge**, whose lead violation falls in
  2008-01-01 to 2026-09-01. Cases still open (no disposition recorded on any charge) are excluded —
  74,387 dockets — because they have no outcome to predict. Among decided cases, 53 were dropped
  for incomplete lead-charge fields and 2,115 for falling outside the window.
- **Splits:** temporal, by the case's lead `violation_date`, with no random component. A case is
  never split across two files — the split is taken over cases, not over the source's charge rows.

| split | file | period | cases | Liable | positive rate |
|---|---|---|---|---|---|
| train | `public/train.csv` | < 2018-01-01 | 47,414 | 29,959 | 0.631860 |
| eval | `public/eval.csv` | 2018-01-01 to 2022-01-01 | 3,436 | 3,077 | 0.895518 |
| holdout | `private/holdout.csv` | 2022-01-01 to 2026-09-01 | 2,913 | 2,715 | 0.932029 |

## What is in this package

| file | bytes | sha256 (first 16) |
|---|---|---|
| `public/train.csv` | 3,751,973 | `67b2a58379b4d1ca` |
| `public/eval.csv` | 267,311 | `bcecdbff8018f74c` |
| `private/holdout.csv` | 226,237 | `e9855daa7a7d523e` |
| `meta.json` | 2,300 | `696730446f8bb10c` |
| `quality.json` | 3,803 | `7ee12a3db4dbd00b` |

`SHA256SUMS` carries the full digests and `MANIFEST.json` records them with the qualification
result. `get_dataset.py` fetches the published asset and unpacks exactly these five files into
`./task`.

## Download and use

```bash
python3 get_dataset.py --dest ./task
( cd task && sha256sum -c ../SHA256SUMS )
python3 code/qualify_dataset.py ./task
sh baseline/reproduce_baseline.sh ./task
```

`get_dataset.py` verifies every file's SHA-256 against `SHA256SUMS` before finishing, and refuses
to leave a mismatched file in place.

## Baseline

One baseline, through the runner's own `train.py`/`validate.sh` unmodified, on a worker of its own
that first rebuilt the artifact and refused to measure it unless the rebuild was byte-identical to
the artifact that passed qualification (`chicago-baseline-001`; full evidence in
`baseline/baseline_result.json`).

| metric | value |
|---|---|
| eval AUC (from `train.py`) | **0.6915** |
| eval AUC (from `validate.py`, `predict_proba` with the target removed) | 0.6915 |
| training time | 0.2 s |
| dependency versions used | pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1 |
| runner files | bundled hashes == benchmark hashes (unmodified) |

**Read this against the split, not against 0.5.** eval's positive rate is 0.8955, so a
constant-`Liable` predictor scores 89.6% accuracy while carrying no information; AUC 0.6915 is the
honest floor for a model that actually ranks. Nothing here is an agent or harness score, and none
is implied.

## Findings and limitations

- **The label is administrative, not moral.** `Liable` means the City proved its charge at a
  hearing (often because nobody appeared: `Default` is folded in as it is recorded per charge).
  Nothing in this dataset establishes that a violation occurred.
- **The positive rate climbs steeply over time** — 0.632 → 0.896 → 0.932 across the three periods.
  This is a property of the City's docket, not of the split. A model can gain on eval and holdout
  by learning recency alone, without learning anything about the charge.
- **Decided cases are a selected population.** Cases with no disposition on any charge are
  excluded, and the disposition mix is administrative as much as legal.
- **`hearing_date` is excluded outright, not merely unused.** The City documents it as the date of
  the *most recent* hearing, which on a decided case is the hearing where the disposition was
  recorded; a feature built from it separates the classes on its own. `case_disposition` (the label
  source) and `imposed_fine`/`admin_costs` are excluded for the same reason.
- **"Not an official product."** This compilation is derived from the source below; it is not
  published by, endorsed by, or affiliated with the City of Chicago.
- **The source is republished daily.** This version is defined by the hashes here, not by the live
  endpoint; note the endpoint may already differ.

## Attribution and citation

Data provided by the City of Chicago, Department of Administrative Hearings — Adjudication
(`6br9-quuz`), used under the **City of Chicago Data Terms of Use** (see `LICENSE.md`, which
carries the required disclaimers). Please credit the City of Chicago when redistributing this
compilation.

> City of Chicago, "Department of Administrative Hearings — Adjudication", Chicago Open Data
> Portal. https://data.cityofchicago.org/d/6br9-quuz (accessed 2026-09-26). Compilation by the
> Scout project, version 2026.09.

## Versioning

`2026.09` identifies this compilation. The exact bytes are fixed by the `artifact_version` and the
digests above. A rebuild from the live endpoint will differ as the City republishes; the frozen
extract's source-side digests are recorded in `measurements.json` so drift is visible rather than
silent.

<!-- dataset-factory:links -->
**Dataset Factory · v2026.09**

[Dataset website](https://earino.github.io/chicago-doah-adjudication/versions/v2026.09/) · [GitHub release](https://github.com/earino/chicago-doah-adjudication/releases/tag/v2026.09) · [Hugging Face](https://huggingface.co/datasets/earino/chicago-doah-adjudication/tree/v2026.09) · [Catalogue](https://earino.github.io/dataset-factory-site/)

Artifact: b71586bf28fa56ebbfaede26c4494d68b166545ac504b2ebd8a52c7f272627ef
<!-- /dataset-factory:links -->
