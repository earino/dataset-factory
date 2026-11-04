
INDEPENDENT PRE-PUBLICATION AUDIT — Cape Town Switching-substation Evening-peak Exceedance
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/za-cct-substation-evening-peak-exceedance
Release tag: v2026.11. Five release assets (flat names):
  public-train.csv    2638747 bytes  sha256 f7b533529492c86155a2ddc2659…
  public-eval.csv     2866998 bytes   sha256 2e416315a3f32fb5dc5f816ea0b…
  private-holdout.csv 2879772 bytes sha256 9ab07c57bbe241661fe5f5c8049…
  meta.json           2011 bytes   sha256 935a7438a96b326fb646b802ae2…
  quality.json        33378 bytes sha256 f0690d28e99324461b6f9b8f250…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: 9f2e10ce485635f65e695072…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per switching substation (33/66/132kV) per target day D with at least 30 prior evenings of history at the 06:00 SAST prediction instant (temporal split on the target day: train = 2022, eval = 2023, holdout = 2024; the first 30 days of each station's series are burn-in, counted and never scored), with the publisher's own substation names as identity. 25 columns:
  `station_day`, `station`, `date`, `day_of_week`, `day_of_year`, `doy_sin`, `doy_cos`, `month`, `m00_00`, `m00_30`, `m01_00`, `m01_30`, `m02_00`, `m02_30`, `m03_00`, `m03_30`, `m04_00`, `m04_30`, `m05_00`, `m05_30`, `morning_mean`, `morning_max`, `morning_min`, `hist_morningpeak_mean_90`, `exceeds`.
  Rows 13735 train / 14965 eval / 15006 holdout;
  positives 1539 / 1256 / 1382.
- Prediction instant: the 06:00 SAST (Africa/Johannesburg) instant of day D - a period_end instant with zero feature lag (the source is an administrative telemetry table, not a delayed statistical release); every shipped feature reads only half-hourly MVA readings with timestamps <= the instant (including day D's 00:00-06:00 slots) plus trailing aggregates over mornings strictly before it, and the evening target window 16:00-22:00 SAST lies entirely after the instant. Every shipped feature must be
  knowable at that instant; the label derives from the day-D evening peak (maximum half-hourly MVA over 16:00-22:00 SAST) exceeding the same substation's trailing-90-evening 95th percentile (minimum 30 prior evenings, p95 = sorted(h)[int(0.95*(n-1))]), computed from the sealed evening matrix that never ships that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the benchmark's own runner (train.py + validate.sh bundled verbatim, sha256-equal to the read-only clone) reaches eval AUC 0.5107 on eval rows only - the holdout was never opened or scored; this sits 0.2233 AUC BELOW the strongest simple reference on identical rows, morning_ratio AUC 0.734 (morning_max / hist_morningpeak_mean_90, reading only shipped at-instant columns - a fair same-information target with NO information asymmetry; paired bootstrap 150 resamples: morning_ratio over persistence [-0.1012, -0.0706] and over calendar_identity [-0.1019, -0.0627], both excluding zero; persistence vs calendar_identity is inconclusive, the interval spans zero), which the publisher records as the recorded property of the stock runner under this protocol (an agent-headroom benchmark by operator decision (a), NOT a no-headroom verdict: the extractable signal provably exists in the shipped at-instant features and the stock template does not find it); the ladder is month_only 0.6541, calendar_identity 0.6504, persistence_prev_evening 0.6502 (information-asymmetric BY DESIGN - recomputed scorer-side from strictly-earlier same-station rows because a shipped prior-evening label is exactly the P0 cross-row recovery the design excludes), identity_only 0.5134; majority-class accuracy 0.916071 on this split; global_rate is a constant score with null AUC (degenerate, recorded); prevalence drifts across splits (11.20% -> 8.39% -> 9.21%) and positives cluster city-wide on regime days (227/246/247 distinct exceedance days, the clustered independent-observation counts); the construction is RETROSPECTIVE RESEARCH (the publisher serves one closed static 2022-2024 table, item created 2026-02-28, so no historical-operational-availability claim is made and label timing is unverified outside the artifact's own timestamp order); the evening label matrix is sealed outside every solver-visible frame and NO evening-derived column ships (a sliding evening-quantile column would reconstruct labels at 0.995 exact agreement - the fts-appeal-003 P0 lesson; the gate's measured cross-row probe morning_history_delta_attack bounds the one history-derived shipped column at 44.9% eval mismatches, no recovery); the publisher's caveat carries through (readings are indicative MVA not corrected for load shifts or load shedding, so the label measures demand-as-dispatched, not underlying demand); all stated as limitations in quality.json and VERIFICATION.md, not as strengths.

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
   morning_ratio eval AUC 0.734; month_only eval AUC 0.6541; calendar_identity eval AUC 0.6504; persistence_prev_evening eval AUC 0.6502 (information-asymmetric by design); identity_only eval AUC 0.5134; global_rate a constant score with null AUC (degenerate); majority-class accuracy 0.916071 (majority fitted on train, measured against eval labels); the runner baseline eval AUC 0.5107 quoted from worker job za-cct-baseline-001 (refit your own model - your fit need not match). Refit a simple gradient-boosted or logistic model on
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
