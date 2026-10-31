# UK trade mark application registration outcome (ipo-trademark-registration-outcome)

A binary prediction task built from the UK Intellectual Property Office's trade mark
open data release (the frozen `opendatadomestic.zip` snapshot of 2018-02-13), published
under the Open Government Licence v3.0.

**Question.** For a UK domestic trade mark application, using only what is fixed at
filing - the mark text, its Nice class coverage (45 binary columns), the category and
mark type, series membership and series size, the owner's country / region / postcode
area, and the filing date - will the mark reach **registration** (a recorded Registered
date) as resolved in that frozen snapshot?

- **Prediction instant:** the application's filing date (`Filed`, Europe/London) - an
  `event_time` contract. This is a clearly-labelled **retrospective, single-snapshot**
  task: every feature is a filing-time field *as recorded in* the one frozen snapshot
  (sha256 `3b6063be...`). No historical operational availability is claimed, because the
  publisher exposes exactly one vintage; training-label timing is UNVERIFIED and the
  evaluation contract is retrospective research only (see `quality.json`'s
  `evaluation_contract`).
- **Target:** `registered` = 1 iff the Registered date is non-empty. Negative iff
  Registered is empty AND the status is `Refused` or `Withdrawn`. Applications whose
  outcome is unresolved at the snapshot (still in examination, opposition or appeal)
  are **censored - excluded and counted per cohort, never labelled negative**
  (21 / 172 / 809 across train / eval / holdout).
- **Population:** domestic applications with a parseable filing date in 2010-01-01 ..
  2016-12-31 (the publisher's own coverage statement lists all outcomes only from
  2010; the 2017+ cohorts are too censored to score). One row per distinct trade mark -
  16,909 duplicate rows removed; letter-suffixed series sub-marks are distinct records.
- **Splits:** cohort split on filing year - train 2010-2012 (106,990 rows, 86.61%
  positive), eval 2013-2014 (97,274 rows, 83.99%), holdout 2015-2016 (115,172 rows,
  86.29%). Disjoint calendar-year windows, both classes in every window.
- **Honesty notes carried from construction:** the 94 rows with embedded pipes inside
  Mark Text are recovered by right-anchored parsing (asserted in-build, counted); owner
  fields and class columns are snapshot-vintage (ownership can be assigned after filing,
  classes can be narrowed) - a declared uniform-vintage limitation, not a
  point-in-time claim.

## Measured evidence (identical eval rows, after gate acceptance)

| Reference / model | Eval AUC (97,274 rows, 81,699 positives) |
| --- | --- |
| Full model - the stock XGBoost runner baseline, verbatim | **0.6224** |
| Mark-type rate (train-fitted positive rate per mark type) | **0.5650** |
| Nice-class rate (train-fitted rate per class, averaged) | 0.5421 |
| Series-flag rate | 0.5213 |
| Owner-country rate | 0.5191 |
| Category rate | 0.5031 |
| Calendar-month rate | 0.4972 |
| Majority-class accuracy on this split | 0.8399 |

Persistence is **not applicable** (recorded, not skipped): every scored row is a new
application; no prior observation of the same entity exists at the filing instant.
Paired row-level bootstrap (150 resamples, diag job ipo-tm-diag-002, resampler
alignment verified): model - mark_type **+0.0574** [0.0533, 0.0605]; model -
nice_class **+0.0803** [0.0748, 0.0862]; model - calendar **+0.1252** [0.1174, 0.1315].
Every interval excludes zero, and the per-filing-year advantage holds in both eval
years (2013: 0.6233 vs 0.5639; 2014: 0.6216 vs 0.5660). Read this as: **demonstrated
headroom over every measured simple reference under this protocol** - an observed
result with recorded scope (row-level intervals only: `tm_number` is unique per row so
no dependence cluster is measurable from the shipped columns; one model configuration,
no re-tuning; two filing years in eval), not a bound on other models.

All figures were computed on a temporary worker after exact-byte acceptance of artifact
`2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d` (gate 1.5.0,
45/45 checks on the full artifact). The holdout was never read by any scoring job and
stays sealed. Labeled eval is development/validation evidence, never an untouched
final test.

## Layout

```
public/train.csv    train split   (filings 2010-2012)
public/eval.csv     eval split    (filings 2013-2014)
private/holdout.csv holdout split (filings 2015-2016)
meta.json           runner descriptor
quality.json        qualification descriptor (timing, splits, evaluation contract)
code/               construction (build.py), the gate, references, run order
baseline/           the benchmark's own runner files + reproduction script
get_dataset.py      downloads the release assets, verifies digests, restores layout
```

GitHub release assets are flat (no `/` allowed); `get_dataset.py` restores the layout
above. `python3 get_dataset.py --dest ./task` does the download, digest verification
and layout in one step.

## Licence

Our code and documentation: MIT (`LICENSE-MIT.txt`). Our rights in the derived
compilation: CC0-1.0 (`LICENSE-CC0-1.0.txt`), scoped to our contribution only. The
underlying IPO trade mark data keeps its own designation and remains subject to the
Open Government Licence v3.0, whose attribution condition carries through to every
copy: *Contains public sector information licensed under the Open Government Licence
v3.0. Source: UK trade mark applications open data (Intellectual Property Office),
opendatadomestic.zip snapshot of 2018-02-13.* See `LICENSE.md` for the full terms,
scope and required attribution. This is a derived research dataset - not an
Intellectual Property Office product.

## Provenance

- Source: `https://assets.publishing.service.gov.uk/media/5a82e5f4e5274a2e87dc387d/opendatadomestic.zip`
  (63,238,846 B, sha256 `3b6063bed36a78e8a04f10a5383f2881f4072a1be13e706a81ab097fb56ee571`,
  Last-Modified 2018-02-13T13:19:48Z), a single anonymous GET.
- Constructed by worker job `ipo-tm-004` (build.py `--built-at 2026-10-30T00:00:00Z`);
  qualified by the same job with `code/qualify_dataset.py` (gate 1.5.0) and
  exact-byte accepted before any metric existed. The construction, baseline and
  diagnostic jobs all ran on temporary workers; the bulk bytes never passed through
  the small coordinator.
- Register fidelity cross-checked in-build against the IPO's own facts-and-figures
  workbook (national UK applications 2012-2016 agree within 0.12% every year), and
  against three named marks at the file head and tail (`measurements.json`).
- The gate report for exactly these bytes ships as `qualification.json`.
