# chicago-doah-adjudication

**Status: strong runner-up; blocked on licence review (2026-09-18).**

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

Status set to `parked`. The remaining work was an operator licence review, not research: leaving it `investigating` implied someone was still working on it.
