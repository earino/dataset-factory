# Baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own runner files, shipped
verbatim (hashes recorded in `MANIFEST.json`'s baseline block). Do not edit them: the point of the
baseline is that it is the contract a solver inherits.

```bash
sh baseline/reproduce_baseline.sh ./task
```

The script materializes a workdir the way `bench/workdir.py` does - `task.json` plus
`data/train.csv` and `data/eval.csv` from the public splits; the private holdout is never copied -
then runs `python3 train.py` and `sh validate.sh`. Both must print the same Eval AUC. The measured
result of this exact procedure on the published bytes is recorded in `../VERIFICATION.md`.

Dependencies (ranges from the benchmark's `pyproject.toml`):

```
pandas>=2.2,<3
numpy>=1.26
xgboost>=3.0
scikit-learn>=1.5
```

This is the runner contract only - a single XGBoost pass - not the agent harness loop. It says
nothing about how well a coding agent could do on the task; that is a separate experiment.