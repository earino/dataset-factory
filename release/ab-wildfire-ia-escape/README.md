# Alberta wildfire initial-attack escape (assessment-instant prediction)

A binary prediction task on the Government of Alberta's own per-wildfire
operational record: at Alberta Wildfire's recorded **initial assessment** of a
newly discovered wildfire in the Forest Protection Area (`assessment_datetime`,
"originally assessed by Alberta Wildfire employees"), predict whether it
**escapes initial attack** - final area burned at least 100 ha: `escape = 1`.
Base rate at eval: 104 / 5,707 = 1.82%.

Every feature is the regulator's own crew-observed assessment record (size at
assessment, rate of spread, fire behaviour type, position on slope, in-situ
weather over the fire, FBP fuel type), a pre-instant timing field (elapsed hours
from report/discovery/estimated start, detection channel), or
calendar/geography - each documented "at the time of initial assessment" by the
publisher's own data dictionary, shipped verbatim as
`publisher-data-dictionary-transcript.md`. Every post-instant family (cause,
dispatch, suppression milestones) is excluded with measured ordering evidence,
and the label sources (`current_size`, `size_class`, `first_uc_date`) are
excluded from every shipped column.

Derived research dataset, **not a Government of Alberta or Alberta Wildfire
product**. Contains information licensed under the Open Government Licence - Alberta. Source: Government of Alberta, Forestry and Parks / Alberta Wildfire - Historical wildfire data 2006-2025 (open.alberta.ca, dataset a221e7a0-4f46-4be7-9c5a-e29de9a3447e). Licence: https://open.alberta.ca/licence.

This package is release v2026.11 of artifact `c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2` (gate 1.5.0, 45 checks,
failed checks: none, exact-byte accepted; the five files' digests are in
`MANIFEST.json` and `SHA256SUMS`).

## The recorded result, first

**Headroom is demonstrated under the pre-registered rule** - the runner-contract model beats every triad member with a day-clustered paired bootstrap 95% CI excluding zero in its favour, on eval 2016-2020 only; the holdout (2021-2025) is sealed and has never been scored. The honest reading travels with the number: the persistence analogue (the fire's own observed size at assessment) ranks escape at 0.9096 on its own, and the construction-time simple logistic reference's edge over it is INCONCLUSIVE (+0.0111, CI [-0.0292, 0.0514], interval contains zero). No figure from this dataset may be quoted without the comparison above beside it. No re-tuning of threshold, window, label or features happened after any score.

| Reference / model (identical 5,707 eval rows, 2016-2020) | Eval AUC |
| --- | --- |
| Runner-contract baseline (benchmark `train.py` + `validate.sh`, one XGBoost pass) | **0.9554** |
| persistence analogue - `assessment_hectares`, the observed size at the instant | 0.9096 |
| calendar/identity prior - train rate per month x forest_area | 0.7130 |
| construction-time full-feature L2 logistic (simple reference, supplementary) | 0.9206 |
| majority-class accuracy (constant fitted on train, vs eval labels) | 0.9818 |

- runner model minus persistence: [0.0154, 0.0871] (day-clustered paired bootstrap,
  500 resamples, cluster = `assessment_date`)
- runner model minus calendar/identity prior: [0.1911, 0.2998]
- the degenerate majority constant: the model's own day-cluster-bootstrap AUC
  CI [0.9382, 0.9686]
- construction-time logistic minus persistence: +0.0111, CI [-0.0292, 0.0514] -
  INCONCLUSIVE (the interval contains zero; not parity)
- construction-time logistic minus calendar: +0.2077, CI [0.1551, 0.2644];
  persistence minus calendar +0.1966, CI [0.1371, 0.2694]

The per-year eval breakdown (2016-2020, with 2020 thin at 3 positives) is in
`measurements.json`.

## Prediction instant and contract

The instant is the publisher's own initial-assessment timestamp. Timestamps
carry no timezone marker and are read as **America/Edmonton local operational
time**, confirmed against the official 2016 Horse River wildfire review
(detection 16:03h MDT 2016-05-01 = the record's naive 16:03; under-control and
extinguished dates match). The label (final area burned from `current_size`)
lies entirely after the instant; `assessment_hectares` is the size *at* the
instant, not the final size (2,220 fires end smaller than assessed, 88 were
already >= 100 ha at assessment - both recorded).

**Retrospective-research scope, stated everywhere.** The archive is ONE
current compilation (portal updated 2026-02-17, covering through 2025; no
historical per-fire vintages), and the publisher documents in-place revision of
area burned (spring aerial-photography interpretation), cause and location - the
2019 aggregate revision is measured at -10.4% against the publisher's
own season statistics. Label-flip exposure is bounded: 89 fires lie within
+-20% of the 100 ha threshold. So no operational as-of claim is made and
training-label timing stays unverified (`use: retrospective_research`,
`access: isolated_rows`, vintage `current_snapshot`). Honest evaluation predicts
row-wise from the shipped columns and keeps rows isolated.

## Splits

Temporal on the assessment instant's calendar year (the time column), declared
windows:

- train: 2006-2015 - 15,864 rows / 297 positives (1.87%),
  156 distinct positive dates
- eval: 2016-2020 - 5,707 rows / 104 positives (1.82%),
  79 distinct positive dates
- holdout: 2021-2025 - 6,257 rows / 257 positives (4.11%),
  128 distinct positive dates (**sealed; never evaluated**)

Population: ALL 27,828 assessed FPA wildfires 2006-2025 - eligibility is
assessment-based (every discovered wildfire is assessed), no
outcome-conditioned rule; winter (Nov-Feb) rows kept and counted (587);
356 winter carryover fires move with their assessment instant. Positive rate
rises into the holdout (1.87% -> 1.82% -> 4.11%): the
2021-2025 window contains the 2023 record season - documented non-stationarity,
recorded as a property, not repaired. Positives cluster on extreme
fire-weather days, so distinct-positive-date counts are the conservative
independent-observation count and every interval is day-clustered.

Missingness is real and shipped as blank: the weather block covers
88.7% of train / 94.1% of holdout rows, FBP fuel type
68.8% / 81.6%, discovery-to-assessment hours fall to 59.9%
in the holdout (the dictionary documents unplanned-detection blanks); all rates
recorded per window in `measurements.json`.

## Contents

- `public/train.csv`, `public/eval.csv`, `private/holdout.csv`, `meta.json`,
  `quality.json` - release assets (flat names; `get_dataset.py` restores the
  layout and verifies every sha256)
- `code/` - the construction script (`build.py`, stdlib-only, refuses any source
  CSV other than the pinned sha256), the worker pipeline (`run.sh`), the
  references implementation (`score.py`), the runner-workdir materializer
  (`materialize.py`) and the qualification gate (`qualify_dataset.py` 1.5.0)
- `baseline/` - the harness benchmark's own runner files, verbatim, plus the
  reproduce script
- `publisher-data-dictionary-transcript.md` - the publisher's 50 field
  definitions transcribed verbatim from the scanned dictionary PDF: the
  evidence that every shipped feature is documented at the assessment instant
- `measurements.json`, `MANIFEST.json`, `SHA256SUMS`, `VERIFICATION.md`,
  `REPRODUCE.md`, `RELEASE_NOTES.md`, `DATA_DICTIONARY.md`, `LICENSE.md`

## Quick start

```bash
python3 get_dataset.py --dest ./task          # download, verify, lay out
python3 code/qualify_dataset.py ./task        # gate 1.5.0 over the artifact
sh baseline/reproduce_baseline.sh ./task      # the recorded baseline + references
```

Licensing: our code and documentation MIT; our rights in the derived
compilation CC0-1.0 (our contribution only); the Government of Alberta's
wildfire records keep the Open Government Licence - Alberta v2.2 with
attribution - see `LICENSE.md`.
