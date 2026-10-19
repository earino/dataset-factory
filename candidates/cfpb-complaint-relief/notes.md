# cfpb-complaint-relief

**Verdict: REJECT (2026-10-19).** Dropped on novelty before any data fetch; the search
evidence, recorded 2026-10-19.

## What already exists (the equivalent)

| Prior art | What it ships |
|---|---|
| arXiv 2606.22664 "Sub-Issue Vs. % Of Replies..." | The exact task: binary monetary-relief classification on CFPB complaint data from narrative text + LDA topics + structured intake fields (company, state), XGBoost, **temporal train/test split**, AUC-ROC 0.78 vs 0.69 TF-IDF baseline, PR-AUC under class imbalance |
| "Customer complaint analytics in digital financial services" (Future Business Journal, 2026) | Predicts subsequent *untimely* company responses from intake-time information; chronological holdout; ROC AUC 0.7653, AP 0.04985 |
| github.com/RishiRatnakarData/consumer-complaint-intelligence | End-to-end pipeline: intake-time-only features, **leakage-aware**, chronological 75/25 split, DuckDB/SQL models, measured company-level relief rates (TransUnion 63.3%, Equifax 63.2%, Experian 0.7%) |
| Yale SOM (Shin, Shin & Kim, 2025) | 1.1M+ complaints analysed for relief outcomes vs LLM-written narratives; 10.28 pp relief increase for LLM-assisted complaints |

## What was observed (not measured - no data probe)

- Endpoint reachability from the coordinator, 2026-10-19:
  `https://data.consumerfinance.gov/api/views/s4z5-9hvp.json` answered a 4,419-byte
  non-JSON (HTML error) page; `resource/x94y-yhhf.json` answered 404; TLS to the host
  fails for both curl and urllib ("unable to get local issuer certificate") because the
  server does not send the full chain. The current access path is the data-research API
  at `api.consumerfinance.gov`, which was not probed because the novelty rejection came
  first. Licence was therefore not re-read; it is moot for a rejected candidate.

## Why it fails the standing test

The task, the intake-time feature discipline, the temporal-split protocol and even
company-level baseline rates are all public. Ours would be re-partitioning only -
a mirror, not a contribution. Rejected per the standing novelty test.
