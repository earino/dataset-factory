# Reproducing this release

```bash
sh baseline/reproduce_baseline.sh ./task
```

The script builds the runner workdir from the public splits (the holdout is never copied), runs the
harness's own `train.py`, then `validate.sh`; both must print the same eval AUC.

Rebuilding from source: `python3 code/build.py --out <extract>`, which fetches the OAD panel from
the ABS Data API (`https://api.data.abs.gov.au/data/OAD_COUNTRY/...`) and applies the publication-lag
gate. The API is anonymous and documented.

Checksums: `sha256sum -c SHA256SUMS` from the package root (the manifest names nested paths).
