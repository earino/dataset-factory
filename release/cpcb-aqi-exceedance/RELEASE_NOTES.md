# Release notes - v2026.11

## What this is

The first release of `cpcb-aqi-exceedance`: a next-day binary prediction task
on India's CPCB CAAQM PM2.5 monitoring network (via the XKDR Forum's India
Air Quality Database). At 23:59 IST on day D, predict whether the station's
D+1 calendar-day 24-hour mean PM2.5 exceeds 90 ug/m3 - the Poor-band lower
breakpoint of CPCB's own National AQI.

- artifact `a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959` (gate 1.5.0, 45/45 checks, failed checks: none,
  exact-byte `--accept` on the worker in job `cpcb-aqi-build-004`; re-accepted
  from fetched bytes in job `cpcb-aqi-baseline-001` before any score existed)
- splits: train 2019-2022 (288,754 rows / 61,075 positives),
  eval 2023 (126,570 / 19,819), holdout 2024 (145,124 / 18,222,
  sealed); excluded rows counted per split
- source: one pinned XKDR export of the CPCB CAAQM PM2.5 stream
  (exported_at 2026-09-30T11:25:11+00:00, 196,521,834 rows), fetched in 168
  monthly requests; GODL-India (CPCB) + CC BY 4.0 (XKDR compilation)

## The recorded finding

The runner-contract baseline (the benchmark's own unmodified `train.py` +
`validate.sh`) scored **eval AUC 0.9734** on the identical 126,570 eval
rows. The pre-registered triad reached station_persistence 0.9689 and
state_season_climatology 0.8617 (global_rate degenerate; station_train_rate
0.7616 supplementary; majority-class accuracy 0.8434). The model beats
**every** member with the station-clustered paired bootstrap 95% CI excluding
zero - persistence by +0.004491 ([0.0038, 0.0052]), climatology by +0.1118
([0.1002, 0.1252]), and its own AUC CI [0.9713, 0.9753] entirely above 0.5 for the
degenerate member - so **headroom is demonstrated** under the rule written
before any score, on eval 2023 only. The holdout (2024) stays sealed.

The comparison is the finding, not just the number: the label is largely
persistence-carried (persistence alone ranks D+1 exceedance at 0.9689
and dominates the climatology by +0.1073, [0.0959, 0.1208]), so the demonstrated
edge over persistence is real but small. No model beyond the stock runner
has been measured, no agent or harness comparison was run, and no re-tuning
happened after any score.

## Contract limitations stated everywhere

- **Retrospective research:** the archive is ONE pinned export
  (exported_at 2026-09-30T11:25:11+00:00; the build refuses any other), so
  training-label timing is UNVERIFIED, no operational as-of claim is made,
  and honest evaluation keeps rows isolated (`use: retrospective_research`,
  `access: isolated_rows`, vintage `current_snapshot`).
- **Intraday latency unmeasured:** treating day-D trailing hours as complete
  at the 23:59 IST instant is a declared assumption; CPCB's own bulletins
  show non-participating stations on any given day.
- **The label source is excluded** from every shipped column; the threshold
  is a published band edge of the publisher's own AQI instrument, pinned by
  the Delhi 2024-11-18 known-event fixture and the monsoon trough negative
  control.
- **One network, one country:** generalisation beyond India's CAAQM PM2.5
  network and its 2019-2024 regime is not established.
- **Prevalence drift:** 21.15% train -> 15.66% eval ->
  12.56% holdout; an out-of-distribution as well as temporal test.

## What is not covered

See `VERIFICATION.md`: no agent/harness loop was run, the holdout was never
scored, and the small model-over-persistence edge carries the clustered
interval rather than a claim of large headroom.

## Provenance

Construction commit 75652fb (build.py sha256 4c10003f0e41dd6d13832a826f0d55a69f7697d7f8e347cbe4b98fbe29f04153, run.sh
7f1e04e39b4e69c63bb971b56a375c1bbef3356ffd3e140799d07414177ca399, score.py 1ffefa53a13037afb76a5af24492917c5cbdb775ff56f83dde178b69ca9d9ae0); the gate is the canonical
`qualify_dataset.py` 1.5.0 (4fab8a34fe4f3357b7cd911087bfa243c56a96d8720e40d0d4cb2169100404d1); `baseline/` ships the harness
benchmark's runner files verbatim. Licensing: MIT for our code and
documentation, CC0-1.0 for our rights in the derived compilation (our
contribution only), GODL-India preserved for the CPCB measurements and
CC BY 4.0 preserved for the XKDR compilation, both with attribution - see
`LICENSE.md`.
