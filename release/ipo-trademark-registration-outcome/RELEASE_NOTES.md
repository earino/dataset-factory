# Release notes - v2026.10

## What this is

`ipo-trademark-registration-outcome` is a binary prediction task: will a UK domestic
trade mark application filed 2010-2016 reach registration, predicted from what is
fixed at filing (mark text, Nice class coverage, category, mark type, series
membership/size, owner country/region/postcode area, filing date), as resolved in the
IPO's frozen 2018-02-13 open-data snapshot. This is the first packaged release; there
is no prior version.

The prediction instant is the **filing event** (`event_time`). The task is a
clearly-labelled retrospective single-snapshot construction: the publisher exposes
exactly one frozen vintage, no historical vintages exist, and none are reconstructed.
Training-label timing is UNVERIFIED by construction; the evaluation contract in
`quality.json` is retrospective research under an isolated-rows design intent - the
shipped benchmark validator passes the whole feature table to the predictor, so the
row-per-application isolation is the artifact's contract, not a runtime-enforced
protocol. No operational screening claim is made.

## Artifact identity

- Artifact version (gate digest over the five files): `2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d`
- Gate version: 1.5.0, 45/45 checks on the full artifact, exact-byte `--accept`
  ACCEPTED on the worker (job `ipo-tm-004`) and re-accepted in jobs
  `ipo-tm-baseline-001`, `ipo-tm-diag-001`, `ipo-tm-diag-002`.
- Source snapshot: `opendatadomestic.zip` (63,238,846 B, sha256
  `3b6063bed36a78e8a04f10a5383f2881f4072a1be13e706a81ab097fb56ee571`,
  Last-Modified 2018-02-13T13:19:48Z).
- Splits (filings-year cohorts, scored rows / positives / positive rate):
  train 2010-2012 **106,990 / 92,668 / 0.866137**; eval 2013-2014 **97,274 / 81,699 /
  0.839885**; holdout 2015-2016 **115,172 / 99,385 / 0.862927**. Censored (unresolved
  at the snapshot, excluded and counted, never labelled): 21 / 172 / 809.

## Measured evidence (identical eval rows, after acceptance)

All figures on the same 97,274 eval rows; the holdout was never read and stays sealed.

| Reference / model | Eval AUC | Brier |
| --- | --- | --- |
| Full model (stock runner XGBoost, verbatim) | **0.6224** | 0.1318 |
| Mark-type rate (train-fitted, dominant simple reference) | 0.5650 | 0.1341 |
| Nice-class rate (train-fitted, required comparator) | 0.5421 | 0.1359 |
| Series-flag rate | 0.5213 | - |
| Owner-country rate | 0.5191 | - |
| Category rate | 0.5031 | - |
| Calendar-month rate (calendar control) | 0.4972 | - |
| Majority-class accuracy on this split | 0.8399 | - |

Persistence: **not applicable** - every scored row is a new application; no prior
observation of the same entity exists at the filing instant. Recorded, not skipped.

Paired differences (row-level bootstrap, 150 resamples, job `ipo-tm-diag-002`, the
fixed resampler with the alignment invariant; the precursor `ipo-tm-diag-001`
intervals were INVALID - positional-weight defect, preserved as the defect they were -
and its point figures are unchanged by the fix):

- model - mark_type_rate: **+0.0574**, CI95 [0.0533, 0.0605] - excludes zero
- model - nice_class_rate: **+0.0803**, CI95 [0.0748, 0.0862] - excludes zero
- model - calendar_month_rate: **+0.1252**, CI95 [0.1174, 0.1315] - excludes zero

Per filing year the model's advantage holds in both eval years: 2013 (46,293 rows)
0.6233 vs mark_type 0.5639; 2014 (50,981 rows) 0.6216 vs 0.5660; prevalence is flat
across the two years (0.8409 -> 0.8390), so the advantage is not a prevalence artefact.
A pandas second implementation in the diagnostic job replicated all 10 recorded
reference figures exactly.

**Interpretation.** Demonstrated headroom over every measured simple reference under
this protocol. The scope is explicit: row-level intervals only (no dependence cluster
is measurable from the shipped columns - `tm_number` is unique per row), one model
configuration with no re-tuning, and two filing years of eval coverage. This is an
observed result, not a bound on other models and not an operational-validity claim.

## What is not claimed

- No point-in-time or historical availability claim: one frozen vintage exists, none
  is reconstructed, and training-label timing stays unverified.
- No claim that beating these rate references proves a causal signal; other simple
  rules were not exhaustively enumerated.
- No agent/harness comparison was run; the runner-contract baseline says nothing
  about how a coding agent would score on the task.
- The labelled holdout ships as an asset but stays outside evaluated agents'
  workspaces; no job in this record has read it.
- The derived dataset is not an Intellectual Property Office product.

## Provenance and licence

Source terms preserved (OGL-UK-3.0, attribution required); our code MIT; our
compilation contribution CC0-1.0 - see `LICENSE.md`. Register fidelity was
cross-checked in-build against the IPO's own facts-and-figures workbook (national UK
applications 2012-2016 agree within 0.12% every year) and against three named marks
at the file head and tail.
