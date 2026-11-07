# Flip queue — independent pre-publication audit, 2026-11-07

## Queue summary

- **ab-wildfire-ia-escape — DO NOT PUBLISH** — Frozen shipped-fixture lookup recovers 3 eval and 4 holdout labels exactly; false holdout guarantees and prevalence statements.
- **cpcb-aqi-exceedance — DO NOT PUBLISH** — Frozen later-row/count/rate attacks recover 99.3727% of eval and 99.0829% of holdout exactly; min/max columns are reversed.
- **cqc-care-home-deregistration — DO NOT PUBLISH** — Frozen builder-fixture lookup recovers 4 eval labels exactly; cross-split linkability and beds-bucket claims are false.
- **za-cct-substation-evening-peak-exceedance — DO NOT PUBLISH** — False digest-enforcement and interval-direction claims; shipped worked example exposes a named holdout answer (documentary finding).
- **cra-charity-filing-exit — READY-TO-BUILD** — No exact filing-exit task found; OGL-Canada and public row-level CSV catalogue verified, direct download blocked in this environment.
- **datasus-sinasc-cesarean-share-decline — LICENCE-BLOCKED** — Dataset CC-BY metadata conflicts with the same source’s blanket BY-ND footer; clean derivative-redistribution permission remains unresolved.
- **ibama-auto-infracao-recidivism — READY-TO-BUILD** — Public infringement-row bulk archive and open-data grant verified; no exact recurrence task found.
- **npri-facility-reporting-exit — READY-TO-BUILD** — Public facility/substance/year CSV and OGL-Canada verified; no exact reporting-exit task found.
- **oecd-ncp-specific-instance-acceptance — READY-TO-BUILD** — Public case-level enumeration and OECD reuse terms verified; no exact acceptance-prediction release found.
- **tw-typhoon-day-closure — READY-TO-BUILD** — Corrected differentiation survives inspection of the actual LFS data: population, full-day label and pre-announcement features differ materially.
- **wto-dispute-panel-escalation — FIX-THE-RECORD** — Prior ML-ready research data cannot be dismissed for lacking splits; compare establishment versus ruling explicitly before claiming novelty.
- **defra-avian-influenza-spillover — READY-TO-BUILD** — OGL wild-bird rows and case-level outbreak listings exist; no exact UK county-week spillover task found.
- **my-rapidrail-od-exceedance — READY-TO-BUILD** — Public station-pair/day bulk CSV and CC BY 4.0 verified; no exact Klang Valley exceedance task found.

## Scope, evidence standard and freeze

This is a read-only artifact audit, signed below. No repository content was edited, no repair or publication was performed, and no publisher was contacted. All work products are in this local audit directory. These verdicts apply to the captured bytes, not to subsequent releases. **FAIL** denotes an observed contradiction; **NOT VERIFIED** denotes a check that could not be completed. A negative novelty search is bounded evidence, never proof of universal non-existence. READY-TO-BUILD is discovery clearance for the stated task, not publication clearance.

The four per-item prompts were read and their attack, integrity, reference and contract checks were performed as described below. The operator’s P0/P1 standard takes precedence over factory procedures and scoring language. A weak baseline, disclosed censoring/vintage uncertainty, prevalence shift or an illustrative runner’s lack of enforcement is not itself a failure. A claimed enforcement guarantee is a failure. Shipped label columns were excluded from all blind predictor construction; merely opening the intentionally labeled holdout is not the alleged leakage.

Factory snapshot: `earino/dataset-factory`, commit `e159268e86be418358c2dda2dd7b1ddca77d7602`. GitHub metadata reports the factory public, although the brief called it private. All four release repositories were acquired with operator-provided GitHub access; credentials were not written into the audit. Discovery status in this snapshot added WTO, DEFRA and RapidRail to the six named Tier C items. The November 1 clearances were not reopened, and the three explicitly excluded candidates were not audited. The November 1 attack code and November 3 OCHA-FTS report informed the battery; the original November 3 temporary attack code was not available and was not represented as rerun.

Environment: macOS 27.2 arm64; attack/rebuild Python 3.13.1, NumPy 2.5.4, pandas 2.3.3, scikit-learn 1.9.1, SciPy 1.18.1, XGBoost 3.4.1. Full installed-package inventory and executable are in [environment.json](environment.json). Some read-only acquisition/formatting helpers used the system Python 3.12; their outputs do not generate or tune recovery predictions. `gh` used existing keyring authentication. No dependency installation was required.

**Chronology:** code/plan freeze at 10:33:59.048758 UTC; all four feature-only prediction archives frozen at 10:35:29.282648 UTC; first target-column access at 10:35:54.286860 UTC, solely after the prediction freeze. Metadata, documented outcomes and builder fixtures were visible before the freeze, as explicitly recorded. They are shipped predictor inputs, not secretly accessed target columns. No recovery rule was added, refitted or tuned after scoring. Later scripts only acquired source evidence, rebuilt artifacts, checked documentary claims, summarized fixed results or ran the predeclared supervised controls. The Cape Town worked-example finding is deliberately separated from the frozen scored battery.

| Frozen object | SHA-256 |
|---|---|

| [PLAN.md](PLAN.md) | `9b62287c0b7d0a45761785f9af854f875d2b767eed17952f250b2cec65816e86` |
| [attack.py](attack.py) | `d07a9d3695de7a9c706ea11e67fce4652334b84258762203232692aee5c023c8` |
| [claims.py](claims.py) | `25d08852c213f7aa44e0d3d9febcf69834c4962da7c06a6a66c5fda7019013da` |
| [run_references.py](run_references.py) | `bab2d11f4ebad3dd2187fc4980f7d65c4271011d82a0e580ad250e04cd92d181` |
| [integrity.py](integrity.py) | `1d31f99d83cc81a12fd0670c542ada2cfd6a6259bc1ae53ad3f97c50f20dd1ec` |
| [environment.json](environment.json) | `bddb3d999a9da6435e456bd56fe0103ef90fa8536d1bc13a08dae87eb451d9b0` |
| [code-freeze.json](code-freeze.json) | `a8f965c4ca3d627a8661b23191ef0ea794b65b65565ac91f1e3659e8de2a1a1f` |
| [prediction-freeze.json](prediction-freeze.json) | `ce3d617e35c345fad73e29416b00ac4cf5f01b1d8e24886c622b06e526aec31c` |
| [first-label-access.json](first-label-access.json) | `f89ac1e53ad4c62c4afe953a72fbf03892a8b0338fedae419713d698fefce689` |

The code freeze records **2,719 files**, including all acquired factory text/code and release code/documents. The prediction freeze records **12 files**: four vector archives, four feature-only tables and four vector indexes. End-of-analysis rehash: **2,719/2,719 and 12/12 unchanged**, zero mismatches. [supplemental-results.json](supplemental-results.json) records the check. Every frozen file’s full digest is in the freeze manifests; the final `AUDIT-SHA256SUMS` seals the entire local audit, including later source receipts and this report.

The fixed battery produced **5,808 vectors**. It tested numeric/lexical ranks, missingness, word/character tokens, row order, date parts and offsets, numeric-pair arithmetic, same-split and all-shipped-row joins, next-row lag/recency/count identities, and entity quasi-identifiers. Exact recovery requires a predeclared mechanism plus zero scored errors; a lucky constant over a tiny subset is not treated as a discovery. Unanimous single/pair lookup controls and a fixed logistic model were fitted on **training labels only**, after the blind freeze, and are explicitly supervised controls. No eval/holdout fitting occurred. The detailed JSON retains every probe, coverage and error count, including failures.

Integrity was recomputed before feature/target use: all **20/20 release assets**, GitHub asset sizes/digests, each repository’s SHA256SUMS, all **97/97 manifest-listed package files**, and all four artifact identities matched. Artifact identity is the publisher’s SHA-256 of sorted `key:digest` entries for train, eval, holdout, meta.json and quality.json; it is not the tarball hash. The necessary manifest/checksum carriers were read to discover these checks, not treated as independent truth. Repositories, release JSON and archive hashes remain locally available.


## Tier A — ab-wildfire-ia-escape

**DO NOT PUBLISH**

Release **437179999**, tag **v2026.11**; repository commit `d610ffe20959ce747635631fc8aba659be3b4823`. Artifact identity `c2c8ceb56c7ff52aaf748473e1251725c4ee86912edb9b17387e6b44d0e43da2`.

| Item freeze | SHA-256 |
|---|---|
| [factory/candidates/ab-wildfire-ia-escape/pre-flip-audit-prompt.md](factory/candidates/ab-wildfire-ia-escape/pre-flip-audit-prompt.md) | `20446e5917145082648ffdf8744006b8c7da75c102ea781a755b945dd6da5f74` |
| [ab-wildfire-ia-escape/repository/MANIFEST.json](ab-wildfire-ia-escape/repository/MANIFEST.json) | `86b2da764a765d4f518ef062a96bf25518056660da0bcd380eb11d6af83e7233` |
| [ab-wildfire-ia-escape/repository/SHA256SUMS](ab-wildfire-ia-escape/repository/SHA256SUMS) | `7705734c8d7b47d3e5a5a9dccc24f6c0f837db3244ab3364ca3ccfe64c63527b` |
| [ab-wildfire-ia-escape/predictions/blind.zip](ab-wildfire-ia-escape/predictions/blind.zip) | `8dc4d874eec989dcfd7ddfeeef9237761723529d9165471b70c521fec48c6897` |

**PASS integrity:** 5/5 assets and 25/25 manifest-listed package files matched; all checksum entries matched. 1,884 frozen vectors. Complete receipts: [ab-wildfire-ia-escape/integrity.json](ab-wildfire-ia-escape/integrity.json).

| Asset | Bytes | Recomputed SHA-256 |
|---|---:|---|
| meta.json | 1,217 | `aeb2ef927fc0d8565a86a6901afe5ee29359787bb39693342d18ce6850a9bcfb` |
| private/holdout.csv | 930,923 | `53583f4d2dff386bfebe864f49dba348d9717ee7bf96d28574082f80668edc12` |
| public/eval.csv | 838,515 | `d099e4cb9da999e3e301b0e4da1cc98cd56fc11371feba7711447571c83a7759` |
| public/train.csv | 2,351,953 | `575649d52c304d2fa0751411e0e4dc291309b42fbd0b280cbeae9e4b747cc2ae` |
| quality.json | 21,089 | `331a4ceb0944d33b80b0a6519c0148603b19b4fff1ae5136571ae3126cff3ec1` |

| Split | Rows | Positives | Positive rate | Time/key range |
|---|---:|---:|---:|---|
| train | 15,864 | 297 | 1.872163388805% | 2006-04-02 16:00:00 → 2015-12-31 10:45:00 |
| eval | 5,707 | 104 | 1.822323462415% | 2016-01-02 11:45:00 → 2020-12-19 14:17:00 |
| holdout | 6,257 | 257 | 4.107399712322% | 2021-01-10 13:07:00 → 2025-12-16 13:55:00 |

Schema: **25 columns**. Zero duplicate declared IDs in each split, zero shared declared row IDs between splits, and ordered disjoint split time keys. CQC month keys require the production-date qualification below. Detailed population/year/missingness/calendar/join checks: [ab-wildfire-ia-escape/claims-results.json](ab-wildfire-ia-escape/claims-results.json).


### Findings

**FAIL — P0 exact label leakage.** `MANIFEST.json`’s named-fire fixtures and shipped builder provide a literal answer table. Frozen `shipped_named_fire_fixture` recovered **3/5,707 eval** and **4/6,257 holdout**, **zero errors**. Eval: 2016-MWF009, 2019-HWF042 and 2019-SWF049 are positive. Holdout: 2023-HWF058, 2023-HWF036 and 2023-EWF031 are positive; 2023-LWF002 is negative. The holdout subset contains both classes, AUC 1.0. These are shipped-byte lookups, not internet-assisted hindsight. Disclosing the fixtures does not waive the operator’s prohibition.

The separate assessment-size ≥100 rule was not exact: **13 eval predictions, 2 errors; 35 holdout predictions, 5 errors**. It is not counted as exact recovery. No shared fire IDs crossed splits. Single-column rank AUCs did not exceed .95: assessment_hectares **.9095728249975975 eval / .8986896887159532 holdout**; fire_spread_rate **.9037094140402054 / .8866821849611445**, on 4,956/5,918 nonmissing rows. Strong predictive association is not itself a leakage verdict.

**FAIL — P0 false claims.** `quality.json` evaluation_contract.scope_note and limitations assert that holdout stays outside evaluated agents’ workspaces and that the benchmark protocol keeps it there. The operator specifies an illustrative runner, and the package ships the holdout plus named holdout answers. These guarantees are unsupported by the artifact. The same limitations text gives train/eval prevalence **1.86% / 1.85%**, versus measured **1.8721633888% / 1.8223234624%** (rounding to 1.87% / 1.82%). `MANIFEST.json` population eligibility contains unresolved `@@TOTAL@@` and `@@WINTER@@` placeholders rather than actual counts.

**PASS — measured population and rebuild.** The three files contain **27,828 fires**. Winter rows: **288 / 93 / 206 = 587**. Record-year versus assessment-year differences: **236 / 120 / 0 = 356**; the split uses assessment time. The shipped builder reproduced all five artifacts byte-for-byte from the pinned 10,400,030-byte source CSV, SHA-256 `8b6ed447ab0f958dbe845a53dc15362b8ef5c0810ad9420d2143f9f5ee010a72`. This source was acquired from the publisher’s staging mirror; it is reconstruction of the pinned input, not independent verification of the current Alberta origin server. Source-backed fixture assertions and exclusion accounting passed. Missing feature cells are retained; the disclosure of current-vintage retrospective research is not failed.

**PASS, bounded — novelty.** [WildfireIA](https://labrai.github.io/WildfireIA/) uses US FPA-FOD natural fires. The closer [Tremblay/Duchesne/Cumming Dryad release](https://datadryad.org/dataset/doi%3A10.5061/dryad.dm8m5) supplies Alberta 1996–2002 lightning-fire data and R analysis, but classifies growth between initial assessment and being held, followed by survival analysis; it does not supply this all-cause ≥100-ha final-area task. No exact task release was found in the bounded searches.

**NOT VERIFIED — current source licence reading.** The package scopes its CC0 dedication to its own compilation and carries Alberta attribution/OGL-Alberta v2.2. However, [Alberta’s licence page](https://open.alberta.ca/licence) returned 403, and available browser surfaces could not be opened. A publisher-copied licence is not independent source verification. Under the operator’s readable-licence requirement this remains an additional publication blocker; it is not an assertion that OGL prohibits reuse.

### NOT COVERED

Independent re-download of the original Alberta CSV and current readable OGL-Alberta text; historical per-fire vintages or real-time availability; independent reconstruction of the season-PDF −10.4% comparison and all near-threshold revision estimates; unbounded web outcome lookup; exhaustive arbitrary text encodings. The fixed attacks did not prove recovery beyond the reported subsets. Construction-time/stock-model bootstrap claims not separately listed in the reproduced reference output were not independently resampled from saved stock-model predictions.

### Reproduced illustrative references and controls

| Reference | Eval AUC | Brier / accuracy where applicable |
|---|---:|---|
| majority_constant | 0.5 | Brier 0.018223234624145785; accuracy 0.9817767653758542 |
| persistence_assessment_hectares | 0.9095728249975974 | Brier None |
| calendar_identity_only | 0.712964551957056 | Brier 0.017944783101809417 |
| full_feature_logistic | 0.9206280289405401 | Brier 0.015837186409891707 |

The bundled stock trainer and validator both reproduced **eval AUC .9554**, exit 0 / CONTRACT OK. The independent, fixed logistic control scored **0.9317003940196873 eval / 0.9484610894941635 holdout**. These supervised results are not label-blind recoveries. Reference code was run from the frozen package, with scalar reference scores cross-checked by the independent battery where applicable. Cape Town persistence intentionally uses prior labels scorer-side and is not a blind predictor. Constant-score null/0.5 conventions are recorded rather than interpreted as differing performance.

Evidence: [ab-wildfire-ia-escape/blind-results.json](ab-wildfire-ia-escape/blind-results.json), [ab-wildfire-ia-escape/controls.json](ab-wildfire-ia-escape/controls.json), [ab-wildfire-ia-escape/reference-results.json](ab-wildfire-ia-escape/reference-results.json), [ab-wildfire-ia-escape/baseline-execution.log](ab-wildfire-ia-escape/baseline-execution.log), [ab-wildfire-ia-escape/reconstruction-results.json](ab-wildfire-ia-escape/reconstruction-results.json), [ab-wildfire-ia-escape/reconstruction.log](ab-wildfire-ia-escape/reconstruction.log).


## Tier A — cpcb-aqi-exceedance

**DO NOT PUBLISH**

Release **436366305**, tag **v2026.11**; repository commit `cb3b251faa9e3cac37231746474585cc77f6f9c9`. Artifact identity `a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959`.

| Item freeze | SHA-256 |
|---|---|
| [factory/candidates/cpcb-aqi-exceedance/pre-flip-audit-prompt.md](factory/candidates/cpcb-aqi-exceedance/pre-flip-audit-prompt.md) | `f7e8a349a60dad1860f8e1d10b4c104966b60f235840302ce230bfe6ff55d7d9` |
| [cpcb-aqi-exceedance/repository/MANIFEST.json](cpcb-aqi-exceedance/repository/MANIFEST.json) | `83c24832c72276503888575b2cf0f8b9d24dd02956e122d068a919458a9dfb94` |
| [cpcb-aqi-exceedance/repository/SHA256SUMS](cpcb-aqi-exceedance/repository/SHA256SUMS) | `16d04a2dbb349fc8518ee1862c3ae503ef15a2c11d3d29836efb0a9aa7a7f4f3` |
| [cpcb-aqi-exceedance/predictions/blind.zip](cpcb-aqi-exceedance/predictions/blind.zip) | `aa391087831e05d594ea29baee8e8ce3f254ff168710826f753899ca2d9497ed` |

**PASS integrity:** 5/5 assets and 24/24 manifest-listed package files matched; all checksum entries matched. 1,396 frozen vectors. Complete receipts: [cpcb-aqi-exceedance/integrity.json](cpcb-aqi-exceedance/integrity.json).

| Asset | Bytes | Recomputed SHA-256 |
|---|---:|---|
| meta.json | 1,197 | `1f59e74e4d6003f03371c4514ee9edda7e79e8ecfa3f995723b1520bac6e2fd7` |
| private/holdout.csv | 22,967,353 | `2dae0040cdc2c80fa4adc9cc3b48f26882a6a20f451a252ac3a72f10da8f460f` |
| public/eval.csv | 20,210,392 | `e187f645445e135e092898a280e74a2ecba6e75cb25ed9c5470d6f96f779c478` |
| public/train.csv | 45,644,743 | `24b03a701c34d91834a7c5285d1c928ec33cda9282a2085405b06d541faa9c73` |
| quality.json | 22,603 | `98250e9d2731f89da021aec360f5d5535fc374241a98db14f185397f9126849a` |

| Split | Rows | Positives | Positive rate | Time/key range |
|---|---:|---:|---:|---|
| train | 288,754 | 61,075 | 21.151222147572% | 2019-01-01 00:00:00 → 2022-12-31 00:00:00 |
| eval | 126,570 | 19,819 | 15.658528877301% | 2023-01-01 00:00:00 → 2023-12-31 00:00:00 |
| holdout | 145,124 | 18,222 | 12.556158871034% | 2024-01-01 00:00:00 → 2024-12-30 00:00:00 |

Schema: **23 columns**. Zero duplicate declared IDs in each split, zero shared declared row IDs between splits, and ordered disjoint split time keys. CQC month keys require the production-date qualification below. Detailed population/year/missingness/calendar/join checks: [cpcb-aqi-exceedance/claims-results.json](cpcb-aqi-exceedance/claims-results.json).


### Findings

**FAIL — P0 extensive exact label leakage.** Let x(t) be shipped daily mean, C30(t) the shipped 30-day exceedance count, Nw(t) the shipped valid-day count and Mw(t) its shipped mean. The target for row D is `x(D+1)>90`. Same-station later rows directly supply x(D+1), or it appears in lag1/2/3 of D+2/3/4. Recency zero on D+1 also supplies the answer. More distant recency identifies the last exceedance date, permitting exact positive/negative deductions with abstention when a newer event masks the target.

Count arithmetic supplies the same answer without a next-day raw mean: `C30(D+1)-C30(D)+1[x(D-29)>90]`. A count difference of +1 or −1 alone yields a certain positive or negative. Covered-rate arithmetic reconstructs the incoming value as `Nw(D+1)*Mw(D+1)-Nw(D)*Mw(D)+x(D+1-w)` for w=7 or 30. The frozen code bounds serialization rounding and abstains if the inferred interval straddles 90. Every reported recovery below has **zero errors** and AUC **1.0 on covered rows**; the rows overlap and must not be added.

| Frozen attack, all shipped feature rows as donors | Eval recovered / 126,570 | Holdout recovered / 145,124 |
|---|---:|---:|
| D+1 daily mean; also D+1 recency | 118,728 | 136,110 |
| D+2 lag1 | 111,932 | 128,303 |
| D+3 lag2 | 109,359 | 125,275 |
| D+4 lag3 | 108,341 | 124,033 |
| Count delta extremes only | 17,274 | 18,381 |
| Count delta plus outgoing indicator | 96,128 | 115,583 |
| 7-day count × mean identity | 100,910 | 117,959 |
| 30-day count × mean identity | 96,045 | 115,508 |
| **Union, frozen precedence** | **125,776 (99.37267915%)** | **143,793 (99.08285328%)** |

Union recovered **19,635 positive + 106,141 negative eval labels**, and **17,987 positive + 125,806 negative holdout labels**. There were **zero conflicting rule outputs**. Restricting donors to each split alone still recovers **125,277 eval / 143,793 holdout**, zero errors. Thus neither withholding training labels nor keeping splits separate fixes this exposure. The diagnostic vector `union_conflicting_rules` is a count, not a prediction; its generic scorer’s comparison with labels is meaningless and is not reported as attack errors.

**FAIL — P0 false feature descriptions.** `pm25_max` and `pm25_min` are reversed in the serialized row. The builder reads `(n, mean, low, high)` then writes low under max and high under min. Named min exceeds named max on **288,113/288,754 train**, **126,265/126,570 eval**, **144,851/145,124 holdout**; the remaining **641/305/273** are equal. This contradicts the dictionary’s minimum/maximum meanings. It is a data-description defect, not merely a high AUC.

Single-column dominance flags: pm25_mean **.9689109528605425 eval / .9666395548017255 holdout**, and the misnamed pm25_min **.9509991205649675 eval** (.9490084472298741 holdout). Those individual associations are persistence, while the later-row/count identities above demonstrate self-answering. All label columns were excluded from predictor construction.

**PASS — shipped counts, grain and splits.** Grain is unique station-day; station counts **389 / 509 / 529**, no duplicate IDs or calendar inconsistencies; every scored D has at least 18 hourly readings. Date ranges are 2019–2022 / 2023 / 2024 through December 30. The raw D+1 operands need not be columns in the same row to leak through the panel.

**NOT VERIFIED — complete independent source rebuild.** The builder downloaded part of the monthly export but stopped at **2019-11 batch 0, HTTP 409, error code 1001**. No full reconstruction digest comparison is claimed. The shipped files and package digests nevertheless all matched. Raw-row/exclusion counts that require the complete original export remain unverified, including the stated thin-day/unlabelable-next-day exclusions.

**NOT VERIFIED — upstream licence chain.** [XKDR’s own README](https://raw.githubusercontent.com/xKDR/Air-Quality-Database/main/README.md) states CC BY 4.0 and requests XKDR, CPCB and AirNow credit. The package preserves those scopes and asserts GODL-India for CPCB measurements. However, [CPCB’s copyright policy](https://cpcb.gov.in/copyright-policy/) restricts broader reuse, and a GODL grant for a live AQI resource does not by itself establish the grant for this full historical hourly export. The exact upstream scope was not independently resolved; no clean-licence clearance is given.

**PASS, bounded — novelty search.** The public [CPCB Kaggle collection](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) is a source-data near neighbour. [AkshayKarthick/pm25-next-day-india](https://huggingface.co/datasets/AkshayKarthick/pm25-next-day-india) uses CAMS/Open-Meteo city data, not this CPCB station export. No exact task release was verified. AtmosIQ/cpcb was a catalogue hit whose card returned 404; it is explicitly an unresolved near neighbour, not silently ruled out.

### NOT COVERED

Full historical source reconstruction/exclusion audit after the HTTP 409; a definitive CPCB-to-XKDR licence grant for this export; operational hourly publication latency or vintages; independent verification of the 2024-11-18 CPCB bulletin fixture; exhaustive unseen public datasets including the inaccessible AtmosIQ card. No new recovery rules were devised after seeing the zero-error results. The observed shipped-byte recovery alone decides DO NOT PUBLISH.

### Reproduced illustrative references and controls

| Reference | Eval AUC | Brier / accuracy where applicable |
|---|---:|---|
| station_persistence | 0.9689109528605426 | Brier 0.2830447212174809 |
| state_season_climatology | 0.861668549124152 | Brier 0.09678794864992082 |
| global_rate | null (constant/not applicable) | Brier 0.13508330404901164 |
| station_train_rate | 0.7616362039606324 | Brier 0.12382983558028718 |
| majority_class | null (constant/not applicable) | accuracy 0.843414711226989 |

The bundled stock trainer and validator both reproduced **eval AUC .9734**, exit 0 / CONTRACT OK. The independent, fixed logistic control scored **0.9706899916823624 eval / 0.9671471963494694 holdout**. These supervised results are not label-blind recoveries. Reference code was run from the frozen package, with scalar reference scores cross-checked by the independent battery where applicable. Cape Town persistence intentionally uses prior labels scorer-side and is not a blind predictor. Constant-score null/0.5 conventions are recorded rather than interpreted as differing performance.

Evidence: [cpcb-aqi-exceedance/blind-results.json](cpcb-aqi-exceedance/blind-results.json), [cpcb-aqi-exceedance/controls.json](cpcb-aqi-exceedance/controls.json), [cpcb-aqi-exceedance/reference-results.json](cpcb-aqi-exceedance/reference-results.json), [cpcb-aqi-exceedance/baseline-execution.log](cpcb-aqi-exceedance/baseline-execution.log), [cpcb-aqi-exceedance/reconstruction-results.json](cpcb-aqi-exceedance/reconstruction-results.json), [cpcb-aqi-exceedance/reconstruction.log](cpcb-aqi-exceedance/reconstruction.log).


## Tier A — cqc-care-home-deregistration

**DO NOT PUBLISH**

Release **433767120**, tag **v2026.11**; repository commit `8bc008af97f60fd798bd8d453108c37fc0404d3a`. Artifact identity `afe9ee203f302f3ca41b9b01ad74a937e111d1b830590c7e662bb0b7b6df85d7`.

| Item freeze | SHA-256 |
|---|---|
| [factory/candidates/cqc-care-home-deregistration/pre-flip-audit-prompt.md](factory/candidates/cqc-care-home-deregistration/pre-flip-audit-prompt.md) | `8232cadb42289f5831c7833f07f3faccfbe035f4baab0c231beae6696339b6b3` |
| [cqc-care-home-deregistration/repository/MANIFEST.json](cqc-care-home-deregistration/repository/MANIFEST.json) | `aea22a8c2261cacd520bf934a49e30020e538f1c3ea59c0605f02339bcd76638` |
| [cqc-care-home-deregistration/repository/SHA256SUMS](cqc-care-home-deregistration/repository/SHA256SUMS) | `69424d98f42f36c1f125ae2e1f1482843bf628f6f51b4624bf766466d44408e5` |
| [cqc-care-home-deregistration/predictions/blind.zip](cqc-care-home-deregistration/predictions/blind.zip) | `6b97d8ce02440a40aacb4cc65dec877ce162a019c9bbc4eda30b76a5788f1c9e` |

**PASS integrity:** 5/5 assets and 24/24 manifest-listed package files matched; all checksum entries matched. 1,069 frozen vectors. Complete receipts: [cqc-care-home-deregistration/integrity.json](cqc-care-home-deregistration/integrity.json).

| Asset | Bytes | Recomputed SHA-256 |
|---|---:|---|
| meta.json | 2,349 | `3b350af60fcd415824cd4940b36c4c4e19f4933ec7190d5846fd9920dd9a98c0` |
| private/holdout.csv | 1,788,226 | `880a36d468b779fce541e5419d3f785d482dc86376fadbfd5b436460b55ac552` |
| public/eval.csv | 1,787,102 | `2078146fce1f75b23b0a1060e7efc0241317c981c21a5d502457ada2ec0ee20e` |
| public/train.csv | 9,553,058 | `6138dd92974d7b70504ab32af2c8a3b73b4c0f1d6f87dba99eaac1f10f37ddf1` |
| quality.json | 24,584 | `4e07a858396ec032c47d67a62cd9f1ba9e04a607bd0eeb962c4d7249cef77f50` |

| Split | Rows | Positives | Positive rate | Time/key range |
|---|---:|---:|---:|---|
| train | 78,138 | 4,418 | 5.654099157900% | 2018-01-01 00:00:00 → 2022-01-01 00:00:00 |
| eval | 14,765 | 757 | 5.126989502201% | 2024-01-01 00:00:00 → 2024-01-01 00:00:00 |
| holdout | 14,749 | 761 | 5.159671842159% | 2025-01-01 00:00:00 → 2025-01-01 00:00:00 |

Schema: **21 columns**. Zero duplicate declared IDs in each split, zero shared declared row IDs between splits, and ordered disjoint split time keys. CQC month keys require the production-date qualification below. Detailed population/year/missingness/calendar/join checks: [cqc-care-home-deregistration/claims-results.json](cqc-care-home-deregistration/claims-results.json).


### Findings

**FAIL — P0 exact label leakage.** The shipped builder includes the pseudonym salt `cqc-chd-v1-20261103`, raw fixture IDs and explicit expected answers. Computing `sha256(salt|2024|location_id)[:16]` and joining to eval recovers three answers. The builder’s leap-year boundary comment supplies a fourth: the 2025-01-05 end date is outside the 365-day horizon beginning 2024-01-05. Frozen fixtures yield **4/14,765 eval labels, zero errors**: 1-113831768 positive; 1-10000302982, 1-10086766554 and 1-353801949 negative. No holdout label was recovered by these frozen fixture rules. This is an answer lookup in shipped code; hashing the row ID does not remove it.

**FAIL — P0 linkability claims.** The README says no successor instant exists in a solver-visible frame, and the reference notes say prior-instant labels are structurally unlinkable even for the scorer. Yet January 2025 holdout features are a successor panel for January 2024 eval. Frozen all-shipped-row quasi-joins show:

| Join rule | Eval coverage | Correct | Errors |
|---|---:|---:|---:|
| Unique successor on LA × beds × start year × rating × sector, predict 0 | 9,195 | 9,185 | 10 |
| Unique successor on LA × beds × start year, predict 0 | 8,433 | 8,427 | 6 |
| Unique successor on all tested stable features, predict 0 | 11,258 | 11,250 | 8 |
| Missing-successor rule on unique LA × beds × start year | 9,279 | 8,935 | 344 |

The last rule has covered AUC **.9744320967675709**, but is **not exact recovery**. These results contradict categorical unlinkability, not a claim that every entity was uniquely reidentified. The publisher’s within-split zero-coverage measurements are reproducible in scope but omit the shipped cross-split exposure. Holdout has no shipped 2026 successor, so this battery yields zero holdout successor coverage. Salted row IDs are disjoint; underlying entities need not be.

**FAIL — P0 dictionary.** DATA_DICTIONARY.md says beds_bucket is `1-9, 10-24, 25-49, 50+`. The actual values are **1-3, 4-10, 11-25, 26-50, 51+, unknown**. The builder reproduces those actual bins with **zero mismatches in all three splits**. The reference scorer’s note also says its training rows cover 2016–2022, although the actual training vintages are **2018–2022**; the README correctly discloses dropping 2016/2017.

**FAIL — reproduction claims.** REPRODUCE.md’s printed `python3 code/build.py --out ./extract` omits required work-dir, built-at and summary-out arguments. The code checks the 2024 and deactivated source size/digest prefixes but only records receipts for other vintages; a statement that it verifies every source digest overstates its behavior. These are claims about the delivered program, not a demand for factory ceremony.

**PASS — source reconstruction/data truth.** With the required arguments supplied, the shipped builder fetched the historical CQC/Drive vintages and cumulative deactivated register and reproduced **all five artifacts byte-for-byte**. Training rows by year: **2018 16,104; 2019 15,807; 2020 15,554; 2021 15,467; 2022 15,206**. Eval/holdout are the January 2024/2025 vintages. The CSV’s `instant` is a month key, not a claim that production was January 1; eval production was January 5, 2024 and holdout January 2, 2025. Register end is not physical service closure; the package’s transfer/re-registration caveat is material and accepted.

**PASS — licence.** [CQC’s own reuse page](https://www.cqc.org.uk/about-us/transparency/using-cqc-data) permits reuse under OGL and requires acknowledgement of CQC. The readable [OGL v3 text](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) and attribution are preserved in the evidence and reflected in the shipped licence scope; source data are not converted to CC0.

**PASS, bounded — novelty.** [BenGoodair/Involuntary_care_home_closures](https://github.com/BenGoodair/Involuntary_care_home_closures) and related ownership/closure research are close public work, but involuntary physical closure/transfer-filtered outcomes differ from every registration-end event in a 365-day window. No release of this exact task was verified. New splits alone were not treated as novelty.

### NOT COVERED

Historical first-publication ledgers, physical closure/transfer adjudication, or a complete independent successor-entity registry; a new 2026 donor panel; brute-force reversal of every pseudonym against external IDs; an exact general successor attack. Full-year production-date and outcome truth were checked through the frozen builder, not a separately reimplemented XLSX parser. The broad quasi-join is imperfect and is not promoted to zero-error recovery.

### Reproduced illustrative references and controls

| Reference | Eval AUC | Brier / accuracy where applicable |
|---|---:|---|
| beds_bucket_rate | 0.5297982677571677 | Brier 0.04861142055619016 |
| global_rate | null (constant/not applicable) | Brier 0.04866907734535654 |
| hsca_start_year_rate | 0.5226476076701217 | Brier 0.048655187128748174 |
| last_rating_rate | 0.5597447335246061 | Brier 0.04830835720778777 |
| local_authority_rate | 0.5207061335775669 | Brier 0.04878759944939004 |
| majority_class | null (constant/not applicable) | accuracy 0.9487301049779885 |
| provider_sector_rate | 0.5010938738912734 | Brier 0.0486784248539342 |
| rating_x_beds_rate | 0.5870921937794369 | Brier 0.048261931237345713 |

The bundled stock trainer and validator both reproduced **eval AUC .5659**, exit 0 / CONTRACT OK. The independent, fixed logistic control scored **0.5857806201702443 eval / 0.6056420802963456 holdout**. These supervised results are not label-blind recoveries. Reference code was run from the frozen package, with scalar reference scores cross-checked by the independent battery where applicable. Cape Town persistence intentionally uses prior labels scorer-side and is not a blind predictor. Constant-score null/0.5 conventions are recorded rather than interpreted as differing performance.

Evidence: [cqc-care-home-deregistration/blind-results.json](cqc-care-home-deregistration/blind-results.json), [cqc-care-home-deregistration/controls.json](cqc-care-home-deregistration/controls.json), [cqc-care-home-deregistration/reference-results.json](cqc-care-home-deregistration/reference-results.json), [cqc-care-home-deregistration/baseline-execution.log](cqc-care-home-deregistration/baseline-execution.log), [cqc-care-home-deregistration/reconstruction-results.json](cqc-care-home-deregistration/reconstruction-results.json), [cqc-care-home-deregistration/reconstruction.log](cqc-care-home-deregistration/reconstruction.log).


## Tier A — za-cct-substation-evening-peak-exceedance

**DO NOT PUBLISH**

Release **434422204**, tag **v2026.11**; repository commit `b4e351a94d9166445736b0d75b5180365e515e7d`. Artifact identity `9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180`.

| Item freeze | SHA-256 |
|---|---|
| [factory/candidates/za-cct-substation-evening-peak-exceedance/pre-flip-audit-prompt.md](factory/candidates/za-cct-substation-evening-peak-exceedance/pre-flip-audit-prompt.md) | `3354933e96eee721ff89ddc62c9a360a8980570999fe84a0f20d8c649d5b8926` |
| [za-cct-substation-evening-peak-exceedance/repository/MANIFEST.json](za-cct-substation-evening-peak-exceedance/repository/MANIFEST.json) | `f1479b05f8f09f68df62d454de973885d5f319c2b2dff113f1048af23304cff7` |
| [za-cct-substation-evening-peak-exceedance/repository/SHA256SUMS](za-cct-substation-evening-peak-exceedance/repository/SHA256SUMS) | `bedcbfce88acada8b1b2657036241c84259d2bbb15b5c7f025ace6596952c5bf` |
| [za-cct-substation-evening-peak-exceedance/predictions/blind.zip](za-cct-substation-evening-peak-exceedance/predictions/blind.zip) | `5d0b1b2926edecbb86bddad4596a3174fb732181d1dfb1662ff0635fa58337f0` |

**PASS integrity:** 5/5 assets and 24/24 manifest-listed package files matched; all checksum entries matched. 1,459 frozen vectors. Complete receipts: [za-cct-substation-evening-peak-exceedance/integrity.json](za-cct-substation-evening-peak-exceedance/integrity.json).

| Asset | Bytes | Recomputed SHA-256 |
|---|---:|---|
| meta.json | 2,011 | `935a7438a96b326fb646b802ae2122b2ad8fdcfc5e28e5e9b8e271052606b060` |
| private/holdout.csv | 2,879,772 | `9ab07c57bbe241661fe5f5c8049a0a14a7445e75cc94423edbcf9c9aacb50430` |
| public/eval.csv | 2,866,998 | `2e416315a3f32fb5dc5f816ea0bc3e67d37dd4c62a8514c43e3c5ec64c0309de` |
| public/train.csv | 2,638,747 | `f7b533529492c86155a2ddc26592b52db539ae700bae4c37df370e4b4af9d0b9` |
| quality.json | 33,378 | `f0690d28e99324461b6f9b8f250a1bd77eed480ad22bdd08ec54b4a32a4bb8ec` |

| Split | Rows | Positives | Positive rate | Time/key range |
|---|---:|---:|---:|---|
| train | 13,735 | 1,539 | 11.204950855479% | 2022-01-31 00:00:00 → 2022-12-31 00:00:00 |
| eval | 14,965 | 1,256 | 8.392916805880% | 2023-01-01 00:00:00 → 2023-12-31 00:00:00 |
| holdout | 15,006 | 1,382 | 9.209649473544% | 2024-01-01 00:00:00 → 2024-12-31 00:00:00 |

Schema: **25 columns**. Zero duplicate declared IDs in each split, zero shared declared row IDs between splits, and ordered disjoint split time keys. CQC month keys require the production-date qualification below. Detailed population/year/missingness/calendar/join checks: [za-cct-substation-evening-peak-exceedance/claims-results.json](za-cct-substation-evening-peak-exceedance/claims-results.json).


### Findings

**FAIL — P0 documentary answer exposure.** The shipped README and builder name **Grassy_Park_66kV, 2024-07-15**, give evening peak **150.38**, trailing p95 **146.82**, and conclude label **1**. That key belongs to the declared 2024 holdout. This contradicts statements that the evening label operands are sealed outside the artifact. The code and metadata containing the example were frozen, and the source rebuild’s fixture assertion passed. **Audit limitation:** the frozen vector generator did not include a Cape Town fixture-lookup vector. Consequently this is a directly observed documentary answer disclosure, not a claimed pre-label frozen/scored one-row recovery experiment. No post-score attack was added to fill that omission.

**FAIL — P0 false source-digest guarantee.** VERIFICATION.md says every page SHA is pinned in code/build.py and the build fails if any pinned bytes change. REPRODUCE.md repeats the guarantee. The builder fetches the 54 pages and records their new hashes; it does not compare every page with a pre-existing expected digest. Fixture checks and successful byte reproduction do not implement this claimed guarantee. The printed reconstruction command also omits required `--summary-out`.

**FAIL — P0 interval direction.** README/RELEASE_NOTES describe morning_ratio’s *edge over* persistence with a negative interval. The reproduced output is **persistence minus morning_ratio = −.0838405589707445**, CI **[−.10118117461628362, −.0706365042660001]**. Morning_ratio minus persistence is the positive reverse **[.0706365042660001, .10118117461628362]**. Likewise its edge over calendar_identity is **+.08365799374905047**, CI **[.06274112821084565, .10192888805600986]**. Persistence minus calendar_identity is **−.0001825652216940199**, CI **[−.01684265124782114, .01605528413526447]**: inconclusive difference, not evidence of equivalence. Calling the two “inseparable” overstates that result.

**No general exact recovery demonstrated by the frozen battery.** The frozen one-day positive morning-history-delta rule, using all shipped donors, covers **14,965 eval with 6,711 errors** and **14,965 holdout with 6,657 errors**. The morning-ratio score has AUC **.7340185012588784 eval / .7785346026803811 holdout**; it is predictive, not an exact decoder. Tested 1/2/7/30/90-day differences and the 90-day morning inverse did not demonstrate an evening-answer identity. No numeric single-column AUC exceeded .95. An imperfect morning-history probe does not prove all possible cross-row attacks safe.

**PASS — counts, grain and reconstruction.** The anonymous ArcGIS harvest fetched **54 requests, 52,608 timestamp rows**, each containing 41 station readings; the ML grain is **station × day**, not one source-table row. All three splits have 41 stations; **335 / 365 / 366 days**. There are **44,936 possible station-days**, **1,230 burn-in exclusions**, and **43,706 shipped rows**. All five generated artifacts rebuilt byte-for-byte. Calendar fields and IDs match the files. The closed 2022–2024 table’s 2026 creation and retrospective availability limitation are disclosed, not treated as defects.

The initial generic mean check used an excessively tight rounding tolerance. Slots and their source-derived mean are independently rounded to three decimals. Maximum recomputation differences are **.00075 / .000833333334 / .000833333334 MVA**, all inside the **.001 MVA two-rounding bound**; **zero violations** of that bound. These initial warnings are not data failures. The full rebuild independently corroborates the derivation.

**PASS — licence scope.** The [City’s open-data terms](https://www.capetown.gov.za/general/city-of-cape-town-open-data-terms-of-use/) and [Council open-data policy](https://www.capetown.gov.za/media/vg2plaql/open_data_policy.pdf) were read from City-owned pages and preserved. They support reuse of portal data; the dataset’s own ArcGIS licenceInfo points there. The shipped manifest uses **LicenseRef-CityOfCapeTown-OpenDataTerms**, explicitly says no standard SPDX licence is declared, identifies the operative custom terms, credits the City and limits CC0 to the new contribution. It does not assert a standard Creative Commons grant for the City data. Generic City website/publication restrictions were not substituted for the dataset’s open-data instrument.

**PASS, bounded — novelty.** Searches across web, Hugging Face/Kaggle-indexed results and the source found raw substation telemetry and unrelated power-load tasks, but no usable release of this exact Cape Town morning-to-evening exceedance task.

### NOT COVERED

A pre-label frozen fixture lookup for this item; arbitrary multi-day nonlinear history attacks, external evening-data harvesting as an attack, or operational timestamp-availability verification. The source rebuild validates the closed static table and code, not a live 2022–2024 forecasting deployment. No claim of general leakage absence is made. The losing stock baseline is explicitly **not** a disqualifier.

### Reproduced illustrative references and controls

| Reference | Eval AUC | Brier / accuracy where applicable |
|---|---:|---|
| calendar_identity | 0.6503605075098278 | Brier 0.11733772555830475 |
| global_rate | null (constant/not applicable) | Brier 0.07767581635737097 |
| identity_only | 0.513407814058643 | Brier 0.07887296541116173 |
| majority_class | null (constant/not applicable) | accuracy 0.9160708319411961 |
| month_only | 0.6540502879924992 | Brier 0.09087705476604252 |
| morning_ratio | 0.7340185012588782 | Brier 0.9927826756544286 |
| persistence_prev_evening | 0.6501779422881337 | Brier 0.10758436351486803 |

The bundled stock trainer and validator both reproduced **eval AUC .5107**, exit 0 / CONTRACT OK. The independent, fixed logistic control scored **0.761615585186727 eval / 0.767521274281446 holdout**. These supervised results are not label-blind recoveries. Reference code was run from the frozen package, with scalar reference scores cross-checked by the independent battery where applicable. Cape Town persistence intentionally uses prior labels scorer-side and is not a blind predictor. Constant-score null/0.5 conventions are recorded rather than interpreted as differing performance.

Evidence: [za-cct-substation-evening-peak-exceedance/blind-results.json](za-cct-substation-evening-peak-exceedance/blind-results.json), [za-cct-substation-evening-peak-exceedance/controls.json](za-cct-substation-evening-peak-exceedance/controls.json), [za-cct-substation-evening-peak-exceedance/reference-results.json](za-cct-substation-evening-peak-exceedance/reference-results.json), [za-cct-substation-evening-peak-exceedance/baseline-execution.log](za-cct-substation-evening-peak-exceedance/baseline-execution.log), [za-cct-substation-evening-peak-exceedance/reconstruction-results.json](za-cct-substation-evening-peak-exceedance/reconstruction-results.json), [za-cct-substation-evening-peak-exceedance/reconstruction.log](za-cct-substation-evening-peak-exceedance/reconstruction.log).


## Tier C scope note

Only novelty, source-owned licence/attribution and actual public row-level channels were checked for these additions. The three newly ready records (WTO, DEFRA, RapidRail) were included from the captured status records. No Tier C labels or prediction artifacts were built. Source responses, unsuccessful fetch receipts and public-search results are retained under `evidence/`; catalogue query records are under `evidence/catalogues/`. Searches were bounded rather than exhaustive. READY findings do not approve enforcement language, guarantee novelty everywhere, or pre-clear leakage in a future panel.

The tables below hash each captured candidate record (included in the pre-label code freeze) and key independently acquired evidence. A digest establishes the exact bytes read, not the truth of their contents. A challenge page is explicitly identified as such and never counted as a CSV. Complete source URLs/status/headers are in the adjacent JSON receipts. Web-tool-only primary text is preserved in the `web-*.json` evidence files and the final seal.


## Tier C — cra-charity-filing-exit

**READY-TO-BUILD**

**Novelty — PASS, bounded.** Web/Hugging Face/Kaggle-targeted searches found T3010 collections, including the [Borealis T3010 master dataset](https://doi.org/10.5683/SP2/QXWUAZ), and US Form 990 failure work. No verified release provides the exact Canadian next-fiscal-year non-filing target. A cleaned T3010 panel is a serious near neighbour; the absence of splits alone would not distinguish it, and its entire schema was not downloaded here.

**Licence — PASS, source text readable through indexed primary pages.** The [CRA catalogue](https://open.canada.ca/data/en/dataset/80c00cdb-1358-415c-bb8b-0de7f12675b8?res_page=1) assigns OGL-Canada. The [source-owned OGL-Canada v2 text](https://open.canada.ca/en/open-government-licence-canada) permits modification and redistribution, including commercially, with source acknowledgement and a licence link; personal information/third-party rights and official symbols are outside the grant. The candidate records attribution and limits its own dedication rather than relicensing CRA data.

**Channel — PASS for existence; direct transfer NOT VERIFIED.** The primary catalogue advertises actual downloadable Identification CSV, **12 fields / 13,203,780 bytes**, and Charitable Programs CSV, **29,465,670 bytes**, with row schemas, resource IDs and validation timestamps. These are bulk row-level files, not an aggregate portal view. This audit’s direct CSV/API requests returned **244-byte challenge HTML despite HTTP 200**, including an alternate endpoint; they are not counted as downloaded CSV evidence. The READY verdict is based on the source-owned resource catalogue establishing the public bulk channel, with this explicit acquisition limitation.

### NOT COVERED

Full CSV download or all historical years; all Borealis columns/derived outcomes; construction, leakage, fiscal-year selection, late filings, operational availability and label truth. If actual downloads remain blocked at construction, this channel must be resolved before building; this report does not certify a working local transfer.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/cra-charity-filing-exit/record.json](factory/candidates/cra-charity-filing-exit/record.json) | 23,871 | `482475de8f27d92d555479f5ceb62d874db88473018c786b6f29d7e469845f4f` |
| [evidence/http/cra_sample.bin](evidence/http/cra_sample.bin) | 244 | `86e4061767050d57d65020b428e89861dfea9b63c75445c155206900c2bab6a1` |
| [evidence/http/cra_catalogue.bin](evidence/http/cra_catalogue.bin) | 244 | `97a41f4ffed8e7395e49bd278d385523ec10c74a42dc65b86b5be811e1efbbfe` |
| [evidence/http/canada_license.bin](evidence/http/canada_license.bin) | 244 | `3f7f78abaeabda3323316cc8ce03f93f6443ce6eb01c3f9bb299daee54087f2c` |

## Tier C — datasus-sinasc-cesarean-share-decline

**LICENCE-BLOCKED**

**Novelty — PASS, bounded.** [SidneyBissoli/sinasc](https://huggingface.co/datasets/SidneyBissoli/sinasc), jgchaicoski/datasus_sinasc and other public SINASC exports provide birth microdata. The inspected card describes raw microdata, not municipality-level T-to-T+2 cesarean-share decline of at least two percentage points. No exact ready task was found.

**Licence — unresolved, publication/build clearance blocked.** The [Ministry’s dataset page](https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc) embeds `license_id=cc-by`, title Creative Commons Atribuição, but its blanket site footer says **CC BY-ND 3.0**. The candidate honestly records both, then adopts a dataset-over-footer interpretation. I do not treat that interpretation or a third-party CC-BY-4.0 card as a clean source-owned resolution. The precise CC-BY version is also not explicit in the package metadata. This is **NOT VERIFIED clean derivative permission**, not an allegation that the publisher concealed the conflict or a definitive legal holding that every factual aggregation is prohibited. Under the operator’s clean-terms requirement the verdict is LICENCE-BLOCKED until the exact data grant is resolved and preserved. Do not relabel the ministry rows CC0.

**Channel — PASS.** The source page lists **95 resources**. A **65,536-byte HTTP 206** prefix of the official 2024 ZIP decoded the `SINASC_2024.csv` entry, **62 columns**, including residence municipality, birth date and PARTO; the decoded prefix has **1,636 lines**, with the last potentially partial. This establishes genuine birth-level bulk rows, not just TABNET aggregates.

### NOT COVERED

Full ZIP download/year completeness, municipality-year reconstruction, all preview/final vintage claims, exact future label availability, or independent reading of the entire ministry open-data plan. No scoring or leakage test was performed for this discovery-only item.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/datasus-sinasc-cesarean-share-decline/record.json](factory/candidates/datasus-sinasc-cesarean-share-decline/record.json) | 37,727 | `4f7353459789bb36ab13a5b60af37a1d88e05aeb19a21c6c06d58e5538bd01f1` |
| [evidence/http/sinasc_catalogue.bin](evidence/http/sinasc_catalogue.bin) | 175,790 | `e1c89b6d3f01dd7d0d172a2973f3d4dd858076e34f69bc46f37819bbbc13740b` |
| [evidence/http/sinasc_sample.bin](evidence/http/sinasc_sample.bin) | 65,536 | `5f544e8a0c5750b38c474c57a03ea981fa3458a667474f51ceeaa14e080ea8ce` |

## Tier C — ibama-auto-infracao-recidivism

**READY-TO-BUILD**

**Novelty — PASS, bounded.** Search results include general IBAMA enforcement/deforestation data and the sparse [Embellow/Ibama](https://huggingface.co/datasets/Embellow/Ibama) card (31 bytes), but no verified exact future-repeat-infringement task. The sparse card does not support an exhaustive exclusion of every file it may contain.

**Licence — PASS, custom public-sector instrument.** The [IBAMA catalogue](https://dadosabertos.ibama.gov.br/dataset/fiscalizacao-auto-de-infracao) says Outra (Aberta). The [official consolidated Decree 8,777 text](https://www2.camara.leg.br/legin/fed/decret/2016/decreto-8777-11-maio-2016-783082-normaatualizada-pe.pdf), read on the Chamber of Deputies’ own site, supports free reuse of federal open datasets, with authorship/source credit and third-party rights qualifications. No Creative Commons version should be invented: retain **NOASSERTION** for SPDX and preserve the operative catalogue/policy instruments plus IBAMA attribution. The candidate records this custom route; an own-compilation dedication cannot erase it.

**Channel — PASS.** An anonymous **65,536-byte HTTP 206** prefix from IBAMA’s published bulk ZIP decoded `auto_infracao_1977.csv`, **84 fields**, **header plus 2 records**. The schema includes infringement ID, date, municipality and person/entity identifiers. The ZIP is genuine row-level data, not a map screenshot or counts table. The prefix is not a complete archive audit.

### NOT COVERED

All annual entries, full recurrence construction/entity resolution, cancellation/revision semantics, personal-data field policy, future temporal leakage or the uninformative Hugging Face repository’s complete contents. No new built artifact was available for a publication audit.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/ibama-auto-infracao-recidivism/record.json](factory/candidates/ibama-auto-infracao-recidivism/record.json) | 45,660 | `f99e291a076dd9e3e3eb1910dcab9a9b3f428c611bcd0b872dcb7c52398e69b4` |
| [evidence/http/ibama_catalogue.bin](evidence/http/ibama_catalogue.bin) | 65,761 | `fe0eb804a7105fff54c2a59825080e781471f1badbf5173165897246d53a3ada` |
| [evidence/http/ibama_decree_current.bin](evidence/http/ibama_decree_current.bin) | 70,399 | `d124203e8e973f6cc193f63243fbe1552088b6e648743792152fa62b18821132` |
| [evidence/http/ibama_sample.bin](evidence/http/ibama_sample.bin) | 65,536 | `3930f7418f4e18689ea32c22d323fd61e09b8949baedb4e8665ecca60fa4cdc5` |

## Tier C — npri-facility-reporting-exit

**READY-TO-BUILD**

**Novelty — PASS, bounded.** Searches found NPRI raw emissions, inventories and modelling/research uses, but no exact facility-next-year reporting-exit release. A pollutant-emissions task is not this filing-population task.

**Licence — PASS.** The [source-owned catalogue](https://open.canada.ca/data/en/dataset/348504f1-43a6-4e0c-aee5-fc470b1dc888) explicitly assigns OGL-Canada; the readable [OGL-Canada terms](https://open.canada.ca/en/open-government-licence-canada) require source acknowledgement/licence linkage and preserve exclusions. Credit ECCC/NPRI and retain the source licence; the candidate records that route.

**Channel — PASS.** The official ECCC storage endpoint returned **65,536 bytes, HTTP 206**, of the 2023 CSV with actual facility/substance rows. The underlying source grain is facility × substance × year, not one facility-year; constructing filing exit requires deduplication across substances. Current primary catalogue pages list annual CSV/XLSX resources, including 2020–2024.

### NOT COVERED

All historic editions, source revisions, submission deadlines, facility-ID succession and pollutant filtering; complete novelty inspection of every research supplement; any built labels, count arithmetic or cross-row leakage. Direct CKAN responses were challenge HTML, so catalogue licence reading used the indexed primary page and row transfer used ECCC storage.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/npri-facility-reporting-exit/record.json](factory/candidates/npri-facility-reporting-exit/record.json) | 25,543 | `cc31bd6bc771c7c9d880b85577e9a56e015528247579d8a430b3722ae1743061` |
| [evidence/http/npri_sample.bin](evidence/http/npri_sample.bin) | 65,536 | `a9a3ecf9432497d555a725baafa901964b9870c8408a8190a472ca0e44302f30` |
| [evidence/http/npri_catalogue.bin](evidence/http/npri_catalogue.bin) | 244 | `0f5c1440606b8f1d8fc2bc0a7c572966f69155639ef9413a595ec61a6634e791` |

## Tier C — oecd-ncp-specific-instance-acceptance

**READY-TO-BUILD**

**Novelty — PASS, bounded.** NCP/OECD Watch case collections and research on outcomes exist; no exact ML-ready initial-acceptance prediction release was found. Raw status tables alone are not claimed to prove novelty or non-novelty.

**Licence — PASS, scoped.** [OECD’s own terms, section 3](https://www.oecd.org/en/about/terms-conditions.html) permit downloading, adaptation and redistribution of OECD-owned data for any purpose, subject to specific/third-party restrictions. Credit must include OECD, year, dataset, source URL/DOI and access date, and the acknowledgement requirement must pass to downstream recipients. Use **NOASSERTION for a single standard SPDX grant covering the entire mixed case collection**; do not blanket-relicense it CC0 or assume all pre-2024 written content is CC BY 4.0. The candidate’s source-data route is supported; restricted annual-report annexes and external NCP documents are not automatically included.

**Channel — PASS.** The public OECD RSS enumeration returned **15 case entries / 13,814 bytes**. A source-owned [2026 Korean NCP case](https://www.oecd.org/en/networks/national-contact-points-for-responsible-business-conduct/database/2026/kr0029.html) supplies case-level lead NCP, filing date, country, source, sector, topics and **Not accepted** status, with a dated assessment. An enumerable case-level HTML channel qualifies as row-level acquisition; an aggregate dashboard alone would not. The web tool could read source pages even though direct urllib requests returned 403.

### NOT COVERED

All pages/cases and pagination completeness; third-party rights for every external attachment; full annual report annexes; at-filing availability of narrative text (which often contains the outcome), label parsing or leakage. The case narrative is not cleared for blind prediction merely because the channel exists.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/oecd-ncp-specific-instance-acceptance/record.json](factory/candidates/oecd-ncp-specific-instance-acceptance/record.json) | 32,596 | `afc37a12e61fd1abb2d16a0fbe7147b17b2367c42474eb84cecb7fc0c20a60f9` |
| [evidence/http/oecd_feed.bin](evidence/http/oecd_feed.bin) | 13,814 | `1f2dd6f480fd07fa3c2613247d67a50aa600e1fa9feff7559ceeb7fd31078c4e` |

## Tier C — tw-typhoon-day-closure

**READY-TO-BUILD**

**Novelty — PASS, bounded; the corrected material differentiation holds.** I fetched the actual Git LFS objects from [kxykxyou/TyphoonDayoffPrediction](https://github.com/kxykxyou/TyphoonDayoffPrediction), commit `762df51b3968ae84167f4176806ab11dee4a7cef`, not just pointer files. `station_dayoff_neat.csv` has **87,669 rows, 10 columns, 3,366 county/date pairs, 153 dates (2001-07-30–2021-10-12)**. Every date has a positive somewhere. The modelling CSV has **51,458 rows, 47 columns, 25,909 nonmissing TmrDayoff values, 9,726 positives and 25,549 missing targets**. R code shifts to tomorrow’s closure using complete daily observations; the training notebook uses a random 80/20 split and references a feature-selected file absent from the captured tree.

The proposed task materially differs: **all county-days during land warnings**, including warning days with no closures; **county-wide full-day closure**, excluding district/partial-day positives; and **features published before 19:00 on D−1**, rather than full-day observations. Those differences, not a new split or scoring wrapper, support clearance. Drifting back to any closure on announcement-conditioned dates would invalidate it.

The record’s **1,056 positives** reproduces only with **keep-last** county/date deduplication. There are **174 county/date pairs with conflicting day_off labels**: keep-first yields **1,071**, any-positive **1,195**, all-positive **1,021**. This is an important qualification to its count, not proof its numerical claim is necessarily false. The record should name the reduction rule and acknowledge contradictory station-expanded labels. [Koyun/tw-typhoon](https://huggingface.co/datasets/Koyun/tw-typhoon) is another catalogue hit: its card has only **20 text input/output/title/summary/content examples**, not a released county-day closure panel.

**Licence — PASS.** [DGPA’s open-data declaration](https://www.dgpa.gov.tw/archive?uid=75) and [CWA’s declaration](https://www.cwa.gov.tw/V8/C/information.html) were directly readable and preserved; they permit copying/adaptation with source credit. Retain those exact grants and source attribution. The prior GitHub repo has no licence in its captured tree; it was used as audit evidence, not proposed as redistributable source data.

**Channel — PASS at bounded discovery level.** DGPA’s historical closure listing has downloadable records/attachments; CWA’s historical warning listing is public. Both own-source pages were fetched, and the prior project also demonstrates public row-level source assembly. This does not certify every historical attachment or warning API response.

### NOT COVERED

Reconstruction of the proposed 2001–2026 warning population, all bulletin issue timestamps and full-day label parsing; full download of the 20-example HF corpus; historical source gaps. The prior repository’s complete modelling run was not reproduced. Its missing licence/splits are not themselves arguments for exact-task novelty.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/tw-typhoon-day-closure/record.json](factory/candidates/tw-typhoon-day-closure/record.json) | 28,858 | `eba955e896e2169ad8c7d14c1303db721d258e984c192ae9b4df869dc101635e` |
| [evidence/http/dgpa_terms.bin](evidence/http/dgpa_terms.bin) | 38,492 | `e4bda004934e1e698ffaf6db24477daa75008a2f79c74663ec922fec0e757635` |
| [evidence/http/cwa_terms.bin](evidence/http/cwa_terms.bin) | 11,880 | `bc655c8bf05b1b9e98538168d2c9d241c97f3707d8209d5d7676ab55837968af` |
| [evidence/http/dgpa_channel.bin](evidence/http/dgpa_channel.bin) | 45,296 | `394ca95fd83f36e93a8fa9dea772512d13daf560d4d227a6d0753952aea78e34` |
| [evidence/http/cwa_channel.bin](evidence/http/cwa_channel.bin) | 15,742 | `084aa73edf34b663a880fd92f3b92610a2d9672acab18e27033a7365859b38d5` |
| [evidence/typhoon/lfs-content/station_dayoff_neat.csv](evidence/typhoon/lfs-content/station_dayoff_neat.csv) | 7,416,655 | `6415a8ad6347880fc0727c37a8fd958bd0b54a01f1a608b57c1fdae68e5fbcff` |
| [evidence/typhoon/lfs-content/data_ver_6_DCT.csv](evidence/typhoon/lfs-content/data_ver_6_DCT.csv) | 13,844,282 | `2614e79e91a020106c68c0515e19056999d52c5573eb59d5131a070bb74232fd` |
| [evidence/typhoon/dedup-check.json](evidence/typhoon/dedup-check.json) | 148 | `0f05106993e4596a6db1f6fa25dd1d75cc311763460ebc10d29d62e051e7e813` |

## Tier C — wto-dispute-panel-escalation

**FIX-THE-RECORD**

**Novelty — FIX-THE-RECORD.** The record dismisses public econometric releases as not ML-ready because they lack splits and a scored contract, and because some cannot be commercially redistributed. Neither reason satisfies the operator’s exact-task test. Usable data with predictors and outcomes count as prior art regardless of whether we may relicense them.

I downloaded the public [Sattler–Spilker–Bernauer data linked by ETH Zurich](https://ib.ethz.ch/research/data/2013.html): **SSB_Data.dta, 73,644 bytes, 331 rows, 19 columns**, plus its **37,434-byte tabular text export** (the ETH link calls the latter replication material, but its contents are data). It includes WTO dispute number, initiation date, complainant, defendant, sector/instrument covariates and a labeled **Panel ruling** outcome. It is already a model-usable research release, not merely a paper or aggregate chart. Its DTA SHA-256 is `d5c3c4a9b8908eaf3fac83782b1832ca73994e08af7df5a35c3843b57c68e799`; text SHA-256 `2c4836c0907a04f3a85b2be9897e9255d50ed01a88594f8abb68eaa8d8a91a4b`.

**I do not label it an exact duplicate:** a panel *ruling* differs from DSB *establishment*, and the prior has multiple complainant/dyad rows for some disputes. The candidate’s exact establishment endpoint may be differentiated. The corrected record must make that comparison, and resolve the closer establishment-stage fields in Horn–Mavroidis and other named releases, instead of relying on lack of splits. Exact-task non-novelty is **NOT VERIFIED**, so the verdict is FIX-THE-RECORD rather than NOT-NOVEL.

**Licence — PASS for the stated source scope.** The primary WTO portal JSON assigns **Attribution 4.0 International** to both disputedb and ds_db. [WTO’s own copyright terms](https://www.wto.org/english/info_e/copyrights_permissions_e.htm) distinguish unrestricted official documents from other publications requiring more limited reuse/permission. This supports structured case facts from the licensed DS datasets/unrestricted official documents, not wholesale relicensing of unrelated Secretariat prose. The candidate records WTO credit and the no-logo scope.

**Channel — PASS.** The official dates workbook downloaded successfully (**117,180 bytes; worksheet XML has 667 row elements**, not asserted to be 667 eligible disputes). The ds_db catalogue points to public case/document resources. The separate disputedb resource advertises internal `http://dsdb/`, which is not a usable public download and was not accepted as channel proof; the public XLSX and case pages supply that proof.

### NOT COVERED

Complete Horn–Mavroidis schemas/establishment labels, every relevant modelling supplement and exact eligibility-window equivalence; reconstructing all WTO case pages or reconciling the record’s older workbook counts with the current 667 worksheet rows; construction/scoring, late settlements and timing. No external request for permission or clarification was sent.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/wto-dispute-panel-escalation/record.json](factory/candidates/wto-dispute-panel-escalation/record.json) | 27,148 | `d0529381d6e4897a9086dcd6bbccc06e650886ef0cf39086cea6a55e7a035dc1` |
| [evidence/http/wto_catalogue.bin](evidence/http/wto_catalogue.bin) | 9,995 | `25aa459cde4e34394b9a53a3f41fb9008c6f4a6cd6054453cc8c35c43fb0500a` |
| [evidence/http/wto_documents.bin](evidence/http/wto_documents.bin) | 7,825 | `778f211f9531bdeefc3f916927a81b30120271045fae6cec7f273320ed56900b` |
| [evidence/http/wto_dates.bin](evidence/http/wto_dates.bin) | 117,180 | `9cb85ce6bba5dc4c56df58116c4f3030bdf0ddca340e2b730a0a5987d60bc10d` |
| [evidence/http/wto_prior_data.bin](evidence/http/wto_prior_data.bin) | 73,644 | `d5c3c4a9b8908eaf3fac83782b1832ca73994e08af7df5a35c3843b57c68e799` |

## Tier C — defra-avian-influenza-spillover

**READY-TO-BUILD**

**Novelty — PASS, bounded.** [Open Avian Flu Dataset, Zenodo 8246456](https://zenodo.org/records/8246456) is a relevant public event compilation including England; it is not verified as this aligned UK county-week future-spillover task. The [citizen-science study’s Dryad release](https://doi.org/10.5061/dryad.6hdr7sr8x) does not publicly supply the processed farm dataset needed for its task; its inputs/outcome differ. US county-month and European WAHIS studies likewise do not establish an exact source/task duplicate. New splits alone were not used as differentiation.

**Licence — PASS.** The [GOV.UK wild-bird publication](https://www.gov.uk/government/publications/avian-influenza-in-wild-birds) and [England case listing](https://www.gov.uk/animal-disease-cases-england?disease_type%5B%5D=bird-flu) carry OGL v3. Preserve Crown/Defra/APHA attribution and the OGL grant; any own-compilation dedication must remain separate.

**Channel — PASS.** An actual official 2026 week-44 CSV downloaded: **24,771 bytes, 310 physical lines**, with week, district, county, country, species, virus and positive counts. This is row-level surveillance data at its published aggregation, not just a national chart. The case listing is enumerable case-level HTML with opening dates and geographic titles. Together they provide the two event streams needed for a county/week task.

### NOT COVERED

All annual files, historical web-archive availability, full enumeration of case pages, county harmonisation, the candidate’s availability-keyed construction, label lead time or leakage. A full vintage ledger and operational publication timing remain construction/audit work.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/defra-avian-influenza-spillover/record.json](factory/candidates/defra-avian-influenza-spillover/record.json) | 20,447 | `b9c8ab38fbcfe89716ac1570c92500cae505b9386070f73f2c3e58a4d26d798c` |
| [evidence/http/defra_birds.bin](evidence/http/defra_birds.bin) | 202,374 | `371ea1421cfd132af294d834f594d4632f4d21eb33131814e79ac7adbc6fee29` |
| [evidence/http/defra_cases.bin](evidence/http/defra_cases.bin) | 166,666 | `5fc2d7afd21db31e4c4b3dabc8f1fd5415ce334676c9c23b82c0225b4e5b42e3` |
| [evidence/http/defra_sample.bin](evidence/http/defra_sample.bin) | 24,771 | `2da61a7e696fdcf4de0fca33a5d00c637524d35e53722461d8c87bc037731bef` |

## Tier C — my-rapidrail-od-exceedance

**READY-TO-BUILD**

**Novelty — PASS, bounded.** Source-specific web, Kaggle-targeted and Hugging Face searches found no exact daily station-pair exceedance release for Klang Valley Rapid Rail. SHMetro/HZMetro and SHMOD/HZMOD use different cities or regression contracts; descriptive Klang Valley transit dashboards do not establish an exact ready task.

**Licence — PASS.** [data.gov.my’s own dataset page](https://data.gov.my/data-catalogue/ridership_od_rapidrail_daily) embeds **CC BY 4.0**. The candidate’s licence record credits Prasarana/MOT through data.gov.my, identifies the derived product and scopes CC0 to its own contribution. Preserve the source grant and attribution on redistributed rows.

**Channel — PASS.** An anonymous **65,536-byte HTTP 206** prefix from the official 2024 annual CSV contains the actual **origin,destination,date,ridership** header and station-pair/day records. The primary catalogue provides CSV/Parquet annual editions. The general OpenAPI route’s lack of support does not block a working bulk storage channel.

### NOT COVERED

Complete annual files, origin/destination coverage and Putrajaya omissions, date-format drift across editions, publication-lag evidence, the 07:00 instant versus whole-day outcome, labels and panel self-answering. This is discovery-only clearance, not endorsement of an unbuilt forecast contract.

### Record freeze and evidence digests

| Object | Bytes | SHA-256 |
|---|---:|---|
| [factory/candidates/my-rapidrail-od-exceedance/record.json](factory/candidates/my-rapidrail-od-exceedance/record.json) | 25,825 | `ec77fe657e56125dee1b0da8966701d4cbf7a7e32b5045129f48256234bd3734` |
| [evidence/http/rapid_catalogue.bin](evidence/http/rapid_catalogue.bin) | 87,149 | `3d5bf50c8d34f4b153c8b58342ebecf79bd6fbf5a2657fab482dae461bdb6a46` |
| [evidence/http/rapid_sample.bin](evidence/http/rapid_sample.bin) | 65,536 | `25d31e1bedea6aa25256897e46b5617eefee229c91b8d2fd29214b798d57beab` |

## Final boundaries and signature

All four Tier A releases fail the operator’s publication standard. Honest exposure disclosures and reproduced model numbers do not waive demonstrated answer lookups or false artifact claims. No verdict here depends on a baseline beating persistence or on the runner enforcing a scoring protocol.

The accompanying machine-readable outputs are part of this report: every frozen probe and supervised lookup result, exact asset/package checks, baseline logs, source-reconstruction commands/receipts, primary-page fetches and novelty queries are retained. The audit makes no universal claim that an unbroken probe family proves safety. Failed network acquisition is marked NOT VERIFIED, not falsely described as a source-data contradiction.

**Signed:** Codex, independent artifact auditor (no publisher contact).  
**Date:** 2026-11-07 (UTC).  
**Local audit directory:** `/Users/earino/research/dataset_verification/flip-audit-2026-11-07`.
