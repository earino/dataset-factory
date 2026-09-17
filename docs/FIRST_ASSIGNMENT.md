# Discover and construct our first task

The objective is one finished, interesting prediction task from a source the
operator has not selected for you. Read the supplied hosted inventory in
`../deployment/capabilities.md`, then begin researching real sources.

## Investigate

Explore a small, varied shortlist. City calendars, parking observations,
transport, environmental measurements, and public operational records are useful
starting directions, not mandatory domains.

For each serious lead, use `python3 -m factory candidate create <short-id>` and
record the source URL, an example schema, access/license evidence, and a concrete
prediction question. Explain when the prediction would be made and how its outcome
would be observed. A calendar alone does not establish attendance labels; find
observable outcomes or use the calendar as a feature source for another task.

Use small samples or metadata first. Keep large downloads on workers. Record
rejections and avoid repeating failed investigations without new evidence.

## Construct and measure

Pick a promising source based on evidence. Prepare a worker job that downloads
the source, records its checksum, builds reproducible splits, and reports a simple
baseline plus data-quality checks. Implement only the tools needed for this
candidate, making reusable pieces explicit as they emerge.

The first task should fit the existing binary-classification runner. Treat that
as a starting proposal, not a reason to discard a promising regression source;
record those leads for later. Use sufficient data for meaningful evaluation, with
temporal splits when appropriate. Explain the task without suggesting a solution.

The intended prepared layout is:

```
<task>/meta.json
<task>/public/train.csv
<task>/public/eval.csv
<task>/private/holdout.csv
```

The `private` directory is excluded from evaluated agents' workspaces even when
the dataset's holdout is publicly downloadable. Preserve the runner metadata
contract in the original spec. Never modify the existing benchmark checkout.

If benchmark access is missing, finish the construction and available checks,
record the remaining experiment, and keep the candidate under investigation.
Do not invent a runner, scores, or an acceptance verdict.

## Bring a concrete candidate for review

Deliver construction code, source and license evidence, small machine-readable
measurements, checksummed artifact links, runner results when available, a draft
dataset README, and a short proposed monthly write-up. Bulk artifacts should
already be preserved off the worker before it is deleted.

The public dataset repository must work without this private factory repository.
Record uncertainties and any remaining work plainly. Review comes before public
publication. Continue researching other leads while a candidate awaits review.
