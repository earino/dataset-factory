# Independent pre-flip audit prompt — template

Generate this prompt when a candidate reaches the flip decision (or the operator
asks for a verification agent). Fill every `{{PLACEHOLDER}}` **programmatically**
from `release/<id>/MANIFEST.json` and `candidates/<id>/record.json` — digests,
sizes, counts and figures are copied from the recorded evidence, never
hand-transcribed (the nz-ea one-character digest lesson). The auditor runs on
the operator's side with their platform access; the publisher's sessions never
see the audit until the verdict returns.

The static sections (method, attacks, report format) are the 2026-10-27
ec-merger version the operator endorsed — keep them verbatim when filling.

---

INDEPENDENT PRE-PUBLICATION AUDIT — {{DATASET_TITLE}}
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/{{DATASET}}
Release tag: {{TAG}}. Five release assets (flat names):
  public-train.csv    {{TRAIN_BYTES}} bytes  sha256 {{TRAIN_SHA256}}…
  public-eval.csv     {{EVAL_BYTES}} bytes   sha256 {{EVAL_SHA256}}…
  private-holdout.csv {{HOLDOUT_BYTES}} bytes sha256 {{HOLDOUT_SHA256}}…
  meta.json           {{META_BYTES}} bytes   sha256 {{META_SHA256}}…
  quality.json        {{QUALITY_BYTES}} bytes sha256 {{QUALITY_SHA256}}…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: {{ARTIFACT_VERSION}}…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: {{GRAIN}}. {{NCOLUMNS}} columns:
  {{COLUMN_LIST}}.
  Rows {{TRAIN_ROWS}} train / {{EVAL_ROWS}} eval / {{HOLDOUT_ROWS}} holdout;
  positives {{TRAIN_POS}} / {{EVAL_POS}} / {{HOLDOUT_POS}}.
- Prediction instant: {{TIME_COLUMN}}. Every shipped feature must be
  knowable at that instant; the label derives from {{LABEL_DERIVATION}} that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: {{BASELINE_TRIAD_CLAIMS}}.

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT {{TARGET}} to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on {{ID_COLUMNS}} or other key columns, or on
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
   {{REFERENCE_LIST}}. Refit a simple gradient-boosted or logistic model on
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
