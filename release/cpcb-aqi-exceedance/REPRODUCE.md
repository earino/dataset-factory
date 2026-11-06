# Reproducing this release

Every step below was executed on the released bytes, in a fresh environment
with no access to the private factory repository (worker job cpcb-aqi-baseline-001 for
the baseline and references; the fresh-consumer verification of the staged
release is recorded in the candidate record). Commands assume the repository
root as the working directory.

## 1. Fetch and verify the artifact

```bash
python3 get_dataset.py --dest ./task     # verifies every size + sha256
sha256sum -c SHA256SUMS                  # the manifest's own checksums
```

Expected: 5 files, `downloaded and verified 5 files`. While the repository is
private this needs `GITHUB_TOKEN` (see `get_dataset.py`'s docstring).

## 2. Qualification (gate 1.5.0) and exact-byte acceptance

```bash
python3 code/qualify_dataset.py ./task --json --report /tmp/qual.json
python3 code/qualify_dataset.py --accept qualification.json ./task
```

Expected: `ok=true`, `failed_checks=[]` over all 45 checks, then
`ACCEPTED: ./task matches the qualified artifact a749f0df2f9dd010`. The shipped
`qualification.json` is the gate report the worker wrote for exactly these
bytes (sha256 d2d367b63b6cd59235251f4131845862783a462258f90416d30e1b7ad2882fea); acceptance fails if any file changed after
qualification.

## 3. Dependencies

The runner's ranges (as installed for the recorded baseline: python 3.13.18, pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1):

```bash
python3 -m pip install --no-cache-dir "pandas>=2.2,<3" "numpy>=1.26" \
    "xgboost>=3.0" "scikit-learn>=1.5"
```

## 4. The recorded baseline (runner contract)

```bash
sh baseline/reproduce_baseline.sh ./task
```

Expected: both implementations print eval AUC **0.9734**
(train.py's Eval AUC and validate.py's independent recompute agree to ~2e-6)
and `validate.sh` ends with `[validate] CONTRACT OK`. The script materializes
the runner workdir from the public splits only - the private holdout is never
copied into a workdir. See `baseline/README.md`.

## 5. The pre-registered references

```bash
python3 code/score.py --data ./task \
    --accepted-report qualification.json \
    --report /tmp/references.json
```

Expected, on the identical 126,570 eval rows: station_persistence AUC
0.9689 (Brier 0.2830), state_season_climatology 0.8617
(Brier 0.0968), global_rate degenerate (constant 0.211512,
Brier 0.1351), station_train_rate 0.7616 (supplementary),
majority-class accuracy 0.8434. The deciding check (model vs every member,
station-clustered paired bootstrap, 1,000 resamples, cluster = station_id)
is recorded in `measurements.json`; recomputation must reproduce
model-minus-persistence [0.0038, 0.0052] and model-minus-climatology [0.1002, 0.1252].

## 6. Rebuilding from source (optional, needs the pinned export)

`code/build.py` fetches from the XKDR export pinned in the build
(exported_at 2026-09-30T11:25:11+00:00, 196,521,834 rows) and **refuses to run against
any other export**, so a rebuild is possible only while data.xkdr.org serves
that export unchanged:

```bash
python3 code/build.py --out /tmp/rebuild
python3 code/qualify_dataset.py /tmp/rebuild --json --report /tmp/q2.json
python3 code/qualify_dataset.py --accept /tmp/q2.json /tmp/rebuild
```

A byte-identical rebuild reproduces all five files' sha256 as recorded in
`MANIFEST.json`; the Delhi and monsoon fixtures and the 2025 hole-month
assertions re-verify on every rebuild. If the export has changed, the build
exits non-zero by design - the artifact is reproducible from the release
assets (steps 1-5) regardless.
