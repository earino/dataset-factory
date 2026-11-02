
INDEPENDENT PRE-PUBLICATION AUDIT — OCHA FTS Appeal Funding Trajectory (re-audit of the corrected rebuild)
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/ocha-fts-appeal-funding-trajectory
Release tag: v2026.11. Five release assets (flat names):
  public-train.csv    29660 bytes  sha256 db0c7eea0efd3362f369b64c446d…
  public-eval.csv     9322 bytes   sha256 c11c03935277ecb164ccde4648fd…
  private-holdout.csv 12862 bytes sha256 ffa427d9e67cd1ed7213c370b805…
  meta.json           1891 bytes   sha256 9f3095a8f2662387c75e098f4d1a…
  quality.json        23348 bytes sha256 5dd17cea147d298c7e8249dd3e66…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: ac529cd4e9d4da90f804ecef425e…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per primary humanitarian appeal plan-year (country, plan year); eligible primary plan-years with launch-vintage original requirements. 9 columns:
  `plan_year_id`, `plan_year_anchor`, `country_iso3`, `plan_year`, `plan_type`, `is_part_of_gho`, `orig_requirements_usd`, `years_since_country_prior`, `reached_half`.
  Rows 437 train / 139 eval / 182 holdout;
  positives 279 / 81 / 96.
- Prediction instant: the appeal plan-year launch (plan_year_anchor / plan_year; the v2026.10-era attack surface was the launch-time history features). Every shipped feature must be
  knowable at that instant; the label derives from cumulative appeal-linked funding crossing half the original requirements (the FTS flow record, closed as the plan year unfolds) that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the stock runner 0.6452 TRAILS persistence 0.7171 on the identical 139 eval rows (prior-mean 0.7143, ask-size 0.7126, country-history 0.6729, plan-type 0.6692, majority accuracy 0.5827), recorded as a defect beside the number; the model is deliberately denied the last prior same-country outcome under the P0 standard while the persistence reference reads it scorer-side - an information asymmetry you should weigh. THIS IS A RE-AUDIT: your 2026-11-01 queue audit (DO NOT PUBLISH) recovered 120/139 eval and 128/182 holdout labels exactly through the then-shipped prior-outcome features (country_prior_appeals, country_prior_covered_rate, country_last_prior_covered). Those columns no longer ship; rows are unchanged; the only history-derived column is years_since_country_prior, which reads only prior appeal YEARS and is asserted label-free at construction. The isolated-rows declaration is the conservative posture, NOT an enforcement claim: the illustrative runner still passes the whole eval feature table to the predictor, and the publisher asks you to re-run your 2026-11-01 frozen attacks (count x rounded-rate arithmetic, history subtraction, last-prior chains) on these bytes and to try harder - the corrected design claims no shipped column is a function of another row's outcome, and that claim is yours to break.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT reached_half to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on plan_year_id or other key columns, or on
     (entity, date offsets) — does an earlier row carry the later row's answer?
   - duplicate/key lookup tables: any shipped column, or pair of columns, that
     reproduces the label exactly or near-exactly (per-level positive rates
     with unanimous donors; check every categorical, every count feature, and
     ESPECIALLY free-text columns — n-grams/tokens that encode the outcome).
   - construction shortcuts: does date arithmetic, row order, or file ordering
     leak the label? Are derived date/time columns consistent with the
     declared instant, and do they hide the target?
   - single-column dominance: score each column alone (rank AUC); flag any
     AUC in {0, 1} or > 0.95 on eval or holdout.
B. Reproduce the reference figures exactly from the shipped bytes:
   stock runner eval AUC 0.6452; persistence 0.7171; prior-mean 0.7143; ask-size 0.7126; country-history 0.6729; plan-type 0.6692; majority accuracy 0.5827. Refit a simple gradient-boosted or logistic model on
   train and check the publisher's headline model figure is a fair,
   reproducible scale (your fit need not match exactly; wildly better/worse
   is a finding).
C. Contract honesty: does any shipped column contain information that could
   postdate the prediction instant? Does quality.json's declared evaluation
   contract match the actual columns and rates? Are the splits actually
   disjoint and ordered in time?

REPORT
Verdict first: PUBLISH / DO NOT PUBLISH / PUBLISH WITH CONDITIONS.
Then: exact numbers for every check, freeze hashes, digest results, and an
explicit NOT COVERED section (what you did not try). Use PASS / FAIL / NOT
VERIFIED per finding; FAIL means observed contradiction, NOT VERIFIED means
you could not check. Sign and date it. Read-only audit: change no repository
content, publish nothing, repair nothing.
