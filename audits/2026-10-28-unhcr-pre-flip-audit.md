# Independent pre-flip audit — unhcr-refugee-data-finder

Auditor: Codex (independent; no publisher contact; read-only)
Date: 28 October 2026
Candidate: unhcr-refugee-data-finder, staged private release v2026.10 (GitHub release
426752344, Hugging Face main 89485538)
Relayed by the operator to the publisher session, 2026-10-28. Complete audit evidence,
code, predictions, and results are held by the auditor in
`/tmp/unhcr-independent-audit-20261028-rIv2q7-evidence.zip`.

**Auditor's verdict: DO NOT PUBLISH in its present form as a benchmark with an
"enforced isolated-rows" protocol.**

The numerical results and dataset construction reproduce. The claimed mitigation does
not: the supplied validator passes the entire eval feature table to the predictor,
enabling a frozen, label-blind cross-row attack with eval AUC 0.975325. The same
attack reaches holdout AUC 0.983034 using holdout features alone.

## PASS — Integrity and source reconstruction

All five assets match both MANIFEST.json and SHA256SUMS, including their byte counts.

| Asset | Bytes | Recomputed SHA-256 |
|---|---:|---|
| public-train.csv | 343359 | c7ebd552f1158bd5f470c495b027c48fc17ea9195c34185a662a8620407bd167 |
| public-eval.csv | 195252 | 4b7f06c3afd9eec286652383d95797a5fbaccc3517e68b2c334c615026bc9393 |
| private-holdout.csv | 202783 | 54decaaaf74eac1ea362bf1acf711010069b1feb94ad2abfcb70a1fccff858bd |
| meta.json | 1250 | 595aab31c00772d987a2436ea8f13d33bc2edd224aeb294731bcfa7579a65d19 |
| quality.json | 18609 | e7517f8fbee8f15a7f667aa57fa398e8e880c8b55c91cee349f904580d1a4df2 |

The recomputed combined artifact identity is:

`6fa7becdf32925b74522c81001dcfe802b6a389425fd6deb4af4fc25ba7f1f53`

All 25 manifest-listed package files also match their hashes. Final rechecks passed.

The auditor independently fetched the source distribution: 8,669,567 bytes,
SHA-256 d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950,
HTTP Last-Modified: Thu, 20 Aug 2026 15:33:52 GMT. It contains 120,597 rows,
including 99,281 G/P rows, spanning 2000-2025. Independent aggregation reconstructed
all 7,212 shipped rows and all 16 fields, including labels: zero missing rows, zero
extra rows, zero field mismatches.

## PASS — Grain, counts, derivations, and temporal splits

| Split | Actual label years | Rows | Positives | Positive rate | Positive origin-year clusters |
|---|---|---:|---:|---|---:|
| Train | 2002-2016 | 3363 | 283 | 0.08415105560511447 | 183 |
| Eval | 2017-2021 | 1887 | 165 | 0.08744038155802862 | 109 |
| Holdout | 2022-2025 | 1962 | 227 | 0.11569826707441386 | 133 |

Across all splits:

- Missing feature cells, duplicate row IDs, duplicate corridor-year keys: 0.
- Row-ID overlap between every split pair: 0.
- apps_d minimum: 500; apps_d1 minimum: 5; corridor_age minimum: 1.
- Incorrect ID, cluster, date, or surge-flag derivations: 0.
- Maximum log-growth rounding error: 4.999770667132863e-7, consistent with six-decimal
  storage.
- Every file is sorted by target year, origin, asylum.

Corridors legitimately recur: 398 shared between train/eval, 357 train/holdout, and
449 eval/holdout. Disjoint years do not prevent cross-row exposure.

## FAIL — Isolation enforcement; PASS — disclosed exposure reproduced

The frozen attack joins corridor (origin, asylum) at year T to year T+1, then copies
surged_recently. It never reads doubled.

| Available donor features | Scored split | Exact covered labels | Covered errors | Full-split AUC¹ |
|---|---|---:|---:|---|
| Eval only | Eval | 1265/1887 | 0 | 0.943326998205047 |
| Holdout only | Holdout | 1239/1962 | 0 | 0.9769934872856074 |
| All three splits | Eval | 1528/1887 | 0 | 0.9993700066870798 |

¹Uncovered rows receive the frozen score 0.5.

The predeclared missing-successor rule is stronger: copy the successor flag when
present; otherwise predict zero before the donor pool's final year, and use 0.5 at
its final year.

| Feature access | Exact non-abstaining predictions | Errors among those predictions | Abstentions | Full-split AUC |
|---|---:|---:|---:|---|
| Eval only | 1584 | 0 | 303 | 0.9753246753246754 |
| Holdout only | 1422 | 0 | 540 | 0.9830339346697305 |
| All splits → eval | 1887 | 1 | 0 | 0.996969696969697 |

The sole all-splits error is AFG-TJK-2021.

A further frozen attack recovers the target-year count from either next-year apps_d or
two-years-later apps_d1. It exactly recovers 1,625 eval labels and 1,259 holdout
labels, with zero errors; full-split AUCs are 0.9995407031992398 and 0.9776536454696645.

The contradiction is concrete: validate.py, line 23
(/tmp/unhcr-independent-audit-20261028-rIv2q7/repo/baseline/validate.py:23) calls the
predictor with the whole eval table, after removing only the target column. The
qualification gate accepts a declared isolated_rows setting; it does not enforce
runtime isolation.

The stock model itself is row-wise: batch versus individual-row predictions differ by
0.0 on both splits. That establishes its behavior, not protection against another
predictor.

NOT VERIFIED: whether a separate, unshipped production harness enforces stronger
restrictions.

## PASS, bounded — Other shortcut searches

13,144 frozen prediction vectors per split were scored, including all 15 non-target
columns, all 105 column pairs, training-donor rate/unanimity lookups, feature-derived
donor lookups, 6,252 token/ngram indicators, and order/date/count transformations.

No single-column, token, or order/date transformation reached AUC 0, 1, >0.95, or <0.05.

| Column | Eval AUC | Holdout AUC |
|---|---|---|
| row_id | 0.511857 | 0.516338 |
| origin | 0.511725 | 0.516061 |
| asylum | 0.522118 | 0.559812 |
| target_year | 0.541124 | 0.321654 |
| apps_d | 0.452069 | 0.446789 |
| apps_d1 | 0.420818 | 0.413804 |
| log_growth_d | 0.574165 | 0.592101 |
| surged_recently | 0.585619 | 0.579342 |
| host_apps_d | 0.395319 | 0.518512 |
| host_growth_d | 0.491099 | 0.597546 |
| origin_apps_d | 0.491715 | 0.453840 |
| origin_growth_d | 0.513174 | 0.551444 |
| corridor_age | 0.482098 | 0.362351 |
| target_date | 0.541124 | 0.321654 |
| surge_cluster | 0.512586 | 0.512627 |

Other findings:

- Training-donor single/pair rate lookups peak at 0.6132984901277584 eval AUC, and
  0.5793421269788875 holdout AUC.
- One pair, (asylum, origin_apps_d), perfectly recovers 9 holdout rows, including 1
  positive. Its full-split AUC is only 0.5044979623963742. This is a small
  covered-subset match, not broad recovery.
- Row-order AUC: 0.543846126772956 eval, 0.32561032893651054 holdout. Within-year
  order: 0.48377503255552035, 0.47741878150033645.
- Next-year outcome recovery from train-only donors has zero coverage on both later
  splits.
- Structured identifiers contain no additional prose field; the token/ngram tests
  found no near-perfect encoding.

Unique-ID unanimity was not treated as evidence. Repeated-level unanimity diagnostics
and every score are retained in the exhaustive results
(/tmp/unhcr-independent-audit-20261028-rIv2q7/results/scores.json).

## PASS — Reference reproduction and negative finding

The unmodified stock runner reproduces the reported results.

| Method | Eval AUC | Eval Brier |
|---|---|---|
| Stock XGBoost | 0.5393499454475063 | 0.08509893581145778 |
| Momentum | 0.5741649948967023 | Not a probability |
| Surge flag | 0.5856192587899904 | 0.21621621621621623 |
| Calendar/identity prior | 0.5409266884876641 | 0.11563487150737081 |
| Recent-rate constant | 0.5 | — |

Majority-class accuracy is 0.9125596184419714. The XGBoost Brier differs from the
publisher's longer decimal by approximately 1.36e-13.

All four 1,000-resample paired row-bootstrap intervals reproduce to the published six
decimals:

| Stock model minus reference | Difference | 95% interval |
|---|---|---|
| Momentum | -0.034815 | [-0.105633, 0.040850] |
| Surge flag | -0.046269 | [-0.110322, 0.014362] |
| Calendar/identity | -0.001577 | [-0.059444, 0.058719] |
| Recent constant | 0.039350 | [-0.004657, 0.085904] |

All contain zero. The persistence gaps are negative.

| Eval year | Rows / positives | Stock AUC | Momentum AUC |
|---|---|---|---|
| 2017 | 361 / 27 | 0.3938234642 | 0.7450654247 |
| 2018 | 386 / 41 | 0.5478967833 | 0.6567691764 |
| 2019 | 423 / 34 | 0.5634734614 | 0.6272493573 |
| 2020 | 414 / 6 | 0.8417075163 | 0.1164215686 |
| 2021 | 303 / 57 | 0.6126800742 | 0.5683925260 |

The independent, fixed logistic model scores 0.6073311512335902 eval AUC,
Brier 0.10037489062934132. On holdout it scores 0.5156546357069406,
Brier 0.17254834079166992. Stock XGBoost holdout AUC is 0.4740989475555104, versus
momentum 0.592100953420762.

The stock baseline's reported scale is reproducible. Its failure to demonstrate
headroom over persistence is honestly disclosed. The exploratory logistic result does
not establish reliable superiority.

## Contract honesty

- PASS — Feature-year construction: source reconstruction confirms the numerical
  features use years at or before D.
- NOT VERIFIED — Historical knowability: current-vintage reconstruction cannot
  establish what was published at each historical prediction instant. Revised past
  values could postdate those instants. The metadata acknowledges this.
- FAIL — Literal identification of target_date with the prediction instant: all 7,212
  dates are December 31 of the outcome year. They are calendar identifiers, not
  publication timestamps. quality.json correctly distinguishes these.
- NOT VERIFIED — "One refresh later" and strictly later label availability for every
  row: only one pinned vintage and its modification timestamp were verified; no
  historical publication ledger establishes that universal claim.
- PASS, with qualification — Eligibility: source reconstruction confirms the
  threshold/history conditions. Final inclusion additionally uses disclosed
  outcome-year observability censoring: 21/7/5 host-silent exclusions and 496
  live-edge exclusions. Final membership is therefore not determined solely by
  prediction-time information.
- FAIL — Stale exclusion count: quality.json says 386 missing-history exclusions.
  Reconstruction finds 377: 314 train, 31 eval, 32 holdout.
- PASS — Column inventory; qualification needed: all columns are disclosed, but the
  runner consumes 14 inputs, including target_date and surge_cluster, rather than
  only the 12 entries in quality.json.features.

Publication as the claimed benchmark should wait for demonstrable runtime isolation
and corrected timing/count statements. These are required changes, not repairs
performed by this audit.

## Freeze record and environment

Code freeze: 2026-10-28 18:27:10.947322 UTC.

| Frozen item | SHA-256 |
|---|---|
| Plan | d22f34b26f7f7573f3ba7036be4f65b37ab4bdcfb4cd6bca7a83bdf1088f0f9c |
| Attack/model/scoring code | 7dc75054688c36a15cc64f88bead0e53133c37ae5c0eb0b44da902d4b9b5297c |
| Independent source checker | 1f98aeb35210af6101614759279aa13df6a5def5299c3a5c3a2ff2f1637a0983 |
| Blind eval predictions | 50d47bab1e71d2e9be467bcc54455ad9cfccda83e9d574816c776e289612bfdb |
| Blind holdout predictions | 5b576c2aa55b2520d2f1a5a1580f81d04d4c818958dee1c590242e641d615e36 |
| All eval predictions | c322b37a13aa074b85bfb029d83b2401e4d89ec707c8f77ad781dcde0b859299 |
| All holdout predictions | 3bf0e22e241dc8865d20b529b6d7cdc7cbe73139f2b8458a96889961730c3529 |

Blind predictions were sealed at 18:27:24.623264 UTC, before target-column access. All
prediction archives were sealed at 18:27:33.495517 UTC. Final hash checks passed.

Method qualification: metadata/source fixture labels were visible during the required
metadata review; they were not used in attacks. Train-supervised models and donor
lookups were explicitly separated from label-blind attacks. The unmodified runner
internally reads and scores eval before its prediction archive is hashed; its output
was withheld until sealing. Consequently, that reproduction is code-frozen, but does
not satisfy a literal prediction-hash-before-label-read requirement. No fitting,
tuning, or attack revision occurred after score exposure.

Environment: Python 3.13.1, NumPy 2.5.4, pandas 2.3.3, scikit-learn 1.9.1,
XGBoost 3.4.1, macOS 15.7.4 ARM64.

## NOT COVERED

- Historical source vintages, revision magnitudes, and per-row
  publication/label-availability ledgers.
- Enforcement by any external production harness; the supplied validator was inspected
  but not rerun, avoiding post-score retraining.
- Cluster/block-bootstrap uncertainty; the reproduced intervals are row-bootstrap
  intervals.
- Hyperparameter search, model ensembles, arbitrary higher-order keys, cryptographic
  encodings, or unrestricted attack synthesis.
- Independent validation of UNHCR's underlying administrative statistics.
- A certification that shipping the labeled holdout preserves secrecy; it plainly does
  not.

Signed: Codex — independent auditor
Dated: 28 October 2026
