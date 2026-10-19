# The baseline runner, and why it is shipped here

`train.py`, `validate.py` and `validate.sh` are **copied verbatim** from `earino/harness_benchmark`
(file set `task_template/`). They are included so the baseline in `MANIFEST.json` is reproducible
from this repository alone, without access to that project.

| file | sha256 (must match `MANIFEST.json`) |
|---|---|
| `train.py` | `a3c6bcf13735bc85c52129ded68f839090dffdc266ebc3810dc61b2e6ea5e7e8` |
| `validate.py` | `b597e7f84fed614e64b4a86fbecbd6ec0145916a24d0d221a796586976418e7b` |
| `validate.sh` | `3f06ca48f11c2e05d331b4d8394284925de660c1d4b086d2f8243959e83b7e6d` |

**Provenance and permission.** Source: `earino/harness_benchmark`, file set `task_template/`,
retrieved 2026-10-14. That project is the copyright holder's own work, developed with Claude and
Szilard; the holder confirmed permission to release these copies here under MIT, with credits
preserved. They are distributed unchanged - the digests above are identical to the ones the
benchmark holds.

## Running it

    sh baseline/reproduce_baseline.sh ./task sec_56_12004

The script materialises the config into the runner's expected layout (`task.json`,
`data/train.csv`, `data/eval.csv`) via `code/materialize.py`, runs the contract, and prints the
eval AUC. The holdout is not copied into the working directory: the contract scores train and
eval only, and the labelled holdout stays outside the workspace an evaluated agent is given.

## Reproducing the numbers from a clean checkout

1. `python3 get_dataset.py --dest ./task --config sec_56_12004` - downloads the config's five
   assets, verifies them against the release's recorded sizes and `SHA256SUMS`.
2. `sh baseline/reproduce_baseline.sh ./task sec_56_12004`.
3. Expect `Eval AUC: 0.8036` from `train.py` and `0.8036, CONTRACT OK` from the independent
   `validate.py` re-run. The runner's training is not bit-reproducible (xgboost with default
   threading on identical bytes), so the last decimal can move between runs; the artifact digests
   do not.

The recorded run (job `msha-baseline-001`) measured the released bytes in place - the config's
files were fetched from the private staging release and sha256-verified in transit, not rebuilt -
and its installed stack was pandas 2.3.3, numpy 2.5.4, xgboost 3.4.1, scikit-learn 1.9.1,
scipy 1.18.1.
