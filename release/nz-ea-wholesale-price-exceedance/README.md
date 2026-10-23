# NZ Wholesale Price Exceedance (Electricity Authority, Te Mana Hiko)

A binary prediction task built from the New Zealand Electricity Authority's EMI
"Final energy prices" datasets: **at the publication instant of the final
wholesale energy prices for trading day D - conservatively D + 6 calendar days,
covering the maximum publication lag measured on the publisher's daily-file
channel - given the published island daily mean final prices for trading days
up to and including D, will an island's daily mean final price on trading day
D+7 exceed NZD 100/MWh?**

The prediction instant is a documented publication event: the Authority states
interim prices "will be declared to be final prices by 2pm the following business
day", and on the publisher's daily-file channel Last-Modified minus trade date
measures 0-5 calendar days over 365+ files (1d: 249, 2d: 52, 3d: 52, 4d: 9,
5d: 5, 0d: 1). Features read final prices for trading days <= D only; the
target trading day D+7 has not finished trading at the instant, so its price
cannot exist there under any publication scheme.

- **Grain:** one row per (island, anchor trading day D); `row_id` = `{island}-{anchor_date}`.
- **Panel:** 1996-10-01..2026-10-22, 10,979 trading days, 0 missing, both
  islands every day (21,958 candidate island-days; shipped rows are the
  anchor days with a full 30-day published history and an observable D+7
  target).
- **Splits (temporal, on the anchor day):** train 1996-10-30..2016-01-01
  (14,004 rows, 2,789 positives, 19.92%, 404 positive target-weeks); eval
  2016-01-01..2022-11-01 (4,992 rows, 2,150 positives, 43.07%, 231 weeks);
  holdout 2022-11-01..2026-10-16 (2,890 rows, 1,571 positives, 54.36%, 152
  weeks). The eval->holdout boundary coincides with the documented 2022-11-01
  real-time pricing regime change, so no window straddles a structural break
  and the holdout is a different market regime by design. Both classes appear
  in every split and every eval year.
- **Label:** `target_high_price` = 1 iff the island daily mean of
  `DollarsPerMegawattHour` over trading day D+7 exceeds NZD 100/MWh (threshold
  frozen from the training-window design, never tuned on a held-out score).
  The label source columns are excluded from every shipped file, and the
  gate's single-column AUC sweep confirmed no shipped column determines the
  label.
- **Baseline (runner contract, unmodified):** eval AUC 0.8924, printed
  identically by the benchmark's `train.py` and `validate.py` and matched by an
  independent stdlib recompute. The triad on identical eval rows:
  calendar-only 0.5011 < persistence_value (last published day) 0.8820 <
  persistence_mean7 0.8843 < full model 0.8924. The model's advantage over
  persistence is positive but **not demonstrated** under the pre-declared
  criterion: the target-week-clustered paired intervals contain zero
  (+0.0104 [-0.0010, +0.0226] over persistence_value; +0.0081 [-0.0028,
  +0.0206] over persistence_mean7). Calendar-only is beaten decisively
  (+0.391). Persistence is quoted beside every model number; see
  `VERIFICATION.md` for the full comparison and what it does and does not
  establish.
- **Known-event fixtures asserted in-build:** the August 2024 dry-year episode
  (four days at 814.77-883.56 $/MWh market means must exceed; the Authority's
  own Review of winter 2024 records "in early August the average daily price
  reached $820/MWh"), 2008-07-01 (mean 305.79 must exceed), and the January
  1997 quiet-era control (max 50.0 must not).

The dataset is **derived**: it is not the Electricity Authority's official
product, and the Authority has not reviewed or endorsed it. The source data
carry the Authority's CC BY 4.0 terms (EMI LegalInformation); see `LICENSE.md`
for the attribution that carries through to every copy, and
`DATA_DICTIONARY.md` for every column's documented meaning, unit and
reference frame.

## Layout

```
public/train.csv      train split (anchor days 1996-10-30 .. 2016-01-01)
public/eval.csv       eval split (2016-01-01 .. 2022-11-01)
private/holdout.csv   holdout split (2022-11-01 .. 2026-10-16) - ships like
                      the other splits and is never copied into a runner workdir
meta.json             task metadata the runner reads
quality.json          the qualification descriptor (splits, timing, units, exclusions)
```

## Use

```bash
python3 get_dataset.py --dest ./task     # download + verify + restore the layout
python3 code/qualify_dataset.py ./task   # re-run the qualification gate on the bytes
sh baseline/reproduce_baseline.sh ./task  # reproduce the recorded baseline
```

See `REPRODUCE.md` for the full reproduction chain (source fetch -> build ->
gate -> baseline) and `VERIFICATION.md` for what was verified, how, and what
is not covered.
