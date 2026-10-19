# Reproducing this dataset from a clean checkout

Nothing below needs the private repository that built it. This package is self-contained: the
runner files are shipped verbatim, the construction code is in `code/`, and every number is
checkable against `SHA256SUMS` and `MANIFEST.json`.

## 1. Get the data

```bash
python3 get_dataset.py --dest ./task                  # all 226 assets, ~3.3 GB
python3 get_dataset.py --dest ./task --config sec_56_12004     # one config (5 files, ~73 MB)
```

The repository is private until publication, so authenticate first: `gh auth login`, or export
`GITHUB_TOKEN`.

`get_dataset.py` verifies each file against the release's own recorded `size` and against
`SHA256SUMS`, and refuses the download on any mismatch. It restores the layout the runner
expects:

```
task/sec_56_12004/public/train.csv      task/sec_56_12004/public/eval.csv
task/sec_56_12004/private/holdout.csv   task/sec_56_12004/meta.json
task/sec_56_12004/quality.json          ... 45 configs ...
task/labels.csv                         (joint multi-label matrix)
```

## 2. Check the bytes

```bash
sha256sum -c SHA256SUMS        # after get_dataset.py has laid the tree out under ./task
```

`MANIFEST.json.levels` carries the **gate-produced** artifact version of each of the 45 configs,
and the top-level `artifact_version` names all 45 together (a derived label; the gate's own
values are the per-config ones). Every digest was cross-checked against the bytes preserved in
the private staging release before anything was manifested.

## 3. Re-run the qualification gate

The gate is shipped at `code/qualify_dataset.py` (version 1.3.0). Run it per config, on the
config directory:

```bash
python3 code/qualify_dataset.py ./task/sec_56_12004
```

Expect `ok: true`, **32 checks, 0 failed**. The gate is what makes a number from this dataset
usable: it tests leakage (no shipped column determines the label), prediction timing, the
splits (disjoint ordered windows, both classes in eval and holdout, the declared cluster counts),
and the runner's input contract. A number quoted from an artifact the gate has not passed is not
usable. The shipped artifact passed on all 45 configs on the worker that built it (job
`msha-002`, recorded in `VERIFICATION.md`).

## 4. Reproduce the baseline

```bash
sh baseline/reproduce_baseline.sh ./task sec_56_12004
```

Expect **eval AUC ~0.804** on `sec_56_12004` from the runner's own output, `CONTRACT OK` from
both `train.py` and the independent `validate.py` re-run. The recorded value is 0.8036 (train
AUC 0.8036 on the same run, so no overfit gap). The runner's training is not bit-reproducible
(xgboost with default threading on identical bytes), so the last decimal can move between runs;
the artifact digests do not move. The runner files are the benchmark's, copied verbatim; their
digests are in `baseline/README.md` and `MANIFEST.json`.

To work on another section, pass any config directory name: `sh baseline/reproduce_baseline.sh
./task sec_75_400`. Only `sec_56_12004` has a recorded end-to-end baseline measurement; per-config
persistence references for all 45 are in `MANIFEST.json` (`measurements.levels`).

## 5. The persistence reference

`prev_target_cited` alone - did the mine's most recent strictly-earlier inspection cite this
section - scores **0.5831** eval AUC on `sec_56_12004` (measured on the same released bytes, in
the build summary). The full 24-feature model clears it by 0.2205. This is the number that keeps
the baseline honest: the learned signal is not the target section's own persistence in disguise.

## What is deliberately not here

- The raw MSHA zips. The build (`code/build.py`, worker entrypoint `code/run.sh`) streams
  `Violations.zip`, `Inspections.zip` and `Mines.zip` from the publisher once each and writes the
  45 configs; re-running it reproduces the extract from the live source rather than from this
  release. `labels.csv` and the split files together are the shipped evidence.
- Any agent or harness comparison. None was performed; nothing about coding-agent performance is
  measured or implied.
- A scored holdout. The holdout ships labelled and has never been used for model selection,
  threshold choice or tuning. `baseline/reproduce_baseline.sh` deliberately does not copy it into
  the workspace the contract scores.
