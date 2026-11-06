# The runner-contract baseline

`train.py`, `validate.py` and `validate.sh` are the harness benchmark's own
runner files, shipped verbatim at the sha256 recorded in
`measurements.json` (`unmodified: true` in the abwildfire-baseline-002 result). The
recorded baseline was produced by worker job abwildfire-baseline-002 (server
174894664, 264.6 s) on the accepted bytes, after
re-acceptance against the gate report and with the private holdout never
copied into the workdir.

`reproduce_baseline.sh` runs the same sequence locally: re-accept,
materialize the workdir from the public splits only, then the benchmark's
own runner. Expected output: both implementations print eval AUC 0.9554
and validate.sh ends with `[validate] CONTRACT OK`; the references stage
prints persistence 0.9096, calendar 0.7130 and the logistic
reference 0.9206. Every figure is part of the recorded comparison -
see README.md: the verdict under the pre-registered rule is **headroom_demonstrated**
and the construction-time logistic-minus-persistence difference +0.0111
(CI [-0.0292, 0.0514]) is INCONCLUSIVE.
