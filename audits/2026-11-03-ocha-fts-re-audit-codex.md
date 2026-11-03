# Independent pre-flip re-audit — ocha-fts-appeal-funding-trajectory v2026.11

Auditor: Codex (independent; no publisher contact; read-only)
Date: 3 November 2026, UTC
Candidate: ocha-fts-appeal-funding-trajectory, staged private release v2026.11
(tag == commit 3bb489c866c00d696e109fad94147ad40cdf6952)
Relayed by the operator to the publisher session, 2026-11-03. Complete audit
evidence, frozen code and predictions are held by the auditor at
/tmp/ocha-independent-20261103/audit-evidence.zip (results.json beside it).

**Auditor's verdict: PUBLISH WITH CONDITIONS — for retrospective research only.**

The corrected release removes the demonstrated prior-outcome leakage channel. No
replacement exact-recovery shortcut was found in the frozen feature-only attacks,
and all seven advertised reference figures reproduce. However, the country-year
grain claim is false, and launch-time availability and strictly-after-launch label
timing remain NOT VERIFIED.

Publication conditions:

1. Describe the grain as one FTS appeal-plan ID × plan year. (country, plan year)
   is not unique.
2. Retain the retrospective-only restriction. Do not present these bytes as a
   verified historical forecasting benchmark.
3. Keep the model's underperformance and persistence's information advantage
   beside performance claims.

## Integrity and audit discipline — PASS

All five downloaded assets matched their byte counts, full manifest digests, and
SHA256SUMS. All 24 manifest-listed package-file hashes also matched.

| Asset | Bytes | Recomputed SHA-256 |
|---|---:|---|
| public-train.csv | 29,660 | db0c7eea0efd3362f369b64c446d4f237b390d8d5539306dc9b66857e685b787 |
| public-eval.csv | 9,322 | c11c03935277ecb164ccde4648fd6541e69d962239a561347832e220c981ef2c |
| private-holdout.csv | 12,862 | ffa427d9e67cd1ed7213c370b805287e58549d9058e9241bb01af40105dd37d9 |
| meta.json | 1,891 | 9f3095a8f2662387c75e098f4d1a4e60292109f5ebc503288a357df864659b5e |
| quality.json | 23,348 | 5dd17cea147d298c7e8249dd3e661541dc58a65cbb00da711ce09c90696f67c7 |

The artifact identity independently recomputes to:
ac529cd4e9d4da90f804ecef425e74c94a946b857fe39095fd73a0407506b8c0.

Metadata and quality declarations were read before target columns. The plan and
attack code were frozen before any target-column access (code freeze 20:39:42 UTC;
feature-only prediction freeze 20:40:02; supervised prediction freeze 20:40:30;
first eval/holdout target access 20:40:40). Feature-only predictions excluded
reached_half from every split; eval and holdout labels were opened only after
those predictions were frozen; no attack, threshold or model was revised after
scoring. The metadata itself contains an Afghanistan worked outcome; this was
encountered during the explicitly requested metadata review - no accidental early
target-column exposure occurred. Persistence vectors necessarily read earlier
eval labels; they are reference reproduction, not label-blind attacks.

| Freeze item | SHA-256 |
|---|---|
| Audit plan | 70dcf7bd8a82ee559fdf4c98990f84d5494cd25fc881cc3e4bd838cf0c9c1522 |
| Audit code | be5d148f41a27962b196740b14e3f1e95932626354dc4dbc7af0d8c51530ca4b |
| Original November 1 attack code | 790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699 |
| Feature-only predictions | fc39ff41e9e063253e5716f3af26e987a726fb396bef2db1a82c562c99fbcf80 |
| Supervised predictions | 3fd79bf6230020283f384f8a702411fc16843210652228814574ce67bfaad94e |
| Scorer-side persistence/prior-mean predictions | b038519e44e030f926b3e4ac9350c9dc295e79ca8fd72c248e409e49d0b6051b |

Environment: macOS 15.7.4 ARM64; Python 3.13.1; NumPy 2.5.4; pandas 2.3.3;
scikit-learn 1.9.1; SciPy 1.18.1; XGBoost 3.4.1. Model-library versions match the
publisher's recorded versions; Python patch version differs.

## Schema, grain and splits

| Finding | Status | Observed result |
|---|---|---|
| Nine-column schema | PASS | Exact agreement with metadata and quality declarations |
| Train | PASS | 437 rows; 279 positives; rate 0.6384439359267735; 2000-2016 |
| Eval | PASS | 139 rows; 81 positives; rate 0.5827338129496403; 2017-2020 |
| Holdout | PASS | 182 rows; 96 positives; rate 0.5274725274725275; 2021-2025 |
| Target domain | PASS | Only {0,1} |
| Missing cells / nonpositive asks / invalid GHO indicators | PASS | 0 / 0 / 0 |
| Unique appeal-plan-year IDs | PASS | 758 unique; 0 duplicates |
| Unique country-year grain | FAIL | 41 repeated groups; 43 excess rows |
| Temporal partition | PASS | Ordered, disjoint plan-year ranges |

For example, Tanzania has both 2001-43 and 2001-73; Indonesia has both 2002-85
and 2002-94. These are distinct appeals within the same country-year.

| Split pair | Shared countries | Shared full IDs | Shared underlying plan IDs | Identical complete feature rows |
|---|---:|---:|---:|---:|
| Train-eval | 48 | 0 | 0 | 0 |
| Train-holdout | 40 | 0 | 0 | 0 |
| Eval-holdout | 34 | 0 | 0 | 0 |

There are 83 countries overall; split counts are 78 / 51 / 43. Shared country
identities are real dependence, but are not duplicate examples.

## Cross-row and construction attacks

- PASS — former operands removed. All three columns are absent:
  country_prior_appeals, country_prior_covered_rate, country_last_prior_covered.
  The original November 1 routine was invoked unchanged and stopped with the
  missing country_last_prior_covered attribute; its count/rate arithmetic also
  lacks both operands. It produced no recovery predictions - an unavailable
  channel, not a scored zero-error result.
- PASS — recency reconstruction. Independently recomputed
  years_since_country_prior matches 758/758 rows using only country and strictly
  earlier plan years. Code inspection confirms the feature does not read funding
  or labels.
- PASS — calendar consistency. 0 anchor/year mismatches; 0 ID/year mismatches.
  All 758 anchors equal January 1 of their plan year.
- PASS — ordering explanation. All three files follow year, country and plan-ID
  ordering. Row-order AUC is 0.5017028522775648 on eval and 0.3512596899224806 on
  holdout.
- PASS — tested feature-only shortcuts. 1,223 frozen probes, including 172
  word-token and 939 character-ngram probes, were scored on both splits. None had
  AUC above 0.95, below 0.05, or exactly 0/1, including partial-coverage probes.

The strongest complete-coverage feature-only eval probe was ask divided by
recency: 0.801404853128991 AUC. The strongest complete-coverage holdout probe in
either orientation was year minus GHO membership: raw AUC 0.3464147286821706,
reversed 0.6535852713178294. These maxima describe a precommitted search, not
validated model improvements.

Successor ask probes scored 0.7768620268620269 on 120/139 eval rows and
0.6053113553113553 on 134/182 holdout rows. Future-row presence therefore carries
association, but did not reproduce the former exact-answer channel.

| Column | Eval AUC | Holdout AUC |
|---|---:|---:|
| plan_year_id | 0.4919114517 | 0.3561046512 |
| plan_year_anchor | 0.5136228182 | 0.3487160853 |
| country_iso3 | 0.4671136654 | 0.5067829457 |
| plan_year | 0.5136228182 | 0.3487160853 |
| plan_type | 0.3767560664 | 0.5626211240 |
| is_part_of_gho | 0.5319284802 | 0.5024224806 |
| orig_requirements_usd | 0.7705406556 | 0.5455426357 |
| years_since_country_prior | 0.3601532567 | 0.5014534884 |

Numeric columns use numeric order; categorical/string columns use fixed lexical
order, which has no intrinsic substantive meaning.

PASS, with a localized flag — supervised lookup controls. All 36 single/pair
combinations of the eight shipped predictors were tested, plus nine combinations
involving the extracted plan ID, and country/year offsets 1-25. These controls use
train labels and are reported separately from label-blind attacks. Direct
full-ID and underlying-plan-ID lookups cover 0 eval / 0 holdout rows. No
complete-coverage lookup has extreme AUC. One partial lookup deserves explicit
disclosure: unanimous training donors keyed by country and recency, requiring at
least two donors, achieve eval coverage 28/139, 26/28 correct, AUC 0.9545454545454546
(holdout: 32/182, 17/32, AUC 0.40476190476177477... [as reported: 0.40476190476190477]).
Three other partial rules are perfect on only 2, 3 and 4 eval rows respectively;
none is perfect on any nonempty holdout subset tested. This does not establish a
construction leak. Per-level purity was checked for every shipped single/pair key.
Unique identifiers and all 758 distinct ask amounts were not credited as evidence
of recovery through singleton memorization.

## Reference reproduction — PASS

All figures use the identical 139 eval rows.

| Metric | Reproduced value |
|---|---:|
| Stock runner AUC | 0.6451681566624096 → 0.6452 |
| Persistence AUC | 0.7171136653895275 → 0.7171 |
| Prior-mean AUC | 0.7143465304384845 → 0.7143 |
| Ask-size AUC | 0.7126436781609196 → 0.7126 |
| Country-history AUC | 0.6729459344401874 → 0.6729 |
| Plan-type AUC | 0.669220945083014 → 0.6692 |
| Majority accuracy | 0.5827338129496403 → 0.5827 |

The unmodified stock validator returned CONTRACT OK and 0.6452 through
predict_proba with the target removed. The independent, untuned logistic model
scored 0.6445295870583228 eval AUC - supporting the advertised model scale. Frozen
holdout AUCs were 0.568919573643411 for stock XGBoost and 0.6217296511627908 for
logistic regression.

PASS — underperformance disclosure. README and verification text explicitly
disclose the stock model's 0.0719455087 AUC deficit to persistence.

PASS — information asymmetry disclosure, materially important. Persistence takes
its last outcome from training rows for 50 eval cases and earlier eval rows for 86;
3 use the no-prior fallback. Its advantage is not a controlled comparison of
algorithms with identical information. Separately, the model also trails the
train-only ask-size reference, so asymmetry does not explain all underperformance.

## Contract honesty and temporal validity

| Finding | Status | Assessment |
|---|---|---|
| Quality schema, split sizes and rounded rates | PASS | Match the bytes |
| Conservative isolated-row declaration | PASS | Explicitly disclosed as unenforced; validator passes the whole feature table |
| January 1 anchor as actual launch timestamp | NOT VERIFIED | It is a derived calendar key; 0 row-level launch timestamps ship |
| Historical availability of every feature | NOT VERIFIED | Current-snapshot attributes and sampled evidence do not establish all-row launch-time availability |
| Recency known at actual launch | NOT VERIFIED | Earlier plan year does not itself prove earlier launch date, particularly for December launches |
| Label crossing strictly after launch | NOT VERIFIED | 0 crossing timestamps ship; construction compares final funding with original requirements |
| Training labels available before first eval launch | NOT VERIFIED | Publisher explicitly acknowledges this gap |
| Original-requirements vintage for every row | NOT VERIFIED | Source naming and selected fixtures do not verify all 758 historical values |

The observed code implements 2 x fundingTotal >= original_requirements. That
verifies the intended arithmetic in the implementation; without the pinned funding
harvest and event timestamps, it does not independently verify every label or
establish a post-launch first crossing.

## NOT COVERED

- Full source reharvest, source-to-label reconciliation, or historical vintage
  reconstruction.
- Empirical proof of strictly-after-launch funding crossing.
- Comparison against the previous release to establish that every row and label
  remained unchanged.
- Formal proof against all possible encodings, external-data joins or
  undiscovered cross-row attacks.
- Hyperparameter searches, calibrated uncertainty intervals, significance claims,
  or operational usefulness.
- Independent licensing review.
- Enforcement of workspace isolation. The holdout was intentionally opened for
  this audit and is now audit-consumed.

No repository content was changed, nothing was repaired, and nothing was
published. Final asset hashes remained unchanged and the audited checkout was
clean.

Signed: Codex — independent auditor
Dated: 3 November 2026, UTC
