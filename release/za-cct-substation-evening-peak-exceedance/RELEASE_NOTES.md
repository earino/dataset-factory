# Release notes - v2026.11

## What this is

The first release of `za-cct-substation-evening-peak-exceedance`: a same-day
binary prediction task on the City of Cape Town's published switching-substation
load telemetry. At 06:00 SAST on day D, predict whether the evening peak
(16:00-22:00 SAST) will exceed the station's trailing-90-evening p95.

- artifact `9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180` (gate 1.5.0, failed checks: none, exact-byte `--accept`
  on the worker in job `za-cct-001`; re-accepted from fetched bytes in job
  `za-cct-baseline-001` before any score existed)
- splits: train 2022 (13,735 rows / 1,539 positives), eval 2023
  (14,965 / 1,256), holdout 2024 (15,006 / 1,382, sealed);
  burn-in 1,230 station-days counted, never scored
- source: City of Cape Town Open Data Portal, Switching Substation Load Profile
  (ArcGIS item bebf20c25bfa4ffaa7fc07a1a94ba287), anonymous REST, 54 pinned
  requests, 67,346,440 bytes; Open Data Terms of Use + Council Open Data
  Policy 27781

## The recorded finding, and what this package is

The runner-contract baseline (the benchmark's own unmodified `train.py` +
`validate.sh`) scored **eval AUC 0.5107** on the identical 14,965 eval rows -
far below the pre-registered headroom reference `morning_ratio`
(morning_max / hist_morningpeak_mean_90) at **0.7340**, and below
persistence (0.6502), calendar_identity (0.6504) and even identity_only
(0.5134): at chance. The observed gap to the reference is 0.2233 AUC.

By the operator's recorded decision (a) (2026-11-04), this package is an
**agent-headroom benchmark** - the ocha-fts precedent: the consumer is an agent
that edits `train.py`, the reference is computed from shipped at-instant
columns in one line, and the ladder above is the target to beat. This is NOT a
demonstrated-model-headroom claim, and NOT a no-headroom verdict either:
`morning_ratio` proves the extractable signal exists in the shipped features
(paired clustered bootstrap over persistence [-0.1012, -0.0706] and over
calendar_identity [-0.1019, -0.0627], both excluding zero); the stock template does not
find it. No model above the reference has been measured.

## Contract limitations stated everywhere

- **Retrospective research:** the publisher serves 2022-2024 as ONE CLOSED
  static table (item created 2026-02-28, modified 2026-03-02, hasStaticData);
  no historical vintages exist, so training-label timing stays unverified and
  no operational forecasting claim is made (`use: retrospective_research`,
  `access: isolated_rows`).
- **The threshold is sealed:** no evening-derived value ships in any split
  file; the model predicts exceedance of a threshold it never sees.
- **Load-shedding caveat (publisher's own):** readings are not corrected for
  temporary load shifts or load fluctuations due to load shedding; Cape
  Town's 2022-2024 load-shedding regime suppresses observed peaks. The label
  measures demand-as-dispatched.
- **One city, 41 substations:** generalisation beyond Cape Town's
  grid and regime is not established.
- **Prevalence drift:** 11.20% train -> 8.39% eval -> 9.21%
  holdout; an out-of-distribution as well as temporal test.

## What is not covered

See `VERIFICATION.md`: no agent/harness loop was run, the holdout was never
scored, and the stock-runner gap carries recorded diagnosis candidates rather
than a verified counterfactual.

## Provenance

Construction commit c57e371 (build.py sha256 5ffefd98be870c4ab303d6892814f535bdd7fe055a64050ec087d5726182480b, run.sh
2584200ee0526851193f827de76b929dea000dae3369c105230709b0d4055c31, score.py 8d6332c1192bfde78adc75bec2f0260543ef75963bc98267189c2636418d1572); the gate is the canonical
`qualify_dataset.py` 1.5.0 (4fab8a34fe4f3357b7cd911087bfa243c56a96d8720e40d0d4cb2169100404d1); `baseline/` ships the harness
benchmark's runner files verbatim. Licensing: MIT for our code and
documentation, CC0-1.0 for our rights in the derived compilation (our
contribution only), the City of Cape Town's Open Data Terms of Use preserved
for the source with attribution - see `LICENSE.md`.
