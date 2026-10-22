---
name: large-dataset-builds
description: "Use when bulk-file datasets must build under tight RAM."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [data-engineering, streaming, memory, csv, parquet, aggregation, pandas]
    category: software-development
    related_skills: [dataset-qualification, validation-gate-design, multi-destination-publishing]
---

# Large dataset builds

Turning tens of monthly bulk files into one tidy artifact looks like a pandas one-liner and is not:
the naive version holds the whole panel in memory, dies silently on a small host, and produces nothing
for an hour. This is the procedure that gets to a verified artifact on a machine with a few GB of RAM.

## When to use

- A source publishes one file per month (or per day) and the panel spans years.
- The raw input is measured in GB and the host has 2-4 GB of RAM, or you do not know the host's limit.
- A first attempt "hung" with no output, or was killed without a message.

## Procedure

1. **Measure one unit before designing.** Read a single input file and count: rows, distinct entities,
   the grain you actually need, and how many rows survive the eligibility filter. Multiply. That
   number decides the scope (one state, a sample of entities, a shorter window) before you write the
   pipeline - not after it runs out of memory.
2. **Reduce each input as it lands, and delete the raw file.** One file at a time: parse, aggregate to
   the grain you need, write a compact parquet, remove the CSV. Peak disk becomes one file instead of
   the whole corpus, and re-runs after a crash skip what is already reduced.
3. **Stream the output.** Never accumulate emitted rows in a list of dicts: a million-row panel is
   already ~1 GB of Python objects. Have the per-period emitter call a sink that writes to the split
   file with `mode="a"` and a header only on first write. Memory stays flat in the number of rows.
4. **Decide eligibility from the past only.** A row may exist because of what is known at the
   prediction instant; the outcome period supplies the label and must not decide membership. Count
   rows dropped for missing history and rows dropped for an unobserved outcome as separate numbers.
   `validation-gate-design` explains why a later period deciding membership is a defect even when
   every feature is clean.
5. **De-duplicate at period boundaries.** A month file starting mid-week, or a week appearing in two
   consecutive files, emits the same row twice. Keep a seen-set of period keys and skip a period
   already emitted; a duplicate-identifier count is the symptom the gate catches later.
6. **Run the qualification gate on a slice first, then the full artifact.** Descriptor-shape failures
   (splits, measurements, sentinels) cost seconds on 5k rows and minutes-to-OOM on a million. Fix the
   descriptor against the slice, then run the full build once.
7. **Write the artifact's own summary.** Split counts, positives, unobserved outcomes and the scope
   filter go into `summary.json`: every downstream reader needs them, and re-deriving them from the
   CSV is how two readers end up disagreeing.

## Pitfalls

- **A filtered run that matched nothing looks like one that matched everything.** If the filter column
  was dropped in a previous step, an explicit equality filter raises - but a merge that quietly
  misses, or a filter over an absent column, returns the full set, and the build proceeds at full
  national scale under a state-scoped log line. Assert the filtered row count against the unfiltered
  one and exit when the filter removed nothing, before any expensive work.
- **A process at 4% CPU is not idle, it is swapping.** On a 2 GB host with 1 GB of swap, a build
  holding a million dicts shows near-zero CPU while thrashing. Read RSS and swap before concluding
  "slow"; the fix is the streaming shape above, not a longer timeout.
- **Piping a long build through a pager hides every progress line.** The pipe buffers until exit, so a
  working run and a wedged one look identical. Run unbuffered (`python -u`) and print a periodic
  count, or write progress to a log and read it with `read_file` while the build runs.
- **Duplicate column names in the output header.** Building the column list as `identity + features`
  where the feature list already contains those identity columns produces repeats, and a column-wise
  reader then collects twice as many values as labels. Assert the emitted header has no duplicates.
- **NaN features the contract cannot express.** A lag that does not exist must be a sentinel the gate
  and the model both understand (a negative value for a strictly positive quantity), documented in
  the data dictionary. Leaving NaN breaks leakage scoring and silently changes model behaviour.
- **Choosing scope to dodge the size problem after the fact.** "Sample 15% of premises" chosen because
  the build was too big is a different task from the one in the candidate record. Decide scope from
  the measurement in step 1, state it in the task definition, and keep it stable across rebuilds.
- **Trusting a successful exit as a complete build.** Check split counts, excluded-row counts and
  artifact size against the estimate from step 1; a build that lost half its months still exits 0.
