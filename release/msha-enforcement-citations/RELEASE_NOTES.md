# Release notes - version 2026.10

First release of the MSHA enforcement-citations dataset: **45 binary prediction tasks** built
from MSHA's Open Government Data Sets, one per frequently-cited 30 CFR section, plus the joint
multi-label matrix `labels.csv`.

## What is in this release

- **The task.** For each pooled MSHA inspection (497,897 inspections, 2001-2025), predict - at
  the moment the inspection begins - whether a given 30 CFR section will be cited. Features are
  the mine's structural attributes, the inspection's own recorded trigger, the calendar position
  of the begin date, and the mine's strictly-earlier inspection history (24 features; the
  identifier `event_no` and the time column `inspection_date` are declared, not hidden).
- **45 configs, one artifact pool.** Construction measured the floor on its own pool: **80
  sections** are cited in >= 1% of pooled inspections; the **45** highest-prevalence ship under
  the config cap, and 35 are held back. Train 2001-2020 (415,088 inspections), eval 2021-2023
  (49,233), holdout 2024-2025 (33,576) - identical rows in every config, so the 45 instances are
  directly comparable.
- **Gated on the worker, on the full artifact.** Gate version 1.3.0, 32 checks per config,
  **45/45 passed, 0 failed** - leakage, prediction timing, units and frames, temporal splits
  and the runner's input contract, per config (job `msha-002`).
- **Baseline through the runner's contract.** `sec_56_12004`: eval AUC **0.8036**, train AUC
  0.8036, `CONTRACT OK` from both the train path and the independent validate path (job
  `msha-baseline-001`). Persistence reference (`prev_target_cited` alone): **0.5831**.

## The corrected feature, and why the first build was thrown away

`prev_target_cited` is documented as "the target section was cited on the mine's **most recent
strictly-earlier** pooled inspection". The first full build (job `msha-001`) wrote the
**cumulative ever-cited** set instead: the feature answered "has this mine ever cited this
section" while the shipped `quality.json` claimed the recent-visit reading. The tell was the
persistence baseline - 0.99+ AUC on some configs under the cumulative reading, which is lifetime
history masquerading as a prior-visit feature. The artifact was collected and **never packaged**;
the build was repeated with the corrected script (job `msha-002`), and the released bytes were
proven to carry the fix: `sec_75_400`'s eval file differs from the superseded build in **exactly
one column** (`prev_target_cited`, 4,933 of 49,233 rows), identical in size, rows, label column
and every other column. The persistence baseline fell on **all 45 configs** (mean 0.754 -> 0.576;
`sec_75_400` 0.9403 -> 0.6733). The full evidence is in `VERIFICATION.md` and in the factory
repository's candidate record.

## Scale

3,290,163,078 bytes across the 45 configs' split files, plus `labels.csv` at 93,605,740 bytes;
226 release assets in total. Built in one streamed pass over the publisher's three zips (no API,
no credential), 581 s of worker time on a 4 vCPU / 8 GB machine.

## Known properties, recorded rather than hidden

- **Positives cluster by mine and by day.** The gate's per-config checks recompute the declared
  cluster counts; `mine_id` spans split windows by design because prior history is the point.
- **The base rate is not stationary across decades** - enforcement intensity and the mine
  population both move; the eval window (2021-2023) and holdout (2024-2025) are later and
  slightly more positive than train (e.g. `sec_56_12004`: 0.0886 / 0.1063 / 0.0996). This is a
  property of the phenomenon, documented rather than "fixed".
- **The holdout is labelled and shipped.** It has never been scored by us; `baseline/reproduce_baseline.sh`
  keeps it out of the workspace the contract scores.

## Licence

MIT for our code and documentation; CC0-1.0 for our rights in the derived compilation (our
contribution only); the source is a US federal government work, public domain by statute
(17 USC 105), with the publisher's attribution preserved. Derived data, labelled as derived -
not an official MSHA or US Department of Labor product. See `LICENSE.md`.

## Status

Public. Published 2026-10-19 after explicit operator authorisation, with both destinations public
and re-verified without a credential: GitHub release `v2026.10` (226 assets, digests read back from
the assets API) and the Hugging Face repository (same 226 assets, `load_dataset` loading every
config). `DESTINATIONS.json` records the per-destination evidence and the manifest now derives
`visibility: public`, `published: true` from it. The data files, the tag and the artifact version
are unchanged by publication.
