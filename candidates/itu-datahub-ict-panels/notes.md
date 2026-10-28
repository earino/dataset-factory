# itu-datahub-ict-panels — discovery notes (2026-10-22)

ITU DataHub triaged. Rejected on aggregate-panel shape + existing World Bank mirror; licence
recorded as class B (CC BY-NC-SA 3.0 IGO) so a future session need not re-derive it.

## Access (measured)

```
curl 'https://datahub.itu.org/'          -> HTTP 000 (wrong TLD, connection failure)
curl 'https://datahub.itu.int/'          -> HTTP 403 (919 B)  } plain-client bot wall
curl '.../about/'  '/api/'  '/indicators/'  '/data/'  -> HTTP 403
real browser -> datahub.itu.int/about/ loads; rendered text 11,614 chars
```

The 403-to-plain-client rule from the discovery skill was applied: the page was re-read in a real
browser before any terms claim was recorded.

## Licence (publisher's own instrument, read in-browser 2026-10-22)

> "The Data is licensed to the public through a Creative Commons Attribution-Non-Commercial-
> ShareAlike 3.0 IGO license. Under the terms of this licence, you may copy, redistribute, and
> adapt the Data for non-commercial purposes, provided the work is appropriately cited."

Plus: third-party data caveats per indicator, no-endorsement/no-logo terms, suggested citation
with access date. Class B; NC and SA would carry through unchanged to any release.

## Grain and mirror

- Publisher's own scope (About page): hundreds of ICT indicators, about 200 economies; annual
  questionnaire collections (Household ICT Indicators, World Telecommunication Indicators, ICT
  Price Baskets, Regulatory Information, Tariff Policies).
- Mirror already in usable form: World Bank Data 360 dataset ITU_DH
  (data360.worldbank.org/en/dataset/ITU_DH) carries per-indicator pages labelled
  "License: CC BY-NC-SA 3.0 IGO" (e.g. IT_CEL_SETS mobile-cellular subscriptions, 230 economies,
  2000-2024, annual), and the WB Data Catalog copy (dataset 0067055, 5.6 MB, updated 2026-03-14)
  claims CC BY 4.0 — conflicting republisher labels; the publisher's NC-SA instrument governs.

## Why rejected

- Annual country panels -> level target is persistence-dominated; change target's positives
  cluster into a few global-trend years (same family defect measured on the OECD probe this
  session and the nhs-ae drop).
- The identical panel is already distributed bulk-downloadable by the World Bank: an ML-ready-
  equivalent channel exists, so the novelty bar fails for any formulation of this data.
- NC-SA licence additionally limits a benchmark meant for commercial AI evaluation.

Cost of this verdict: six plain-client fetches + one real-browser read. No bulk data pulled.

## 2026-10-28 — reopen-hook probe: the satellite-filings registry (International-organisations tick)

The record's reopen condition named the ITU Radiocommunication satellite-filings registry as the only known
row-level family. Probed this session (bounded: publisher pages only, no data pulled):

- ITU Space Explorer (https://www.itu.int/itu-r/space/apps/public/spaceexplorer/, read 2026-10-28):
  "Access to the SNS technical data in ITU SpaceExplorer requires a login. It is granted to ITU members
  having a TIES User account, or to those with an annual subscription to the Space Network System (SNS)."
- ITU FAQ on satellite filings (PDF, March 2025, itu.int/en/ITU-R/Documents/FAQs on ITU satellite Fillings-March 2025.pdf,
  read 2026-10-28): filings "Processed and published: Published in BR IFIC" and "The BR IFIC is available for
  viewing through a paid subscription." The e-submission FAQ states as-received filings are publicly listed
  (https://www.itu.int/net4/itu-r/res55asreceived/) once published "as-received".
- Conclusion: the outcome data (processed status, bring-into-use, published in BR IFIC) and the bulk
  technical characteristics (Space Explorer SNS database) both sit behind a paid subscription or a TIES
  member login - an authorisation we do not hold. The free public part (as-received list) carries raw
  submissions, not the later outcomes a prediction task needs.

Verdict: the reopen hook resolves CLOSED on access terms (authorisation not held - class D posture for that
family). Cost: 6 web reads, 0 data requests. What would reopen it: ITU publishing a documented anonymous
bulk/API channel for filings including their processing outcomes under open terms, or the operator supplying
a subscription and an explicit candidate-specific risk acceptance.

