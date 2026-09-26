# Reproduce this dataset

Everything here is reproducible **from this repository alone**. No credential is needed: the
source is the City of Chicago's open Socrata endpoint and is read anonymously.

## 1. Rebuild the extract

```bash
python3 code/build.py --out /tmp/extract --built-at 2026-09-26T20:00:00+00:00
```

`code/build.py` is stdlib-only Python 3.13. It issues **18 requests** — one `count(*)` probe and
17 pages of 50,000 rows, ordered by the publication's own `id` — and reduces each case's charge
rows to one row. The same requests, in the same order, produce the same bytes: the reduction
selects a case's lead charge by `(violation_date, violation_code, row id)`, so it does not depend
on the order rows arrive in.

**Pass `--built-at`.** `meta.json` embeds the build timestamp, so without it a rebuild differs in
that one field and its artifact version will not match. The pin above is this release's recorded
`built_at_utc` (`measurements.json` → `extraction_cost.built_at_utc`).

Then check the rebuild against the recorded hashes:

```bash
cd /tmp/extract && sha256sum -c /path/to/repo/SHA256SUMS
```

**Measured cost of extraction.** 93.4 s wall clock and **345 MB peak RSS** for the full build,
producing 4,245,521 bytes of CSV, on the orchestration host (4 vCPU, 1.9 GiB RAM). The same build
inside the qualification worker (2 vCPU, 2 GB, `cpx32`, Helsinki) took 92.6 s for the whole job
including the gate. The rebuild was run independently on both machines and matched on all five
digests, byte for byte.

## 2. Re-run the qualification gate

`code/qualify_dataset.py` is the gate that gated this version — the file itself, not a
re-implementation:

```bash
python3 code/qualify_dataset.py ./task            # all checks, exit non-zero on any failure
python3 code/qualify_dataset.py --selftest        # proves the gate still rejects its broken fixtures
```

The released version passed **32 checks, 0 failures**, gate version 1.3.0, over the full artifact
(4.25 MB of rows, not a sample). Coverage:

- *Leakage* — every shipped column declared (feature, identifier, high-cardinality, or label
  source); no answer source or post-hoc column shipped; no single shipped column determines the
  target on its own; the label source is not a feature.
- *Prediction timing* — the prediction instant declared; every feature documented as available at
  docketing; post-hoc columns declared and absent.
- *Splits* — files present and non-empty; both classes in eval and holdout; declared positive
  counts recomputed from the rows; clustered event counts recomputed; **no identifier spans two
  splits**; rates not uniform; actual date ranges disjoint and inside the declared windows; enough
  independent positive events.
- *Runner compatibility* — holdout private, train/eval public; `meta.json` carries every key the
  runner reads and agrees with the files; identifiers are not also features.

## 3. Reproduce the baseline

```bash
sh baseline/reproduce_baseline.sh ./task     # ./task is what get_dataset.py produces
```

This runs the benchmark's own `train.py` and `validate.sh` **unmodified** — the three runner files
are bundled in `baseline/` and their SHA-256 hashes are recorded in `MANIFEST.json` and in the
run's own report, so "the existing runner" is checkable rather than asserted. Task materialization
mirrors the benchmark's `bench/workdir.py`: `task.json` carries the keys the runner reads, and
`data/train.csv` + `data/eval.csv` come from the public split. **The private holdout is never
copied into a workdir.**

The script installs the benchmark's declared dependency ranges (`pandas>=2.2,<3`, `numpy>=1.26`,
`xgboost>=3.0`, `scikit-learn>=1.5`) if they are missing.

The recorded run was made on a worker of its own (`chicago-baseline-001`), which also **rebuilt
the accepted artifact and refused to measure it unless the rebuild was byte-identical** to the
artifact that passed qualification; see `baseline/baseline_result.json` for that run's evidence,
including the dependency versions it actually used.

## Reproducibility, stated honestly

- **The build is deterministic.** Two independent machines produced identical digests for all
  five files.
- **The source is not frozen.** The City republishes this dataset daily. A rebuild today may
  return more rows than this version has; the version is defined by the hashes in `MANIFEST.json`
  and the counts in `measurements.json`, not by the endpoint. The frozen extract's source-side
  digests (`source_rows_sha256`, `case_table_sha256`) are recorded there so a drift is visible
  rather than silent.
- **`violation_code` and `ward` are strings**, deliberately: leading zeros are significant and
  `ward` `0` is a real published value.
