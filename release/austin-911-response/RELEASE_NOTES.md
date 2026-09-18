# Austin 911 response time — `2026.09`

First release. A leakage-checked, time-split prediction dataset built from the City of Austin's
public `APD 911 Calls for Service 2023-2026` records: predict, **at the moment a call is
dispatched**, whether the first unit will reach the caller more than 20 minutes later.

**1,049,636 rows**, three time-separated splits, Public Domain source data.

## Assets

| asset | rows | notes |
|---|---|---|
| `task/public/train.csv` | 572,180 | before 2025-01-01 |
| `task/public/eval.csv` | 285,665 | 2025 |
| `task/private/holdout.csv` | 191,791 | 2026-01-01 onward — keep out of an evaluated agent's workspace |
| `task/meta.json` | — | target, positive label, id columns, columns, rows, split |
| `task/quality.json` | — | the descriptor the qualification gate validated the rows against |

Verify with `sha256sum -c SHA256SUMS`. The artifact version is
`e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`.

## What was checked before this was released

- **Qualification gate 1.3.0: 33 checks, 0 failures**, run on the worker over the full artifact —
  leakage, prediction timing, split capacity and boundary integrity, and the runner's input
  contract.
- **No leakage:** `response_time` (the label's source) is absent from every file; no shipped
  column separates the classes on its own; post-hoc columns are excluded and listed.
- **Splits are temporal and disjoint**, with both classes in eval and holdout and enough
  independent positive events to score.
- **Provenance:** identical row counts to the source's per-year counts, so extraction lost and
  duplicated nothing.

## Measured

| | |
|---|---|
| Baseline, single feature (`initial_problem_category`) | eval AUC **0.627031** |
| Baseline, the benchmark's own `train.py` unmodified | see `REPRODUCE.md` / `MANIFEST.json` |
| Build + qualification cost | 353.7 s on 2 vCPU / 2 GB, ~136 MB output |

Baselines are floors, not results. **No agent or harness comparison has been run on this
dataset** — that is a separate milestone, and no comparison should be inferred from this release.

## Known properties, stated rather than hidden

- `incident_number` is **not unique** in the source: 24 of 1,049,636 rows share a number with
  another row, all inside one split. 4 of those 24 pairs carry different labels because they are
  *different events sharing a number* (hours apart, different category and sector). Declared in
  `quality.json`.
- The label's clock starts when the call was **answered**, which is slightly before
  `response_datetime` — measured median offset −58 s.
- The source is a live catalogue, so rebuilding later will not reproduce these bytes. The
  hashes, not the source URL, define this version.
- The class balance (~38–40% positive) follows from the physical 20-minute threshold. It was
  deliberately not tuned to balance classes.

## Licence

Source data: **Public Domain** (City of Austin), evidence quoted in `LICENSE.md`. Construction
code: licence not yet chosen — flagged for the maintainer rather than assumed.

## Citation

> City of Austin. *APD 911 Calls for Service 2023-2026*. Austin Open Data. Public Domain.
> Accessed 2026-09-18. Derived dataset: Austin 911 response time prediction dataset,
> version 2026.09, artifact `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`.

---

**Draft status:** prepared for human review. Nothing in this repository or this release has been
published, and the review notes in the factory's `STATE.md` list what a reviewer should decide —
starting with the code licence.
