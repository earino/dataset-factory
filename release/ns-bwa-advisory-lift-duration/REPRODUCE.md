# Reproduce

Everything below runs from a fresh clone of this repository with no access to any
private factory repository. The only requirements are Python 3.11+ and network access
to this repository's release (plus `GITHUB_TOKEN` with `repo` scope **while the
repository is private**; once public, no credential is needed).

## 1. Download and verify the artifact

```bash
python3 get_dataset.py --dest ./task
```

Downloads the five release assets (`public-train.csv`, `public-eval.csv`,
`private-holdout.csv`, `meta.json`, `quality.json`), verifies every byte against the
sizes and sha256 digests recorded inside the script (and cross-checkable against
`SHA256SUMS` and `MANIFEST.json`), and lays out the runner tree:

```
task/public/train.csv  task/public/eval.csv  task/private/holdout.csv
task/meta.json         task/quality.json
```

## 2. Re-run the qualification gate

```bash
python3 code/qualify_dataset.py ./task
```

This is the same gate (shipped verbatim in `code/qualify_dataset.py`) that passed
46/46 checks on the full artifact on the build worker (job ns-bwa-001, gate 1.5.0,
artifact version `e8ed2a53eaf0453c...`). It re-checks leakage (every shipped column
scored against the target), prediction timing, the evaluation contract, split
integrity (disjoint windows, both classes, clustered positive events) and the runner
contract (meta counts), and executes the declared cross-row probes. Expect: `OK`.

## 3. Re-run the runner-contract baseline

```bash
pip install "pandas>=2.2,<3" "numpy>=1.26" "xgboost>=3.0" "scikit-learn>=1.5"
sh baseline/reproduce_baseline.sh ./task
```

Materializes a workdir the way the benchmark's `bench/workdir.py` does (`task.json`
from `meta.json`, public train+eval only - the private holdout is never copied into a
workdir), then runs the benchmark's own `train.py` and `validate.sh`, unmodified.
Expect both to print **Eval AUC: 0.5086** on the 372 eval rows. The measured
figures on these bytes - including the site-persistence reference 0.6124 that
outscores the stock model - are in `VERIFICATION.md`, `measurements.json` and
`RELEASE_NOTES.md`; a materially different number means the bytes or the runner were
changed.

## 4. Rebuild from source (optional)

`code/build.py` is the construction script. It fetches the register's current
distribution (anonymous Socrata download, no key), so a re-run after the publisher's
next quarterly refresh pins a **newer vintage** than the released one and can
legitimately differ; the closed train/eval/holdout windows are expected to reproduce
except for publisher revisions. A local CSV copy can be supplied with
`--source <path>`:

```bash
python3 code/build.py --out ./rebuilt --work-dir /tmp/nsbwa --built-at 2026-10-29T00:00:00Z
python3 code/qualify_dataset.py ./rebuilt
```

The pinned vintage is sha256
`60f77ac4945ca824700f5bcd3eaf564f4e5c5d4ec3f08496e8dd796e7184a30a`,
283,987 bytes, content current as of 2026-06-16. The exact worker sequence that
produced the shipped artifact is `code/run.sh`: construct -> qualify -> accept exact
bytes -> references, each stage stopping the next.

## 5. Recompute the references (optional)

`code/score.py` is the reference implementation the release's figures come from. It
refuses to run unless the accepted report passed, fits its priors on train only, and
evaluates on the eval split's own labels. The gate's own collected report ships with
this package as `qualification.json`:

```bash
python3 code/score.py --data ./task --accepted-report qualification.json --report refs.json
```

Expect the eval references in `refs.json` to match `RELEASE_NOTES.md`:
site persistence 0.6124 (Brier 0.2819), calendar/identity (county x month) 0.5075
(0.3101), reason prior 0.4307 (0.2440), facility prior constant scores (no ranking
information), majority-class accuracy 0.6048. Every one of these figures was also
replicated by a second, independent implementation (worker job ns-bwa-diag-001).
