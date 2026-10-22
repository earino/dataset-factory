# Reproduce

Everything below was executed against the staged bytes of this release; the exact
commands and their results are in `VERIFICATION.md`. Nothing requires access to any
private repository once the release is public.

## 1. Download and verify

```bash
python3 get_dataset.py --dest ./task
```

Downloads the five release assets, verifies each against its recorded size and sha256,
and restores the runner layout (`public/train.csv`, `public/eval.csv`,
`private/holdout.csv`, `meta.json`, `quality.json`). Checksums: `sha256sum -c SHA256SUMS`.

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

The gate (shipped verbatim in `code/`) re-checks leakage over the shipped columns,
prediction timing, units and reference frames, temporal splits and runner compatibility
on the downloaded bytes. Gate version 1.4.0 passed all 38 checks on this artifact.

## 3. Re-accept against the recorded report

```bash
python3 code/qualify_dataset.py --accept qualification.json ./task
```

Proves the downloaded bytes still hash to the artifact version the gate passed
(`3540ad2180d8df8a...`), not merely to something plausible.

## 4. Reproduce the baseline

```bash
sh baseline/reproduce_baseline.sh ./task
```

Materializes the runner workdir the way the benchmark's `bench/workdir.py` does (public
splits only; the holdout is never copied) and runs the benchmark's own unmodified
`train.py` + `validate.sh`. Recorded result: eval AUC 0.9199, printed identically by
both entry points (`CONTRACT OK`). Dependencies: `pandas>=2.2,<3`, `numpy>=1.26`,
`xgboost>=3.0`, `scikit-learn>=1.5`.

## 5. Rebuild from the source (full construction)

`code/build.py` is the exact construction script that produced this artifact
(sha256 72ad5626c72673c4..., the bytes worker job eutl-001 executed). It downloads the
Union Registry daily bulk extract (one anonymous GET, ~6 MB) plus the EEA aggregate zip
(~10.8 MB) used for the in-build publisher cross-check, builds the
(registry, installation, compliance year) panel with settlement-lagged features, writes
the runner layout and `quality.json`, asserts the known-event fixtures (the three AT
installation-1 sample rows and the phase-3 allocation-cut rate jump) and the EEA
cross-check on the written rows, then the qualification gate runs over the exact
artifact - the job fails when the gate fails. `code/run.sh` is the worker entrypoint
that ran it. Source vintage for this artifact: the daily extract as last-modified
Thu, 22 Oct 2026 10:08:26 GMT, `SNAPSHOT_DATE` 2026-10-22 (sha256 recorded in
`meta.json` / `MANIFEST.json`). `--panel-file/--eea-file` accept local copies for a
full-assertion dry run without a worker.

Rebuilding from a later daily vintage will produce a different artifact (live 2026
rows gain verified emissions once they are reported, due 31 March 2027); that is
expected, and a rebuilt artifact must be re-qualified from scratch before any number
from it is quoted.
