# chicago-doah-adjudication

**Status: `qualified` (2026-09-26). Built, gated and baselined on workers; packaged and staged
private pending operator authorisation to publish.** The licence review below was resolved on
2026-09-19 (operator accepted the City's data terms).

## The task

Chicago Department of Administrative Hearings building-code cases. Predict, at
docketing time, whether the case ends "Liable" or "Not Liable". The outcome is a
hearing officer's ruling, recorded by the city - real, observable, and outside our
control.

This is the most unusual source on the shortlist: an administrative adjudication
corpus, not a sensor feed or a service-request log.

## Measured evidence (2026-09-18, anonymous Socrata API)

Endpoint: `https://data.cityofchicago.org/resource/6br9-quuz.json` (official
"Ordinance Violations"; `dmac-8gtz` is a community view with identical columns).

| Query | Result |
|---|---|
| `$select=count(*)` | 823,637 rows |
| hearing_date range | 2008-01-10 to 2027-02-18 |
| disposition counts | Liable 290,724 / Non-Suit 254,431 / Default 115,978 / Not Liable 106,477 / Continuance 31,055 / blank 19,719 / Adjudication Performance-Other 4,196 / Dismissed Without Prejudice 664 / Judgment Vacated 393 |
| Liable vs Not Liable | 290,724 vs 106,477 - 73.2 % positive |
| null disposition | 19,719 rows |
| future-dated hearings | 6,485 as of 2026-09-18 (scheduled, unruled) |
| issuing_department | Buildings only - 823,637 rows |
| top violation codes | 190019 (46,585), 061014 (29,618), 070024 (29,485), 196029 (25,065) |

## Split trap

Each row is a *violation*; a case has many rows sharing one `docket_number`. A
random row split puts the same case on both sides. Split by `docket_number`.

The 6,485 future-dated hearings are a natural forward holdout, but the dataset is
updated daily and dispositions fill in over time, so the extract must be frozen
with checksums; otherwise the "holdout" changes under the task.

## Licence

Both datasets report **"See Terms of Use"** with source link cityofchicago.org.
That is not an explicit open-content licence. Since the project publishes publicly,
this needs the operator's review before the raw records or a derived split is
released. Publishing only construction scripts, schema documentation and checksums
is a fallback that does not redistribute the records.

## Next action

Operator licence review, then write the construction script splitting by
`docket_number` over a frozen extract.

## Parking verdict (2026-09-19)

Status set to `parked`. The remaining work was an operator licence review, not research: leaving it `investigating` implied someone was still working on it. **Reopened 2026-09-26** once the operator
accepted the City's data terms.

## Construction record (2026-09-26)

Release artifact `b71586bf28fa56ebbfaede26c4494d68b166545ac504b2ebd8a52c7f272627ef`, built by job
`chicago-003` and gate 1.3.0 (32 checks, 0 failed). 53,763 cases of 130,318 dockets: 74,387 had no
disposition on any charge, 53 had an incomplete lead charge, 2,115 fell outside the declared
window. 18 anonymous Socrata requests (one `count(*)` probe, 17 pages of 50,000 rows by `:id`).

### The defect the first two artifacts carried, and why the gate did not catch it

`chicago-001` and `chicago-002` built an artifact that **passed the gate** and was still wrong. It
shipped 13 columns, including `hearing_date` and a derived `days_to_hearing`, both declared as
ordinary features in `meta.json`:

- The City documents `hearing_date` as *"the date of the most recent hearing"*. On a decided case
  that is the hearing at which the disposition was recorded — after the prediction instant. The
  original design used it as the split key on the belief that it was the case's first scheduled
  hearing.
- `days_to_hearing`, derived from it, **separates the classes on its own** — single-column AUC 0.84
  over the case rows. That is leakage, and the runner hands every non-identifier column to the
  model, so shipping a column that strong hands the answer over.

The gate's post-hoc rule keys off the artifact's own declarations: a column declared as a feature
is not treated as post-hoc, so **a wrong declaration passes**. The leak was caught by reading the
built CSV header, not by the gate. Fixed in `build.py`: `hearing_date` is not read at all,
`days_to_hearing` no longer exists, the split is keyed on `violation_date` (the notice date, which
is on the notice before the case is docketed), and the window is enforced on the case date (2,115
cases dropped, against 60 before).

**Worth remembering: "the gate passed" is evidence about declarations, not about columns.**

### Determinism

`chicago-002` re-ran `chicago-001`'s builder: identical `source_rows_sha256` and
`case_table_sha256`, so the build does not depend on request timing or paging order. For the
released artifact the same held across machines — an independent local rebuild reproduced
`chicago-003`'s source-row stream digest, case-table digest and all five file digests exactly.

### Baseline

`chicago-baseline-001`: the benchmark's own `train.py`/`validate.sh`, hashes verified unmodified, on
a worker that rebuilt the artifact first and refused to measure it unless the rebuild was
byte-identical. `Eval AUC: 0.6915` from both paths, contract OK. **Read it against eval's own
0.8955 positive rate, not against 0.5**: a constant-`Liable` predictor already scores 89.6%
accuracy. No agent or harness comparison was run and none is implied.
