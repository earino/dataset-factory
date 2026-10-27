# UNHCR corridor application-doubling (unhcr-refugee-data-finder)

A binary prediction task built from UNHCR's asylum-applications statistics (applications
residing in each country of origin, annual, 2000-), distributed via the Humanitarian Data
Exchange (HDX) under CC BY 3.0 IGO.

**Question.** Each year the applications distribution is refreshed to carry complete data
through year D (the last fully published year). For an origin-asylum corridor that reported
at least 500 government-procedure applications in year D and has a published year-D-1 value,
using only what is published at that instant - the corridor's own recent levels and growth,
the host's and origin's aggregate context, corridor age and calendar - will the corridor's
total applications **double** in year D+1 (reach at least twice its year-D level)?

- **Prediction instant:** the publication of the distribution carrying complete year-D data
  (a delayed statistical release: the observed 2026-08-20 refresh carries complete data
  through 2025, 232 days after the 2025 period end). Eligibility reads only published years
  <= D; the target year D+1 never enters selection.
- **Target:** `doubled` = 1 if the corridor's year-D+1 government/procedure persons total is
  at least 2x its year-D total, else 0. Base rates: train 8.42% (label years 2002-2016),
  eval 8.74% (2017-2021), holdout 11.57% (2022-2025). Corridors whose host files no report
  at all in D+1 are **censored and counted** (`unobserved_target`), never labelled; live-edge
  label years beyond the fetched vintage are likewise excluded and counted.
- **Splits:** temporal on the label year - train 3,363 rows / 283 positives / 183
  (origin,label-year) positive clusters, eval 1,887 / 165 / 109, holdout 1,962 / 227 / 133.
- **Vintage:** the HDX resource publishes one current distribution and retains no historical
  vintages, so training-label timing and full-row historical availability are unverified;
  the evaluation contract is retrospective research over the current snapshot under an
  isolated-rows access posture (see `quality.json`'s `evaluation_contract`). No point-in-time
  reconstruction is claimed.
- **Known cross-row exposure, measured and declared:** a corridor's `surged_recently` feature
  in label year T+1 equals its label in label year T. The gate executed the declared probe
  across all splits (2,439 / 1,265 / 1,239 train/eval/holdout rows covered, 0 mismatches);
  the artifact is usable only under the restricted protocol the contract states.

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (1,887 rows, 165 positives) |
| --- | --- |
| Full model - the benchmark's stock XGBoost baseline, verbatim runner | **0.5393** |
| Persistence: corridor momentum (`log_growth_d`, observed at the instant) | **0.5742** |
| Persistence: surge flag (`surged_recently`) | **0.5856** |
| Calendar/identity prior (train rate per origin-asylum corridor, then origin) | 0.5409 |
| Recent-era constant (train rate over the last three train years) | 0.5000 (constant, no ranking information) |
| Majority-class accuracy on this split | 0.9126 |

Paired differences (row bootstrap, 1000 resamples): model - momentum **-0.0348**
[-0.1056, +0.0409]; model - surge flag **-0.0463** [-0.1103, +0.0144]; model - calendar
-0.0016 [-0.0594, +0.0587]. Every interval contains zero: the differences are inconclusive,
and the observed gaps are **negative** - the stock baseline trails both persistence
references on these rows. Read this as: **no demonstrated headroom over simple persistence
under this protocol with the stock model**. The 2020 pandemic year inverts the panel
(momentum AUC 0.116 on only 6 positives; the model reaches 0.842 there) while 2017-2019
belong decisively to momentum; the per-label-year table is in `RELEASE_NOTES.md`. All
measures sit close to chance, so the honest summary is weak signal throughout, recorded as
a finding rather than a promise of headroom.

## Layout

```
public/train.csv    labeled training rows       (agent-visible)
public/eval.csv     labeled evaluation rows     (agent-visible)
private/holdout.csv labeled holdout             (never copied into a workdir; the
                                                benchmark's score is holdout AUC)
meta.json           target, positive label, id columns, split description, counts
quality.json        the qualification descriptor the gate verified
```

`get_dataset.py` downloads the five files from this repository's release, verifies every
byte against `SHA256SUMS`, and lays out the runner tree. `REPRODUCE.md` is the full
reproduction path; `VERIFICATION.md` states exactly what was run, on what bytes, and what
was **not** covered.

## Licence

Derived research dataset, **not** a UNHCR product. Source: CC BY 3.0 IGO (attribution
required; no implied endorsement). Our code: MIT. Our rights in the derived compilation:
CC0-1.0. See `LICENSE.md`.

## Provenance

Built by worker job `unhcr-001` from construction commit `f90fd1b` (the `code/build.py`
bytes are recorded in `MANIFEST.json`); qualified by gate 1.5.0 (45/45 checks on the full
artifact, exact-byte acceptance on the worker). The full candidate record, probes and
decision trail live in the factory repository at `candidates/unhcr-refugee-data-finder/`.
