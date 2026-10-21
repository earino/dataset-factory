# Reproducing this dataset from a clean checkout

Nothing below needs the private repository that built it. The package is self-contained: the
runner files are shipped verbatim, the construction code is in `code/`, and every number is
checkable against `SHA256SUMS` and `MANIFEST.json`.

## 1. Get the data

```bash
python3 get_dataset.py --dest ./task        # 5 files, ~6.6 MB
```

The repository is public, so no credential is needed. `get_dataset.py` verifies every file against
the release's recorded size and sha256 and refuses the download on any mismatch. It restores the
layout the runner expects:

```
task/public/train.csv      task/public/eval.csv
task/private/holdout.csv   task/meta.json      task/quality.json
```

## 2. Check the bytes

```bash
sha256sum -c SHA256SUMS      # run in a directory holding the five flat asset names
python3 -c "import json;print(json.load(open('MANIFEST.json'))['artifact_version'])"
```

`MANIFEST.json` records the artifact version the qualification gate produced
(`b1323a27fa02eb79...`) and every package file's digest. The flat asset names are
`public-train.csv`, `public-eval.csv`, `private-holdout.csv`, `meta.json`, `quality.json`.

## 3. Re-run the qualification gate

The gate is shipped at `code/qualify_dataset.py` (version 1.3.0).

```bash
python3 code/qualify_dataset.py ./task
```

Expect `ok: true`, **0 failed checks**. The gate is what makes a number from this dataset usable: it
tests leakage, prediction timing, units and reference frames, the splits and the runner's input
contract. It also re-checks the known-event fixture and the systematic-negative frame rule against
the written rows.

## 4. Reproduce the baseline

```bash
pip install "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
sh baseline/reproduce_baseline.sh ./task
```

This materializes the runner workdir exactly as the benchmark's `bench/workdir.py` does - public
train and eval only; the private holdout is never copied - and runs the benchmark's own
`train.py` and `validate.sh`, unmodified. Both print an Eval AUC; they must agree. The measured
result is recorded in `VERIFICATION.md`.

## 5. Rebuild from the source (optional)

`code/build.py` downloads the publisher's full table (one request, ~32 MB) and rebuilds the
artifact byte-identically:

```bash
python3 code/build.py --out ./rebuilt
python3 code/qualify_dataset.py ./rebuilt
sha256sum rebuilt/public/train.csv rebuilt/public/eval.csv rebuilt/private/holdout.csv
```

The source is a live register: WHO updates FluNet weekly, so a rebuild after 2026-10-20 will pick
up later weeks and is **not expected** to match these digests. The published artifact is the
2026-10-20 vintage; `meta.json`'s `built_at_utc` and `measurements.json`'s source sha256 identify
it.

## 6. What the numbers mean

- The base rate differs between splits by design of the phenomenon, not by sampling: 59.2% train,
  23.9% eval, 40.7% holdout. A model scored on eval only is scored on the COVID-era trough.
- Positives cluster by country-season. The effective sample size is the distinct country-year
  count (235 / 257 / 422), not the row count.
- Persistence (score = week W's own positivity) is a strong reference: 0.8929 AUC on eval, 0.8745
  on holdout. The runner-contract XGBoost baseline is in `VERIFICATION.md`; treat both as floors
  for a useful solution.