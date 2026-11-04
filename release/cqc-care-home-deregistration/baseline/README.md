# Baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own
runner files, shipped verbatim (bundled sha256 equal the benchmark's declared
hashes, recorded in `VERIFICATION.md`). Do not edit them: the point of the
baseline is that it is the contract a solver inherits.

```bash
sh baseline/reproduce_baseline.sh ./task
```

The script materializes a workdir the way `bench/workdir.py` does - `task.json`
plus `data/train.csv` and `data/eval.csv` from the public splits; the private
holdout is never copied - then runs `python3 train.py` and `sh validate.sh`.
Both must print the same Eval AUC. The measured result of this exact procedure
on the released bytes is recorded in `../VERIFICATION.md`.

Dependencies (ranges from the benchmark's `pyproject.toml`):

```
pandas>=2.2,<3
numpy>=1.26
xgboost>=3.0
scikit-learn>=1.5
```

This is the runner contract only - a single XGBoost pass - not the agent
harness loop. It says nothing about how well a coding agent could do on the
task; that is a separate experiment.

## Reading this task's baseline

The stock XGBoost baseline scored **Eval AUC 0.5659** on the 14,765 eval rows
(January 2024 vintage, 5.13% positive). On the identical rows it sits **below
the strongest simple reference** and above every one-line prior:

| Reference / model | Eval AUC |
| --- | --- |
| `rating_x_beds_rate` (train-fitted rate table over latest rating x beds) | **0.5871** |
| Full model (this baseline) | **0.5659** |
| `last_rating_rate` (best one-line prior) | 0.5597 |
| `beds_bucket_rate` | 0.5298 |
| `hsca_start_year_rate` | 0.5226 |
| `local_authority_rate` | 0.5207 |
| `provider_sector_rate` | 0.5011 |

There is no persistence reference by design (per-instant pseudonymised
identity; `hsca_start_year_rate` is the nearest shippable history prior), and
the global constant is degenerate as a score. Majority-class accuracy on eval
is 0.94873 but a constant carries no ranking information.

The stock runner trailing `rating_x_beds_rate` is a **recorded defect of the
runner under this protocol**, not a property of the task: the reference reads
only shipped at-instant columns, so any consumer can compute it in one line -
and beating it is the natural first target for a solver. One verified
diagnosis candidate: the stock `train.py` treats `instant` (YYYY-MM) as a
train-only categorical, so the eval instant 2024-01 is unseen and every eval
row gets NaN there. Quote no model figure from this dataset without the
ladder above beside it.
