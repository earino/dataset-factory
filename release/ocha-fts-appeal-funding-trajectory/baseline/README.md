# Baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own runner
files, shipped verbatim (bundled sha256 equal the benchmark's declared hashes,
recorded in `VERIFICATION.md`). Do not edit them: the point of the baseline is
that it is the contract a solver inherits.

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

This is the runner contract only - a single XGBoost pass - not the agent harness
loop. It says nothing about how well a coding agent could do on the task; that is
a separate experiment.

## Reading this task's baseline

The stock XGBoost baseline scored **Eval AUC 0.6452** on the 139 eval rows
(appeal years 2017-2020, 58.27% positive), measured on the released bytes in
baseline job fts-baseline-002 after an exact-byte gate `--accept` of the
downloaded artifact (both the runner's own `train.py` and `validate.py`'s
independent predict_proba recompute print 0.6452).

The comparison that qualifies the number, on the identical 139 eval rows:

| Reference / model | Eval AUC |
| --- | --- |
| Persistence (last prior same-country coverage; scorer-side recompute) | **0.7171** |
| Prior-mean rate (scorer-side recompute) | 0.7143 |
| Original-ask size rate | 0.7126 |
| Country history rate (train-era) | 0.6729 |
| Plan-type rate (train-era) | 0.6692 |
| **Full model (this baseline)** | **0.6452** |
| Majority-class accuracy (train label, eval agreement) | 0.5827 |

The model **trails the persistence reference by 0.0719 AUC**. Under the
dataset-qualification protocol that is a recorded defect, not an encouraging
result: any headroom claim on this task requires beating `persistence_last_coverage`
on the same rows, and no such claim is made here.

One asymmetry is inherent to the task's leakage standard and must travel with
the number: the prior-outcome features that would give the model the last prior
same-country coverage allowed exact cross-row label recovery (the 2026-11-01
queue audit recovered 120/139 eval and 128/182 holdout labels through them) and
are unshippable, so `persistence_last_coverage` is recomputed scorer-side from
prior-in-time labels (train+eval only; the holdout is never opened) while the
model is deliberately denied that value. The comparison is honest but not
information-equal, and is recorded as **no demonstrated headroom under this
protocol for the stock runner** - an observed result on these rows with this
runner configuration, not a bound on other models and not an
operational-validity claim.
