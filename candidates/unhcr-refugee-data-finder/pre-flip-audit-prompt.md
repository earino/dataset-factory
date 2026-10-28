INDEPENDENT PRE-PUBLICATION AUDIT — UNHCR Asylum Corridor Application Doubling
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/unhcr-refugee-data-finder
Release tag: v2026.10. Five release assets (flat names):
  public-train.csv    343359 bytes  sha256 c7ebd552f1158bd5f470c495…
  public-eval.csv     195252 bytes   sha256 4b7f06c3afd9eec286652383…
  private-holdout.csv 202783 bytes sha256 54decaaaf74eac1ea362bf1a…
  meta.json           1250 bytes   sha256 595aab31c00772d987a2436e…
  quality.json        18609 bytes sha256 e7517f8fbee8f15a7f667aa5…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: 6fa7becdf32925b74522c810…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per asylum corridor-year (country of origin O, country of asylum H, target year D+1), eligible at the instant by >= 500 government-procedure applications in year D and a published year-D-1 corridor value. 16 columns:
  `row_id`, `origin`, `asylum`, `target_year`, `apps_d`, `apps_d1`, `log_growth_d`, `surged_recently`, `host_apps_d`, `host_growth_d`, `origin_apps_d`, `origin_growth_d`, `corridor_age`, `target_date`, `surge_cluster`, `doubled`.
  Rows 3363 train / 1887 eval / 1962 holdout;
  positives 283 / 165 / 227.
- Prediction instant: `target_date`/`target_year` - the prediction instant is the publication of the HDX refresh carrying complete year-D data (observed 2026-08-20 carrying complete data through 2025); every shipped feature reads published years <= D. Every shipped feature must be
  knowable at that instant; the label derives from the corridor's year-D+1 government-procedure application total, which is published one refresh after the instant that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the publisher's own negative finding - the stock XGBoost baseline scores eval AUC 0.5393 (Brier 0.085099) and TRAILS both persistence references on the identical 1887 eval rows: momentum `log_growth_d` 0.574165, surge flag `surged_recently` 0.585619; calendar/identity prior 0.540927; recent-rate constant 0.5 is degenerate (a constant cannot rank) and majority-class accuracy on this split is 0.91256. Every paired row-bootstrap interval contains zero (differences inconclusive, observed gaps negative); per label year, 2020 (6 positives) inverts momentum completely (model 0.8417 vs momentum 0.1164). The publisher claims NO demonstrated headroom over persistence under this protocol. A declared cross-row exposure exists and is mitigated by an enforced isolated-rows protocol: a corridor's `surged_recently` at T+1 equals its T label (0 mismatches on covered rows), so the publisher asks you to try the cross-row join attack especially hard..

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT doubled to build predictions; you may read labels only to
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
   full model (stock XGBoost, verbatim runner) eval AUC 0.5393, Brier 0.085099; momentum persistence 0.574165; surge-flag persistence 0.585619; calendar/identity prior 0.540927; majority-class accuracy 0.91256. Refit a simple gradient-boosted or logistic model on
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
