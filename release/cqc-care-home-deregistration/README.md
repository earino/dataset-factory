# CQC care-home deregistration (12-month register-exit prediction)

A binary prediction task on the Care Quality Commission's public register bulk
files. At the production instant of a CQC "HSCA Active Locations" monthly vintage
T, for every care home active at T, predict whether the location's CQC
registration ends within the following 12 months: `deregistered_12m = 1` when
the location has Location Status Inactive-Dereg or Removed with a Location HSCA
End Date in (T, T+365d], joined from the Deactivated Locations cumulative
register. Base rate at the eval instant: 757 / 14,765 = 5.13%.

Derived research dataset, **not a CQC product**. Contains public sector
information licensed under the Open Government Licence v3.0. Source: Care
Quality Commission (CQC), HSCA Active Locations and Deactivated Locations bulk
files. CQC's in-sheet disclaimer carries through: CQC is not responsible for
subsequent analysis of this raw data and must not be quoted as the source of
the analysis or interpretation.

## The recorded result, first

The runner-contract baseline (the benchmark's own unmodified `train.py` +
`validate.sh`, one XGBoost pass) scored **eval AUC 0.5659** on the 14,765 eval
rows - **below the strongest simple reference** on the identical rows:

| Reference / model (identical 14,765 eval rows) | Eval AUC |
| --- | --- |
| `rating_x_beds_rate` - train-fitted rate table over latest rating x beds (headroom reference) | **0.5871** |
| Full model (stock runner baseline) | 0.5659 |
| `last_rating_rate` - train-fitted rate table over latest rating (best one-line prior) | 0.5597 |
| `beds_bucket_rate` | 0.5298 |
| `hsca_start_year_rate` | 0.5226 |
| `local_authority_rate` | 0.5207 |
| `provider_sector_rate` | 0.5011 |
| global constant | degenerate |

Majority-class accuracy on eval is 0.94873 (constant fitted on train, measured
against eval labels); a constant score carries no ranking information. There is
**no persistence reference by design**: identity ships as per-instant salted
pseudonyms, so no prior-instant outcome is linkable - for solvers too.
`hsca_start_year_rate` is the nearest shippable history prior.

The stock runner trailing `rating_x_beds_rate` is a **recorded defect of that
runner under this protocol**, not a verdict on the task: the model beats every
one-line prior, and the headroom reference reads only shipped at-instant
columns (`latest_overall_rating` x `care_home_beds`), so there is no
information asymmetry - a consumer of this artifact can compute the reference
in one line and a better model plausibly reaches or beats it. One verified
diagnosis candidate for the gap: the stock `train.py` treats the `instant`
column (YYYY-MM) as a train-only categorical, so the eval instant 2024-01 is
unseen and every eval row receives NaN there, while part of the 30-tree depth-6
budget was spent on train-instant memorization that cannot transfer. No model
above the reference has been measured. **No figure from this dataset may be
quoted without the comparison above beside it.**

## Prediction instant and contract

The vintage is an administrative register snapshot: its production date IS the
instant (kind `period_end`, 0-day lag, `source_kind: administrative_record`).
Every feature is read from the T vintage's own bytes - beds, service-type and
service-user-band flags, latest overall rating and its publication date,
geography, provider sector, HSCA start year. As-of was asserted in-build: 0 of
the 14,765 eval-instant rows carry a rating publication date after T. Row
selection reads only the T vintage (`'Care home?' = Y`). The label is looked up
afterwards, solely to compute the label, from the pinned Deactivated Locations
edition (2026-11-02). Full details: `quality.json`.

## Framing limitation (stated everywhere)

The target is the **register event** (deregistration of the location), not
necessarily service cessation. CQC's own file note says some deactivations
continue under a new registration, and BMJ Public Health 2024 (8,346 complete
closures vs 14,911 register events 2011-2023) implies roughly 40-55% of
deregistrations are re-registrations or transfers. Successor linkage needs
developer-portal API access that the bulk files cannot verify, so the honest
register-event target ships with this limitation stated.

## Splits

Temporal by vintage instant, one instant per frame (the missing-successor P0
design - no row's successor instant exists in any frame a solver can see):

- train: January vintages 2018-2022 (78,138 rows / 4,418 positives, 5.65%)
- eval: the January 2024 vintage, T = 2024-01-05 (14,765 / 757, 5.13%)
- holdout: the January 2025 vintage, T = 2025-01-02 (14,749 / 761, 5.16%)

The 2016/2017 vintages were dropped loudly (unresolved required columns); the
2023 vintage is excluded by design so every train outcome window closes at
least 12 months before the eval instant. The holdout is final scoring only; it
was never copied into a runner workdir and never evaluated.

## Contents

- `public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`,
  `quality.json` - release assets (flat names; `get_dataset.py` restores the
  layout and verifies every sha256)
- `code/` - the construction script (`build.py`, stdlib-only), the worker
  pipeline (`run.sh`), the references implementation (`score.py`), the runner
  workdir materializer (`materialize.py`) and the qualification gate
  (`qualify_dataset.py`)
- `baseline/` - the benchmark's own runner files, verbatim, plus the reproduce
  script
- `measurements.json`, `MANIFEST.json`, `SHA256SUMS`, `VERIFICATION.md`,
  `REPRODUCE.md`, `RELEASE_NOTES.md`, `DATA_DICTIONARY.md`, `LICENSE.md`

## Quick start

```bash
python3 get_dataset.py --dest ./task          # download, verify, lay out
python3 code/qualify_dataset.py ./task        # gate 1.5.0 over the artifact
sh baseline/reproduce_baseline.sh ./task      # the recorded baseline
```

Licensing: our code and documentation MIT; our rights in the derived
compilation CC0-1.0 (our contribution only); the CQC source keeps its own
Open Government Licence v3.0 terms with attribution - see `LICENSE.md`.
