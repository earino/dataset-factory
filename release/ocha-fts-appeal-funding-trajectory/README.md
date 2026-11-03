# ocha-fts-appeal-funding-trajectory

Humanitarian-appeal funding-trajectory prediction task, built from OCHA's
Financial Tracking Service (FTS). Derived research dataset - **not** an OCHA or
FTS product.

## The prediction question

For a UN-coordinated humanitarian appeal or response plan (single-country HRP,
CAP, flash appeal and similar) at its **public launch instant** - requirements
first published, at or before the plan year starts - will the plan receive
funding equal to at least **50% of its ORIGINAL launch-vintage requirements** by
the close of its plan year?

A useful prediction identifies, months ahead, which appeals will end the year
underfunded - the quantity FTS/GHO gap analysis reports after the fact - which
is what donor advocacy and fundraising prioritization need.

- **Prediction instant:** the appeal's launch (event time; requirements
  announcement). Every feature is a launch-time attribute. Nothing that happens
  after launch ships.
- **Target:** `reached_half` = 1 when year-end funding >= 0.5 x original
  requirements (both US dollars from the same publisher; the threshold is a
  task-defined policy fraction fixed before construction, not data-derived).
- **Label source:** the FTS flow endpoint's per-plan-year `incoming.fundingTotal`
  - never shipped in any split. The HDX bulk CSV's funding column cross-checks
  it on every row at construction.
- **Splits (temporal on the plan year):** train 2000-2016 (437 rows, 279
  positive), eval 2017-2020 (139 rows, 81 positive), holdout 2021-2025 (182 rows,
  96 positive). The 2026+ live edge is excluded until those years close;
  exclusions are counted in their own buckets, never scored as negatives.
- **Id:** `plan_year_id` (one row per appeal-plan ID × plan year). (country, plan year) is **not** unique — 41 country-year groups carry more than one appeal (e.g. Tanzania 2001-43 and 2001-73).

## Files

| Path | What |
| --- | --- |
| `public/train.csv`, `public/eval.csv` | public splits (feature columns + target) |
| `private/holdout.csv` | final-scoring split; ships as an asset, never enters a runner workdir during development |
| `meta.json`, `quality.json` | runner task metadata and the full qualification declaration (timing, evaluation contract, split windows, exclusions) |
| `code/` | construction script (`build.py`), worker run order (`run.sh`), references implementation (`score.py`), workdir materializer (`materialize.py`), the qualification gate (`qualify_dataset.py`) |
| `baseline/` | the benchmark's own runner files, verbatim, plus the reproduce script |
| `get_dataset.py` | downloads the five release assets, verifies every size and sha256, restores the runner layout |
| `measurements.json` | the measured panel, references, baseline result and the finding beside it |
| `MANIFEST.json`, `SHA256SUMS` | every file's identity: sizes, digests, licences, qualification, baseline |

## Quick start

```bash
python3 get_dataset.py --dest ./task          # download + verify + lay out
python3 code/qualify_dataset.py ./task        # re-run the qualification gate
sh baseline/reproduce_baseline.sh ./task      # runner-contract baseline
```

See `REPRODUCE.md` for the full reproduction path, `DATA_DICTIONARY.md` for
every column's documented meaning, and `VERIFICATION.md` for what was verified
and what is not covered.

## The finding that qualifies every number

On the identical 139 eval rows: the stock runner's full model scores **0.6452**
AUC; the persistence reference (`persistence_last_coverage`, recomputed
scorer-side from prior-in-time labels) scores **0.7171**. The model trails
persistence by 0.0719 - recorded as **no demonstrated headroom under this
protocol for the stock runner**, with the information-asymmetry note (the model
is deliberately denied the last prior same-country outcome under the operator's
P0 leakage standard, while the persistence reference reads it scorer-side)
beside every quoted figure. A solver must beat `persistence_last_coverage` for
any headroom claim on this task. Full comparison in `measurements.json` and
`baseline/README.md`.

## Leakage posture

The 2026.10-era prior-outcome features (`country_prior_appeals`,
`country_prior_covered_rate`, `country_last_prior_covered`) allowed exact
cross-row label recovery and **do not ship** in this version: a 2026-11-01
independent audit recovered 120/139 eval and 128/182 holdout labels through
them, and the fts-appeal-003 rebuild removed the channel with rows unchanged.
The only history-derived column is `years_since_country_prior`, which reads the
YEARS of strictly-earlier same-country appeals - never any row's outcome - and
is asserted label-free by brute-force recompute at construction. The FTS API
exposes no historical vintages, so the panel is current-vintage retrospective:
`quality.json`'s `evaluation_contract` declares `isolated_rows` access and a
restricted retrospective-research scope, and no historical forecasting claim is
made. Eval is labeled development/validation; holdout is final scoring.

## Licence

Our code and documentation: MIT (`LICENSE-MIT.txt`). Our rights in the derived
compilation: CC0-1.0 (`LICENSE-CC0-1.0.txt`) - covering only our contribution.
The source's own terms are preserved: FTS use-and-republish terms plus CC BY-IGO
on the HDX bulk distribution, with attribution carried into every copy. See
`LICENSE.md` for the exact attribution statements and scope.

Derived dataset based on Financial Tracking Service (FTS) data,
https://fts.unocha.org . Not an OCHA or FTS product.
