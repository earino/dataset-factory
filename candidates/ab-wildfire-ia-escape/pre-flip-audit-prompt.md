
INDEPENDENT PRE-PUBLICATION AUDIT — Alberta Wildfire Initial-Attack Escape (100 ha)
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/ab-wildfire-ia-escape
Release tag: v2026.11. Five release assets (flat names):
  public-train.csv    2351953 bytes  sha256 575649d52c304d2fa0751411e0e…
  public-eval.csv     838515 bytes   sha256 d099e4cb9da999e3e301b0e4da1…
  private-holdout.csv 930923 bytes sha256 53583f4d2dff386bfebe864f49d…
  meta.json           1217 bytes   sha256 aeb2ef927fc0d8565a86a6901af…
  quality.json        21089 bytes sha256 331a4ceb0944d33b80b0a6519c0…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: c2c8ceb56c7ff52aaf748473…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per assessed wildfire in Alberta's Forest Protection Area, at the publisher's own initial-assessment instant (fire_id = YEAR-FIRE_NUMBER, unique, asserted at construction); temporal split on the assessment instant's calendar year in Alberta local operational time (America/Edmonton): train = 2006-2015, eval = 2016-2020, holdout = 2021-2025; the population is all-cause and assessment-based (every discovered wildfire is assessed, 100% coverage measured - no outcome-conditioned rule); winter (Nov-Feb) rows are kept (587) and 356 winter carryover fires assessed in the year after their record year move with their assessment instant. 25 columns:
  `fire_id`, `assessment_ts`, `assessment_date`, `day_of_week`, `month`, `doy_sin`, `doy_cos`, `forest_area`, `latitude`, `longitude`, `assessment_hectares`, `fire_spread_rate`, `fire_type`, `fire_position_on_slope`, `weather_conditions_over_fire`, `temperature`, `relative_humidity`, `wind_speed`, `wind_direction`, `fuel_type`, `detection_agent_type`, `hours_report_to_assessment`, `hours_discovery_to_assessment`, `hours_start_to_assessment`, `escape`.
  Rows 15864 train / 5707 eval / 6257 holdout;
  positives 297 / 104 / 257.
- Prediction instant: assessment_ts - the publisher-documented initial-assessment instant ('the date and time the wildfire was originally assessed by Alberta Wildfire employees'), the moment the agency itself makes the initial-attack resourcing decision. Every shipped feature is documented 'at the time of initial assessment' (size, spread rate, fire behaviour type, position on slope, the five in-situ weather fields, FBP fuel type) or measured never to fall after it (reported/discovered/estimated start, detection channel: assessment never precedes reported_date, 27,828/27,828); the post-instant families (cause, dispatch with its measured 2.41% mixed ordering, suppression milestones, discovered size) are excluded from every shipped file. Timestamps carry no timezone marker and are read as America/Edmonton local operational time, confirmed against the official Horse River review. The archive is one current compilation (no per-fire vintages), so every shipped feature is the current-vintage value of an at-instant field - retrospective research, no as-of claim. Every shipped feature must be
  knowable at that instant; the label derives from final area burned (current_size, the publisher's 'final area burned of the wildfire', sealed and never shipped) at or above 100 ha on the current compilation's recorded value - inside the publisher's size-class D band; the threshold was fixed before any score and never re-tuned; a secondary containment-duration label was measured at discovery but is NOT shipped that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the stock runner (harness train.py + validate.sh, bundled verbatim, unmodified: true) reaches eval AUC 0.9554 on eval rows only (2016-2020), the holdout never opened by the publisher's own baseline and re-verified green by the fresh-consumer job abwildfire-consumer-001 on the released bytes; the strongest simple reference on identical eval rows is the persistence analogue 0.9096 (the fire's own observed size at assessment, assessment_hectares, as the score - full coverage by construction), which the model beats by +0.0459 AUC (day-clustered paired bootstrap, 500 resamples, cluster = assessment day, CI95 [0.0154, 0.0871], excluding zero); next is the calendar/identity prior 0.713 (smoothed train rate per month x forest area), beaten by +0.2428 CI95 [0.1911, 0.2998]; the model's own day-cluster AUC CI [0.9382, 0.9686] lies entirely above 0.5 (the degenerate majority constant); the construction-time full-feature L2 logistic 0.9206 is a supplementary simple reference whose edge over persistence is INCONCLUSIVE (+0.0111, CI [-0.0292, 0.0514], interval contains zero) - the bar any simple model must clear is the persistence rule, not 0.5; majority-class accuracy 0.9818 (majority fitted on train, measured against eval labels). Prevalence rises across splits: 1.87% train -> 1.82% eval -> 4.11% holdout (the 2021-2025 holdout contains the 2023 record season), an out-of-distribution test as much as a temporal one. The construction is RETROSPECTIVE RESEARCH: the publisher ships one living current compilation with no per-fire historical vintages and no first-publication ledger, the dictionary documents in-place revision of area burned (spring aerial-photography interpretation) and the 2019 season total differs from the current archive by -10.4% (measured against the publisher's own season PDFs), so training_label_timing is UNVERIFIED and no certified historical-forecasting claim is made; label-flip exposure is bounded and measured (89 fires within +-20% of the 100 ha threshold). The label sources current_size, size_class and first_uc_date never ship (asserted absent); fire_id is a declared unique identifier (high cardinality, not a leak). The known-event fixture - the 2016 Horse River Wildfire (MWF009) at its publisher-documented final size 485,123.6 ha, corroborated by the Government of Alberta's official review (detection 16:03h MDT 2016-05-01 matching the record's naive local timestamp) - must read as 'escape'; nine further named fires are asserted in-build, including the already-controlled negative 2023 LWF002 (0.01 ha). All stated as limitations in quality.json and VERIFICATION.md, not as strengths.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT escape to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on fire_id or other key columns, or on
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
   persistence analogue (assessment_hectares) eval AUC 0.9096; calendar/identity prior eval AUC 0.713 (Brier 0.0179); construction-time full-feature L2 logistic eval AUC 0.9206 (Brier 0.0158, simple reference, supplementary); majority-class accuracy 0.9818 (majority fitted on train, measured against eval labels); the runner's own baseline eval AUC 0.9554 is quoted from the private baseline job abwildfire-baseline-002 and was reproduced step-for-step by the fresh-consumer job on the released bytes - refit your own model, your fit need not match. Refit a simple gradient-boosted or logistic model on
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
