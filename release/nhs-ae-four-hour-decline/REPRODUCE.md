# Reproducing this dataset from a clean checkout

Nothing below needs the private repository that built it. The package is self-contained: the
runner files are shipped verbatim, the construction code is in `code/`, and every number is
checkable against `SHA256SUMS` and `MANIFEST.json`.

## 1. Get the data

```bash
python3 get_dataset.py --dest ./task        # 5 files, ~4.0 MB
```

**While this repository is private (under review), `get_dataset.py` needs `GITHUB_TOKEN` or an
authenticated `gh` CLI** and downloads through the API's asset path; publication to public is
the operator's approval, and once the repository is public no credential is needed at all.
`get_dataset.py` verifies every file against the release's recorded size and sha256 and refuses
the download on any mismatch. It restores the layout the runner expects:

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
(`0990af0f90fbe304...`) and every package file's digest. The flat asset names are
`public-train.csv`, `public-eval.csv`, `private-holdout.csv`, `meta.json`, `quality.json`.

## 3. Re-run the qualification gate

The gate is shipped at `code/qualify_dataset.py` (version 1.4.0).

```bash
python3 code/qualify_dataset.py ./task
```

Expect `ok: true`, **0 failed checks**. The gate tests leakage (per-column AUC against the
target), prediction timing, units and reference frames, the temporal splits (windows and counts
recomputed from the rows) and the runner's input contract.

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

`code/build.py` enumerates the publisher's year pages, downloads the 102 monthly provider-level
CSVs and rebuilds the artifact:

```bash
python3 code/build.py --out ./rebuilt
python3 code/qualify_dataset.py ./rebuilt
sha256sum rebuilt/public/train.csv rebuilt/public/eval.csv rebuilt/private/holdout.csv
```

Two measured caveats:

- **The source is a live register.** NHS England republishes recent months as revised CSVs and
  adds a new month roughly three weeks after it ends, so a rebuild after 2026-10-21 will not
  reproduce these digests. The published artifact is the 2026-10-21 vintage;
  `meta.json`'s `built_at_utc` and `measurements.json`'s source composite sha256 identify it.
- **Datacenter IPs are blocked.** The publisher's CDN serves HTTP 202 with an empty body to
  datacenter addresses (measured 2026-10-21), so run this from a residential or office network;
  the build's client ladder records per-attempt diagnostics when a page does not return its
  expected content. The published artifact was built from the same bytes via a staged, verified
  copy (see `VERIFICATION.md`).

## 6. What the numbers mean

- The m/m-decline label is balanced in all three windows (55.5% / 50.3% / 48.6%) **by
  construction**; the underlying within-4-hour rate is not stationary (83.0% national Type 1 in
  2018, ~60% in 2025-26). A model can win on the direction without the level being learnable
  from history.
- Positives cluster within providers. The effective sample size is the distinct positive provider
  count (114 / 124 / 121), not the row count.
- The bars to beat: **target-month-of-year prior** 0.6027 eval (train-only seasonal prior) and
  **mean reversion** (`rate_m - rate_mean_6m`) 0.6562 holdout, with reversal (`rate_delta_1m`)
  0.5839 / 0.6007 and persistence (`rate_m`) 0.5758 / 0.6046 between them. Momentum is
  anti-predictive (0.4161 / 0.3993). The runner-contract XGBoost baseline measured **0.5511**
  eval AUC - below every eval reference; treat the references as the floor for a useful
  solution, and see `VERIFICATION.md` before quoting it.
