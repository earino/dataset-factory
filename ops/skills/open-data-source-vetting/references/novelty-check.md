# The novelty (mirror) check

Before building on a source, establish that the *task* does not already exist in ML-ready form.
Raw material being published is expected and fine; an existing formulation with splits, a feature
contract and a scored baseline makes the rebuild a mirror, and a mirror is not published.

## Sweep the catalogs mechanically

All three endpoints are public, need no credential, and answer with JSON or Atom:

```sh
# dataset catalogs
curl -s "https://huggingface.co/api/datasets?search=<terms>&limit=10"                 # JSON list
curl -s "https://zenodo.org/api/records?q=<terms>&size=5"                            # hits.total
# preprint index (Atom XML; count <entry> blocks, no parser dependency needed)
curl -s "http://export.arxiv.org/api/query?search_query=all:<terms>&max_results=5"
```

Run several *task-shaped* terms, not one source-shaped term: for a station-level exceedance task,
`coastal flood`, `tide gauge`, `water level exceedance` find more than the product name does.
URL-encode terms; keep a per-request timeout and record a failed request as `unavailable` rather
than as zero hits.

Read the hits before drawing a conclusion. A catalog full of *observation-level mirrors* of the
same series is not evidence the task is taken - if anything it is evidence that republishing the
observations would add one more copy.

## Then the literature and the operational field

Search for the formulation and for whoever already runs it in production. A mature field can
operate the exact prediction daily while nobody ships it as a benchmark, and a recent
large-scale dataset in the same phenomenon but a different formulation (inundation depth and
extent rather than per-entity threshold exceedance, say) is prior art to cite and differentiate
from, not a veto. Record each precedent with a citation and one clause saying how it differs.

## The verdict is required input, never inferred

The search can be automated; the judgement cannot. Take it as an explicit argument with a fixed
vocabulary and refuse to record a search without one:

- **no precedent** - nothing comparable found;
- **differentiated** - something exists, and what is ours is stated;
- **mirror** - the same task already exists in ML-ready form. **Unpublishable.**

State it two-sided: **what already exists** (publisher, prior art, operational systems) and **what
is ours** (the frozen entity panel, the label anchored to an external threshold and validated
against the publisher's own counts, the feature contract excluding what is unknowable at prediction
time, the splits, the gating). A verdict with no "ours" is a search, not a check.

Write the whole thing into the candidate record: checked-at timestamp, the queries, the per-source
hits read, the precedents, both statements, and the verdict - so a reviewer can disagree with the
judgement without re-running the search.

## Gate placement

Require the block from the **earliest stage at which the rule binds** - before construction spends
a worker, not at release - and treat *mirror* as a refusal in the candidate checker, not a warning.
A verdict recorded only at packaging has already paid for the build it was meant to prevent.
