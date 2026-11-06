# The runner-contract baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own
runner files, shipped verbatim at the sha256 recorded in
`measurements.json` (`unmodified: true` in the cpcb-aqi-baseline-001 result). The
recorded baseline was produced by worker job cpcb-aqi-baseline-001 (server
174753994, 1043.7 s) on the accepted bytes, after
re-acceptance against the gate report and with the private holdout never
copied into the workdir.

`reproduce_baseline.sh` runs the same sequence locally: re-accept,
materialize the workdir from the public splits only, then the benchmark's
own runner. Expected output: both implementations print eval AUC 0.9734
and validate.sh ends with `[validate] CONTRACT OK`; the references stage
prints station_persistence 0.9689 and state_season_climatology
0.8617. Every figure is part of the recorded comparison - see README.md.
