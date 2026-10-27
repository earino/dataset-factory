# Independent pre-flip audit — ec-merger-phase2-opening

Auditor: Codex (independent; no publisher contact; read-only)
Date: 27 October 2026, Europe/Paris
Candidate: ec-merger-phase2-opening, staged private release v2026.10
Auditor's verdict: **PUBLISH WITH CONDITIONS**

The release passes byte integrity, temporal separation, and the frozen shortcut
tests. Its principal model and sector-prior results reproduce. It should not be
published under the blanket claim that every shipped feature was verified as
available at notification. Publication should be limited to retrospective
research, with the metadata corrections and reproducibility requirements below.

[Complete audit evidence, code, predictions, and results are held by the
operator in ec-merger-audit-20261027-evidence.tar.gz and
/tmp/ec-merger-audit-20261027/ on the auditor's host. No repository content was
changed, nothing was published, and no publisher contact occurred.]

## Integrity — PASS

All five byte counts and full SHA-256 digests match both MANIFEST.json and
SHA256SUMS:

| Asset | Bytes | SHA-256 |
|---|---:|---|
| public-train.csv | 429,048 | 1619b6f4ad4a7dab0f437335c231f727f6f5c5f0ea02b3454366f5a71ab90a44 |
| public-eval.csv | 155,077 | 4fb28c0908e4c79ccf194de3b27f2996c05efc0f01ec4074c953a7eb697f24f6 |
| private-holdout.csv | 253,649 | 5867e34f3ebf714b9ec0ef307989cb4296438148390a6a5ea2bcf88795f703fd |
| meta.json | 1,233 | 011a4c0b989705ce2a8577e387e0cf96856cc8e9c65f7c51fbbffd699944d13d |
| quality.json | 17,064 | ca07571caa43e1a0f6fd77c0ed28f535d7ed3c794f6441c6483ce0663acee23c |

Recomputed artifact identity:

e5a98dfc9c05d0b087ed2dead21004fbbd972e415d2174469371a908bcaf90ad

The independently downloaded Commission source also matches the pinned
42,034,960 bytes, SHA-256:

420411333e9b9fc27e0c2e72cbbbb419f1ba4125e7f40d98a9bc5e0911316702

## Freeze procedure — PASS

Metadata and source code were read before CSV targets. Publisher-provided
aggregate and fixture labels in the metadata were visible; no CSV label was
accidentally opened early.

- Label-blind predictions and donor memberships frozen: 20:14:52 UTC.
- Train labels first accessed for the explicitly requested supervised
  reproduction: 20:15:02 UTC.
- Supervised predictions frozen: 20:15:03 UTC.
- Source-outcome inspection and eval/holdout scoring began afterward.
- No attack code, model, or threshold was revised after scoring.

| Frozen object | SHA-256 |
|---|---|
| Audit plan | b353e075cd3fbe7787bd0e9fbad1f5ad847fdf21b62497ea3a3bb9cce5835d9e |
| Attack code | 64d4848fa4d5eb6b7aaca41058b9c54db9d4edd2087deb23eb5efe26ca8a3003 |
| Label-blind prediction bundle | a3d865d7c91ef0a3af1a154ea93d096dd21cfd7376f3e835d82cbce0f31d2878 |
| Single/pair donor memberships | e94c190f3de55d056f03e69eff8f693858de6626a4c999ab802a60edeaffbe95 |
| Cross-split joins | 09fc2166305923c69527d7c62c018befa4754b0581f15a4bde00f81951421cc5 |
| Supervised prediction bundle | 45281e1d429d9a4f58873d8b55457684f0d8cd5ff60102de8b6a867598221369 |

Per-prediction hashes are included separately in the auditor's evidence bundle.
Environment: Python 3.13.1; NumPy 2.5.4; pandas 2.3.3; SciPy 1.18.1;
scikit-learn 1.9.1; XGBoost 3.4.1; macOS 15.7.4 arm64.

## Rows, labels, and splits — PASS

| Split | Rows | Positives | Prevalence | Majority accuracy | Actual notification range |
|---|---:|---:|---:|---:|---|
| Train | 5,406 | 217 | 4.01405845% | 95.98594155% | 1990-10-04–2013-12-23 |
| Eval | 1,770 | 46 | 2.59887006% | 97.40112994% | 2014-01-03–2018-12-21 |
| Holdout | 2,915 | 46 | 1.57804460% | 98.42195540% | 2019-01-03–2026-10-02 |

Overall prevalence: 309/10,091 = 3.06213458%.

All three files have the claimed 12 columns and binary labels. There are 0
duplicate case numbers globally, 0 rows outside declared windows, and 0
date-order reversals. Positive notification-day counts are 209 / 45 / 44.

## Shortcut attacks — PASS within the frozen search

There were 3,796 frozen label-blind predictors per split, covering all
non-target columns, frequencies, text lengths, title unigrams/bigrams, outcome
terminology, calendar arithmetic, case-number residues, and row-order
arithmetic.

No predictor had AUC 0 or 1, ≥0.95, or ≤0.05.

| Column, ascending numeric/date or lexical rank | Eval AUC | Holdout AUC |
|---|---:|---:|
| case_number | 0.406209 | 0.348425 |
| notification_date | 0.475096 | 0.405034 |
| notification_year | 0.479812 | 0.404943 |
| notification_month | 0.472839 | 0.501099 |
| regulation | 0.500000 | 0.500000 |
| sector_divisions | 0.355833 | 0.385561 |
| sector_count | 0.557879 | 0.588495 |
| has_sectors | 0.500000 | 0.500349 |
| party_count | 0.357838 | 0.243790 |
| title_has_jv | 0.489093 | 0.443837 |
| case_title | 0.568862 | 0.532863 |

Categorical lexical ranks test that particular encoding; they do not exhaust
every possible categorical function.

- Cross-split identity recovery — PASS: train→eval and train→holdout
  case-number matches: 0 / 0. All 11 tested case/date offsets also had zero
  coverage.
- Title recovery — PASS: exact and normalized titles each produced 1 eval
  match, whose label disagreed with its train donor; 0 holdout matches.
- Single/pair lookup recovery — PASS: tested 11 single keys + 55 pairs, with
  unanimous train donors. Across individual key specifications, maximum
  positive recovery was 2/46 eval and 1/46 holdout. Requiring at least two
  agreeing donors reduced positive recovery to 0/46 in both splits.
- Sector-combination donors: with at least one unanimous donor, eval agreement
  was 611/619, recovering 2 positives; holdout agreement was 773/787,
  recovering 0 positives. High agreement mostly reflects negatives, not answer
  recovery.
- Outcome-language probe — PASS: matched 8 eval titles and 4 holdout titles,
  all negative. AUCs: 0.497680 / 0.499303. Divestment wording was present, but
  did not identify Phase-II positives.
- Title-token probes — PASS: AUC ranges 0.449385–0.542608 eval, 0.443837–0.540864
  holdout. No qualifying positive-unanimous token shortcut with support ≥3 was
  found.
- Construction probes — PASS: arithmetic AUC ranges 0.415011–0.582947 eval,
  0.393392–0.625036 holdout. Row-order AUCs: 0.474718 / 0.404822.
- Calendar consistency — PASS: year/date and month/date mismatches: 0
  throughout.

Donor-label agreement was evaluated against frozen memberships as a scoring
diagnostic, not presented as a label-blind prediction.

There is residual case dependence: holdout contains two positive IAG / AIR
EUROPA cases, M.9637, 2021-05-25, and M.11109, 2023-12-11. This is not a
train→holdout shortcut, but notification-day clustering does not capture this
relationship.

## Reference reproduction

| Frozen recipe | Eval AUC | Eval Brier | Holdout AUC | Holdout Brier | Finding |
|---|---:|---:|---:|---:|---|
| Stock XGBoost recipe | 0.6973481792 | 0.02534254 | 0.6229370937 | 0.01770337 | PASS |
| Raw sector-division prior | 0.7679246948 | 0.02500763 | 0.6946254565 | 0.01604913 | PASS |
| Recent rate | 0.5000000000 | 0.02531365 | 0.5000000000 | 0.01564826 | PASS |
| Global train rate | 0.5000000000 | 0.02551356 | 0.5000000000 | 0.01612484 | PASS |
| Independent logistic model | 0.8144103702 | 0.02420933 | 0.7767098065 | 0.01505786 | Additional finding |

The recent-rate prediction is 23/865 = 0.026589595375722544, using 2011–2013
train rows.

PASS: the publisher honestly reports that its stock model trails the sector
prior. Reproduced paired AUC difference: −0.0705765156864725.

NOT VERIFIED: the exact published confidence interval. The auditor's frozen
1,000-draw paired row bootstrap, seed 42, returned [−0.1613312046, +0.0137356720],
also crossing zero. The original RNG recipe is absent.
NOT VERIFIED: exact calendar_identity = 0.5606148492. The referenced score.py
is absent from the release repository. The explicitly frozen alternate calendar
logistic recipe scored 0.6696005246 / 0.7074575295; these are not reproductions
of the publisher's comparator.

The independent logistic model improves eval AUC over stock by 0.1170621911,
with improvement also on holdout. Thus 0.6973 is reproducible but is a weak
baseline, not an established performance ceiling. No tuning followed these
results.

## Contract findings and required corrections

| Finding | Status | Evidence |
|---|---|---|
| Shipped features reproduce from pinned register | PASS | 0 mismatches across all 10,091 rows |
| Binary labels agree with the register opener rule | PASS | 0 mismatches |
| Positive opener strictly follows notification | PASS | 309/309; minimum lag 24 days, maximum 556 days; 0 same-day openers |
| Metadata says "308/309 strictly after" | FAIL | Actual count is 309/309. M.3333 remains positive through its later 2007-03-01 opener |
| Claimed 33 censored cases | FAIL | 10,125 eligible − 10,091 shipped = 34 omitted: 30 with no decisions and 4 with referral-only records |
| Sector combinations exceed rows/5 in every split | FAIL | Train has 540 levels, below 1,081.2; eval 414, holdout 668 |
| Literal " / " party-count documentation | FAIL | 39 train / 10 eval / 11 holdout mismatches. Actual implementation splits on slash with optional whitespace; that derivation matches all rows |
| Every shipped value was fixed and verified at notification | FAIL as a blanket contract | Current-vintage sector coding is retrospective; 2,904 notifications predate 2006 |
| Historical availability of titles, sector assignments, counts, and missingness | NOT VERIFIED | Matching a current snapshot does not establish historical availability |
| Training-label availability at historical cutoffs | NOT VERIFIED | No row-level availability ledger |

Eurostat states that NACE Rev. 2 was published in 2006, for statistics covering
2008–2024. Its retrospective use cannot substantiate the claim that those exact
taxonomy values were recorded at earlier notification dates.
Source: https://ec.europa.eu/eurostat/web/nace

### Before publication

1. Make the retrospective-use limitation consistent throughout meta.json,
   quality.json, and feature-evidence statuses.
2. Correct the observed metadata contradictions above.
3. Supply the missing comparator and bootstrap recipes for exact reproduction.
4. Disclose dependence across repeated transactions, alongside notification-day
   clustering.

## NOT COVERED

- Historical snapshots or notification-era validation of every feature and case.
- Independent legal-document verification of all source decision records.
- Exhaustive terminal-decision/maturity verification for every negative.
- Internal sector-code versus textual-label consistency.
- Arbitrary nonlinear shortcuts, unrestricted semantic title interpretation, or
  model tuning.
- Exact original calendar comparator and bootstrap interval.
- Cluster-aware uncertainty beyond the frozen row bootstrap.

Two arrays in contract.json were unimplemented placeholders —
`negative_without_terminal` and `sector_code_label_disagreements` — and must
not be interpreted as successful zero-error checks. This is documented in the
auditor's coverage caveats.

Signed: Codex, independent auditor
Date: 27 October 2026, Europe/Paris
