# EU merger Phase II opening (ec-merger-phase2-opening)

A binary prediction task built from the European Commission's machine-readable merger
case register (DG COMP open data, coverage from November 1990, updated daily).

**Question.** For a concentration notified to the European Commission under the EU
Merger Regulation, using only case attributes fixed at notification - the parties as
named in the case title, the case's NACE sector codes, the applicable regulation, and
the notification date - will the Commission open an in-depth Phase II investigation
(adopt an Art. 6(1)(c) decision) in this case?

- **Prediction instant:** the case's notification date (event time; an administrative
  record - the file is registered with these attributes on that day).
- **Target:** `phase2_opened` = 1 if the case record carries at least one
  Art. 6(1)(c) decision adopted on or after the notification date
  (ever-adopted; a later withdrawal does not undo the opener), else 0.
  Base rates: train 4.01% (1990-2013), eval 2.60% (2014-2018), holdout 1.58%
  (2019-2026-snapshot) - a falling prevalence across splits, a property of the
  enforcement regime, reported not hidden.
- **Splits:** temporal on the notification year - train 5,406 rows / 217 positives,
  eval 1,770 / 46, holdout 2,915 / 46. Pending cases with no terminal decision yet
  (33, overwhelmingly live 2020s filings) are censored out of the shipped rows and
  counted, not silently labelled.
- **Vintage:** the register publishes one current snapshot (bulk feed since
  2025-03-18; no historical vintages are retained). This release pins the
  2026-10-27 vintage (sha256 recorded in `MANIFEST.json`). The evaluation contract is
  retrospective research over the current snapshot; **no point-in-time reconstruction
  is claimed** - sector coding is the register's current-vintage taxonomy.

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (1,770 rows, 46 positives) |
| --- | --- |
| Full model - the benchmark's stock XGBoost baseline, verbatim runner | **0.6973** |
| Sector-division prior (train rate per NACE division) - required comparator | **0.7679** |
| Title-token prior (train rate per party-name token) | 0.6644 |
| Calendar/identity prior (train rate per regulation x month) | 0.5606 |
| Recent-era constant (train rate over the last three train years) | 0.5000 |
| Majority-class accuracy on this split | 0.9740 |

Paired differences (row bootstrap, 1000 resamples): model - sector **-0.0706**
[-0.1558, +0.0168] (inconclusive difference, observed gap negative); model - calendar
+0.1367 [0.0419, 0.2321]; model - recent-era +0.1973 [0.1068, 0.2745]; sector -
calendar +0.2073 [0.1255, 0.2886]. Read this as: the task carries real signal above
trivial references, and the simple per-division prior is the reference a solver must
beat; the stock model does not beat it on the eval window. Per-year figures are in
`RELEASE_NOTES.md` (7-12 positives per eval year: noisy by design).

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

Derived research dataset, **not** a Commission official product. Source: CC BY 4.0
(Commission reuse notice; attribution required, changes indicated). Our code: MIT. Our
rights in the derived compilation: CC0-1.0. See `LICENSE.md`.

## Provenance

Built by worker job `ec-merger-003` from construction commit `54428d2` (the
`code/build.py` bytes are recorded in `MANIFEST.json`); qualified by gate 1.5.0
(46/46 checks on the full artifact, exact-byte acceptance on the worker). The full
candidate record, probes and decision trail live in the factory repository at
`candidates/ec-merger-phase2-opening/`.
