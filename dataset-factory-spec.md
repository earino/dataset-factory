# Dataset Factory — specification

**Status:** specification, not yet built. Written 2026-09-17.

## What you are building

A pipeline that finds, constructs, screens and qualifies **tabular supervised-learning tasks** for use as agent
evaluation problems, and maintains them as a versioned collection with full provenance.

A task is a prediction problem packaged so that a coding agent can be handed a working directory and told to improve
a model, while a **holdout set the agent never sees** decides the score. One such task already exists (`airline`) and
the whole evaluation method rests on it. The purpose of this project is to turn a sample of one into a collection of
many, and to make the collection's quality mechanical rather than a matter of taste.

Build the **qualifier first**. Candidate generation is the easy, replaceable half: a research agent can propose fifty
datasets an hour. Knowing which of them are any good is the hard part, it has a mechanical definition, and it is the
durable asset. Treat the generator as a swappable front end to a well-defined filter.

## Why this exists

Three problems with the current state, in order of severity.

**Contamination.** Agent benchmarks built on public datasets measure recall as much as research. Every famous tabular
dataset has a public leaderboard, and the winning feature recipes are in the training data of the models being
evaluated. An agent that remembers "bin the departure hour and target-encode the carrier" is not doing the work we
claim to be measuring. **Tasks we construct ourselves have no leaderboard by definition.** This is the same logical
move as hiding the test data, applied one level up: hide the task.

**Generality.** Every result we have comes from one dataset. The sharpest question a reviewer can ask is not "how
many runs did you do" but "does any of this hold on another problem". A collection answers it.

**Reuse.** A paper gets cited; a maintained set of uncontaminated, holdout-graded, continuously scored tasks gets
used. Whoever holds the task set influences what gets measured next.

## What you need before you start

This project is built **outside** the benchmark repository and talks to it across a documented interface. Nothing
here assumes the two live together.

| input | how to obtain it | required for |
|---|---|---|
| **The benchmark runner** — an existing harness that runs a coding agent against a prepared task in an isolated container and scores the delivered code on the private holdout | Location supplied by the operator. **If you have not been given it, ask before proceeding; do not write your own.** | stage 4 only |
| **Two reference tasks**, `airline` and `fraud`, in the prepared layout below | Ship with the benchmark repository under `data/prepared/`. | acceptance tests |

Stages 0–3 and 5 need neither of these, so **start there**. They are the bulk of the work and can be built and
tested against nothing but a candidate dataset and the layout contract below.

If the reference tasks cannot be obtained, say so and stop rather than inventing substitutes: the acceptance tests
depend on their *known* verdicts, and a synthetic stand-in proves nothing.

## Non-goals

- **Do not build a new benchmark runner.** One already exists; stage 4 invokes it through the interface above.
- **Do not build a leaderboard or a scoring service.** This produces tasks, not rankings.
- Do not handle images, audio, or free-text-dominant problems. Tabular only.
- Do not attempt to automate the final human review. The last gate is a person.

## The one methodological rule that matters most

**Qualify a task on headroom. Never on the spread of agent outcomes.**

It is tempting to keep tasks where repeated agent runs differ a lot, because that looks like an interesting task.
Doing so would be a serious error. Selecting tasks on outcome variance means selecting for noisy tasks, and any
later finding about how much agent runs vary would then be partly an artifact of how the tasks were chosen.

The gate is a property of the *task*: **a competent solution beats the naive baseline by a stated margin.** Variance
is measured afterwards, as a result. Anyone modifying the qualifier must preserve this separation, and the
acceptance tests below exist partly to enforce it.

## Output contract: the data layout

A qualified task must be written in the layout the benchmark consumes. This contract is stated here in full so that
you can build and test stages 0–3 without access to the benchmark source:

```
<prepared-data-root>/<name>/
  meta.json
  public/
    train.csv          # the agent gets this
    eval.csv           # the agent gets this
  private/
    holdout.csv        # the agent MUST NEVER see this; only the scorer reads it
```

`public/` is mounted into the agent's container. `private/` is not. The separation is load-bearing: the benchmark
runs an isolation probe that asserts the holdout file exists nowhere inside the cell. A task that cannot be split
this way is not a task.

`<prepared-data-root>` is wherever the benchmark reads prepared tasks from; the factory writes there, or writes to
its own output directory and the operator copies. The factory must not assume it is inside the benchmark's tree.

`meta.json` must carry at least these fields. This is the reference task's own file, reproduced in full so you can
build against it without the benchmark checkout:

```json
{
  "name": "airline",
  "description": "US domestic flights. Predict whether a flight's departure is delayed by 15+ minutes (dep_delayed_15min = Y/N). Columns: Month, DayofMonth, DayOfWeek (as c-<n> strings), DepTime (scheduled departure, hhmm as integer), UniqueCarrier, Origin, Dest, Distance (miles). Classes are balanced. train.csv is from 2005, eval.csv from 2006 (time-separated).",
  "target": "dep_delayed_15min",
  "positive_label": "Y",
  "id_columns": [],
  "split": "train=2005-slice1-100k, eval=2006-slice1-100k, holdout=2006-slice2-1m",
  "source": "Data Expo 2009 airline on-time data, Harvard Dataverse doi:10.7910/DVN/HG7NV7",
  "experiment_timeout_hint_seconds": 120,
  "columns": ["Month", "DayofMonth", "DayOfWeek", "DepTime", "UniqueCarrier", "Origin", "Dest", "Distance", "dep_delayed_15min"],
  "rows": {"train": 100000, "eval": 100000, "holdout": 1000000},
  "positive_rate": {"train": 0.5, "eval": 0.5, "holdout": 0.5}
}
```

**The `description` is read by the agent.** It must state the prediction problem precisely and must not hint at a
solution. Write it the way a careful colleague would describe the data, not the way a tutorial would. Note how the
reference describes the columns and the split without suggesting a single feature to build.

## Output contract: the task record

Every candidate, qualified or rejected, gets a machine-readable record. This is the project's real output — the
thing that makes the eventual public repository defensible. Store one JSON file per candidate under
`factory/records/<id>.json`. Nothing here may be prose-only; a reviewer must be able to re-check every claim.

```jsonc
{
  "id": "nyc-taxi-tip-2024",
  "status": "candidate|screened|qualified|rejected|published|held_back",
  "rejected_reason": null,              // required when status = rejected; use the gate name, e.g. "saturation"
  "domain": "transport",                // for diversity accounting
  "source": {
    "url": "https://...",
    "download_date": "2026-09-17",
    "sha256": "...",                    // of the raw download
    "license": "CC-BY-4.0",
    "license_url": "https://...",
    "redistributable": true,            // may we republish a derived slice?
    "published_date": "2025-03-01"      // of the source data; later is better for contamination
  },
  "construction": {
    "script": "factory/tasks/nyc-taxi-tip-2024/build.py",
    "target_definition": "tip_amount > 0",
    "split_strategy": "temporal",       // temporal strongly preferred over random
    "split_detail": "train=2024-Q1, eval=2024-Q2, holdout=2024-Q3 1M rows",
    "deterministic_seed": 7
  },
  "measurements": {
    "baseline": {"model": "xgboost-default", "metric": "auc", "score": 0.71, "fit_seconds": 38},
    "headroom": {"best_score": 0.76, "delta": 0.05, "method": "stage4-agent-runs", "n_runs": 3},
    "stability": {"seeds": 5, "baseline_sd": 0.0009},
    "cost": {"fit_seconds_p95": 44, "peak_rss_mb": 2100}
  },
  "audits": {
    "leakage": {"pass": true, "max_single_column_auc": 0.68, "eval_holdout_gap": 0.004, "duplicate_rows_across_splits": 0},
    "saturation": {"pass": true, "note": "baseline 0.71 is inside [0.60, 0.85]"},
    "contamination": {"risk": "low", "searched": ["kaggle", "github", "papers"], "leaderboard_found": false, "evidence": ["..."]}
  },
  "review": {"reviewer": null, "date": null, "notes": null}
}
```

## The pipeline

Five automated stages plus a human gate. Each stage is cheaper than the next; kill candidates as early as possible.
Most should die at 0–2. Only survivors earn stage 4, which costs real compute.

### Stage 0 — metadata screen (seconds, no download)

Reject unless all hold:

| gate | threshold |
|---|---|
| rows, total | ≥ 2,000,000 preferred; ≥ 700,000 acceptable with a note |
| columns | ≤ 200 |
| license | permits redistribution, **or** permits script-only distribution (see below) |
| access | direct download, no click-through agreement, no PII |
| form | static file or dump, not a live API |

### Stage 1 — acquire and construct (minutes)

Download, checksum, and run the construction script. The script must be **deterministic**: same input, same output,
recorded seed. It emits the `<prepared-data-root>/<name>/` layout above.

Prefer a **temporal split** — train on an earlier period, hold out a later one. It is the realistic setting, it
resists leakage through near-duplicate rows, and it is what `airline` does. Use a random split only when the data
has no time dimension, and say so in `split_strategy`.

The holdout should be ~1,000,000 rows where the data allows. Large holdouts make scores precise, which is the whole
point: the measurement noise we care about is the agent's, not the scorer's.

### Stage 2 — baseline and saturation (minutes)

Fit a default gradient-boosted tree model. Record the score.

| gate | threshold | rationale |
|---|---|---|
| baseline AUC | **within [0.60, 0.85]** | below, the problem may be noise; above, there is no room to improve |
| fit time | **≤ 120 s** on 4 cores, 6 GB RAM | the task is run hundreds of times; this matches `experiment_timeout_hint_seconds` |
| peak memory | ≤ 4 GB | cells are capped at 6 GB |

**Saturation is the most common failure and the most important to catch.** A previous candidate (`fraud`, the
Sparkov simulated card-transaction set) reached AUC ≈ 0.997 from three obvious columns and was discarded. If a
default model nearly solves the problem, no agent can demonstrate anything on it.

For regression targets, the equivalent gate is that a default model's RMSE must be beatable by ≥ 5 percent relative,
and the baseline must not already be within 5 percent of a strong tuned model. Classification is the priority for a
first version; regression tasks are a valuable second metric family but may follow.

### Stage 3 — leakage and stability audit (minutes)

All must pass:

- **No single column predicts the target too well.** Compute per-column univariate AUC. Any column above 0.95 is
  either the target restated or a downstream artifact. Investigate and usually reject.
- **Eval and holdout agree.** Fit on train, score on both. A large gap means the split leaks or the periods differ
  more than intended. Record `eval_holdout_gap`.
- **No duplicate or near-duplicate rows across splits.** Exact-match on the feature tuple at minimum.
- **Target definition is causally clean.** No column may be recorded *after* the outcome it predicts. This cannot be
  fully automated; heuristics plus the human gate.
- **Baseline is stable across seeds.** Refit five times; the SD must be small relative to the headroom threshold
  (target: `baseline_sd` < 0.005).

### Stage 4 — headroom via real agent runs (hours)

This is the qualification test, and it calls the benchmark named in "What you need before you start" rather than
approximating it. Point that runner at the candidate task with a small configuration — one agent, one model,
**3–5 seeds** — and read the outcome distribution.

Treat the runner as an external dependency behind a thin adapter: the factory hands it a prepared task directory and
receives back, per run, a holdout score and a completion status. Keep that adapter to one module, so a change in the
runner's own interface does not reach into the rest of the pipeline. If the runner is not available yet, build
stages 0–3, leave stage 4 behind the adapter boundary, and mark candidates `screened` rather than `qualified`.

| outcome | verdict |
|---|---|
| best run beats baseline by **≥ 0.03 AUC** | **qualify** |
| best run beats baseline by < 0.03 | reject: insufficient headroom |
| runs beat baseline by an implausible margin | **re-audit for leakage before believing it** |
| runs fail or crash for task-specific reasons | reject: not runnable |

Note what is *not* here: no gate on how much the runs differ from each other. See the methodological rule above.

### Stage 5 — human review

A person reads the `description`, the construction script, and the contamination evidence, then sets
`review.reviewer` and `review.date`. Tasks are not qualified until this happens.

## Contamination assessment

For every candidate, search and record evidence: Kaggle competitions and notebooks, GitHub repositories, published
papers and blog posts that use this source *with this target*. Record `risk` as low, medium or high with the
evidence that supports it.

**Constructed tasks are the preferred answer.** When you define the target, the slice and the split yourself from a
raw source, no leaderboard exists even if the raw data is famous — `airline` is exactly this. Prefer raw sources
published after mid-2024, and record `source.published_date`.

## Distribution policy

**Where the license permits redistribution**, publish the derived slice.

**Where it does not**, publish the construction script and a pinned source URL plus checksum instead. A deterministic
build script is a legitimate and well-established way to distribute a task, and it has a side benefit: the task
definition is yours even when the raw data is not.

**Decide the publish-versus-withhold split now, before there is anything worth withholding.** Some qualified tasks
are published so others can reproduce the work. Others are **held back** as a genuinely uncontaminated set for later
evaluation rounds, because a task's contamination clock starts the moment it is published. The `held_back` status
exists for this. Retrofitting this policy after everything is on GitHub is not possible.

## Diversity requirement

The collection must vary in **what kind of thinking wins**, not merely in subject matter. Eight tasks that all reward
the same time-and-category feature engineering are eight copies of one task. Track and balance across: temporal
structure, geographic or spatial aggregation, rare-event handling, high-cardinality categorical interactions, and
signal spread thinly across many weak features. Record `domain`, and report the distribution in `factory report`.

Aim for **at least one task with natural class imbalance**. `airline` is deliberately balanced 50/50, which means
average precision on it ranks runs but is not production precision. A task with realistic prevalence would let
downstream work make cost arguments without that caveat.

## Acceptance tests

The qualifier must reproduce two known verdicts before it is trusted on anything new. These are a labeled test set
for the pipeline itself.

1. **`airline` must QUALIFY.** Baseline AUC 0.7148, agents reach roughly 0.74–0.77, 100k train / 100k eval / 1M
   holdout, temporal split (train 2005, eval and holdout 2006), fits well inside the time budget.
2. **`fraud` (Sparkov) must be REJECTED at stage 2 for saturation.** A default model reaches AUC ≈ 0.997. The
   pipeline must reach this verdict on its own, without being told.

**If the pipeline does not independently reject `fraud`, it is not ready to judge a new candidate.** Both tasks ship
with the benchmark repository in the prepared layout above; copy them in. Note that `fraud` is rejected at stage 2,
which needs no agent runs at all — so that half of the acceptance test works before stage 4 exists.

For reference when checking your verdicts: `fraud` is a simulated card-transaction set with a positive rate near
0.006 and roughly 500k/150k/556k rows. Its problem is not the imbalance, which is realistic and desirable; it is
that three obvious columns carry almost all the signal.

## Suggested surface

```
factory discover [--n 30]        # research agent proposes candidates, writes records with status=candidate
factory screen <id>              # stages 0-3; updates the record; exits non-zero on rejection
factory qualify <id>             # stage 4; calls the external benchmark runner via the adapter
factory report                   # status table: candidates, qualified, rejected by reason, domain spread
factory publish <id> [--hold]    # emit to the public collection, or mark held_back
```

Keep discovery separate from screening in both code and process, so that the generator can be replaced — by a
different research agent, by a human with a hunch, by a list from a collaborator — without touching the filter.

## Definition of done, version 1

- The pipeline runs end to end on both acceptance tests and returns the correct verdict for each.
- At least **eight qualified tasks**, spanning at least five domains and at least three of the "kinds of thinking"
  listed above, with at least one naturally imbalanced target.
- Every qualified task has a complete record, a deterministic construction script, and a human review.
- `factory report` renders the collection's status and diversity.
- A written policy file naming which tasks are published and which are held back, and why.

## Open questions for the human

These are deliberately unresolved; raise them rather than guessing.

1. How many tasks should be held back versus published in the first release?
2. Should regression tasks be in version 1, or does classification-only ship first?
3. Is there an appetite for tasks that take longer than 120 s to fit, given the cost multiplies by hundreds of runs?
4. Who is the named reviewer for stage 5?
