---
name: dataset-discovery
description: "Use when choosing or vetting an open-data source as a prediction task. Decides usability before any construction work is spent."
version: 1.0.0
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [datasets, open-data, sourcing, licences, prediction-tasks, feasibility, vetting]
    category: research
    related_skills: [dataset-qualification, dataset-release, grounded-citations]
---

# Dataset discovery

## When to use

While looking for a prediction task, or when deciding whether a lead is worth construction:

- A candidate source has been found and nobody has yet verified it can carry a dataset.
- A construction attempt would be justified only if the source passes a cheap feasibility test.
- A queue needs its next task chosen, or a stalled candidate needs a verdict: build, park, or drop.
- A reviewer asks why a source was rejected - the rejection needs recorded evidence too.

Not for building the files (`dataset-qualification` gates them) and not for publishing
(`dataset-release`). Discovery ends when a candidate is **ready**, not when it is constructed.

## The four contracts a source must satisfy

A source that fails any one of these cannot produce a usable dataset, however interesting it
looks. Each is cheap to test and expensive to discover late:

1. **Redistribution.** The licence or terms must permit publishing derived rows. Publicly
   *viewable* is not *redistributable*. A source silent on redistribution is not publishable -
   record the question and escalate it as a decision, never assume permission.
2. **Prediction timing.** The instant a prediction is made must be stateable, and every
   intended feature's meaning must be documented by the publisher. An undocumented column is
   unusable, not "probably fine".
3. **Target.** The label must be derivable from data that can actually be obtained, and its
   source column must be excludable from what ships.
4. **Split capacity.** Enough *independent* positives, spread over time, to fill disjoint
   train/eval/holdout windows with both classes present.
5. **Not a mirror.** The *task* must not already exist in ML-ready form. The publisher having the
   raw data is fine and expected; the publisher or anyone else already shipping this prediction
   task with splits and a scored contract is not. **A mirror is not published** - better to
   publish nothing than to republish what a consumer can already download.

## Commands

```bash
# candidate tracking
python3 -m factory candidate list
python3 -m factory candidate show <candidate-id>

# mechanical completeness check over a candidate record
python3 scripts/check-candidate.py <candidate-id>

# the novelty check: mechanical search, explicit verdict, recorded in the record
python3 scripts/check-novelty.py <candidate-id> \
    --query "coastal flood" --query "tide gauge" \
    --verdict differentiated \
    --ours "what this contributes that does not already exist" \
    --theirs "what the publisher and prior art already provide" \
    --prior-art "FloodCastBench, Sci Data 12:431 (2025)"
python3 scripts/check-novelty.py <candidate-id> --check      # is a valid verdict recorded?

# probe pattern: read-only aggregate queries first, on the worker if the source is large
python3 candidates/<id>/probe_*.py --limit 200
```

Measure, do not estimate, the extraction cost: wrap the fetch function and count requests, and
record the wall-clock time and output size on the machine class that will run it.

## Required evidence

A candidate record (`candidates/<id>/record.json`) that answers all of:

- Source identity: endpoints/URLs, publisher, retrieval date, licence and the terms quote.
- Schema: every column with its **documented** meaning and whether it is available at
  prediction time, post-hoc, or the label source.
- The prediction instant, stated in one sentence, and the target definition with its source
  column named.
- Split windows with counts **computed from the source**, plus the clustered/independent count
  where positives arrive in clusters.
- Extraction cost: HTTP requests, bytes, wall-clock on the intended machine class.
- A known-event fixture (named event, expected verdict, source) wherever an external threshold
  is compared against.
- A cross-check against the publisher's own summary product where one exists.

`notes.md` carries the row-level probes: the exact command and its result. A claim without a
command behind it is a guess.

## Order of work, cheapest first

1. **Licence and terms.** Free to check, and a veto.
2. **Aggregate queries.** Counts, ranges, base rates, distinct keys - offline, no bulk transfer.
3. **Read the column documentation.** Every field, not the suspicious ones. This is where
   post-hoc fields are caught before they reach a feature list.
4. **Uniqueness and ordering probes.** Establish a total order before any paging (see below).
5. **Split capacity.** Compute whether three disjoint windows can each carry both classes.
6. **Cost.** Measure requests/bytes/time; only then is construction budgeted.
7. **Construction and qualification.** Hand off to `dataset-qualification`.

## Common failure modes

| Symptom | Cause | Action |
| --- | --- | --- |
| Pages repeat or drop rows | Paging on a non-unique key | Use a total order with a tiebreaker (e.g. `incident_number,:id`); verify by re-reading a page |
| Thousands of positives, tiny effective sample | Positives cluster (same storm/day/station) | Report the clustered count and put intervals on it |
| Uniform result from a threshold | Threshold's unit/reference frame unstated | Find the frame; add a known-event fixture before using it |
| "Public data" assumed publishable | Licence silent on redistribution | Record the question, escalate as a decision, do not ship |
| Feature list looks right, dataset scores perfectly | A carried source column shipped the answer | Hand to `dataset-qualification`; it tests shipped columns, not lists |
| Cost estimate wrong by an order of magnitude | Paging arithmetic guessed instead of measured | Wrap the fetch, count requests, record the machine class |
| Candidate sits "interesting" for weeks | No verdict recorded | Force build/park/drop with the reason; parking is a valid outcome |
| The "dataset" is really a mirror | Only the source was checked, not the existing task | Search public catalogs *and* the literature for the exact task; `check-novelty.py` refuses an absent verdict and marks `mirror` as unpublishable |
| The publisher nearly hands us the task | Feasibility mistaken for contribution | The easier the fetch, the *less* the access is worth: state what is ours (formulation, splits, gating, validation) or don't publish |
| A negative finding from a wrong probe | Query typo read as "does not exist" | The API's own error text lists valid parameters; read it, and re-probe before recording a negative |

## Completion criteria

A candidate is **ready** - the buffer state, before construction - when:

- [ ] All four contracts are satisfied, each with recorded evidence.
- [ ] The licence question is either settled or explicitly escalated as a decision.
- [ ] `check-candidate.py` reports no missing required field, including a **novelty check** with
      a verdict of `no_precedent` or `differentiated` - never `mirror`.
- [ ] Split windows and their computed counts are recorded, with clustered counts where they differ.
- [ ] Extraction cost is measured, not estimated.
- [ ] `record.json` carries a verdict: `ready`, `parked` (with the blocker) or `dropped` (with the reason).

Aim to keep **one ready candidate in the buffer** behind whatever is currently being built, so a
failed construction never leaves the queue empty.

## References

- `scripts/check-candidate.py` - mechanical completeness check over a candidate record.
- `skills/dataset-qualification/` - the gate that runs after construction.
- `skills/dataset-release/` - packaging and publication once a dataset is qualified.
