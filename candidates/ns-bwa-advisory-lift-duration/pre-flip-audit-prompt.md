INDEPENDENT PRE-PUBLICATION AUDIT — Nova Scotia Boil Water Advisory Lift-Within-30-Days
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/ns-bwa-advisory-lift-duration
Release tag: v2026.10. Five release assets (flat names):
  public-train.csv    133840 bytes  sha256 beacb2292ca0a045610662bd02ba…
  public-eval.csv     50575 bytes   sha256 ec1f733558558d4c30c2c50bf934…
  private-holdout.csv 121058 bytes sha256 78b62dd3bd5923f67c014010eede…
  meta.json           1555 bytes   sha256 6b43e4eaf1020ba3436a91c1c2c9…
  quality.json        21707 bytes sha256 7a61f6fa1bd17f01804428b939ab…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: e8ed2a53eaf0453c8ed52aea…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per issued boil water advisory (labeled; censored and invalid-outcome rows excluded and counted). 19 columns:
  `advisory_id`, `issue_date`, `site_name`, `county`, `facility_type`, `reason`, `issue_month`, `issue_dow`, `site_prior_advisories`, `site_days_since_last`, `site_prior_resolved`, `site_prior_lift30_rate`, `site_active_prior`, `county_prior_advisories`, `county_days_since_last`, `county_prior_resolved`, `county_prior_lift30_rate`, `county_active_prior`, `lift30`.
  Rows 1,069 train / 372 eval / 884 holdout;
  positives 715 / 225 / 514.
- Prediction instant: the advisory's issue date (issue year partitions the splits: train 2008-2017, eval 2018-2020, holdout 2021-2024). Every shipped feature must be
  knowable at that instant; the label derives from the register's removal date ('Date Advisory Removed'/'Length of Advisory in Days'), which can only occur after issuance; lift30 = removed within 30 days of issue that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the package claims NO demonstrated headroom under this protocol: the stock runner model (ns-bwa-baseline-001, replicated by ns-bwa-diag-001) scores eval AUC 0.5086 and TRAILS the shipped site-persistence reference 0.6124 on the identical 372 eval rows, with paired intervals EXCLUDING zero (model-vs-persistence -0.1038, row CI [-0.1693,-0.0357], site-cluster CI [-0.1706,-0.0383] over 286 clusters); calendar/identity 0.5075 and reason prior 0.4307 on the same rows; majority-class accuracy 0.6048; per-year persistence 0.6084/0.6203/0.5991 vs model 0.5554/0.5018/0.4886 across the 2018-2020 prevalence shift 0.7442->0.6400->0.4153. The package declares a measured cross-row (reverse-history) exposure covering 369 train / 56 eval / 217 holdout rows and states isolated_rows as the row-per-advisory DESIGN INTENT, explicitly not runtime-enforced by the shipped validator..

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT lift30 to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on advisory_id or other key columns, or on
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
   site persistence 0.6124 (Brier 0.2819, coverage 231/372), calendar/identity (county x issue month) 0.5075 (0.3101), reason prior 0.4307 (0.2440), full stock model 0.5086 (0.3609), majority-class accuracy 0.6048. Refit a simple gradient-boosted or logistic model on
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
