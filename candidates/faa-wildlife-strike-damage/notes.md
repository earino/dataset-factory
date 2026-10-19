# faa-wildlife-strike-damage

**Verdict: REJECT (2026-10-19).** Dropped on novelty before any fetch of the source.
The search evidence that killed it, recorded 2026-10-19:

## What already exists (the equivalent)

| Prior art | What it ships |
|---|---|
| github.com/oldguy773/FAA-Wildlife-Strike-Analysis | Full pipeline on the public `database.csv`: 174,104 records, damage target (8.6% positive), **post-strike leakage columns identified, dropped and documented**, tuned RF with 62% damage recall from pre-strike features only, feature importances |
| Misra et al. 2022, Int J Sustainable Aviation (10.1504/IJSA.2022.122328) | RF/ANN/logreg/SVM/XGBoost/KNN on the same database; RF 78.81% accuracy; top variables bird size, impact height, airspeed, aircraft mass |
| CARI/OSU 2025 helicopter study | Same task on the helicopter segment: 2,816 strikes 2013-2022, 14.38% damaging, logistic regression on phase/altitude/speed/time-of-day/sky/bird-size |
| arXiv 2608.12390 | Open versioned aggregates of the same database 1990-2026: frozen seed 347,575 reports, damaging = DAMAGE_LEVEL in {M, M?, S, D}, conditional damage rates by family/airframe/airport |
| ERAU SRS 2025 poster | LLM extraction over the same database for damage-factor analysis |

## Why it fails the standing test

The task (damage prediction from pre-strike fields) exists in usable form, including
the leakage discipline a coding-agent eval would need to rediscover. What would be ours
is only splits and packaging. Per the operator's rule - "a source whose equivalent
already exists in a usable form is a rejection, not a candidate" - this is a rejection.

## What was measured

Nothing by this session, deliberately: the novelty search ran first and settled it, so
no fetch of wildlife.faa.gov happened. Figures above (174,104 records; 347,575 reports
1990-2026; 8.6% damage rate) are third-party published measurements of the source,
labelled as such in `record.json`. Licence: public domain (US Government work),
third-party attested via arXiv 2608.12390; not re-read from the portal since the
candidate was never opened for construction.
