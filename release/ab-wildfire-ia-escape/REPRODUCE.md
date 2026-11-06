# Reproducing this release

Every step below was executed on the released bytes, in a fresh environment
with no access to the private factory repository (worker job abwildfire-baseline-002 for
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
`ACCEPTED: ./task matches the qualified artifact c2c8ceb56c7ff52a`. The shipped
`qualification.json` is the gate report the worker wrote for exactly these
bytes (sha256 16697cd8aef51394f84b125964104adea5bf9dd8536f4fde291f817469cb07bb); acceptance fails if any file changed after
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

Expected: both implementations print eval AUC **0.9554** and `validate.sh`
ends with `[validate] CONTRACT OK`. The script materializes the runner workdir
from the public splits only - the private holdout is never copied into a
workdir. See `baseline/README.md`.

## 5. The pre-registered references

```bash
python3 code/score.py --data ./task \
    --accepted-report qualification.json \
    --report /tmp/references.json
```

Expected, on the identical 5,707 eval rows (2016-2020): persistence
(`assessment_hectares`) AUC 0.9096, calendar/identity prior 0.7130
(Brier 0.0179), full-feature L2 logistic 0.9206 (Brier
0.0158), majority-class accuracy 0.9818. The paired differences
are deterministic (fixed-seed LCG): logistic minus persistence +0.0111
CI [-0.0292, 0.0514] (INCONCLUSIVE), logistic minus calendar +0.2077 CI [0.1551, 0.2644],
persistence minus calendar +0.1966 CI [0.1371, 0.2694]; recomputation must reproduce
all three intervals exactly, and the per-year breakdown in
`measurements.json`.

## 6. Rebuilding from source (optional, needs the pinned publisher CSV)

`code/build.py` refuses any source CSV other than the pinned one (sha256
8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72, 10,400,030 bytes). open.alberta.ca Cloudflare-challenges plain
HTTP clients (curl 403, measured 2026-11-06), so the file must be fetched
through a real browser:

1. open
   `https://open.alberta.ca/dataset/a221e7a0-4f46-4be7-9c5a-e29de9a3447e/resource/80480824-0c50-456c-9723-f9d4fc136141/download/fp-historical-wildfire-data-2006-2025.csv`
   in a normal browser session and save the CSV;
2. verify: `sha256sum fp-historical-wildfire-data-2006-2025.csv` must equal
   `8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72` (10,400,030 bytes) - a changed source refuses the build by
   design;
3. rebuild and re-gate:

```bash
python3 code/build.py --source fp-historical-wildfire-data-2006-2025.csv \
    --out /tmp/rebuild
python3 code/qualify_dataset.py /tmp/rebuild --json --report /tmp/q2.json
python3 code/qualify_dataset.py --accept /tmp/q2.json /tmp/rebuild
```

A byte-identical rebuild reproduces all five files' sha256 as recorded in
`MANIFEST.json`; the named-fire fixtures, the size-class consistency check and
the publisher season-hectares cross-checks re-verify on every rebuild. The
publisher's scanned data dictionary (sha256
bfff81c0d0e4b5cb0684180a53ddab4da54ddb5dd63f0c0f9497fa67f2334cdf) is
transcribed verbatim in `publisher-data-dictionary-transcript.md`; the
artifact is reproducible from the release assets (steps 1-5) regardless of the
publisher's Cloudflare posture.
