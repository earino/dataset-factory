# rasff-notification-risk-decision — discovery notes

Opened 2026-10-27 by the scheduled Europe (EU/EEA) discovery tick, after the
TED lead was closed as a mirror. Status: **dropped — mirror** (licence
deliberately unread: the mirror veto is decisive regardless of licence class).

## Task considered

Prospective user: food-safety authorities and importers triaging incoming
RASFF notifications. Question: at the circulation of a new notification
(product, origin, notifier, reason for notification, hazard signal), will the
risk assessment classify it as a serious risk?

## Source discovery (2026-10-27, probe/probe_rasff_catalogue.py)

data.europa.eu hub search (queries: "RASFF notifications food feed safety",
"Rapid Alert System Food Feed RASFF portal data") returns exactly one official
EU dataset: **restored_rasff — "Food and Feed Alert Notifications"**,
publisher **Directorate-General for Health and Food Safety (DG SANTE)**, issued
2015-08-18, modified 2025-03-07, 4 distributions:

1. RASFF Window search page (HTML):
   https://webgate.ec.europa.eu/rasff-window/screen/search
2. APIs User Guide (PDF):
   https://developer.datalake.sante.service.ec.europa.eu/api-details#api=2955fdc1-9da2-4927-977f-40dc50db1128&operation=cc6aab62-bd15-4904-b20d-54551ccb9468
3. Food and Feed Alert Notifications (JSON API, same developer portal)
4. XLSX "RASFF notifications pre-2021 public information":
   https://data.europa.eu/euodp/data/storage/f/2021-06-03T125456/RASFF%20notifications%20pre-2021%20public%20information.xlsx

All distribution-level licence fields are null (the DG SANTE datalake API
terms and the window's legal notice would be the instruments to read first on
any reopen). The API itself was **not** called this session — the novelty
search landed first and was decisive.

## Why it is a mirror (novelty searches, 2026-10-27)

The obvious task — classifying RASFF notification risk decisions — is a
published, repeatedly-posed ML task with chronological splits and released data:

- **Frontiers in Food Science & Technology (2026)**
  doi:10.3389/frfst.2026.1890831: binary serious/not-serious classification;
  28,708 RASFF records 2019-2025 → 22,643 after dropping ambiguous risk
  decisions; **chronological training/calibration/test split**; XGBoost +
  Mondrian conformal prediction + Platt scaling; accuracy 0.784; serious base
  rate 79.1% post-exclusion.
- **Springer (2025) doi:10.1007/s11947-025-03819-4**: LR/SVM/RF/DT/NB/XGBoost/
  LightGBM/AdaBoost/ANN classifying serious / not serious / undecided over
  **61,350** RASFF entries (serious 28.93%, not serious 22.42%, undecided
  48.65%), with enrichment and XAI.
- **arXiv 2009.06704 (2020)**: categorical-embedding MLP/CNN predicting
  product category, hazard category and the action/measure to be taken,
  RASFF 2004-2018, accuracy 74.08-93.06%.
- **MDPI (2026) 2673-4532/6/3/36**: 1,138 pesticide-residue RASFF alerts
  2020-2025; **the cleaned dataset (RASFF_enriched.csv) is released as
  supplementary material**.

Product-category, hazard-category, required-measure and risk-decision targets
are therefore all taken. Any reopened task needs a genuinely different target
variable, its own recorded novelty sweep, and — independently — a resolution
of the vintage problem: the public record is the **current consolidated
notification**; the risk decision is assigned during post-notification
assessment, and initial-notification vintage is not separately published, so
feature availability at a stated instant cannot be evidenced from this source
alone as it stands.

## Regional coverage note

This record plus ted-procurement-single-bid document the 2026-10-27 EU/EEA
tick: two machine-readable EU leads probed, both resolving as mirrors of
published tasks with the prior art named. The EC infringement-procedure lead
was checked and found to have **no official machine-readable register
dataset** on data.europa.eu (searches return only irrelevant national
datasets; the Commission publishes monthly decision packages as HTML/PDF), so
it was not opened as a candidate — a data-availability dead end, recorded
here and in STATE.md.
