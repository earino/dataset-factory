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

The stock XGBoost baseline scored **Eval AUC 0.6224** (Brier 0.1318) on the 97,274 eval
rows (filings 2013-2014, 83.99% positive). Every measured simple reference sits well
below it on the identical rows, with paired row-level intervals excluding zero:

| Reference / model | Eval AUC |
| --- | --- |
| Full model (this baseline) | **0.6224** |
| Mark-type rate (dominant simple reference) | 0.5650 |
| Nice-class rate | 0.5421 |
| Series-flag rate | 0.5213 |
| Owner-country rate | 0.5191 |
| Category rate | 0.5031 |
| Calendar-month rate | 0.4972 |

- model - mark_type **+0.0574**, CI95 [0.0533, 0.0605] - excludes zero
- model - nice_class **+0.0803**, CI95 [0.0748, 0.0862] - excludes zero
- model - calendar **+0.1252**, CI95 [0.1174, 0.1315] - excludes zero

Persistence is not applicable here: every scored row is a new application, so no prior
observation of the same entity exists at the filing instant. Majority-class accuracy on
this split is 0.8399 - a reminder that accuracy is the wrong lens on an 84%-positive
split; the AUC ordering is where the task lives. The advantage holds in both eval filing
years (2013: 0.6233 vs 0.5639; 2014: 0.6216 vs 0.5660) at flat prevalence.

Scope of the finding, carried from `../VERIFICATION.md`: row-level intervals only (no
dependence cluster is measurable from the shipped columns), one model configuration with
no re-tuning, two filing years of eval coverage. Demonstrated headroom over these
references under this protocol - an observed result, not a bound on other models and not
an operational-validity claim.
