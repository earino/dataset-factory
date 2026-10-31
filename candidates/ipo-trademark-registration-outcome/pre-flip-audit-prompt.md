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

INDEPENDENT PRE-PUBLICATION AUDIT — UK Trade Mark Application Registration Outcome
Auditor: you. You have no contact with the publisher. Nothing below is a claim you
must trust; everything is a claim you should try to break. You are adversarial.

WHERE THE DATA IS
Private repository: https://github.com/earino/ipo-trademark-registration-outcome
Release tag: v2026.10. Five release assets (flat names):
  public-train.csv    20048573 bytes  sha256 f4bb622df6e985ea3bd85d8e962a90022e029588bf56ae3a4d89721877a25a51…
  public-eval.csv     18142219 bytes   sha256 54e06a89d7f565ba690f5abe0fd8cdce5a91c55aaa50738690f8efeee474c520…
  private-holdout.csv 21503483 bytes sha256 26cfc5a8a2131bac4d700ee4733a79eee6eae327dc7c6aa5ed93cf1a0589fa41…
  meta.json           1993 bytes   sha256 caf2a4d916611470ca1f1535113acf179efa2ef71d497a88f4e79f2e5bcb1011…
  quality.json        41854 bytes sha256 efa5b4d3d9b68f07ba8cdffee484a9c6e51b80323851158786a01fdaef7d1bd6…
(sha256 prefixes shown; the repo also ships MANIFEST.json and SHA256SUMS —
recompute and match every digest before you use any byte. Artifact identity
claimed by the publisher: 2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d…). All three CSVs are labeled;
the holdout file ships by design. Download them; work locally.

WHAT THE PUBLISHER CLAIMS (verify each from the bytes, never from prose)
- Grain: one row per distinct domestic trade mark application filed 2010-2016 (first occurrence per stripped mark-number string); 319,436 scored rows across three splits. 57 columns:
  `tm_number`, `category`, `mark_type`, `series_flag`, `series_marks_count`, `nice_class_count`, `class1`, `class2`, `class3`, `class4`, `class5`, `class6`, `class7`, `class8`, `class9`, `class10`, `class11`, `class12`, `class13`, `class14`, `class15`, `class16`, `class17`, `class18`, `class19`, `class20`, `class21`, `class22`, `class23`, `class24`, `class25`, `class26`, `class27`, `class28`, `class29`, `class30`, `class31`, `class32`, `class33`, `class34`, `class35`, `class36`, `class37`, `class38`, `class39`, `class40`, `class41`, `class42`, `class43`, `class44`, `class45`, `owner_country`, `owner_region`, `mark_text`, `owner_postcode_area`, `filed_date`, `registered`.
  Rows 106,990 train / 97,274 eval / 115,172 holdout;
  positives 92,668 / 81,699 / 99,385.
- Prediction instant: the application's filing date (filed_date, Europe/London) - an event_time contract. Every shipped feature must be
  knowable at that instant; the label derives from the presence of a Registered date in the one frozen 2018-02-13 snapshot (registered = 1 iff Registered non-empty; negative iff Registered empty AND status Refused/Withdrawn; unresolved marks censored - excluded and counted, never labelled negative) that
  can only occur strictly after it.
- Splits: disjoint by time, ordered train → eval → holdout.
- Honest disclosure to confirm, not assume: the package claims demonstrated headroom over every measured simple reference under this protocol: the stock runner model (ipo-tm-baseline-001, per-row scores replicated by ipo-tm-diag-002) scores eval AUC 0.6224 on the identical 97,274 eval rows vs mark-type rate 0.5650 nice-class rate 0.5421 (+0.0804 [0.0748, 0.0862]), calendar-month rate 0.4972 (+0.1250 [0.1174, 0.1315]); mark-type gap +0.0573 [0.0533, 0.0605]; all intervals row-level only (tm_number is unique per row - no dependence cluster measurable from the shipped columns), one model configuration, no re-tuning, two filing years of eval. PERSISTENCE IS RECORDED NOT-APPLICABLE (every scored row is a new application; no prior observation of the same entity at the filing instant) - attack that claim: series marks, owner country/region/postcode and mark text repeat across rows; does any earlier row carry a later row's answer? Scope declarations to confirm: retrospective single-snapshot task (event_time filing instant; the publisher exposes exactly one vintage, 2018-02-13, so training-label timing is UNVERIFIED and owner/class columns are snapshot-vintage - ownership can be assigned after filing and classes can be narrowed); eligibility uses only the filing date (never the outcome), 21/172/809 censored rows per cohort train/eval/holdout, prevalence 0.8661 train -> 0.8399 eval -> 0.8629 holdout..

METHOD — FREEZE BEFORE YOU LOOK
1. Read meta.json and quality.json first. Write your audit plan and all attack
   code BEFORE opening any target column. Hash your code and any predictions
   you construct; record the hashes. Label-blind means you may use any column
   EXCEPT registered to build predictions; you may read labels only to
   score frozen predictions. No fitting, threshold tuning or revision after a
   score is seen. If you open a label early by accident, record it and stop
   that attack line.
2. Integrity: verify the five digests. Record your environment (python, libs).

ATTACKS (the core of this audit — bounded to ~30 active minutes)
A. Cross-row shortcut recovery, label-blind, on eval AND holdout:
   - same entity appearing in multiple splits; joins of eval/holdout rows
     against train rows on tm_number or other key columns, or on
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
   nice_class_rate 0.5421, mark_type_rate 0.5650, owner_country_rate 0.5191, calendar_month_rate 0.4972, category_rate 0.5031, series_flag_rate 0.5213, majority-class accuracy 0.8399, headline model eval AUC 0.6224 (the benchmark's own train.py, replicated by the consumer job ipo-tm-consumer-001 on the published bytes). Refit a simple gradient-boosted or logistic model on
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
