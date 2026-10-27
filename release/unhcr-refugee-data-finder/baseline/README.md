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

The stock XGBoost baseline scored **Eval AUC 0.5393** on the 1,887 eval rows. Both
persistence references outscore it on the identical rows: the corridor's own momentum
(`log_growth_d`) scored **0.5742** and the surge flag (`surged_recently`, 1 when the
corridor already doubled in year D) scored **0.5856** (paired differences -0.0348,
bootstrap95 [-0.1056, +0.0409] and -0.0463, [-0.1103, +0.0144]: inconclusive differences
whose observed gaps are negative). **No headroom over persistence is demonstrated under
this protocol** - quote 0.5393 only next to 0.5856, never alone. Per label year the
picture is heterogeneous: momentum owns 2017-2019 (0.745 vs 0.394 in 2017), the stock
model owns the 2020 pandemic year (0.842 vs 0.116) on only 6 positives, and 2021 is a
near-tie. All references and paired comparisons are recorded in `../VERIFICATION.md`
and `../RELEASE_NOTES.md`, with the recomputation path in `../REPRODUCE.md`.
