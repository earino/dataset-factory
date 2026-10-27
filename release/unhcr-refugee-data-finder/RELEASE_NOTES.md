# Release notes - v2026.10

First release of `unhcr-refugee-data-finder`, one task instance, one artifact.

## What this is

A retrospective binary classification task over UNHCR's asylum-applications statistics
(HDX, CC BY 3.0 IGO): at the publication instant of the distribution carrying complete
year-D data, for an eligible origin-asylum corridor, predict whether its total
applications will double in year D+1. The HDX resource publishes one current
distribution with no historical vintages, so training-label timing and full-row
historical availability are unverified; the evaluation contract declares retrospective
research over the pinned 2026-08-20 vintage with an isolated-rows access posture, and
makes no point-in-time or operational-forecasting claim.

## Artifact identity

- Artifact version (gate 1.5.0 digest over the five shipped files):
  `6fa7becdf32925b74522c81001dcfe802b6a389425fd6deb4af4fc25ba7f1f53`
- Source snapshot: `asylum_applications_residing_world.csv`, 8,669,567 B, sha256
  `d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950`,
  last-modified Thu 20 Aug 2026 15:33:52 GMT (byte-identical to the discovery pin).
- Construction commit: `f90fd1b` (worker job `unhcr-001`, server 172873699; the exact
  `code/build.py` / `code/run.sh` / `source/score.py` byte digests it executed are
  recorded in `MANIFEST.json`).
- Qualification: gate 1.5.0, 45/45 checks on the full artifact on the worker, exact-byte
  `--accept` verified before any figure was computed; the declared cross-row probe was
  executed on every split (2,439/1,265/1,239 rows, 0 mismatches).
- Design refinement at preflight (recorded in the candidate notes): eligibility was
  tightened to require a published year-D-1 corridor value (decidable at the instant;
  the momentum feature family needs it), with every excluded row counted per split
  (377 missing_history, 33 host-silent unobserved_target, 496 live-edge label-year 2026).

## Measured evidence (eval window, 1,887 rows / 165 positives, after acceptance)

| Reference / model | Eval AUC | Brier |
| --- | --- | --- |
| Full model (stock XGBoost baseline, verbatim runner) | 0.5393 | 0.085099 |
| Persistence: corridor momentum (`log_growth_d`) | 0.5742 | - |
| Persistence: surge flag (`surged_recently`) | 0.5856 | - |
| Calendar/identity prior (train rate per corridor, then origin) | 0.5409 | - |
| Recent-era constant | 0.5000 (constant, no ranking information) | - |

Paired differences vs the full model (row bootstrap, 1000 resamples): momentum
**-0.0348** [-0.1056, +0.0409]; surge flag **-0.0463** [-0.1103, +0.0144]; calendar
-0.0016 [-0.0594, +0.0587]; recent-era constant +0.0394 [-0.0047, +0.0859] (a
degenerate control: a constant cannot rank). Majority-class accuracy on this split:
0.9126.

**Finding: no demonstrated headroom over persistence under this protocol.** The stock
baseline trails both persistence references on the identical rows; every interval
contains zero, so the difference is inconclusive rather than significant, but the
observed gaps are negative and are recorded beside the model figure so no reader quotes
0.5393 alone. All measures sit close to chance.

Per label year (the honest grain - prevalence swings 1.4% to 18.8% across these years):

| Label year | rows | positives | model AUC | momentum AUC |
| --- | --- | --- | --- | --- |
| 2017 | 361 | 27 | 0.3938 | 0.7451 |
| 2018 | 386 | 41 | 0.5479 | 0.6568 |
| 2019 | 423 | 34 | 0.5635 | 0.6272 |
| 2020 | 414 | 6 | 0.8417 | 0.1164 |
| 2021 | 303 | 57 | 0.6127 | 0.5684 |

Momentum owns 2017-2019. The 2020 pandemic year inverts it completely (the corridors
that doubled into 2019's baseline were the ones that collapsed in 2020), and the model
handles that year far better - but on 6 positives that is fragile evidence, not a
capability claim. The negative finding stands: this release documents a qualified task
whose stock baseline does not beat persistence, and the benchmark's real question -
whether a solver can - remains open and unclaimed.

## What is not claimed

- No operational, real-time or point-in-time forecasting validity: the publisher keeps
  no historical vintages, so past availability cannot be probed; training-label timing is
  recorded as unverified.
- The holdout was never scored and never entered any workdir; its bytes ship verbatim.
- The agent harness loop was not run; the baseline is the runner contract only.
