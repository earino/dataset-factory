# Reproducing this release

```bash
sh baseline/reproduce_baseline.sh ./task
```

The script builds the runner workdir from `public/train.csv` and `public/eval.csv` (the holdout is
never copied), runs the harness's own `train.py`, then `validate.sh`. Both must print the same eval
AUC.

Rebuilding the artifact from source:

```bash
python3 code/prep.py --dir <monthly-csv-dir> --delete-csv   # 36 monthly files -> weekly parquet
python3 code/build.py --source-dir <monthly-csv-dir> \
    --lookup lookup_premise.csv --state Johor --out <extract>
```

The source is a live feed: monthly files are revised, so a later rebuild will not reproduce these
bytes. The artifact version in `MANIFEST.json` pins the vintage.

Checksums: `sha256sum -c SHA256SUMS` from the package root (the manifest names nested paths).
