# The recorded baseline

This directory holds one baseline, run through the benchmark runner's **existing** training and
validation contract, unmodified.

- `train.py`, `validate.py`, `validate.sh` are bundled **verbatim** from `earino/harness_benchmark`
  (`task_template/`). Their SHA-256 digests are recorded in `MANIFEST.json`; they are not edited
  here, and a change to any of them would show up as a hash mismatch rather than as a quietly
  better score.
- `reproduce_baseline.sh` copies them into a scratch workdir, materializes the task from the
  downloaded dataset (`code/materialize.py`, which mirrors the benchmark's `bench/workdir.py`), and
  runs the two contract steps.
- `../candidates/chicago-doah-adjudication/baseline/baseline_result.json` in the factory repository
  records what that run produced on the accepted artifact.

## Run it

```sh
python3 get_dataset.py --dest ./task
sh baseline/reproduce_baseline.sh ./task
```

The script installs the runner's declared dependency ranges if they are missing, then prints:

- `Eval AUC: <value>` from `train.py`, and the same from `validate.py`;
- `[validate] CONTRACT OK`.

## What the baseline is not

It is **one** baseline through the contract, not a leaderboard entry and not a model comparison. No
agent or harness run was performed against this dataset, and none is implied by this number. Its
only job is to show that the published bytes are loadable, that the task is learnable at all, and
that a consumer can reproduce the recorded value exactly.

The **private holdout is never copied into a workdir** — `materialize.py` copies `public/train.csv`
and `public/eval.csv` only. The holdout exists for later scoring by the harness, not for this
baseline, and nothing in this package scores it.
