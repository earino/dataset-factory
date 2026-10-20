# Reproduce this dataset

Everything here is reproducible **from this repository alone**. No credential is needed to read the
source: the City of Chicago's Socrata endpoint is anonymous. (Until the release is made public, a
credential is needed to *download the assets*; `get_dataset.py` explains.)

## 1. Rebuild the extract

```bash
python3 code/build.py --out /tmp/extract --built-at 2026-10-05T08:14:23.594735+00:00
```

`code/build.py` is stdlib-only Python 3. It issues **47 requests** — one `count(*)` probe and 46
pages of 5,000 rows ordered by `inspection_id` (unique per row, so the paging order is total and
stable) — reduces each row to the 18-column shape, derives the licence-history features, and writes
one runner config per floor violation code plus the joint `labels.csv`.

**Pass `--built-at`.** Each config's `meta.json` embeds the build timestamp, so without the pin a
rebuild differs in that one field and the artifact version will not match. The pin above is this
release's recorded build time (`measurements.json` → `extraction_cost`).

**Measured cost of extraction** (job `food-001`, worker `cx23`, Helsinki, 2 vCPU / 4 GB): **510 s**
wall clock for the full build of all 40 configs, 46 pages, producing 1,260,504,640 bytes of split
files plus the 24,319,192-byte `labels.csv`. A bounded probe on the coordinator class measured
20,000 rows in **5 requests, 28,948,432 bytes, 23.2 s** — the full pull's ~458 MB figure in the
candidate record is an **estimate** derived from that probe by arithmetic, labelled as one.

Then check the rebuild against the recorded hashes:

```bash
cd /tmp/extract && sha256sum -c /path/to/repo/SHA256SUMS
```

The source is republished continuously, so a rebuild **today** will return more rows than this
version has; the version is defined by the hashes in `MANIFEST.json`, not by the live endpoint.

## 2. Re-run the qualification gate

`code/qualify_dataset.py` is the gate that gated this version — the file itself, not a
re-implementation. Each config is gated on its own:

```bash
python3 code/qualify_dataset.py ./task/code_38          # one config, all checks
python3 code/qualify_dataset.py --selftest             # the gate still rejects its broken fixtures
```

The released version passed **32 checks, 0 failures, on every one of the 40 configs** (gate version
1.3.0, run on the worker over the full artifact — 1.19 GB of rows, not a sample). Coverage per
config:

- *Leakage* — every shipped column declared (feature, identifier, high-cardinality, or label
  source); no answer source or post-hoc column shipped; no single shipped column determines the
  target on its own; the label source (`violations`) and the inspection outcome (`results`) are
  absent from the files, not merely unlisted.
- *Prediction timing* — the prediction instant declared (the inspection's opening); every feature
  documented as available then; the post-hoc columns declared and absent.
- *Splits* — files present and non-empty; both classes in eval and holdout; declared positive counts
  recomputed from the rows; no identifier in two splits; actual date ranges disjoint and inside the
  declared windows; enough independent positive days per window.
- *Runner compatibility* — holdout private, train/eval public; `meta.json` carries every key the
  runner reads and agrees with the files; identifiers are not also features.

## 3. Reproduce a baseline

```bash
sh baseline/reproduce_baseline.sh ./task code_38    # ./task is what get_dataset.py produces
```

This runs the benchmark's own `train.py` and `validate.sh` **unmodified** — the three runner files
are bundled in `baseline/` and their SHA-256 hashes are recorded in `MANIFEST.json` and in the run's
own report, so "the existing runner" is checkable rather than asserted. Task materialization mirrors
the benchmark's `bench/workdir.py`: `task.json` carries the keys the runner reads, and
`data/train.csv` + `data/eval.csv` come from the config's public split. **The private holdout is
never copied into a workdir.**

The script installs the benchmark's declared dependency ranges (`pandas>=2.2,<3`, `numpy>=1.26`,
`xgboost>=3.0`, `scikit-learn>=1.5`) if they are missing.

The recorded run (`food-baseline-003`) measured **all 40 configs in one job**: each config's bytes
were fetched from the release staging, re-accepted through the gate's `--accept` against the gate's
own collected report for that config (so the scored bytes are proved to be the qualified bytes
before anything is measured), then trained and validated. See `MANIFEST.json` → `baseline` for the
recorded per-config values and the evidence trail.

## Reproducibility, stated honestly

- **The build is deterministic** in construction (fixed page order over a unique key, fixed
  reduction), but the **source is live**: the City republishes this dataset continuously, so a
  rebuild today will not reproduce these bytes from the endpoint. The version is the hashes, and
  the frozen extract's counts are recorded in `measurements.json` so drift is visible rather than
  silent.
- **The 40 configs are not 40 different datasets.** Every config ships the identical pool, the
  identical 18 columns and the identical splits; only the target column (`code_<NN>`) and the one
  config-specific feature `prev_code_present` differ.
- **The other codes' labels are deliberately absent from each config.** They parse from the same
  post-visit `violations` blob as the target, so shipping them as features would be cross-label
  leakage. The joint matrix ships separately as `labels.csv` for consumers who want the set
  formulation.
- **`license_` spans split windows by design.** Prior history is the point of the task, so the
  entity key appears in several windows; the gate checks temporal leakage by rows and windows, not
  by forbidding the entity key to recur (see `README.md` → Findings).
