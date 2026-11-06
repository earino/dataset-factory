
INDEPENDENT PRE-PUBLICATION AUDIT — CPCB Station-day PM2.5 Exceedance (next day)
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/cpcb-aqi-exceedance
Release tag: v2026.11. Five release assets (flat names):
  public-train.csv    45644743 bytes  sha256 24b03a701c34d91834a7c5285d1…
  public-eval.csv     20210392 bytes   sha256 e187f645445e135e092898a280e…
  private-holdout.csv 22967353 bytes sha256 2dae0040cdc2c80fa4adc9cc3b4…
  meta.json           1197 bytes   sha256 1f59e74e4d6003f03371c4514ee…
  quality.json        22603 bytes sha256 98250e9d2731f89da021aec360f…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: a749f0df2f9dd0103d0ba565…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per monitoring station per prediction day D (station_day = station_id + date) where day D is complete and day D+1 is labelable; temporal split on the prediction day in IST: train = 2019-2022, eval = 2023, holdout = 2024; thin day D and unlabelable D+1 rows are counted and never scored (33,586 + 17,416 train; 18,065 + 9,368 eval; the holdout's own counts are in quality.json), and station_id is the identity. 23 columns:
  `station_day`, `station_id`, `state_name`, `date`, `day_of_week`, `month`, `doy_sin`, `doy_cos`, `pm25_mean`, `pm25_max`, `pm25_min`, `n_hours`, `pm25_mean_lag1`, `pm25_mean_lag2`, `pm25_mean_lag3`, `pm25_mean_7d`, `pm25_days_valid_7d`, `pm25_mean_30d`, `pm25_days_valid_30d`, `pm25_hist_mean_90d`, `days_since_gt90`, `exceed_count_30d`, `exceeds`.
  Rows 288754 train / 126570 eval / 145124 holdout;
  positives 61075 / 19819 / 18222.
- Prediction instant: the 23:59 IST instant at the end of day D - declared kind event_time with zero feature lag, because the source is an administrative record (XKDR republishes CPCB's own hourly station measurements 'as reported', 'preliminary and not fully validated', with no gap filling); intraday publication latency is UNMEASURED and day-D trailing completeness at the instant is an explicitly declared assumption, not a proven point-in-time reconstruction. Every shipped feature reads only day-D readings or trailing aggregates over days <= D; the target day D+1 lies entirely after the instant. Every shipped feature must be
  knowable at that instant; the label derives from day D+1's daily mean PM2.5 (next_day_pm25_mean, sealed and never shipped) exceeding 90 ug/m3, the Poor-band lower breakpoint of CPCB's National AQI (external threshold; known-event fixture pinned) that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the stock runner (harness train.py + validate.sh, bundled verbatim) reaches eval AUC 0.9734 on eval rows only, the holdout never opened by the publisher's own baseline; the strongest simple reference on identical eval rows is station_persistence 0.9689 (day-D pm25_mean as the score, full coverage by construction), which the model beats by +0.0045 AUC (paired cluster bootstrap over 509 station clusters, CI95 [0.0038, 0.0052], excluding zero); next is state_season_climatology 0.8617 (train rate per state x season of D+1), then station_train_rate 0.7616 (supplementary identity prior); global_rate is a constant with degenerate null AUC (recorded); majority-class accuracy 0.8434 (majority fitted on train, measured against eval labels). Prevalence drifts across splits: 21.15% train -> 15.66% eval -> 12.56% holdout, an out-of-distribution test as well as a temporal one. The construction is RETROSPECTIVE RESEARCH (XKDR republishes one cleaned CPCB export with no historical vintages and no first-publication ledger, so no full-row availability ledger is possible); training-label timing is UNVERIFIED and no certified historical-forecasting claim is made. The label columns next_day_pm25_mean and next_day_n_hours never ship (asserted absent); station_day is a declared unique-valued identifier (high cardinality, not a leak). The known-event fixture - CPCB Daily AQI Bulletin 2024-11-18, Delhi Severe with PM2.5 the prominent pollutant at 36/39 stations, source https://cpcb.gov.in/upload/Downloads/AQI_Bulletin_20241118.pdf - must read as 'exceeds' under the 90 ug/m3 Poor-band lower breakpoint of CPCB's own National AQI; confirm it from the bytes. All stated as limitations in quality.json and VERIFICATION.md, not as strengths.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT exceeds to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on station_day or other key columns, or on
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
   station_persistence eval AUC 0.9689; state_season_climatology eval AUC 0.8617; station_train_rate eval AUC 0.7616; global_rate constant (degenerate null AUC); majority-class accuracy 0.8434 (majority fitted on train, measured against eval labels); the runner's own baseline eval AUC 0.9734 is quoted from the private baseline job - refit your own model, your fit need not match. Refit a simple gradient-boosted or logistic model on
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
