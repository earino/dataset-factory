# EU ETS Installation Net-Short (European Commission, Union Registry public extracts)

A binary prediction task built from the European Commission's Union Registry public
extracts (EUTL, DG CLIMA): **at the close of compliance year t-1's surrender cycle
(30 April of year t), will a stationary EU ETS installation's verified emissions for
year t exceed the free allocation it holds for year t - a net-short year in which the
operator must buy allowances or face the excess-emissions penalty?**

The prediction instant is the surrender deadline: by 30 April of year t, the
installation's verified emissions for t-1 (reported by 31 March) and its surrendered
allowances are settled in the registry, and its year-t free allocation is already fixed
and published - the extract carries allocation rows through 2030. What is *not* known at
the instant is exactly what the task asks about: year t's verified emissions, which
operators report by 31 March of year t+1 (measured: no numeric verified emissions for
years after 2025 in the daily extract).

- **Grain:** one row per (registry, installation, compliance year t) - the
  `operators_yearly_activity` extract restricted to in-frame years (both
  `VERIFIED_EMISSIONS(t)` and `ALLOCATION(t)` numeric) with a numeric t-1 year.
- **Panel:** 2005..2030 on the 2026-10-22 daily snapshot (617,448 panel rows,
  23,748 installations, 32 registries); shipped rows are the 2006..2025 eligible
  installation-years.
- **Splits (temporal, by compliance year):** train 2006..2019 (141,732 rows, 64,528
  positives, 45.53%); eval 2020..2022 (24,322 rows, 18,002 positives, 74.02%); holdout
  2023..2025 (22,151 rows, 15,993 positives, 72.20%). Both classes appear in every split
  and every year. The rising base rate is the documented ETS phase property (the
  free-allocation share fell while the cap declined), reported per split and per year,
  not smoothed.
- **Label:** `net_short` = 1 iff `VERIFIED_EMISSIONS(t) > ALLOCATION(t)`; exact ties are
  0 and counted (4,224). Both label source values are excluded from every shipped file,
  and the gate's single-column AUC sweep confirmed no shipped column determines the
  label (the strongest is `margin_t` at ~0.90 - the task's intended one-line rule).
- **Baseline (runner contract, unmodified):** eval AUC 0.9199, from the benchmark's own
  `train.py` and reproduced exactly by `validate.py`'s independent recompute.
  Construction-time references on identical eval rows: calendar-only 0.527 <
  identity-only 0.5719 < persistence (t-1 net-position margin) 0.8671 < full model
  0.9199. The full model clears persistence by +0.0532, and the announced-allocation
  margin rule alone reaches 0.8988 - the task is not a persistence exercise, but
  persistence is recorded beside every model number. See `VERIFICATION.md`.
- **Cross-check:** the shipped panel reconciles with the EEA's own EU ETS summary
  product (DE 2022 verified emissions exactly; 2023 within 4 t; free allocation within
  4.3e-4), summing exactly activity codes {10, 20-99}.

The dataset is **derived**: it is not the European Commission's official product, and
the Commission has not reviewed or endorsed it. The source data carry the Commission's
reuse-policy terms ([CC BY 4.0](https://commission.europa.eu/legal-notice_en)); see
`LICENSE.md` for the attribution that carries through to every copy, and
`DATA_DICTIONARY.md` for every column's documented meaning, unit and reference frame.

## Layout

```
public/train.csv      train split (compliance years 2006..2019)
public/eval.csv       eval split (2020..2022)
private/holdout.csv   holdout split (2023..2025) - ships like the other splits and
                      is never copied into a runner workdir
meta.json             task metadata the runner reads
quality.json          the qualification descriptor (splits, timing, units, exclusions)
```

## Use

```bash
python3 get_dataset.py --dest ./task     # download + verify + restore the layout
python3 code/qualify_dataset.py ./task   # re-run the qualification gate on the bytes
sh baseline/reproduce_baseline.sh ./task  # reproduce the recorded baseline
```

See `REPRODUCE.md` for the full reproduction chain (source fetch -> build -> gate ->
baseline) and `VERIFICATION.md` for what was verified, how, and what is not covered.
