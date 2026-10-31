# Baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own runner files,
shipped verbatim (bundled sha256 equal the benchmark's declared hashes, recorded in
`VERIFICATION.md`). Do not edit them: the point of the baseline is that it is the
contract a solver inherits.

```bash
sh baseline/reproduce_baseline.sh ./task
```

The script materializes a workdir the way `bench/workdir.py` does - `task.json` plus
`data/train.csv` and `data/eval.csv` from the public splits; the private holdout is never
copied - then runs `python3 train.py` and `sh validate.sh`. Both must print the same Eval
AUC. The measured result of this exact procedure on the released bytes is recorded in
`../VERIFICATION.md`.

Dependencies (ranges from the benchmark's `pyproject.toml`):

```
pandas>=2.2,<3
numpy>=1.26
xgboost>=3.0
scikit-learn>=1.5
```

This is the runner contract only - a single XGBoost pass - not the agent harness loop. It
says nothing about how well a coding agent could do on the task; that is a separate
experiment.

## Reading this task's baseline

The stock XGBoost baseline scored **Eval AUC 0.6108** on the 28,104 eval rows
(validated 2020-2021, 30.13% positive). Every measured simple reference sits below it
on the identical rows, with paired row-level AND LPA-clustered bootstrap intervals
(150 resamples) excluding zero:

| Reference / model | Eval AUC |
| --- | --- |
| Full model (this baseline) | **0.6108** |
| Procedure-type rate (dominant simple reference) | 0.5551 |
| Shipped rate feature (`lpa_allow_rate_prior`) | 0.5422 |
| LPA history rate (the named headroom reference) | 0.5414 |
| Persistence (previous same-LPA outcome) | 0.5045 |

- model - procedure_type **+0.0558**, row CI95 [0.0467, 0.0626], LPA-cluster CI95 [0.0462, 0.0654]
- model - lpa_hist **+0.0694**, row CI95 [0.0622, 0.0766], LPA-cluster CI95 [0.0597, 0.0792]
- model - shipped_rate_feature **+0.0686**, row CI95 [0.0619, 0.0756], LPA-cluster CI95 [0.0596, 0.0800]

Persistence is measured, not declared not-applicable: 92%+ of eval rows' LPAs have a
train-era decided-case history (the -1 sentinel marks the rest). Majority-class
accuracy on this split is 0.6987 - the majority class fitted on train is 0 (31.09%
train positive rate) and it agrees with 69.87% of eval labels. The calendar-identity
control collapsed onto the LPA rate exactly (eval validation years have no train-era
valid-year support) and is recorded as a degenerate control, never as independent
confirmation.

Scope of the finding, carried from `../VERIFICATION.md`: one model configuration with
no re-tuning, two validation years of eval coverage, row-level and LPA-clustered
intervals. Demonstrated headroom over these references under this protocol - an
observed result, not a bound on other models and not an operational-validity claim.
