# Reproducing this release

Every command below was executed against this release's bytes in a fresh environment: a
temporary worker container holding no credential and no access to any private repository.
While the repository is private, the initial download is performed by the staging worker's
host - which holds the read credential outside the container - and `get_dataset.py`
(re-verification mode), the gate, the baseline and the optional rebuild then run inside
the container on exactly those fetched bytes. Once the release is public, `get_dataset.py`
performs the download itself anonymously. `VERIFICATION.md` records what was run and what
it does not cover.

## 1. Download and verify the artifact

```bash
python3 get_dataset.py --dest ./task
```

This downloads the five release assets, checks each against the size and sha256
recorded in `MANIFEST.json`/`SHA256SUMS`, and restores the runner layout
(`public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`,
`quality.json`) under `./task`. While the repository is private the script needs
`GITHUB_TOKEN` (or an authenticated `gh`); once public, no credential is needed.

The equivalent by hand:

```bash
gh release download v2026.10 --repo earino/ipo-trademark-registration-outcome --dir ./flat
sha256sum -c SHA256SUMS   # from the repository root, after renaming to the layout above
```

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

Gate 1.5.0, the exact script the worker ran (digest-verified against
`MANIFEST.json`). Expected: all checks pass, artifact version
`2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d`. The report the
worker wrote for these exact bytes ships as `qualification.json`; to re-verify it
against the bytes instead of just re-running:

```bash
python3 code/qualify_dataset.py --accept qualification.json ./task
```

## 3. Re-run the runner-contract baseline

```bash
sh baseline/reproduce_baseline.sh ./task
```

Needs the benchmark's dependency ranges (pandas>=2.2,<3; numpy>=1.26; xgboost>=3.0;
scikit-learn>=1.5). Expected: `CONTRACT OK` and both AUC prints **0.6224**. The
script copies only the public splits into the workdir; the holdout is never copied.

## 4. Rebuild from source (optional)

`code/build.py` reconstructs the five artifact files from the pinned source
snapshot (one anonymous GET, 63 MB) and asserts every construction count in-build:

```bash
python3 code/build.py --out ./rebuild --work-dir /tmp/ipotm --built-at 2026-10-30T00:00:00Z
sha256sum ./rebuild/public/train.csv ./rebuild/public/eval.csv ./rebuild/private/holdout.csv ./rebuild/meta.json ./rebuild/quality.json
```

Expected: byte-identical files - the same five digests `MANIFEST.json` records
(`f4bb622d...`, `54e06a89...`, `26cfc5a8...`, `caf2a4d9...`, `efa5b4d3...`). The
`--built-at` pin is required: the build embeds it, and reproducibility means
byte-identical, not merely similar.

`code/run.sh` is the worker entrypoint that ran on the job, in the fixed order
construct -> qualify -> accept exact bytes -> references; no performance number is
computed before acceptance anywhere in it.

## 5. Recompute the references (optional)

```bash
python3 code/score.py --data ./task --accepted-report qualification.json --report ./references.json
```

Expected (eval rows only, holdout sealed): nice_class_rate 0.5421, mark_type_rate
0.5650, owner_country_rate 0.5191, calendar_month_rate 0.4972, category_rate
0.5031, series_flag_rate 0.5213, majority-class accuracy 0.8399. `score.py` refuses
to run without the accepted report, keeping the acceptance-before-scoring order.
