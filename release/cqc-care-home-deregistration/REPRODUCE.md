# Reproduce

Everything here runs from this repository alone - no access to any private
factory repository is needed. A clean environment needs Python 3.11+ and, for
the baseline, the benchmark's dependency ranges (pandas>=2.2,<3, numpy>=1.26,
xgboost>=3.0, scikit-learn>=1.5).

## 1. Download and verify the artifact

```bash
python3 get_dataset.py --dest ./task
```

Downloads the five release assets (flat names - GitHub forbids `/` in asset
names), restores the runner layout and refuses any file whose size or sha256
differs from the recorded values. While this repository is private, set
`GITHUB_TOKEN` (a read token is enough); after publication no credential is
needed.

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

The gate (1.5.0) re-checks the full artifact from the rows: leakage (every
shipped column scored for single-column separation of the target), prediction
timing, units and reference frames, temporal splits (disjoint, ordered, both
classes, clustered event counts) and runner compatibility. It exits 0 only
when every check passes. The recorded report is `qualification.json`; to
re-verify that exact report against your downloaded bytes:

```bash
python3 code/qualify_dataset.py --accept qualification.json ./task
```

## 3. Reproduce the baseline

```bash
sh baseline/reproduce_baseline.sh ./task
```

Materializes a runner workdir from the public splits only (`task.json` +
`data/train.csv` + `data/eval.csv`; the private holdout is never copied),
then runs the benchmark's own `train.py` and `validate.sh` unmodified. Both
must print the same Eval AUC. The recorded result on the released bytes, from
both implementations: **eval AUC 0.5659** - which must be quoted beside the
headroom reference `rating_x_beds_rate` **0.5871** (see README, VERIFICATION
and measurements.json; the stock runner trailing that reference is a
recorded defect of the runner, not a property of the task).

## 4. Rebuild from the CQC source

```bash
python3 code/build.py --out ./extract
```

`build.py` (stdlib-only) re-downloads the pinned CQC source bytes - the
January HSCA Active Locations vintages 2016-2022 + 2024 + 2025 from CQC's
public Google Drive archive and the 2026-11-02 Deactivated Locations edition -
verifies every sha256, walks the workbook to the Location ID header sheet
(dropping no-header vintages loudly), builds the panel with the per-instant
pseudonymised identity, writes the runner layout, then `code/run.sh` runs
gate -> exact-byte accept -> the post-acceptance references (`code/score.py`).
A rebuild reproduces the artifact byte-identically (fixed `--built-at`).

## Checksums

`SHA256SUMS` carries the five artifact digests; `MANIFEST.json` additionally
hashes every file in this package and records the staging provenance, the
licenses block and the measured baseline block.
