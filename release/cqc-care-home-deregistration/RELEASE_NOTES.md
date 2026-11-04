# Release notes - v2026.11

## What this is

The first release of `cqc-care-home-deregistration`: a vintage-anchored binary
prediction task on the Care Quality Commission's public register bulk files.
At the production instant of a monthly "HSCA Active Locations" vintage T, for
every care home active at T, predict whether the location's CQC registration
ends within the following 12 months (register event; see the framing
limitation below).

- artifact `afe9ee203f302f3ca41b9b01ad74a937e111d1b830590c7e662bb0b7b6df85d7`
  (gate 1.5.0, failed checks: none, exact-byte `--accept` on the worker; job
  `cqc-chd-004`, re-accepted from fetched bytes in job `cqc-chd-baseline-001`
  before any score existed)
- splits: train 78,138 rows / 4,418 positives (January vintages 2018-2022),
  eval 14,765 / 757 (January 2024), holdout 14,749 / 761 (January 2025);
  holdout sealed and never evaluated
- source: CQC HSCA Active Locations (Google Drive archive 2011-2026, January
  vintages pinned per-file) + Deactivated Locations 2026-11-02 edition
  (27,644,723 B, sha256 49dc3062...), Open Government Licence v3.0

## The recorded finding

The runner-contract baseline (the benchmark's own unmodified `train.py` +
`validate.sh`) scored **eval AUC 0.5659**, below the headroom reference
`rating_x_beds_rate` **0.5871** (train-fitted rate table over latest rating x
beds) on the identical 14,765 eval rows - observed gap 0.0212. This is a
recorded defect of the stock runner under this protocol, quoted beside every
model figure in this package. It is not a no-headroom verdict on the task:

- the model beats every one-line prior (`last_rating_rate` 0.5597,
  `beds_bucket_rate` 0.5298, `hsca_start_year_rate` 0.5226,
  `local_authority_rate` 0.5207, `provider_sector_rate` 0.5011);
- the headroom reference reads only shipped at-instant columns, so a consumer
  of this artifact can compute it in one line - no information asymmetry;
- the reference's superiority over the best one-line prior is measured with a
  paired bootstrap (150 resamples) whose 95% interval excludes zero
  (difference 0.0273, CI [0.0123, 0.0407]);
- one verified diagnosis candidate for the stock runner's gap: `instant`
  (YYYY-MM) is a train-only categorical in the stock `train.py`, so the eval
  instant 2024-01 is unseen and every eval row receives NaN there.

There is no persistence reference by design (per-instant pseudonymised
identity makes prior-instant labels structurally unlinkable - for the scorer
too), and majority-class accuracy on eval is 0.94873 (no ranking information).
No model above the reference has been measured; fitting until a score wins is
not the protocol.

## Framing limitation

The target is the register event (deregistration), which CQC's own file note
says can include services continuing under a new registration - not
necessarily service cessation. BMJ Public Health 2024 implies roughly 40-55%
of deregistrations 2011-2023 were re-registrations or transfers. Every
consumer should read the task as "register exit within 12 months", not
"closure".

## What is not covered

See `VERIFICATION.md` for the full not-covered list: no agent/harness loop
was run, the holdout was never scored, training-label timing is UNVERIFIED
for the 2011-2026 Drive archive (retrospective-research evaluation contract),
and no historical-availability certification is claimed for the deactivated
register beyond the pinned edition.

## Provenance

Construction commit `bf8a5ea` (build.py sha256 5085195b..., run.sh 3db218e1...,
score.py 501bb76b...); the gate is the canonical `qualify_dataset.py` 1.5.0
(4fab8a34...); `baseline/` ships the harness benchmark's runner files
verbatim. Licensing: MIT for our code and documentation, CC0-1.0 for our
rights in the derived compilation (our contribution only), OGL-UK-3.0 terms
preserved for the CQC source with attribution - see `LICENSE.md`.
