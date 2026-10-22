# Baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own runner files, shipped
verbatim (bundled sha256 equal the benchmark's declared hashes, recorded in `VERIFICATION.md`).
Do not edit them: the point of the baseline is that it is the contract a solver inherits.

```bash
sh baseline/reproduce_baseline.sh ./task
```

The script materializes a workdir the way `bench/workdir.py` does - `task.json` plus
`data/train.csv` and `data/eval.csv` from the public splits; the private holdout is never copied -
then runs `python3 train.py` and `sh validate.sh`. Both must print the same Eval AUC. The measured
result of this exact procedure on the released bytes is recorded in `../VERIFICATION.md`.

Dependencies (ranges from the benchmark's `pyproject.toml`):

```
pandas>=2.2,<3
numpy>=1.26
xgboost>=3.0
scikit-learn>=1.5
```

This is the runner contract only - a single XGBoost pass - not the agent harness loop. It says
nothing about how well a coding agent could do on the task; that is a separate experiment.

Note on interpreting the number: on this task the contract baseline (0.8126 eval AUC) sits well
above the construction-time references - the persistence analogue (trailing-12-month casualty
rate) reached only 0.527 eval / 0.495 holdout rank AUC and the best single context column
(activity_type) 0.707 eval / 0.699 holdout - so the model extracts real signal from the
pre-onset context, and the persistence failure mode seen on some panel tasks is absent here.
Those references, and the numbers to beat, are recorded in `../VERIFICATION.md`.
