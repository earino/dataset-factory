# Verification record

What was run, on what, and what it does not cover. Every number below is measured; the command
that produced it is named beside it.

## Artifact identity

| File | Bytes | Sha256 |
| --- | ---: | --- |
| `public/train.csv` | 1,496,272 | `2515289b43bdd49b51479b076f81a9f21bc2ec4382f3d0f7153687a8ecafb102` |
| `public/eval.csv` | 1,589,403 | `7d809b16ed3b833bf13070b50a5f9fba83e3d2fb7569b993408e885eae9ad8e9` |
| `private/holdout.csv` | 3,482,298 | `f7dd814a73c864df9d11ff2a1c39a899c97c9efe46b6687cb279c0d3c3ef276e` |
| `meta.json` | 2,915 | `592552716187b6645070fd625e1c197390a7f12fb1a719b9d8901ec0918f562b` |
| `quality.json` | 5,610 | `efa583ba6a07c1081488d9fe48d74736a484b9f48cd2d5712e2b0cbf190a062b` |

Artifact version **`b1323a27fa02eb79de5fbb12c54068699ae15b3d44a9488942fd17ef0a4caffa`**, produced by
job `flunet-002` (worker 171454743) and preserved in staging release 418940777.

## 1. Qualification gate

- Command: `python3 qualify_dataset.py <extract> --json --report qualification.json` on the worker,
  over the **full** artifact (26,093 rows), gate **1.3.0**.
- Result: `ok: true`, `failed_checks: []`. The gate covers leakage (per-column AUC against the
  target), prediction timing, units and reference frames, temporal splits (windows and counts
  recomputed from the rows), and the runner input contract.
- Hand-off: `python3 qualify_dataset.py --accept qualification.json <extract>` on the coordinator
  returned **ACCEPTED**, `matches the qualified artifact b1323a27fa02eb79` - the report and the
  bytes on disk are the same artifact.
- The report is shipped as `qualification.json` beside this file.

## 2. Timing and frame self-checks (from the build)

- Timing: 201 rows recomputed against a series copy physically truncated at week W - **0
  mismatches**. Any accidental future-week access would fail this check.
- Duplicates: **0** duplicate `row_id` values.
- Frame trap: the 1995-2004 window measures 931/931 country-weeks positive before the
  systematic-negative rule and 14 rows after it. The rule provably removes the trap it was
  designed against, and those rows cannot carry the rate frame.
- Known-event fixture: France 2024-25, blended peak positivity **0.2379** in the week of
  **2025-01-27** over 28 measurable weeks; July-August 2024/2025 off-season maximum **0.0071** over
  17 weeks. Assertions (peak in (0.15, 0.95], off-season < 0.10) pass and pin the 10% threshold and
  the 4-week lead with margin.

## 3. Runner-contract baseline

Job `flunet-baseline-001` (worker 171493937, cx23/hel1; the job ledger records the server's
deletion at 2026-10-21T02:32:29Z, which is the authoritative time - an earlier note said
02:28:57Z and this is corrected against the ledger). It **fetched** the
five released files from staging (6,576,498 bytes, every sha256 verified on arrival, 0 failures) -
it did not rebuild them - re-accepted them through the gate (`ACCEPTED ... b1323a27fa02eb79`),
materialized the runner workdir (public train+eval only; the holdout was not copied), and ran the
benchmark's own `train.py` and `validate.sh` unmodified.

| Measure | Value |
| --- | --- |
| `train.py` Eval AUC | **0.8700** |
| `validate.py` independent predict_proba AUC | **0.8700** |
| Contract line | `[validate] CONTRACT OK` |
| Runner files unmodified | yes - bundled sha256 equal the declared benchmark hashes |
| Dependencies | xgboost 3.4.1, scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.4 (python 3.13) |

The two independent paths agree exactly, so the task.json contract and the column selection are
what the runner expects.

**Reference points measured at construction** (standard-library rank AUC on the written rows, not
the runner): persistence **0.8929** eval / 0.8745 holdout; rolling-8-week mean positivity 0.8281
eval / 0.7683 holdout. Note that the XGBoost baseline at 0.8700 sits **below** persistence on eval:
the plain pass over many low-signal lag columns does not beat simply carrying week W's positivity
forward. That is recorded as measured - it is headroom information for solvers, not a defect.

## 4. What this does not cover

- **No agent or harness comparison was run.** Nothing here says how well a coding agent performs on
  the task; that is a separate experiment.
- The holdout was **not** scored by this baseline. Its rows and digests are verified; its AUC is
  not measured here.
- The source is a live weekly register. A rebuild after 2026-10-20 picks up later weeks and will
  not reproduce these digests; the published artifact is the 2026-10-20 vintage
  (`meta.json.built_at_utc`, `measurements.json.source.sha256`).
- The qualification gate proves the files lack the defects it can see. It says nothing about
  whether the source is what we believe it to be beyond the column documentation recorded in the
  candidate record, and nothing about whether a model can beat the references.
- Country testing practice is not stationary; the systematic-negative rule mitigates the largest
  known break (missing negatives before ~2015) but does not make positivity comparable across all
  countries and years.

## 5. Documentation correction carried in this package

`code/build.py`'s module docstring quoted the candidate record's superseded France fixture
(">40% at peak"). The build itself pinned the measured blended frame (peak 0.2379, floor 0.15); the
docstring paragraph was corrected to match. This is a **documentation-only** edit: no code path,
threshold, gating rule or output byte changed, and the artifact digests above are unchanged.
`release.json` records both the construction commit and the note.