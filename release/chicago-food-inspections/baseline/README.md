# The recorded baselines

This directory holds the runner-contract baselines: one per shipped config, run through the
benchmark runner's **existing** training and validation contract, unmodified.

- `train.py`, `validate.py`, `validate.sh` are bundled **verbatim** from `earino/harness_benchmark`
  (`task_template/`). Their SHA-256 digests are recorded in `MANIFEST.json`; they are not edited
  here, and a change to any of them would show up as a hash mismatch rather than as a quietly
  better score.
- `reproduce_baseline.sh` copies them into a scratch workdir, materializes one config's task from
  the downloaded dataset (`code/materialize.py`, which mirrors the benchmark's `bench/workdir.py`),
  and runs the two contract steps.
- The factory repository's `candidates/chicago-food-inspections/baseline/baseline_result.json`
  records what the recorded run produced on the accepted artifact, all 40 configs in one job.

## Run it

```sh
python3 get_dataset.py --dest ./task --config code_38
sh baseline/reproduce_baseline.sh ./task code_38
```

Pass any shipped config's name (`code_01` … `code_60`; the 40 shipped ones are listed in
`README.md`) as the second argument. The script installs the runner's declared dependency ranges if
they are missing, then prints:

- `Eval AUC: <value>` from `train.py`, and the same from `validate.py`'s independent
  `predict_proba` recompute;
- `[validate] CONTRACT OK`.

## What the baseline is not

It is one baseline per config through the contract, not a leaderboard entry and not a model
comparison. No agent or harness run was performed against this dataset, and none is implied by
these numbers. Their only job is to show that the published bytes are loadable, that each task is
learnable at all, and that a consumer can reproduce the recorded value exactly. Each config's
recorded AUC should be read against **that config's own eval positive rate**, which ranges from
0.0015 to 0.56 across the suite — a rate-0.56 config and a rate-0.0015 config are not comparable
tasks.

The **private holdout is never copied into a workdir** — `materialize.py` copies `public/train.csv`
and `public/eval.csv` only. The holdout exists for later scoring by the harness, not for these
baselines, and nothing in this package scores it.
