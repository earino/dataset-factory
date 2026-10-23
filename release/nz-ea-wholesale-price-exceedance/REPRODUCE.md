# Reproduce

Everything below was executed against the staged bytes of this release; the
exact commands and their results are in `VERIFICATION.md`. Nothing requires
access to any private repository once the release is public.

## 1. Download and verify

```bash
python3 get_dataset.py --dest ./task
```

Downloads the five release assets, verifies each against its recorded size and
sha256, and restores the runner layout (`public/train.csv`, `public/eval.csv`,
`private/holdout.csv`, `meta.json`, `quality.json`). Checksums:
`sha256sum -c SHA256SUMS`.

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

The gate (shipped verbatim in `code/`) re-checks leakage over the shipped
columns, prediction timing, units and reference frames, temporal splits and
runner compatibility on the downloaded bytes. Gate version 1.4.0 passed all
38 checks on this artifact.

## 3. Re-accept against the recorded report

```bash
python3 code/qualify_dataset.py --accept qualification.json ./task
```

Proves the downloaded bytes still hash to the artifact version the gate passed
(`545e0e4418c1f0e5...`), not merely to something plausible.

## 4. Reproduce the baseline

```bash
sh baseline/reproduce_baseline.sh ./task
```

Materializes the runner workdir the way the benchmark's `bench/workdir.py`
does (public splits only; the holdout is never copied) and runs the
benchmark's own unmodified `train.py` + `validate.sh`. Recorded result: eval
AUC 0.8924, printed identically by both entry points (`CONTRACT OK`).
Dependencies: `pandas>=2.2,<3`, `numpy>=1.26`, `xgboost>=3.0`,
`scikit-learn>=1.5`.

## 5. Reproduce the simple references

```bash
python3 code/score.py --data ./task --report ./references.json \
    --accepted-report qualification.json
```

`code/score.py` is the post-acceptance reference stage that ran on the worker
after the gate accepted the bytes: it computes the persistence
(`last_day_mean`, `mean_7d`), calendar-only (train-fitted island x target-week
rate) and majority-class references on the eval rows and writes them as JSON.
Recorded results: persistence_value 0.8820, persistence_mean7 0.8843,
calendar_only 0.5011, majority-class accuracy 0.5693 - see
`measurements.json`.

## 6. Rebuild from the source (full construction)

`code/build.py` is the exact construction script that produced this artifact
(sha256 `ae691ec2...`, the bytes worker job nz-ea-002 executed; `code/run.sh`
is the worker entrypoint that ran the construct -> qualify -> accept ->
references order and fails the job when any stage fails). It downloads the
EMI FinalEnergyPrices blob container listing plus every price file
(714 files, ~3.6 GB - run it where the bandwidth is, not on a laptop) and the
NetworkSupplyPointsTable mapping, builds the (island, anchor day) panel with
30-day published-history features, writes the runner layout and
`quality.json`, asserts the known-event fixtures and the channel cross-check
on the written rows, and records per-file digests in `summary.json`.
`--fixture` runs the same code end to end on a small synthetic panel with no
network access (that is the pre-launch smoke path; fixture data is fabricated
and nothing from it is quotable).

Rebuilding from a later container vintage produces a different artifact (new
trading days arrive daily; the daily channel also re-publishes), and a rebuilt
artifact must be re-qualified from scratch before any number from it is
quoted.
