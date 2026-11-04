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

The stock XGBoost baseline scored **Eval AUC 0.5107** on the 14,965 eval
rows (2023, 8.39% positive). On the identical rows it sits **at chance**
- below the strongest simple reference, below persistence, calendar and even
the identity-only control:

| Reference / model | Eval AUC |
| --- | --- |
| `morning_ratio` (morning_max / hist_morningpeak_mean_90, from shipped columns) | **0.7340** |
| `month_only` (train-fitted month rate) | 0.6541 |
| `calendar_identity` (station x month rate from train) | 0.6504 |
| `persistence_prev_evening` (info-asymmetric by design) | 0.6502 |
| `identity_only` (station rate from train) | 0.5134 |
| Full model (this baseline) | **0.5107** |

By the operator's recorded decision (a), this package is an **agent-headroom
benchmark**: the consumer is an agent that edits `train.py`, and
`morning_ratio` - one line over shipped at-instant columns - is the natural
first target to beat. The global constant is degenerate as a score;
majority-class accuracy on eval is 0.9161 but a constant carries no ranking
information. `persistence_prev_evening` is recomputed scorer-side from
strictly-earlier same-station rows (the model is denied the prior evening's
outcome - information-asymmetric by design), while `morning_ratio` is a fair
same-information target. No model above the reference has been measured.
Quote no model figure from this dataset without the ladder above beside it.
