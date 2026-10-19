# hc-recalls-classification

## 2026-10-19 discovery session (regional focus: Canada)

Probe: `python3 .factory/probe_ca_npri_measure.py` (recalls_stats section), script
deleted after use; CSV downloaded to scratch and deleted after measurement.

- CKAN package_show d38de914: 'Recalls and Safety Alerts', org `hc-sc`, OGL-Canada.
  Resources: CSV + JSON, en/fr, refreshed daily (Last-Modified 2026-10-19 02:25 UTC).
- Full CSV (10,668,115 B): 34,263 rows / 34,263 distinct NIDs; columns NID, Title, URL,
  Organization, Product, Issue, "What you should do", Category, "Recall class",
  "Last updated", Archived.
- Organizations: TC 9,952; Medical devices 8,686; CFIA 5,331; Consumer product safety
  5,217; Drugs and health products 1,941; other HC branches ~3,100.
- Recall class: Class 1/2/3 = 1,964/1,877/1,504 (food); Type I/II/III = 950/6,859/2,838
  (devices); 18,232 rows (53%) carry none (mostly TC vehicles). Archived: 14,446/34,263.
- "Last updated" is a revision date; some rows carry an empty value (measured minimum),
  so a publication-instant panel is not reconstructable from this product alone.

## Verdict: REJECT (novelty), recorded 2026-10-19

The task this source supports (predict a recall's hazard class from pre-classification
features) already exists in usable, leakage-audited form on the US analogue:

- PMC13526789 (2025): 28,448 openFDA food enforcement records, Class I/II/III target,
  ML triage + firm-history baseline.
- RecallRisk-BERT (medical-device recall classification).
- An analysis-ready Kaggle snapshot of openFDA food recalls.
- Our own candidates/openfda-food-recall-classification record (rejected 2026-10-19)
  documents the same comparison.

A Canadian re-issue changes jurisdiction, not task -> rejection per the standing novelty
test. Access, licence and freshness were all fine; the task is the blocker.
