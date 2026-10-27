# Reproduce

Everything below runs from a fresh clone of this repository with no access to any
private factory repository. The only requirements are Python 3.11+ and network access
to this repository's release (plus `GITHUB_TOKEN` with `repo` scope **while the
repository is private**; once public, no credential is needed).

## 1. Download and verify the artifact

```bash
python3 get_dataset.py --dest ./task
```

Downloads the five release assets (`public-train.csv`, `public-eval.csv`,
`private-holdout.csv`, `meta.json`, `quality.json`), verifies every byte against the
sizes and sha256 digests recorded inside the script (and cross-checkable against
`SHA256SUMS` and `MANIFEST.json`), and lays out the runner tree:

```
task/public/train.csv  task/public/eval.csv  task/private/holdout.csv
task/meta.json         task/quality.json
```

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

This is the same gate (shipped verbatim in `code/qualify_dataset.py`) that passed
45/45 checks on the full artifact on the build worker. It re-checks leakage
(every shipped column scored against the target), prediction timing, the evaluation
contract, split integrity (disjoint windows, both classes, clustered positive
events) and the runner contract (meta counts), and executes the declared cross-row
probe. Expect: `OK`.

## 3. Re-run the runner-contract baseline

```bash
pip install "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
sh baseline/reproduce_baseline.sh ./task
```

Materializes a workdir the way the benchmark's `bench/workdir.py` does (`task.json`
from `meta.json`, public train+eval only - the private holdout is never copied into a
workdir), then runs the benchmark's own `train.py` and `validate.sh`, unmodified.
Expect both to print **Eval AUC: 0.5393** on the 1,887 eval rows (the exact figures
measured on these bytes are in `VERIFICATION.md` and `RELEASE_NOTES.md`, including
the references that outscore the stock model; a materially different number means
the bytes or the runner were changed).

## 4. Rebuild from source (optional)

`code/build.py` is the construction script. It fetches the HDX resource's current
distribution, so a re-run today pins a **newer vintage** than the released one and can
legitimately differ (later label years appear, live-edge rows mature); the closed
train/eval windows are expected to reproduce except for publisher revisions:

```bash
python3 code/build.py --out ./rebuilt
python3 code/qualify_dataset.py ./rebuilt
```

## 5. Recompute the references (optional)

`code/score.py` is the reference implementation the release's figures come from. It
refuses to run unless the accepted report passed, fits its priors on train only, and
evaluates on the eval split's own labels. The gate's own collected report ships with
this package as `qualification.json`:

```bash
python3 code/score.py --data ./task --accepted-report qualification.json --report refs.json
```

Expect the eval references in `refs.json` to match `RELEASE_NOTES.md` (momentum
0.574165, surge flag 0.585619, calendar/identity 0.540927, recent-era constant 0.5 -
a constant with no ranking information).

