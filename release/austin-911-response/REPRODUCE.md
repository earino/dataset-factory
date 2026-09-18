# Reproduce this version

Everything here runs from public sources. The private factory repository is where the pipeline
lives, but **it is not needed to rebuild or to evaluate this dataset**.

## 1. Rebuild the dataset from source

```bash
# build.py is stdlib-only Python 3.13; no packages to install.
# Fetch it from the pinned revision that produced this artifact:
#   repository: earino/dataset-factory   (private)
#   commit:     06d7002bc01933e4c094bbe84e4d9899572a893f   (2026-09-18T19:34:24Z)
#   file:       candidates/austin-911-response/source/build.py
#   sha256:     e3a82b4739d1481dc44fd2e8211d7cba605250896de94c4d0748677368d23ea4

python3 build.py --out /tmp/extract --built-at 2026-09-18T19:36:55.770697+00:00
```

**Pass `--built-at`.** `meta.json` embeds the build timestamp, so without it a rebuild differs
from this artifact in that one field and its `artifact_version` will not match. The pin is the
timestamp recorded in this release's `MANIFEST.json` (`built_at_utc`). This is not a
technicality: the first attempt at reproducing this version rebuilt all three split files
byte-for-byte and still failed verification for exactly this reason.

The script fetches the City of Austin catalogue anonymously over the Socrata API (about 53
paginated requests of 20,000 rows, ordered by `incident_number,:id`), derives the label, writes
the three splits in the runner's layout, and writes `meta.json`, `quality.json`, `manifest.json`
and `summary.json`.

**Measured cost:** 353.7 s wall clock on a 2-vCPU / 2 GB machine, ~136 MB of output.

**Do not expect byte-identical output on a later date.** The source is a live catalogue the City
updates, so a rebuild after 2026-09-18 will include later rows and any revisions. This version's
identity is its hashes, not its source URL.

## 2. Verify what you downloaded

```bash
sha256sum -c SHA256SUMS
```

`SHA256SUMS` covers the five artifact files. Their combined artifact version is
`e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`.

## 3. Check the dataset against its own declarations

The qualification gate is versioned with the dataset and is stdlib-only:

```bash
python3 qualify_dataset.py <extract-dir>          # prints every check and exits non-zero on any failure
python3 qualify_dataset.py --selftest             # proves the gate still rejects its broken fixtures
```

The reported run was **gate 1.3.0, 33 checks, 0 failures**, executed on the worker over the full
artifact. Two earlier builds failed and both failures were gate defects, documented in the
factory's record; neither was a data defect.

## 4. Reproduce the baseline

The baseline is the harness benchmark's own `train.py`, run **unmodified** against this dataset
in the runner's contract: `task.json` plus `data/train.csv` and `data/eval.csv`, with the
holdout excluded.

Task materialization follows the benchmark's `bench/workdir.py`: `task.json` carries
`name`, `description`, `target`, `positive_label`, `id_columns`, `split`, `columns`, `rows`;
`data/train.csv` and `data/eval.csv` are the public split; **the holdout is never copied into a
workdir.**

**Runner files used, by hash** — unmodified from the benchmark revision:

| file | sha256 |
|---|---|
| `train.py` | `a3c6bcf13735bc85c52129ded68f839090dffdc266ebc3810dc61b2e6ea5e7e8` |
| `validate.py` | `b597e7f84fed614e64b4a86fbecbd6ec0145916a24d0d221a796586976418e7b` |
| `validate.sh` | `3f06ca48f11c2e05d331b4d8394284925de660c1d4b086d2f8243959e83b7e6d` |

**Dependency ranges** (from the benchmark's `pyproject.toml`):
`pandas>=2.2,<3`, `numpy>=1.26`, `xgboost>=3.0`, `scikit-learn>=1.5`. The versions actually
resolved in the recorded run are in `MANIFEST.json` under `baseline.dependencies`.

**Commands:**

```bash
python3 -m pip install "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
cd <task-dir>            # task.json + data/train.csv + data/eval.csv + the three runner files
python3 train.py         # trains, prints "Eval AUC: <x>"
sh validate.sh           # runs validate.py: checks the contract and re-scores via predict_proba
```

`train.py` prints `Eval AUC:` on the eval split; `validate.py` re-runs it, confirms
`predict_proba(df)` exists and returns finite probabilities in [0, 1], and prints
`[validate] CONTRACT OK`.

**Measured result of the recorded run:**

| | |
|---|---|
| `train.py` eval AUC | **0.7691** |
| `validate.py` eval AUC (via `predict_proba`) | **0.7691** |
| `train.py` exit / `validate.sh` exit | 0 / 0 |
| `[validate] CONTRACT OK` | yes |
| train / score time | 2.6 s / 0.3 s |
| resolved dependencies | Python 3.13.15, pandas 2.3.3, numpy 2.5.3, xgboost 3.4.1, scikit-learn 1.9.1 |

Both AUC figures agreeing matters: `train.py` scores its own in-memory model, while
`validate.py` re-runs the file and scores through `predict_proba(df)` with the target column
removed — so the contract is satisfied, not just the training script.

## 5. What is *not* reproduced here

**No agent or harness comparison.** This release contains one baseline through the runner's
contract. Comparing coding agents or harnesses on this dataset is a separate milestone and no
result of that kind exists yet.
