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

The stock XGBoost baseline scored **Eval AUC 0.6973** on the 1,770 eval rows. The
required comparator - a train-fitted positive rate per NACE division, averaged over the
case's divisions - scored **0.7679** on the identical rows (paired difference
-0.0706, bootstrap95 [-0.1558, +0.0168]: an inconclusive difference whose observed gap is
negative, so no reader should quote 0.6973 as the task's ceiling or as evidence of
headroom over the simple prior). The stock model's cardinality rule did not exclude the
sector signal (`sector_divisions` has 540 train levels, under the 1000 cutoff; only
`case_title` and `notification_date` were dropped), so the gap is a genuine property of
the stock fit at 217 train positives, not a feature-availability artefact. All the
references and the paired comparisons are recorded in `../VERIFICATION.md` and in
`../RELEASE_NOTES.md`.
