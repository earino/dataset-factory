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

Note on interpreting the number: on this task the contract baseline (0.9199 eval AUC)
sits above the persistence margin (0.8671 eval / 0.8789 holdout rank AUC) by +0.0532 on
identical eval rows, so the level target stands and the persistence-dominance failure
mode seen on some panel tasks is absent. Most of the edge is the announced-allocation
margin rule (`margin_t` alone: 0.8988 eval / 0.8881 holdout) - the task's intended
one-line solver rule - and the model adds +0.021 beyond it. The label is persistent
(P(short|short) = 0.857), so persistence is quoted beside every model number, and the
calendar-only (0.527) and identity-only (0.5719) references are recorded with it. Those
references, and the numbers to beat, are in `../VERIFICATION.md`.
