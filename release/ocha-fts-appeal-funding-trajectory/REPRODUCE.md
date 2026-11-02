# Reproducing this dataset

Everything needed is in this repository. No access to any private factory
repository is required. The data arrives as five release assets, each verified
against `SHA256SUMS` and `MANIFEST.json`.

## 1. Download and verify

```bash
python3 get_dataset.py --dest ./task
```

Downloads the five assets (`public-train.csv`, `public-eval.csv`,
`private-holdout.csv`, `meta.json`, `quality.json`) from this repository's
`v2026.11` release, checks every size and sha256 against the recorded values,
and restores the runner layout `./task/{public,public,private}/*.csv` +
`meta.json` + `quality.json`.

While the repository is private (under review) the script needs `GITHUB_TOKEN`
or an authenticated `gh` CLI; once public, no credential is needed.

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

The gate (version 1.5.0) re-checks leakage over the shipped columns, the timing
declaration, split disjointness and both-classes presence, and the runner input
contract, directly against the rows. The staged artifact passed it on the worker
(job fts-appeal-003) and the same bytes passed exact-byte `--accept` again after
download (job fts-baseline-002).

## 3. Reproduce the runner-contract baseline

```bash
python3 -m pip install "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
sh baseline/reproduce_baseline.sh ./task
```

`train.py` and `validate.sh` are the benchmark's own runner files, verbatim. The
workdir is materialized from the public splits only - the private holdout is
never copied. Expected result on these bytes: **Eval AUC 0.6452** from both
`train.py` and `validate.py`'s independent recompute. The full comparison that
qualifies the number (persistence 0.7171 and the other references on the
identical rows) is in `measurements.json` and `VERIFICATION.md`.

## 4. Rebuild from the source (full path)

```bash
python3 code/build.py --out <extract-dir>
```

`code/build.py` is the exact construction script the accepted artifact was built
from (job fts-appeal-003; commit recorded in `MANIFEST.json`). It fetches the
pinned inputs from OCHA's public endpoints (HDX bulk CSV, HPC plan/flow API),
asserts the in-build fixtures (AFG 2023, YEM 2023, Burundi RRP 2021), builds the
panel with every exclusion counted, and writes the five artifact files.

Source-pin caveat, stated rather than hidden: the FTS API exposes **no
historical vintages** (checked at construction). Rebuilding today fetches the
publisher's current vintage of the same plan/flow records, so a rebuild is
expected to match the shipped bytes only while the publisher's data has not
moved. The shipped artifact is pinned by digest; a rebuild is a provenance
check, not a byte-identity promise.

## 5. The worker run order (what the original job did)

`code/run.sh` is the exact order the worker executed: **construct -> qualify
(gate, full artifact) -> exact-byte accept -> score** - each stage stops the
next, and no performance number exists before acceptance. `code/score.py` is
the references implementation (persistence, rate references, majority-class
accuracy), run post-acceptance only, holdout never opened.
