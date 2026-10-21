---
name: dataset-discovery
description: "Use when vetting an open-data source as a prediction task, before construction."
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

## The five contracts a source must satisfy

A source that fails any one of these cannot produce a usable dataset, however interesting it
looks. Each is cheap to test and expensive to discover late:

1. **Redistribution.** The licence or terms must permit publishing derived rows. Publicly
   *viewable* is not *redistributable*. A source silent on redistribution is not publishable -
   record the question and escalate it as a decision, never assume permission. When the operator
   accepts the risk instead of producing a licence, record it as a **risk acceptance, not a
   grant**: `references/licence-posture.md`.
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

## Triage the licence before you probe the task

The licence is the cheapest veto and the most common one: when half the parked candidates die on
licence or terms, almost all of them died **after** their schemas had been read and their volume
measured. That order is the waste. Classify first, in minutes, and record it on the candidate as
`licence_class`:

| Class | Meaning | What happens |
| --- | --- | --- |
| **A** | Explicit open licence permitting redistribution *and* derivatives (OGL, CC BY, CC0, US federal public domain) | Probe the task |
| **B** | Open but conditional - attribution-plus-sharealike, or a compilation licence over a source with its own terms | Probe, and plan to state the conditions in `LICENSE.md` |
| **C** | Unstated, ambiguous, or "contact us" | Park at once with a dated path out; a written enquiry may be drafted, the candidate does not proceed until an answer exists or the operator accepts the risk |
| **D** | Prohibits redistribution or derivatives, or requires an authorisation not held | Reject on the spot with the clause quoted |

- **Classify from the publisher's own instrument**, not from a general policy page. A general
  open-content policy can coexist with dataset-specific terms that restrict alteration or transfer;
  read the terms linked from the dataset itself.
- **`licence_class` belongs in the candidate's required fields** for any status at or beyond
  `ready`, so a candidate cannot reach construction unclassified. Investigate-status records may
  stay unclassified; nothing else may.
- **Sort the construction queue by class**, not by novelty or volume: `python3 scripts/licence-rank.py`
  prints it A -> D and flags buildable-looking candidates stuck at triage. Work down from the top.
- A session that ends with three C verdicts has done its job: it closed three doors cheaply. What it
  must not do is spend the session characterising a source that was never shippable.

## Geographic coverage is a measured property

US federal sources are usually the cheapest to probe anonymously, so an unchallenged pipeline
drifts toward them: the bench looks healthy while its geography is one country. Measure it.

- **`jurisdiction` is a required field on every candidate record** — `{"country": "FR", "region":
  "Europe", "publisher": "..."}`. Put it in the completeness checker's required list: an optional
  field stays empty, and a field added after the fact cannot be trusted to have been measured.
- **"International" means the publisher's jurisdiction**, not the subject matter. A US agency
  publishing global data is a US source; a national statistics office is not.
- Keep a coverage report that prints counts by country and region, the **non-US share of live
  candidates**, and lists unstated jurisdictions as `unknown` — never inferred from a URL — and
  exits non-zero while any are unstated, so a regression fails a check instead of aging quietly.
- Give a recurring discovery routine a **rotating regional focus**, derived deterministically from
  the clock so a report can be reproduced from its timestamp, and require most of a session's
  verdicts from that region. Rotation list and starting points: `references/geographic-coverage.md`.
- **Never backfill the quota with a US source when a region comes up empty.** Record the empty
  result with the probes that produced it; a padded quota hides exactly the gap the routine exists
  to find.
- Count parked candidates in the geography but not in "live". A licence-blocked non-US source does
  not make the published pipeline international.

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

1. **Licence and terms.** Free to check, and a veto: class it (A/B/C/D above) and stop at C or D
   before spending anything on schema or volume.
2. **Aggregate queries.** Counts, ranges, base rates, distinct keys - offline, no bulk transfer.
   **Also count the mix of every categorical provenance column** (`ORIGIN_SOURCE`, `SENTINEL` /
   `NONSENTINEL`, `status`, `measure_type`) before deciding what a row means. Summing two streams
   that are not the same population (sentinel vs non-sentinel sampling, clinical vs survey testing)
   silently changes the label's meaning, and an unlabelled bucket makes it worse: in one source 46%
   of rows carried `ORIGIN_SOURCE=NOTDEFINED`, so a "sentinel + non-sentinel" total was really a
   mixture of three populations. Record the mix and the eligible-row count per stream; if one
   stream cannot carry the task alone, say so at discovery time rather than discovering it when a
   reviewer asks what the target means.
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
| "The publisher states no terms" | A 403 to a plain HTTP client read as an absent page | Re-read it in a real browser before recording silence; then `references/licence-posture.md` |
| Feature list looks right, dataset scores perfectly | A carried source column shipped the answer | Hand to `dataset-qualification`; it tests shipped columns, not lists |
| Cost estimate wrong by an order of magnitude | Paging arithmetic guessed instead of measured | Wrap the fetch, count requests, record the machine class |
| Candidate sits "interesting" for weeks | No verdict recorded | Force build/park/drop with the reason; parking is a valid outcome |
| The "dataset" is really a mirror | Only the source was checked, not the existing task | Search public catalogs *and* the literature for the exact task; `check-novelty.py` refuses an absent verdict and marks `mirror` as unpublishable |
| The publisher nearly hands us the task | Feasibility mistaken for contribution | The easier the fetch, the *less* the access is worth: state what is ours (formulation, splits, gating, validation) or don't publish |
| A negative finding from a wrong probe | Query typo read as "does not exist" | The API's own error text lists valid parameters; read it, and re-probe before recording a negative |
| Target meaning shifts between years or countries | Two provenance streams summed into one rate, or an unlabelled bucket included | Count the provenance mix first; define the task on one stream, or record the mixture as part of the definition |

## Completion criteria

A candidate is **ready** - the buffer state, before construction - when:

- [ ] All four contracts are satisfied, each with recorded evidence.
- [ ] `jurisdiction` recorded as country, region and publisher — measured from the publisher, not
      inferred from the URL.
- [ ] The licence question is either settled or explicitly escalated as a decision.
- [ ] `licence_class` recorded (A or B for anything heading to construction; C only with a dated
      path out; D rejected), and the quoted evidence stored in `license_evidence`.
- [ ] `check-candidate.py` reports no missing required field, including a **novelty check** with
      a verdict of `no_precedent` or `differentiated` - never `mirror`.
- [ ] Split windows and their computed counts are recorded, with clustered counts where they differ.
- [ ] Extraction cost is measured, not estimated.
- [ ] `record.json` carries a verdict: `ready`, `parked` (with the blocker) or `dropped` (with the reason).

Aim to keep **one ready candidate in the buffer** behind whatever is currently being built, so a
failed construction never leaves the queue empty.

## References

- `references/geographic-coverage.md` - a region rotation for international sourcing, with the
  portals, licence habits and gotchas of each.
- `references/licence-posture.md` - what to record when a publisher states no terms: the channels to
  read, the enquiry and its deadline, and how to write an operator risk acceptance so it cannot be
  mistaken for a grant.
- `scripts/check-candidate.py` - mechanical completeness check over a candidate record.
- `skills/dataset-qualification/` - the gate that runs after construction.
- `skills/dataset-release/` - packaging and publication once a dataset is qualified.
