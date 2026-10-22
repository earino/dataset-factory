# Reproduce

Everything below was executed against the published bytes of this release; the exact
commands and their results are in `VERIFICATION.md`. Nothing requires access to any
private repository.

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
on the downloaded bytes. Gate version 1.4.0 passed all 37 checks on this artifact.

## 3. Re-accept against the recorded report

```bash
python3 code/qualify_dataset.py --accept qualification.json ./task
```

Proves the downloaded bytes still hash to the artifact version the gate passed
(`e75a59bb1116e39b...`), not merely to something plausible.

## 4. Reproduce the baseline

```bash
sh baseline/reproduce_baseline.sh ./task
```

Materializes the runner workdir the way the benchmark's `bench/workdir.py` does (public
splits only; the holdout is never copied) and runs the benchmark's own unmodified
`train.py` + `validate.sh`. Recorded result: eval AUC 0.8126, printed identically by both
entry points (`CONTRACT OK`). Dependencies: `pandas>=2.2,<3`, `numpy>=1.26`,
`xgboost>=3.0`, `scikit-learn>=1.5`.

## 5. Rebuild from the source (full construction)

`code/build.py` is the exact construction script that produced this artifact
(sha256 6774fe88bd493971..., the bytes worker job tsb-004 executed). It downloads the
five RODSdb public CSVs from the publisher with a browser-like header set (plain HTTP
clients are refused 403; the required headers are recorded in the script), decodes the
three mixed coordinate encodings, derives the label and splits, writes the runner
layout, and self-checks the panel start, the coordinate envelope, label integrity
against the INJURIES child table, and the publisher's own annual-summary counts.
`code/run.sh` is the worker entrypoint that ran it (build + gate, exit non-zero on any
assertion failure). Source vintage for this artifact: the five CSVs as last-modified
2026-10-21 16:49-16:52 GMT (sha256 recorded in `meta.json` / `MANIFEST.json`).

Rebuilding from a later monthly vintage will produce a different artifact (new
occurrences arrive monthly); that is expected, and a rebuilt artifact must be
re-qualified from scratch before any number from it is quoted.
