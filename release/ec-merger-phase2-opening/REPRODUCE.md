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
46/46 checks on the full artifact on the build worker. It re-checks leakage
(every shipped column scored against the target), prediction timing, the
evaluation contract, split integrity (disjoint windows, both classes, clustered
positive events) and the runner contract (meta counts). Expect: `OK`.

## 3. Re-run the runner-contract baseline

```bash
pip install "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
sh baseline/reproduce_baseline.sh ./task
```

Materializes a workdir the way the benchmark's `bench/workdir.py` does (`task.json`
from `meta.json`, public train+eval only - the private holdout is never copied into a
workdir), then runs the benchmark's own `train.py` and `validate.sh`, unmodified.
Expect both to print **Eval AUC: 0.6973** on the 1,770 eval rows (the exact figures
measured on these bytes are in `VERIFICATION.md`; a materially different number means
the bytes or the runner were changed).

## 3b. Re-run the reference scores and the paired bootstrap

The comparator recipes that produced every reference figure (sector-division prior,
sector-combination rate, calendar identity, title-token rate, recent rate) and the
paired row-bootstrap differences are shipped in this release: `code/score.py`
(references + `paired_bootstrap_difference`, the exact RNG recipe and draw count
used for the published intervals) and `code/report.py` (the worker-side report
assembly that calls it):

```bash
python3 code/qualify_dataset.py ./task --report gate-report.json
python3 code/score.py --data ./task --report references.json --accepted-report gate-report.json
```

`score.py` refuses to score unless the gate report passed and binds its output to
the artifact digest. Expect the reference AUCs recorded in `measurements.json`
(sector_division_rate 0.7679, calendar_identity 0.5606, recent_rate 0.5000,
full-model stock 0.6973) and the paired bootstrap intervals recorded there.
The independent pre-flip audit (2026-10-27) reproduced the stock and
sector-prior figures from these bytes with its own frozen recipes and confirmed
the honest negative paired difference; its untuned logistic variant scored
0.8144 eval / 0.7767 holdout, so the stock figure is a reproducible weak
baseline, not a ceiling.

## 4. Rebuild from source (optional)

`code/build.py` is the construction script. It fetches the publisher's current daily
snapshot of the register, so a re-run today pins a **newer vintage** than the released
one and can legitimately differ in the holdout (live cases arrive, pending cases
mature); train/eval rows for the closed 1990-2018 windows are expected to reproduce
byte-identically except for register corrections:

```bash
python3 code/build.py --out ./rebuilt --work-dir ./work
python3 code/qualify_dataset.py ./rebuilt
```
