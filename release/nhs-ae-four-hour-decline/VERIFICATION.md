# Verification record

What was run, on what, and what it does not cover. Every number below is measured; the command
that produced it is named beside it.

## Artifact identity

| File | Bytes | Sha256 |
| --- | ---: | --- |
| `public/train.csv` | 2,543,862 | `819b6715ad55272ca0d2a482fb4471edd84ee09ae2ee62e560fe786bd9aeb404` |
| `public/eval.csv` | 1,246,633 | `cb786792ac321dd851c272bd159fed24e13d6b633276606b294ddc976e72f266` |
| `private/holdout.csv` | 1,099,411 | `527a385f12a920b019434c70588c6532af1bd4dd5459eb64ed46809b5ef99b70` |
| `meta.json` | 3,292 | `c2f9f43a29d231019396a42c7791639e4acb96179afc0ecd4dfed0c634401813` |
| `quality.json` | 5,148 | `e7576e8a2431bacd0596161526a418a1c3c5dfea9e37399148db0f24d1d67a77` |

Artifact version **`9903df974f233dfaeaa2a005f12012fc97e561673031de44f4b8d7f016d9d957`**, produced
by job `nhsae-002` (worker, 12.1 s) and preserved in staging release 419222791.

## 1. Qualification gate

- Command: `python3 qualify_dataset.py <extract> --json --report qualification.json` on the
  worker, over the **full** artifact (11,591 rows), gate **1.3.0**.
- Result: `ok: true`, `failed_checks: []`. The gate covers leakage (per-column AUC against the
  target), prediction timing, units and reference frames, temporal splits (windows and counts
  recomputed from the rows; no cross-split id reuse refused, `expected_duplicate_ids: 0`
  verified), and the runner input contract.
- Hand-off: `qualify_dataset.py --accept qualification.json <extract>` on the coordinator
  returned **ACCEPTED** - every released file was first re-fetched from staging and re-hashed
  against the release manifest. The same `--accept` was re-run by job `nhsae-baseline-001`
  against the same bytes before any scoring.
- The report is shipped as `qualification.json` beside this file.

## 2. Timing and frame self-checks (from the build)

- Truncation self-check: 201 rows recomputed against a panel copy physically truncated at
  month M - **0 mismatches**. Any accidental future-month access would fail this check.
- Duplicate `row_id` values: **0**.
- Publisher cross-check: the panel's August 2026 volume-gated Type 1 within-4h rate is 60.86%
  against the publisher's own commentary figure of 61.1% (Statistical commentary, August 2026) -
  the difference is revised-vs-provisional publication states. The by-year national series is
  recorded in `measurements.json` (83.0% in 2018 falling to ~60% in 2025-26).
- No external threshold is used by this task, so no known-event fixture applies; the
  threshold-free m/m label replaced the fixed thresholds after they measured near-uniform rates
  (<95% -> 99.9% of holdout provider-months positive; <80% -> 95.8%).

## 3. Runner-contract baseline

Job `nhsae-baseline-001` (worker, cx23/hel1, 56.8 s, destroyed 06:41:51Z, result release
419227918). It **fetched** the five released files from staging (4,898,346 bytes, every sha256
verified on arrival, 0 failures) - it did not rebuild them - re-accepted them through the gate
(`ACCEPTED ... 9903df974f233dfa`), materialized the runner workdir (public train+eval only; the
holdout was never copied), and ran the benchmark's own `train.py` and `validate.sh` unmodified
(bundled sha256 equal the benchmark's declared hashes).

| Measure | Value |
| --- | --- |
| `train.py` Eval AUC | **0.5526** |
| `validate.py` independent predict_proba AUC | **0.5526** |
| Contract line | `[validate] CONTRACT OK` |
| Runner files unmodified | yes |
| Dependencies | xgboost 3.4.1, scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.4 (python 3.13.16) |

The two independent paths agree exactly, so the task.json contract and the column selection are
what the runner expects.

**Reference points measured at construction** (standard-library rank AUC on the written rows,
not the runner): mean reversion (`rate_m - rate_mean_6m`) **0.5659** eval / **0.6562** holdout -
the bar a competent model must beat; momentum (`rate_delta_1m`) 0.4161 / 0.3993
(anti-predictive); winter calendar rule 0.5473 / 0.5090. The XGBoost pass at 0.5526 sits **below
mean reversion on eval**: the plain pass does not beat the one-line rule. That is recorded as
measured headroom information, not a defect - a solution is only interesting on this task if it
beats the reference, and any quoted figure should be compared against all three.

## 4. What this does not cover

- **No agent or harness comparison was run.** Nothing here says how well a coding agent performs
  on the task; that is a separate experiment.
- The holdout was **not scored** by the baseline. Its rows and digests are verified; its AUC is
  not measured here.
- The source is a live register with a monthly revision cycle. A rebuild after 2026-10-21 picks
  up later and revised months and will not reproduce these digests; the published artifact is
  the 2026-10-21 vintage (`meta.json.built_at_utc`, `measurements.json`'s source composite
  sha256 `99cb3339b31ae204...`).
- The publisher's CDN serves HTTP 202 with an empty body to datacenter IPs (measured 2026-10-21
  from a Hetzner worker). The published artifact was built from the coordinator-measured fetch
  via a staged, digest-verified copy; a rebuild from a datacenter may need the client ladder in
  `code/build.py` and can still fail for this reason, which is an access property of the
  publisher, not of the task.
- The qualification gate proves the files lack the defects it can see. It says nothing about
  whether the source is what we believe it to be beyond the column documentation recorded in the
  candidate record, and nothing about whether a model can beat the references.
- Provider organisational changes (mergers, re-codings) are carried as-is by the publisher's Org
  Code; the event-key counts treat each code as one provider.

## 5. Code delta between the executed build and this package

`code/build.py` as shipped (sha256 `cb1d508a...`) differs from the bytes job nhsae-002 executed
(bundled sha256 `7ecf2e1e...`) **only in the HTTP fetch path**: the client ladder and failure
diagnostics were added after nhsae-001 measured the publisher CDN's datacenter block, and
nhsae-002 consumed the staged verified source via `--source-dir`, so none of the added code ran
in the build that produced this artifact. The panel-construction, gating, split and
file-writing core is identical and the artifact digests are unchanged.
