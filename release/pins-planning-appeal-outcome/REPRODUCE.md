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
gh release download v2026.10 --repo earino/pins-planning-appeal-outcome --dir ./flat
sha256sum -c SHA256SUMS   # from the repository root, after renaming to the layout above
```

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

Gate 1.5.0, the exact script the worker ran (digest-verified against
`MANIFEST.json`). Expected: all 45 checks pass, no failed checks, artifact version
`c861bd8f4acd9bbe267bdb58e1168996fdb359c540aaf4030030a632d693c527`. The report the
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
scikit-learn>=1.5). Expected: `CONTRACT OK` and both AUC prints **0.6108**. The
script copies only the public splits into the workdir; the holdout is never copied.

## 4. Rebuild from source (optional)

`code/build.py` reconstructs the five artifact files from the pinned source bytes
(two anonymous GETs of the GOV.UK Excel files, ~34 MB; the build fails if the bytes
change) and asserts every construction count in-build, including the
per-decision-year fixture against the recorded probe counts. The build requires the
recorded worker-side category-dtype probe verdict, which ships with the package:

```bash
python3 code/build.py --out ./rebuild --work-dir /tmp/pins --built-at 2026-10-31T00:00:00Z --category-probe-result code/category_probe.json --summary-out ./summary.json
sha256sum ./rebuild/public/train.csv ./rebuild/public/eval.csv ./rebuild/private/holdout.csv ./rebuild/meta.json ./rebuild/quality.json
```

Expected: byte-identical files - the same five digests `MANIFEST.json` records
(`299e5af4...`, `2ab9271f...`, `3f65dc80...`, `4e7a3104...`, `9203accc...`). The
`--built-at` pin is required: the build embeds it, and reproducibility means
byte-identical, not merely similar. If the pinned source files are already on disk,
pass `--source-dir` to skip the download. `code/category_probe.json` is the recorded
verdict the worker's writer consumed (string levels ship verbatim; the build refuses
to guess the writer mode without it).

`code/run.sh` is the worker entrypoint that ran on the job, in the fixed order
runner-contract probe -> construct -> qualify -> accept exact bytes -> references;
no performance number is computed before acceptance anywhere in it.

## 5. Recompute the references (optional)

```bash
python3 code/score.py --data ./task --accepted-report qualification.json --report ./references.json
```

Expected (eval rows only, holdout sealed): procedure_type_rate 0.5551,
lpa_hist_rate 0.5414, persistence_last_outcome 0.5045, majority-class accuracy
0.6987; the year-rate and global-rate controls are constant (null AUC, degenerate);
the calendar-identity control collapses onto lpa_hist_rate exactly (degenerate,
recorded). `score.py` refuses to run without the accepted report, keeping the
acceptance-before-scoring order.
