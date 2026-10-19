# openfda-food-recall-classification

**Verdict: REJECT (2026-10-19).** Dropped on novelty; the search evidence and the one
measured probe, recorded 2026-10-19.

## What already exists (the equivalent)

| Prior art | What it ships |
|---|---|
| "Hazard-portfolio patterns in US food recall severity reveal ..." (PMC13526789, 2025) | The exact task on the exact source: 28,448 openFDA food enforcement records 2012-2025, three-level classification target (Class I 44.1% / II 50.1% / III 5.8%), ML triage models, firm-history baseline reaching 92% of the best model's performance, 92% of pathogen-related Class I recalls identified for unseen firms |
| RecallRisk-BERT (arXiv 2606.27174) | Same severity-triage task on openFDA *device* recalls, 54,165 records 2002-2025, multi-task severity + root-cause |
| Kaggle "fda-food-drug-device-recalls" (darkmatternet) | Analysis-ready unified snapshot of food/drug/device recalls 2012-2026, harmonised fields, parsed dates, versioned reason categories |
| SafeBite (OpenReview) | Fine-tuned classifiers assigning health-hazard evaluations from recall texts |

## Measured probe (2026-10-19)

| Command | Result |
|---|---|
| `curl -sS 'https://api.fda.gov/food/enforcement.json?limit=1'` | HTTP 200 anonymous; `meta.results.total = 29,485` records (vs the paper's 28,448 through 2025 - the source keeps growing, which is what makes it attractive); first row carries `classification: "Class II"`; meta carries `terms: https://open.fda.gov/terms/`, `license: https://open.fda.gov/license/` and the "results are unvalidated" disclaimer |

## Why it fails the standing test

The source, the task, the label distribution, models and a firm-history baseline are
all published. Ours would be re-partitioning only - a mirror, not a contribution.
Rejected per the standing novelty test. The reachability and licence evidence above is
recorded so nobody re-opens this as a candidate without new prior art contradicting
the 2025 paper.
