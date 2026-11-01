
INDEPENDENT PRE-PUBLICATION AUDIT — UK Planning Appeal Outcome
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/pins-planning-appeal-outcome
Release tag: v2026.10. Five release assets (flat names):
  public-train.csv    14799462 bytes  sha256 299e5af47610af833bec33e15e8…
  public-eval.csv     7688640 bytes   sha256 2ab9271f70c74f857f0c1a7b696…
  private-holdout.csv 14976119 bytes sha256 3f65dc801e0819bd6e828a10106…
  meta.json           2518 bytes   sha256 4e7a31048bb77372cbc42bcf3f8…
  quality.json        44632 bytes sha256 9203accc06369f3d2468b8740ac…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: c861bd8f4acd9bbe267bdb58…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per decided s78_core planning-permission-family appeal (PINS casework type 'Planning Appeal' or 'Householder (HAS)'), validated 2012-06-01..2026-08-21, cross-file deduplicated (3,110 counted duplicates) and restricted to binary decisions in {Allowed, Dismissed}. 32 columns:
  `row_id`, `lpa_name`, `ons_lpa_code`, `casework_type`, `procedure`, `development_type`, `appeal_type_reason`, `appeal_reason`, `type_detail`, `link_status`, `valid_date`, `valid_year`, `valid_day_of_year`, `received_date`, `received_to_valid_days`, `area_of_site_hectares`, `floor_space_sqm`, `number_of_residences`, `green_belt`, `agricultural_holding`, `listed_building_setting`, `historic_building_grant`, `conservation_area`, `flooding_issue`, `aonb`, `sssi`, `lpa_decisions_prior_count`, `lpa_allowed_prior_count`, `lpa_allow_rate_prior`, `lpa_last_outcome`, `lpa_days_since_prev_case_valid`, `allowed`.
  Rows 54834 train / 28104 eval / 56326 holdout;
  positives 17048 / 8469 / 17705.
- Prediction instant: valid_date - the appeal's PINS validation instant (an event_time instant; every feature field is recorded at or before registration/validation from the appeal submission, an administrative record). Every shipped feature must be
  knowable at that instant; the label derives from the final PINS decision (publisher Decision field, Allowed vs Dismissed, issued on the Decision Date 91-365 days after validation for 74% of measured cases) - an event that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the benchmark's own runner (train.py + validate.sh bundled verbatim, sha256-equal to the read-only clone) reaches eval AUC 0.6108 on eval rows only - the holdout was never opened or scored; the simple references on the same 28104 eval rows are procedure_type_rate AUC 0.5551 (Brier 0.20799), lpa_hist_rate AUC 0.5414 (Brier 0.210711), persistence_last_outcome AUC 0.5045 (Brier 0.414994); majority-class accuracy 0.698655 on this split; the calendar-identity control collapsed exactly onto lpa_hist_rate (eval validation years 2020/2021 have no train-era valid-year support, so every eval row fell back to its LPA's train rate - a degenerate control, recorded, never independent confirmation); year_rate and global_rate are constant scores with null AUC (degenerate, recorded); per-validation-year eval AUCs are reported (2020 and 2021 separately) and reference differences carry an LPA-clustered bootstrap (resamples 150); the population is decided-cases-only by publisher design, the vintage is the single current-snapshot 2026-10-22 edition, and split-label timing is declared unverified - all stated as limitations in quality.json and VERIFICATION.md, not as strengths.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT allowed to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on row_id or other key columns, or on
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
   procedure_type_rate eval AUC 0.5551 and Brier 0.20799; lpa_hist_rate eval AUC 0.5414 and Brier 0.210711; persistence_last_outcome eval AUC 0.5045 and Brier 0.414994; majority-class accuracy 0.698655 (majority fitted on train, measured against eval labels); per-validation-year eval AUCs (2020: rows 13797 positives 4126, 2021: rows 14307 positives 4343); the runner baseline eval AUC 0.6108 quoted from worker job pins-planning-baseline-002 (refit your own model - your fit need not match). Refit a simple gradient-boosted or logistic model on
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
