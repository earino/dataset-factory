
INDEPENDENT PRE-PUBLICATION AUDIT — CQC Care-home Deregistration
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/cqc-care-home-deregistration
Release tag: v2026.11. Five release assets (flat names):
  public-train.csv    9553058 bytes  sha256 6138dd92974d7b70504ab32af2c…
  public-eval.csv     1787102 bytes   sha256 2078146fce1f75b23b0a1060e7e…
  private-holdout.csv 1788226 bytes sha256 880a36d468b779fce541e5419d3…
  meta.json           2349 bytes   sha256 3b350af60fcd415824cd4940b36…
  quality.json        24584 bytes sha256 4e07a858396ec032c47d67a62cd…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: afe9ee203f302f3ca41b9b01…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per care home active in a monthly CQC 'HSCA Active Locations' vintage (train = January vintages 2018-2022, eval = January 2024, holdout = January 2025; the 2016/2017 vintages were loudly dropped for unresolved required columns; the 2023 vintage is excluded by design because its 12-month label window would still be open at the eval instant), with the location identity pseudonymised per instant (location_key). 21 columns:
  `location_key`, `instant`, `care_home_beds`, `beds_bucket`, `latest_overall_rating`, `rating_recency_bucket`, `inherited_rating`, `hsca_start_year`, `local_authority`, `region`, `provider_sector`, `svc_nursing`, `svc_residential`, `svc_other_count`, `users_dementia`, `users_older_people`, `users_learning_disabilities`, `users_physical_disability`, `users_mental_health`, `users_other_count`, `deregistered_12m`.
  Rows 78138 train / 14765 eval / 14749 holdout;
  positives 4418 / 757 / 761.
- Prediction instant: instant - the production instant of the CQC 'HSCA Active Locations' monthly vintage T (a period_end instant, administrative-record lag 0 days; every shipped feature is the vintage's own published field at T, and the row-selection reads only the T vintage). Every shipped feature must be
  knowable at that instant; the label derives from the location's CQC registration ending within (T, T+365d] - a register event (Location Status Inactive-Dereg or Removed with a Location HSCA End Date in that window), joined from the cumulative Deactivated Locations register that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the benchmark's own runner (train.py + validate.sh bundled verbatim, sha256-equal to the read-only clone) reaches eval AUC 0.5659 on eval rows only - the holdout was never opened or scored; this sits BELOW the strongest simple reference on identical rows, rating_x_beds_rate AUC 0.5871 (paired bootstrap 150 resamples for rating_x_beds vs last_rating excludes zero: +0.0273 [0.0123, 0.0407]), which the publisher records as a defect of the stock runner under this protocol, NOT a no-headroom verdict: the model beats every one-line prior (last_rating_rate 0.5597, beds_bucket_rate 0.5298, hsca_start_year_rate 0.5226, local_authority_rate 0.5207, provider_sector_rate 0.5011), the reference reads only shipped at-T columns so there is no information asymmetry, and a verified diagnosis candidate is recorded (the stock runner treats `instant` as a train-only categorical, so the eval instant 2024-01 is unseen and every eval row gets NaN there); NO persistence reference exists BY DESIGN (identity ships as a per-instant pseudonym, the missing-successor P0 design, so prior-instant labels are structurally unlinkable - for a scorer too); majority-class accuracy 0.94873 on this split; global_rate is a constant score with null AUC (degenerate, recorded); the label is a REGISTER EVENT, not a service closure (CQC's own in-file note: cessation conflates re-registration/transfer; BMJ Public Health 2024 implies roughly 40-55% re-registrations/transfers, successor linkage not built); the construction is retrospective mixed-vintage (historical Drive vintages + the current cumulative Deactivated register; no full-row availability ledger, so training-label timing is unverified and the evaluation contract is retrospective research requiring isolated rows); cross-row exposure is measured, not enforced - gate probes measured pseudonym-successor coverage 0/0/0 train/eval/holdout and quasi-identifier (LA x beds x start year x rating x sector) eval/holdout coverage 0 (train 11,786, where labels are public anyway); all stated as limitations in quality.json and VERIFICATION.md, not as strengths.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT deregistered_12m to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on location_key or other key columns, or on
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
   rating_x_beds_rate eval AUC 0.5871; last_rating_rate eval AUC 0.5597; beds_bucket_rate eval AUC 0.5298; hsca_start_year_rate eval AUC 0.5226; local_authority_rate eval AUC 0.5207; provider_sector_rate eval AUC 0.5011; global_rate a constant score with null AUC (degenerate); majority-class accuracy 0.94873 (majority fitted on train, measured against eval labels); NO persistence reference by design (per-instant pseudonymised identity); the runner baseline eval AUC 0.5659 quoted from worker job cqc-chd-baseline-001 (refit your own model - your fit need not match). Refit a simple gradient-boosted or logistic model on
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
