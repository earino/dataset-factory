# Dataset release README template

Copy this into the dataset's own repository when preparing its first release.
Replace every placeholder with evidence. The public repo must work independently
of the private factory. This is a content checklist, not a packaging implementation.

## Task

Describe the prediction question, target, unit of observation, prediction time,
available features, population, date range and practical meaning of the outcome.

## Source and permissions

List source URLs, access dates, owners, license links and redistribution terms.
Distinguish the source data license from the construction code license. Record
input hashes, access limitations and transformations.

## Download this version

Link the tagged GitHub Release, assets, sizes and SHA-256 manifest. Provide exact
download, verification and unpacking commands, or reproducible acquisition steps
where redistribution is unavailable. Pin the construction commit and dependencies.

Prepared layout:

```
task/meta.json
task/public/train.csv
task/public/eval.csv
task/private/holdout.csv
```

Explain metadata, target column, categorical treatment, splits and row counts.
The holdout may be publicly downloadable but must remain outside the evaluated
agent's workspace during a benchmark run.

## Reproduce and evaluate

Include runnable acquisition/construction code, dependency versions, measured
resource needs, exact commands and the existing benchmark's pinned revision and
configuration. Describe leakage, duplicate, temporal/group boundary, missing-value
and label prevalence checks. Report measured baselines, headroom and completed
harness experiments with seeds, budgets and uncertainty.

## Findings and limitations

Explain what the task measures, label or sampling weaknesses and what experiments
establish. Link the monthly findings page. Include attribution, citation text,
changelog and correction/versioning policy.
