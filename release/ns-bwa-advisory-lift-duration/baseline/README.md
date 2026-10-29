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
`../VERIFICATION.md` and `../measurements.json`: **0.5086**, with the site-persistence
reference (a shipped feature, `site_prior_lift30_rate`) at **0.6124** on the same rows -
the stock baseline does not beat the one-line rule, and the comparison is part of the
release's recorded finding.

Dependencies (ranges from the benchmark's `pyproject.toml`):

```
pandas>=2.2,<3
numpy>=1.26
xgboost>=3.0
scikit-learn>=1.5
```

This is the runner contract only - a single XGBoost pass - not the agent harness loop. It
says nothing about how well a coding agent could do on the task; that is a separate
experiment. The evaluation contract (`quality.json`) requires isolated-rows access: any
real evaluation must predict each row without any other row, a restriction this
illustrative runner does not enforce.
