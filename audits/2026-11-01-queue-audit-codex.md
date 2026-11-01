# Queue summary

- **ipo-trademark-registration-outcome — DO NOT PUBLISH** — False shipped OGL 3.0 same-licence requirement.
- **ns-bwa-advisory-lift-duration — DO NOT PUBLISH** — Shipped cumulative history recovers 196/372 eval and 286/884 holdout labels without error.
- **pins-planning-appeal-outcome — DO NOT PUBLISH** — False shipped OGL 3.0 same-licence requirement.
- **unhcr-refugee-data-finder — DO NOT PUBLISH** — Corrections verified; unchanged features still recover labels at eval AUC 0.975325 and holdout 0.983034.
- **ocha-fts-appeal-funding-trajectory — DO NOT PUBLISH** — Shipped country history recovers 120/139 eval and 128/182 holdout labels without error.
- **acnc-charity-ais-deadline-compliance — READY-TO-BUILD** — Readable per-year CC BY terms and actual AIS rows; no exact task release found.
- **austender-contract-amendment-occurrence — LICENCE-BLOCKED** — Current AusTender source terms could not be read; licensed historical archive does not clear the declared modern endpoint.
- **conagua-dam-drought-onset — READY-TO-BUILD** — SIH reservoir CSV rows exist; publisher resource states CC BY 4.0; no exact task release found.
- **eu-transparency-register-removal — READY-TO-BUILD** — Bulk organisation snapshots exist under the Commission reuse decision; no exact task release found.
- **jp-moe-pollen-exceedance — READY-TO-BUILD** — MOE publishes actual historical station-hour workbooks under readable reuse terms; no exact task release found.
- **ofsted-childrens-home-next-rating — READY-TO-BUILD** — Ofsted publishes provider-level inspection workbooks under OGL; no exact task release found.
- **tw-typhoon-day-closure — FIX-THE-RECORD** — Public county/day training data contradicts the no-dataset novelty claim; exact full-day target equivalence remains unverified.
- **za-cct-c3-service-request-surge — READY-TO-BUILD** — Public C3 notification rows and readable dataset-specific City terms; no exact surge task release found.
- **za-cct-substation-evening-peak-exceedance — READY-TO-BUILD** — Public half-hour substation rows and readable City terms; no exact evening-peak task release found.
- **za-municipal-audit-opinion — READY-TO-BUILD** — Treasury bulk municipality/year records and readable reuse terms; no exact task release found.
- **za-statsa-liquidations-exceedance — READY-TO-BUILD** — Public monthly series and readable no-sale reuse terms support a free attributed release; no exact task release found.


# Independent pre-publication audit — The Flip Queue

**Signed: Codex, independent auditor. Date: 1 November 2026 (Europe/Paris).**

All five constructed artifacts are **DO NOT PUBLISH under the operator's stated standard**. Nine buffer items pass the bounded pre-construction checks; one is licence-blocked and one needs its novelty record corrected before it can be cleared. READY-TO-BUILD is not approval of a future artifact.

FAIL below means an observed contradiction or demonstrated recovery. NOT VERIFIED means the evidence was unavailable or the check was not completed. The findings do not penalize a losing illustrative baseline, disclosed vintage limitations, or the absence of runtime isolation. Disclosing leakage makes the disclosure honest; it does not waive the operator's P0 prohibition.

## Scope and evidence custody

Read-only remote acquisition; no repository changes, publication, repairs, or publisher contact. Work products are confined to this local audit directory. Factory snapshot: `c1b9e94e294501ff408817b327f46041f0a9ca76`. The factory API reported that repository public; the four dataset repositories and Hub datasets inspected were private. This observation is not used as a dataset-quality failure.

The four supplied Tier A prompts were read and applied alongside the operator's stronger P0/P1 mandate. Tier B was tested from staging release **430443206**, tag **job-fts-appeal-002**. All 15 staging parts matched the acquisition manifest. GitHub release assets were checked before target-column reads; all four Hub main/tag revisions later matched the same five artifact files. No credential is included in the evidence files.

Attack code, plan, environment, source builders, reference code, prompts and supplied documents were frozen at **2026-11-01 20:54:54.897173 UTC**. All five sets of feature-only predictions were frozen at **20:55:41.878891 UTC**, before scoring any target column. Prediction construction explicitly excluded each target using `usecols`. No early target-column read or post-score change to the frozen attack was observed. Aggregate counts and published fixture claims were read before freezing, as permitted by the prompts.

Missing attack scores use **0.5**, fixed in advance. “Self” donors mean features from the scored split alone. “All” donors mean the concatenated train/eval/holdout feature tables, with all target columns excluded. Thus all-split eval recovery includes later holdout features; self-split results demonstrate that the exposure is not dependent on opening holdout labels. Coverage, errors and full-split AUC are reported separately. Train-label lookup/logistic controls are supervised controls, never described as label-blind recovery.

Environment: Python **3.13.1**, macOS **15.7.4 arm64**, pandas **2.3.3**, NumPy **2.5.4**, scikit-learn **1.9.1**, SciPy **1.18.1**, XGBoost **3.4.1**. Python 3.14.7 was used for acquisition/orchestration. Full package inventory is in `environment.json`.

| Frozen object | SHA-256 |
|---|---|
| [attack.py](attack.py) | `790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699` |
| [PLAN.md](PLAN.md) | `11abfd093103cd22f35d45f8937bf967b89c5e9e6a4d90f668094bdf13dda0fb` |
| [environment.json](environment.json) | `26db22e779954b736b459b1d32a7a63910af9fa1cd93d8a46426b9a35d113f21` |
| [code-freeze.json](code-freeze.json) | `64ed0f8c50f3e44ba7f91417254e37ee72050dc7d00816a989aa67aebd3bc891` |
| [prediction-freeze.json](prediction-freeze.json) | `aa9d494841dba4a45de5f82a8a04a1dd490b0d1cbd58834e1c11b98399100ec1` |


`code-freeze.json` records every object in the pre-label code freeze. `prediction-freeze.json` records every feature table, prediction archive and vector index in the pre-score prediction freeze. Post-score source/digest verification scripts are separate and are not represented as pre-label attack code. `EVIDENCE-SHA256SUMS` records the final evidence inventory; `FINAL-SEAL.json` seals the report and that inventory. These are local integrity records, not externally timestamped attestations.

The fixed battery covered numeric and lexical ranks, missingness, string length, the 300 most frequent feature-only tokens/bigrams per text column, row order, calendar/date differences, declared cross-row histories, and train-fitted single/pair lookup controls. It is a bounded battery, not an exhaustive proof that no encoding exists. Full vector-level results, including failed and weak attacks, remain in each `blind-results.json`. Novelty searches covered public web results, GitHub releases/code, indexed Kaggle/paper results, publisher exports and a direct Hugging Face catalogue pass. Search logs are retained. A negative search is not proof of universal novelty.


# 1. ipo-trademark-registration-outcome — DO NOT PUBLISH

Artifact SHA-256 identity: `2c1dade2913d0a8b643c89e628095a18e03223a6167beb9363316389486a544d`.

Frozen attack: `790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699`; this item’s prediction archive: `92fe77c52903dde7a37c974d644ee74cdae539d1caf1c3cb6e350483642b5e12`. Full [blind results](ipo-trademark-registration-outcome/blind-results.json), [integrity results](ipo-trademark-registration-outcome/integrity-results.json), [reference reproduction](ipo-trademark-registration-outcome/reference-reproduction.json).

GitHub main = tag: `74fbdddab6f279078177cec11d496665c75af0db`. Hub main = v2026.10: `8581baa19ac6d992be1b21b59e43fec59b36606e`. Both Hub revisions matched all five artifact files. [Destination evidence](ipo-trademark-registration-outcome/destination-verification.json).

**PASS — digest verification:**

| File | Bytes | SHA-256 |
|---|---:|---|
| train | 20,048,573 | `f4bb622df6e985ea3bd85d8e962a90022e029588bf56ae3a4d89721877a25a51` |
| eval | 18,142,219 | `54e06a89d7f565ba690f5abe0fd8cdce5a91c55aaa50738690f8efeee474c520` |
| holdout | 21,503,483 | `26cfc5a8a2131bac4d700ee4733a79eee6eae327dc7c6aa5ed93cf1a0589fa41` |
| meta.json | 1,993 | `caf2a4d916611470ca1f1535113acf179efa2ef71d497a88f4e79f2e5bcb1011` |
| quality.json | 41,854 | `efa5b4d3d9b68f07ba8cdffee484a9c6e51b80323851158786a01fdaef7d1bd6` |

| Split | Rows | Positives | Columns | Observed time range |
|---|---:|---:|---:|---|
| train | 106,990 | 92,668 | 57 | 2010-01-01 – 2012-12-31 |
| eval | 97,274 | 81,699 | 57 | 2013-01-01 – 2014-12-31 |
| holdout | 115,172 | 99,385 | 57 | 2015-01-01 – 2016-12-31 |

All three pairwise ID intersections are **0**; all split schemas equal meta; duplicate IDs within each split are **0**. The artifact digest is the gate’s SHA-256 over sorted `key:file_sha256` strings for train, eval, holdout, meta.json and quality.json, with no separator between strings. This is distinct from a ZIP digest.

### Findings

**FAIL — P0 false licence claim.** Shipped `LICENSE.md:32` says OGL 3.0 “applies the same-licence condition to adapted versions of the information.” The actual licence grants adaptation and redistribution subject to attribution and other stated conditions, but imposes no share-alike requirement; it expressly permits qualifying adapted information under CC BY 4.0 or ODC Attribution. The same incorrect sentence ships on the Hub. This is a false description of source rights, not a finding that IPO data cannot be redistributed. [Official OGL 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/), [IPO source explanation](https://www.gov.uk/government/publications/ipo-trade-mark-data-release/ipo-data-explained-2016).

**PASS — bounded leakage search, with limits.** No tested single-column/token/date/order score exceeded 0.95 in either direction. The strongest orientation-adjusted blind score was mark-text length: eval **0.5750946996**, holdout **0.5821063119**. Train-fitted single/pair rate tables did not recover labels near-perfectly; strongest eval pair was mark_type + nice_class_count, **0.5883376039**. Fixed logistic eval AUC was **0.5893006834**. These results do not establish absence of more sophisticated leakage.

**PASS — source and quantitative claims checked.** Rebuilt all three CSVs, meta and quality byte-for-byte from the publisher snapshot ZIP. There are **319,436** scored rows; no duplicate IDs or inter-split ID overlap; **0** discrepancies between nice_class_count and the sum of class indicators. The disclosed snapshot-vintage owner/class values do not establish historical filing-time observability. The unresolved-row exclusions and current-vintage limitations are stated in the package, so they are not independently treated as failures.

**PASS — baseline scale.** Reference eval AUCs: nice class **0.542050096312312**, mark type **0.5649860521366877**, owner country **0.5190639759221086**, calendar month **0.49717530762266227**, category **0.5030650964271485**, series **0.5212537612864133**; majority accuracy **0.8398852725291445**. Stock model reproduced **0.6223756038908591**, Brier **0.1317810945453579**. Eval 2013/2014 model AUCs **0.6232809840033328 / 0.6215952653953406**.

**Novelty:** no exact public UK IPO registration-outcome task release was located. Raw IPO bulk data is the source, not by itself evidence of an already constructed task.

### NOT COVERED

Independent historical owner/class vintages; exhaustive owner/series entity resolution; external trademark-register label lookups; exhaustive text encodings; model tuning; independent rerun of the quoted baseline-difference confidence intervals. Source reconstruction used the frozen shipped builder, not a second full parser. Negative novelty search is bounded.


# 2. ns-bwa-advisory-lift-duration — DO NOT PUBLISH

Artifact SHA-256 identity: `e8ed2a53eaf0453c8ed52aea336edb994d888ad11e7b76f7898b663f017180a8`.

Frozen attack: `790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699`; this item’s prediction archive: `4adc9bbc39cca51a6f4c9ad10b1cd0f5f936012ef066b01376341dce82e14508`. Full [blind results](ns-bwa-advisory-lift-duration/blind-results.json), [integrity results](ns-bwa-advisory-lift-duration/integrity-results.json), [reference reproduction](ns-bwa-advisory-lift-duration/reference-reproduction.json).

GitHub main = tag: `23952346eeadb4b25ac5887da0ff2ceae45d6293`. Hub main = v2026.10: `aaef14881a13e0ad4dafb525f133cd708e7b4801`. Both Hub revisions matched all five artifact files. [Destination evidence](ns-bwa-advisory-lift-duration/destination-verification.json).

**PASS — digest verification:**

| File | Bytes | SHA-256 |
|---|---:|---|
| train | 133,840 | `beacb2292ca0a045610662bd02ba85d89fde18b652e43d4ff44276979a3babc5` |
| eval | 50,575 | `ec1f733558558d4c30c2c50bf93408817d0936df4517c126a6d7965f02c5c5c5` |
| holdout | 121,058 | `78b62dd3bd5923f67c014010eede2e6f7c778bd0b79d4265c9f8ef4299328a37` |
| meta.json | 1,555 | `6b43e4eaf1020ba3436a91c1c2c926af7af0b03fd79104a01bd45d944737e260` |
| quality.json | 21,707 | `7a61f6fa1bd17f01804428b939ab7cf620cacbf066c95837f6d9166d7a78258e` |

| Split | Rows | Positives | Columns | Observed time range |
|---|---:|---:|---:|---|
| train | 1,069 | 715 | 19 | 2008-06-27 – 2017-12-27 |
| eval | 372 | 225 | 19 | 2018-01-02 – 2020-12-17 |
| holdout | 884 | 514 | 19 | 2021-01-04 – 2024-12-27 |

All three pairwise ID intersections are **0**; all split schemas equal meta; duplicate IDs within each split are **0**. The artifact digest is the gate’s SHA-256 over sorted `key:file_sha256` strings for train, eval, holdout, meta.json and quality.json, with no separator between strings. This is distinct from a ZIP digest.

### Findings

**FAIL — P0 label recovery.** For consecutive observations of the same site, multiply resolved counts by the rounded lift-within-30-days rate to recover integer cumulative positive counts. When the fixed eligibility checks isolate one new advisory and one new resolution, subtraction reveals its label. The rule and all predictions were frozen before labels. It yields:

| Donors → scored split | Recovered | Errors | Covered AUC | Full-split AUC |
|---|---:|---:|---:|---:|
| Eval → eval | 81 / 372 | 0 | 1.0 | 0.6845956160241875 |
| All features → eval | 196 / 372 | 0 | 1.0 | 0.883673469387755 |
| Holdout → holdout | 286 / 884 | 0 | 1.0 | 0.767167946156273 |

This is substantial exact partial recovery, not a claim of perfect full-split classification. The declared reverse-history exposure is real, but the count-arithmetic recovery is stronger than the disclosed simple **56 eval / 217 holdout** exposure. Disclosed non-enforcement is honest and is not the reason for failure.

**PASS — data truth.** All five files rebuild exactly from the public register. No duplicate IDs or inter-split ID overlap. No tested isolated column achieved an orientation-adjusted AUC above 0.95. The highest was **0.6565079365** on eval and **0.6318014513** on holdout.

**PASS — reference figures.** Site persistence AUC **0.6124414210128496**, Brier **0.2818656910340113**, coverage **231/372**; calendar/identity **0.5074981103552532**, Brier **0.3100867628398012**; reason **0.4306575963718821**, Brier **0.24404174663204806**. Majority accuracy **0.6048387096774194**. Stock model **0.5086167800453515**, Brier **0.36088131466884615**. Model per-year AUCs for 2018/2019/2020: **0.5553977272727273 / 0.5018055555555555 / 0.48861283643892345**. The weak model is not a defect.

**Licence/novelty:** source licence v1.1 permits use, adaptation and distribution with attribution; the package preserves source ownership. No exact pre-existing lift-within-30-days task release was located. [Nova Scotia source licence](https://support.novascotia.ca/services/open-data-portal-licence).

**FAIL — supplied prompt inventory, not an additional shipped-claim finding:** the prompt says the repository ships `MANIFEST.json`; the inspected repository does not. `SHA256SUMS`, qualification and all five bytes were available and verified. This discrepancy is not the basis of the publication verdict.

### NOT COVERED

Archived issue-time register vintages; exhaustive county-wide inverse systems; reconstruction with a second parser; independent rerun of the quoted site-cluster confidence intervals; universal novelty. Partial recovery is reported only for covered rows.


# 3. pins-planning-appeal-outcome — DO NOT PUBLISH

Artifact SHA-256 identity: `c861bd8f4acd9bbe267bdb58e1168996fdb359c540aaf4030030a632d693c527`.

Frozen attack: `790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699`; this item’s prediction archive: `ad63101c20994445175efecdd94a71370797e4700902ff7c74b7468c11837045`. Full [blind results](pins-planning-appeal-outcome/blind-results.json), [integrity results](pins-planning-appeal-outcome/integrity-results.json), [reference reproduction](pins-planning-appeal-outcome/reference-reproduction.json).

GitHub main = tag: `a19978bdaa067768bd6df6185a9d6b7faf4e2ae3`. Hub main = v2026.10: `9628b108011a083fbcde2fd5426cf74534d58a6a`. Both Hub revisions matched all five artifact files. [Destination evidence](pins-planning-appeal-outcome/destination-verification.json).

**PASS — digest verification:**

| File | Bytes | SHA-256 |
|---|---:|---|
| train | 14,799,462 | `299e5af47610af833bec33e15e8a5d8a242f6edebfd401388714b819593c2f65` |
| eval | 7,688,640 | `2ab9271f70c74f857f0c1a7b696fa299427754a5fb0167a7ee6ab11480dd6e72` |
| holdout | 14,976,119 | `3f65dc801e0819bd6e828a101065deb7cfc68b764db339a08b2442deddc6fc96` |
| meta.json | 2,518 | `4e7a31048bb77372cbc42bcf3f8a341e2eeeed0afdce920fb678164f2f6c76b2` |
| quality.json | 44,632 | `9203accc06369f3d2468b8740ac84c293d5e1222907d2daa1d7bb486b437ae33` |

| Split | Rows | Positives | Columns | Observed time range |
|---|---:|---:|---:|---|
| train | 54,834 | 17,048 | 32 | 2012-06-01 – 2019-12-31 |
| eval | 28,104 | 8,469 | 32 | 2020-01-01 – 2021-12-31 |
| holdout | 56,326 | 17,705 | 32 | 2022-01-01 – 2026-08-21 |

All three pairwise ID intersections are **0**; all split schemas equal meta; duplicate IDs within each split are **0**. The artifact digest is the gate’s SHA-256 over sorted `key:file_sha256` strings for train, eval, holdout, meta.json and quality.json, with no separator between strings. This is distinct from a ZIP digest.

### Findings

**FAIL — P0 false licence claim.** Shipped `LICENSE.md:35–36` attributes a same-licence requirement for adaptations to OGL 3.0. That requirement does not exist in the source licence. The incorrect description also ships on the Hub. This blocks publication under the operator's false-claims standard. [Official OGL 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/), [PINS source publication](https://www.gov.uk/government/publications/planning-inspectorate-appeals-database).

**PASS / bounded leakage result.** No tested single-column/token/date/order score exceeded 0.95 in either direction. Best orientation-adjusted blind score: eval **0.5726527728**, holdout **0.5608252409**. All-feature reverse-LPA-history full AUC was about **0.50857 / 0.50848**. A fixed 730-day homogeneous-history heuristic recovered **16 eval rows without error**, but only **13 holdout rows with 1 error**; the 365-day version covered **82 eval rows with 1 error**, **136 holdout rows with 3 errors**. Those tiny, imperfect heuristic subsets do not establish the deterministic widespread recovery found in NS/UNHCR/OCHA. They remain in the evidence rather than being promoted to a leakage failure.

**PASS — reconstruction and counts.** Both source workbooks rebuilt the three CSVs, meta and quality exactly, using the shipped categorical probe evidence. **139,264** rows, 32 columns, no duplicate IDs or inter-split ID overlap. The reference per-year eval counts match: 2020 **13,797 / 4,126 positives**; 2021 **14,307 / 4,343 positives**. The decided-cases-only sample and unverified split-label timing are disclosed limitations.

**PASS — references.** Procedure/type AUC **0.55506072071053**, Brier **0.2079902264250544**; LPA rate **0.5414410163425604**, Brier **0.21071114833737709**; persistence **0.504458138089444**, Brier **0.4149943068602334**. Calendar control equals LPA rate exactly. Majority accuracy **0.6986549957301452**. Stock model AUC **0.6108490008783813**, Brier **0.20416048213388854**; 2020/2021 AUCs **0.6180342602700089 / 0.6038742350657162**.

**Novelty:** public PINS datasets, dashboards and decision-letter search products were found, but no freely usable release of this exact validation-time structured binary task was established. This is a bounded negative finding.

### NOT COVERED

The optional train-fitted single/pair control run failed when the fixed logistic encoder encountered mixed integer/string categories; its in-memory pair results were not retained, so those results are NOT VERIFIED. The frozen attack was not repaired after scoring. The stock model did reproduce. No independent categorical availability probe, second source parser, historical validation-time snapshots, exhaustive latent decision-date reconstruction, or independent LPA-cluster bootstrap rerun was completed.


# 4. unhcr-refugee-data-finder — DO NOT PUBLISH

Artifact SHA-256 identity: `6bd0c307d15d750085a77d4d6e131f3ab9d84b6485ba267ac23415620c9f55c2`.

Frozen attack: `790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699`; this item’s prediction archive: `e33aea0d8639a44b2a0652d7d024d6ac463e3c35dd47a5573e42e551a554c0c5`. Full [blind results](unhcr-refugee-data-finder/blind-results.json), [integrity results](unhcr-refugee-data-finder/integrity-results.json), [reference reproduction](unhcr-refugee-data-finder/reference-reproduction.json).

GitHub main = tag: `ac57a69d4973bf7a64c4fecccba34871560708e5`. Hub main = v2026.10: `77aa1fad752b84063b92c209e449c8c382e6827f`. Both Hub revisions matched all five artifact files. [Destination evidence](unhcr-refugee-data-finder/destination-verification.json).

**PASS — digest verification:**

| File | Bytes | SHA-256 |
|---|---:|---|
| train | 343,359 | `c7ebd552f1158bd5f470c495b027c48fc17ea9195c34185a662a8620407bd167` |
| eval | 195,252 | `4b7f06c3afd9eec286652383d95797a5fbaccc3517e68b2c334c615026bc9393` |
| holdout | 202,783 | `54decaaaf74eac1ea362bf1acf711010069b1feb94ad2abfcb70a1fccff858bd` |
| meta.json | 1,404 | `6620bdc91fdbc71b2d3fad6fb879076243e6f697d5e51d5c700a0c881c0c515c` |
| quality.json | 19,904 | `df419622d98ef2c8d084cb8c62a039c405069ee5e5dd4006f9937ad51929ff06` |

| Split | Rows | Positives | Columns | Observed time range |
|---|---:|---:|---:|---|
| train | 3,363 | 283 | 16 | 2002-12-31 – 2016-12-31 |
| eval | 1,887 | 165 | 16 | 2017-12-31 – 2021-12-31 |
| holdout | 1,962 | 227 | 16 | 2022-12-31 – 2025-12-31 |

All three pairwise ID intersections are **0**; all split schemas equal meta; duplicate IDs within each split are **0**. The artifact digest is the gate’s SHA-256 over sorted `key:file_sha256` strings for train, eval, holdout, meta.json and quality.json, with no separator between strings. This is distinct from a ZIP digest.

### Findings

**PASS — corrections are real.** Rebuilt exclusions are **377 missing-history**: train **314 = 192 panel-start + 122 other missing-prior**, eval **31**, holdout **32**. Host-silent targets are **21/7/5**, separately censored; **496** live-edge rows are separately excluded. All **7,212** target_date values are December 31 of the label year. The inventory and runner input handling agree on **14** inputs. Shipped train label years are **2002–2016**. Reviewed README, Hub card, release notes, verification, metadata, quality and builder distinguish an isolation requirement from enforcement by the runner. Remaining references to enforced isolation are hypothetical conditions or warnings, not assertions that the shipped runner supplies it.

The builder reproduces all three CSVs and corrected meta exactly. Rebuilt quality differs only in the recorded fetch elapsed time (**3.6 → 2.9 seconds**); corrected semantic strings remain intact. Thus correcting the framing did not change the vulnerable data, as disclosed.

**FAIL — P0 recovery persists.** Join on `(origin, asylum)` from target year T to T+1: the successor's `surged_recently` exposes the prior row's label. The fixed missing-successor rule and count recovery produce:

| Frozen rule / donor scope | Eval recovered / errors / full AUC | Holdout recovered / errors / full AUC |
|---|---|---|
| Successor flag, self | 1,265 / 0 / 0.943326998205047 | 1,239 / 0 / 0.9769934872856074 |
| Missing-successor rule, self | 1,584 / 0 / 0.9753246753246754 | 1,422 / 0 / 0.9830339346697305 |
| Missing-successor rule, all | 1,887 / 1 / 0.996969696969697 | 1,422 / 0 / 0.9830339346697305 |
| Next-year apps_d / two-years-later apps_d1, all | 1,625 / 0 / 0.9995407031992398 | 1,259 / 0 / 0.9776536454696645 |

The all-split missing-successor error is **AFG–TJK–2021**. Published rounded recovery figures reproduce. Disclosure is honest; the operator's automatic prohibition still applies.

**PASS — reference claims.** Stock AUC **0.5393499454475063**, Brier **0.08509893581155778**; momentum **0.574165**, surge flag **0.585619**, calendar **0.540927**, majority accuracy **0.9125596184419714**. Reproduced 1,000-resample paired row-bootstrap model-minus-reference intervals: momentum **−0.034815 [−0.105633, 0.040850]**; surge flag **−0.046269 [−0.110322, 0.014362]**; calendar **−0.001577 [−0.059444, 0.058719]**; recent constant **0.039350 [−0.004657, 0.085904]**. All include zero, as claimed.

**Licence/novelty:** the source HDX package identifies CC BY-IGO and the release preserves that posture rather than relicensing UNHCR data. Existing public UNHCR ML-ready population mirrors are not this government-procedure application-doubling task; exact task duplication was not established. [HDX source package](https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8), [nearby population mirror](https://huggingface.co/datasets/electricsheepafrica/unhcr-refugees-asylum-seekers).

### NOT COVERED

Historical publication vintages and operational forecast availability; a second complete source parser; exhaustive higher-order joins or external sources; universal novelty. No assertion that honest illustrative framing makes unrestricted scores valid.


# 5. ocha-fts-appeal-funding-trajectory — DO NOT PUBLISH

Artifact SHA-256 identity: `e7441e1fd868522d1fae1d5d2efca3733ca47c85f8cd612402f89b445c9e9a63`.

Frozen attack: `790213a0a9e07688c4c38235e50ac3f013699fa7ee6028cf61ade719ce24b699`; this item’s prediction archive: `bec93875fb1f40e104daf635b0090c67e4d9aa3f8118ecfe9da7350af3359d23`. Full [blind results](ocha-fts-appeal-funding-trajectory/blind-results.json), [integrity results](ocha-fts-appeal-funding-trajectory/integrity-results.json), [reference reproduction](ocha-fts-appeal-funding-trajectory/reference-reproduction.json).

**PASS — digest verification:**

| File | Bytes | SHA-256 |
|---|---:|---|
| train | 35,621 | `eb0c4dcab27b4e8cd872a26cc711a745952208fd600f3c786f357e9efcda591a` |
| eval | 11,268 | `b40bd9c6dc2cd5b2eeeee61c03aa7a7a191a55faae60aa4a4b772e8be13f8506` |
| holdout | 15,419 | `0819c3f146e663d3854105ee4b9de8a975a5d8b76a9e596410a3d26671a40499` |
| meta.json | 1,775 | `bc3d4b89be7ae1500cae0d724cc04f9d384c84c9c05d89d0e2043aa42a4b1114` |
| quality.json | 25,882 | `32c341f73bf891b99de456acdfaec55eea58f6fa79d82bee9f3761a468e13cb0` |

| Split | Rows | Positives | Columns | Observed time range |
|---|---:|---:|---:|---|
| train | 437 | 279 | 12 | 2000 – 2016 |
| eval | 139 | 81 | 12 | 2017 – 2020 |
| holdout | 182 | 96 | 12 | 2021 – 2025 |

All three pairwise ID intersections are **0**; all split schemas equal meta; duplicate IDs within each split are **0**. The artifact digest is the gate’s SHA-256 over sorted `key:file_sha256` strings for train, eval, holdout, meta.json and quality.json, with no separator between strings. This is distinct from a ZIP digest.

### Findings

**FAIL — P0 label recovery before staging.** A later appeal's country history contains cumulative prior appeal counts, covered rates and a last-prior outcome. Recover integer positive counts by count × rounded rate; subtract histories where the fixed rule isolates one appeal or a homogeneous same-year set. Combine with the declared last-prior tie rule. No label column was used to construct these predictions.

| Donors → scored split | Recovered | Errors | Covered AUC | Full-split AUC |
|---|---:|---:|---:|---:|
| Eval → eval | 84 / 139 | 0 | 1.0 | 0.9197530864197531 |
| All features → eval | 120 / 139 | 0 | 1.0 | 0.9948914431673053 |
| Holdout → holdout | 128 / 182 | 0 | 1.0 | 0.9573643410852714 |

A green gate 1.5.0 report with `failed_checks=[]` therefore does not establish that this artifact is safe under the operator's leakage standard. The disclosed illustrative framing is not itself false.

**PASS — artifact and cached provenance arithmetic.** Five-file artifact identity agrees with qualification; **758** total rows. Independently recomputed every label as `2 × appeal-linked funding >= original requirements` from the staged compact source caches: **0/758 label discrepancies**, **0 original-requirement discrepancies**, **0 country discrepancies**, **0 non-single-country rows**. Flow totals differ from the enumerator CSV on **37/758** rows, matching the disclosed count. This validates internal provenance consistency, not the truth of an unretained API response.

**PASS — reference figures.** Persistence **0.7171136653895275**; prior mean **0.7143465304384845**; original-ask reference **0.7126436781609196**; country rate **0.6729459344401874**; plan type **0.669220945083014**; majority accuracy **0.5827338129496403**. Fixed independent logistic eval AUC **0.7879948914431671**. No isolated feature reached 0.95; original requirements alone reached **0.7705406555981269** on eval. Better model fitting does not cure direct recovery.

**Licence/novelty:** FTS permits republication with FTS attribution, access date and source URL; the HDX enumerator carries CC BY-IGO, which must remain attached to that input. A public ML-ready Lake Chad appeal table exists, but uses revised requirements/current funding rather than this original-launch-requirement 50% target. Exact duplication of the candidate was not established. [FTS reuse terms](https://fts.unocha.org/content/about-fts-using-fts-data), [nearby ML-ready appeal table](https://huggingface.co/datasets/electricsheepafrica/africa-lake-chad-basin-fts-appeal-data).

### NOT COVERED

Full independent API re-harvest, historical launch vintages, and verification against original raw API response bodies (not retained by the builder). An attempted cached builder replay was stopped when its plan-resume lookup began re-fetching; it is not counted as a successful source rebuild. No GitHub/Hub public-destination consistency check is applicable yet. Formal staged audit remains necessary if any later artifact is proposed; this artifact already fails P0.


# 6. acnc-charity-ais-deadline-compliance — READY-TO-BUILD

Candidate record snapshot SHA-256: `8d77f7725f9ad91288cc124c79d8788934009190d5dd9910207f9a2b133c8a86`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `acnc_sample` SHA-256: `c98c8f0fb9f28db52e7fc78c9d1b81379303919c6a41568e1a9adca395e4dc7f`. [Response and acquisition details](evidence/web/acnc_sample.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel/licence.** Directly read 65,536 bytes of the 2024 AIS CSV (HTTP 206; total **38,089,052 bytes**). The header contains ABN, AIS due date and date AIS received, alongside charity attributes. Publisher metadata confirms **CC BY 3.0 Australia for 2023–2024**, **CC BY 2.5 Australia for 2019–2022**; retain each input's own licence and ACNC attribution. [2024 publisher dataset](https://data.gov.au/data/dataset/276ec1bc-4971-461c-88bc-be9f3c99a0f8).

**PASS — bounded novelty.** No ready-made prior-year-to-next-deadline compliance task was located. Hugging Face returns `National-Digital/acnc-register`; that is a relevant raw-register mirror to acknowledge, not evidence here of this AIS deadline task. Its card was inaccessible through the web reader, so detailed equivalence to its contents is NOT VERIFIED.

### NOT COVERED

Full annual-file parsing, non-filer truth, withholding/group-reporting effects, temporal availability, future artifact leakage and every historical licence variant beyond the stated checked years. These are outside the three pre-construction gates.

# 7. austender-contract-amendment-occurrence — LICENCE-BLOCKED

Candidate record snapshot SHA-256: `ebfd0d0972f1c738c44ca462ae66c0a55236f66f8430b98c9d48a9413dc92405`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `aus_data_sample` SHA-256: `d0a810f33e730bdc04c3cfb51dd28362f0bca10656d300873e8f63f750f439ed`. [Response and acquisition details](evidence/web/aus_data_sample.json). This hashes the captured sample/file, not an unfetched whole dataset.

**NOT VERIFIED — current-source licence, blocking under the user's rule.** The declared current report endpoint depends on AusTender terms at `/infolinks/termsofuse`. Direct requests and the web reader returned access errors/403; no readable primary copy of those current terms was obtained. Third-party paraphrases were not accepted as source permission. This is **not** an assertion that AusTender prohibits reuse. [Current terms endpoint](https://www.tenders.gov.au/infolinks/termsofuse).

**PASS — historical channel and its separate licence.** Department of Finance's official historical dataset metadata was readable and carries CC BY 3.0 Australia. A 65,536-byte range of the **30,999,835-byte** FY2017–18 CSV contains original/amendment notice types, parent IDs, publication/amendment dates and values. That is genuine row-level data. It does not automatically establish the current endpoint's terms or support the declared modern windows. [Official historical archive](https://data.gov.au/data/dataset/historical-australian-government-contract-data).

**Novelty:** no exact first-amendment-within-12-months ML task release was found. Public notice exports and procurement-analysis products exist; those alone do not prove exact task duplication.

### NOT COVERED

Current bulk report bytes, current source licence text, exhaustive historical archive, model construction or label availability. This candidate is not cleared as currently recorded. A source restricted to the readable licensed historical archive would be a separately reviewable scope, not an assumed repair.

# 8. conagua-dam-drought-onset — READY-TO-BUILD

Candidate record snapshot SHA-256: `15362d11f34d1ac687b472ec6998c5d23e3732939e0cd90ee3c2eb1cdc9223ff`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `conagua_data` SHA-256: `d07954694e41a56b4037db3c2890dc305f0b256e8a15d6d089fab88799fa2fed`. [Response and acquisition details](evidence/web/conagua_data.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** Downloaded the public SIH CCHNL reservoir CSV: **1,197,414 bytes**, **31,195 daily rows**, dates **1938-12-01 through 2026-10-31**; **12,088** rows have nonempty stored-volume values. This is a reservoir time series, not merely a map or national summary. [SIH source CSV](https://sih.conagua.gob.mx/basedatos/Presas/CCHNL.csv).

**PASS — readable source licence.** The publisher's resource page, read through the web tool's extracted primary-page text, names **CC BY 4.0**. Direct HTTP access to that landing page was blocked, but the licence text on the primary-page result was readable. Preserve CONAGUA attribution and source/access information. [Publisher resource licence](https://www.datos.gob.mx/dataset/estaciones_sistema_informacion_hidrologica/resource/35e8d001-6195-45c7-9a1c-58a8594fb3a1).

**PASS — bounded novelty.** Hidro-MX v2026.06 is relevant nearby prior art: hydrometric/climate data, not the candidate's dam-storage drought-onset formulation. No exact released task was located. [Hidro-MX](https://zenodo.org/records/21231601).

### NOT COVERED

All 210 reservoirs, capacity metadata/PDF joins, volume unit consistency across stations, drought thresholds, source revision history, and eventual leakage. The sample establishes the public channel, not full build fitness.

# 9. eu-transparency-register-removal — READY-TO-BUILD

Candidate record snapshot SHA-256: `bd2b22a449e48923f9980165faa652b6cf774af0d0ff38b6d5d6090a6abc8496`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `eu_sample` SHA-256: `a84c6fd8fbe460eca7c413f4154253096248bbc54e69730504e3321ba825bec7`. [Response and acquisition details](evidence/web/eu_sample.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** Publisher API returned **49 distributions**. A live organisation XML download returned HTTP 200 with filename `ODP_31-10-2026.xml`, declared length **117,860,497 bytes**; the first **65,536 bytes** were inspected and preserved. Historical snapshot links are also present. [Publisher dataset metadata](https://data.europa.eu/api/hub/search/datasets/transparency-register), [current bulk XML](https://transparency-register.europa.eu/odplastorganisationxml_en).

**PASS — licence.** Distribution metadata consistently points to Commission Decision **2011/833/EU**. Its Articles 4/6 permit reuse without an individual application, subject to source acknowledgement and no misleading meaning/endorsement. Preserve this instrument rather than silently substituting a dataset-wide CC licence. [Authoritative decision](https://eur-lex.europa.eu/legal-content/en/TXT/?uri=CELEX%3A32011D0833).

**PASS — bounded novelty.** Register mirrors, LobbyFacts and lobbying-meeting datasets exist. No released snapshot-to-removal prediction task was identified.

### NOT COVERED

Complete XML parsing, all historical snapshot downloads, identity continuity across register redesigns, removal-versus-renaming truth, and future leakage. Removal mechanism is not inferred merely from a missing row in this audit.

# 10. jp-moe-pollen-exceedance — READY-TO-BUILD

Candidate record snapshot SHA-256: `6485959b6fa8a838d653fb32b54dbac2f7e0f2be7d1053ad907e48ab825f8c97`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `pollen_data_sheet` SHA-256: `a9216dd426e3c8ec19f4898b5f56a62ad7f055fdcc172a1d3ce1b2add43ae502`. [Response and acquisition details](evidence/web/pollen_data_sheet.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** MOE archive HTML contains **223 spreadsheet links**. Downloaded and inspected a genuine XLSX, **116,068 bytes**, hourly sheet `時別`, used range **A1:K3626**. This is historical measurement data, not only a pollen map. [MOE archive](https://www.env.go.jp/page_00209.html).

**PASS — licence.** MOE's readable reuse page applies **Public Data Licence 1.0**, with attribution and notice of processing/changes. Carry MOE/source provenance and any applicable third-party exceptions. [MOE terms](https://www.env.go.jp/mail.html).

**PASS — bounded novelty.** A public Hanako scraper exists, but the inspected code retrieves readings rather than publishing this next-day exceedance task. No exact ML-ready task was found. [Hanako scraper](https://gist.github.com/mursts/2156713).

### NOT COVERED

Full 113-file pollen archive, legacy BIFF layouts, station-specific censoring, daily aggregation, archived weather inputs and predictive-time observability. One workbook sample is not verification of all claimed station/seasons.

# 11. ofsted-childrens-home-next-rating — READY-TO-BUILD

Candidate record snapshot SHA-256: `253deb175e03c1531b667d9de958a89f3453d60bd441bb254fe56afd953e0eca`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `ofsted_data_sheet` SHA-256: `444cfe1300d3bcf950bcdbc1cd7e1f01d803b899e3425accc574a31fbd36fd2e`. [Response and acquisition details](evidence/web/ofsted_data_sheet.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** Downloaded the current underlying-data ODS **3,271,438 bytes**. Its XML contains provider-level sheets `Provider_level_at_31_Mar_2026` (**6,709 XML row elements**) and `Provider_level_in_year_2025–26` (**6,180 row elements**), alongside aggregate time-series sheets. These are raw XML row-element counts, including headings/notes, not claimed counts of eligible children's homes. [Ofsted release and underlying data](https://www.gov.uk/government/statistics/childrens-social-care-in-england-2026).

**PASS — licence.** Official publication is under OGL 3.0; retain Ofsted/Crown attribution and source terms. OGL does not require adaptations to use the same licence. [OGL 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

**PASS — bounded novelty.** Inspection analyses and school-rating work are nearby; no usable public release of this exact children's-home next-rating task was located.

### NOT COVERED

Full longitudinal linkage, inspection-selection bias, whether all desired prior ratings can be reconstructed, historical vintages, task labels and model leakage.

# 12. tw-typhoon-day-closure — FIX-THE-RECORD

Candidate record snapshot SHA-256: `8352e69572ab424b751ce3e8b7bb15b6566e4d34db371623c2807ccc35186af2`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

**FAIL — novelty record's factual premise.** The record says predictor demos ship no dataset. The public `kxykxyou/TyphoonDayoffPrediction` repository ships usable county/day and township/day weather-plus-closure CSVs, a binary `TmrDayoff` field, and classifier-training notebooks. Its README explicitly identifies the same **DGPA uid=374 archive** and **CWB/CWA typhoon warning database**. This is materially closer than an app-only demo. [Prior repository](https://github.com/kxykxyou/TyphoonDayoffPrediction).

Downloaded county table `data_ver_6_DC.csv`: **1,298,259 bytes**, **3,573 rows**, **46 columns** including saved index; `TmrDayoff` values **1,102 zero / 725 one / 1,746 NA**. SHA-256 **`2c703863447cacf595bb9c4121118e225f03422c7687e29a726172cd09718a1a`**. Township table: **13,844,282 bytes**, **51,458 rows**, **47 columns**, **22 counties**, observation dates **2001-07-30..2021-10-12**; SHA-256 **`2614e79e91a020106c68c0515e19056999d52c5573eb59d5131a070bb74232fd`**. The notebook explicitly separates `TmrDayoff` from X and splits training/test rows. [County table](https://github.com/kxykxyou/TyphoonDayoffPrediction/blob/master/data/station_observation/data_ver_6_DC.csv), [training notebook](https://github.com/kxykxyou/TyphoonDayoffPrediction/blob/master/DCT_model_training.ipynb).

**NOT VERIFIED — exact target equivalence.** The candidate specifically requires county-wide full-day closure, excludes district/half-day positives, and fixes a prior-evening cutoff. I did not establish that the older release implements exactly those rules. Consequently the defensible verdict is **FIX-THE-RECORD**, not an unsupported definitive NOT-NOVEL. It is not READY-TO-BUILD: the prior-art comparison must confront actual released training data, not claim none exists.

**PASS — source licence/channel at bounded scope.** DGPA's official declaration and CWA reuse page permit reuse with attribution. The DGPA archive exposes individual county-status announcements, and the prior repository independently demonstrates machine-readable extraction is possible. [DGPA reuse declaration](https://www.dgpa.gov.tw/archive?uid=75), [CWA terms](https://www.cwa.gov.tw/V8/C/information.html), [DGPA archive](https://www.dgpa.gov.tw/informationlist?uid=374).

### NOT COVERED

Exact full-day/partial-day equivalence to prior art; a fresh complete DGPA census; bulletin timestamp reconstruction; current archive extraction reliability; candidate labels or predictive-time validity. Direct urllib DGPA retrieval encountered a certificate error; primary pages were read through the web tool.

# 13. za-cct-c3-service-request-surge — READY-TO-BUILD

Candidate record snapshot SHA-256: `0d4cbd53464af25469fa696cf5fdebef35687075caf1e0673aa9ecb3670cd030`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `cct_c3_sample` SHA-256: `d753679993344825a9d546ccc622b6714d6da7fb4cbc32d2a52e4db74cad6124`. [Response and acquisition details](evidence/web/cct_c3_sample.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** ArcGIS service returned **4,512,958 records** and three actual notification records through the public REST query. The item describes the complete SAP C3 notification table from January 2023 onward. The changed count from the older candidate record is a live-source observation, not evidence that the historical count was false. [Publisher dataset item](https://www.arcgis.com/home/item.html?id=da3b6d46845e4671bde500e8de7e1d3e).

**PASS — licence, with named interpretation.** Read the dataset-linked Open Data terms and Council policy **27781**, approved **3 December 2020**. The policy permits use, sharing and building upon open data; the dataset-specific terms supply disclaimers. The general City website restriction is different. My interpretation is that the expressly linked portal instrument governs these rows. Preserve the **custom City terms**, attribution and disclaimers; use **NOASSERTION** for a standard SPDX licence rather than inventing CC terms. [Open Data terms](https://www.capetown.gov.za/general/city-of-cape-town-open-data-terms-of-use/), [Council policy](https://www.capetown.gov.za/media/vg2plaql/open_data_policy.pdf).

**PASS — bounded novelty.** The City's own data-science challenge uses service requests, but is not evidence of an already released exact weekly surge target. No such task release was located. [City challenge](https://github.com/cityofcapetown/ds_code_challenge).

### NOT COVERED

All-record pagination, eventual weekly/category aggregation, timestamp revisions, topic coding, target construction and leakage. No publisher legal clarification was requested or assumed.

# 14. za-cct-substation-evening-peak-exceedance — READY-TO-BUILD

Candidate record snapshot SHA-256: `974295a9e151dc8823e0d3a54ebdcbf2ac7c4787b8f9f7d99c56a7d6c326af93`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `cct_sub_sample` SHA-256: `cc00155fc6d4de3b61394e07f66460d9d99df9fc2dfd8f73bf7a3a5ac8f9e990`. [Response and acquisition details](evidence/web/cct_sub_sample.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** Public ArcGIS service returned **52,608 rows** and three actual sample records with timestamped wide substation load measurements. This supports a half-hour load-series build, rather than a claim based only on a dashboard. [Publisher dataset item](https://www.arcgis.com/home/item.html?id=bebf20c25bfa4ffaa7fc07a1a94ba287).

**PASS — licence.** The item's licenceInfo links the same City Open Data terms, read with Council policy 27781. Dataset-specific terms support redistribution; the general website restriction is not silently used as a licence for data. Preserve City attribution, original terms and disclaimers; standard-licence identifier remains **NOASSERTION**, not a claimed CC licence. [Portal terms](https://www.capetown.gov.za/general/city-of-cape-town-open-data-terms-of-use/), [Council policy](https://www.capetown.gov.za/media/vg2plaql/open_data_policy.pdf).

**PASS — bounded novelty.** Grid-resource catalogues and load datasets exist; no exact Cape Town substation evening-peak exceedance task release was located.

### NOT COVERED

Full series retrieval, time-zone/daylight handling, meter changes, missing intervals, apparent-power semantics, thresholds and label leakage. No legal clarification was requested.

# 15. za-municipal-audit-opinion — READY-TO-BUILD

Candidate record snapshot SHA-256: `4251c5222ed2693c61eadca812d5690bb306d2c53fb57c54d3ab6c509e5b314e`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `municipal_csv` SHA-256: `62d85c6ffc477b8257b618c0d223ddf41a73556a6d56fa9171fbfae531729e95`. [Response and acquisition details](evidence/web/municipal_csv.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel/digest.** Downloaded the Treasury audit-opinion CSV: **733,716 bytes**, **3,688 data rows** (3,689 lines including header), **292 municipality codes**, **14 year ends, 2011–2024**. MD5 **`978b00f1bae50786ea1be561bda84276`** matches the publisher index. SHA-256 **`62d85c6ffc477b8257b618c0d223ddf41a73556a6d56fa9171fbfae531729e95`**. This is municipality/year-level data, not only national totals. [Treasury bulk documentation](https://municipaldata.treasury.gov.za/docs).

**PASS — licence.** Treasury terms explicitly permit copying, publishing, distribution and adaptation, including commercial use, with source/date acknowledgement and no endorsement claim. Preserve the publisher's own terms and attribution. [Treasury source terms](https://municipaldata.treasury.gov.za/terms).

**PASS — bounded novelty.** Public audit-opinion APIs/visualisations exist; no already released exact next-opinion task was located.

### NOT COVERED

Full financial-feature joins, municipal boundary changes, reporting-vintage availability, independent verification against Auditor-General reports, eventual split/label construction and leakage.

# 16. za-statsa-liquidations-exceedance — READY-TO-BUILD

Candidate record snapshot SHA-256: `a2f615c2fcd36280b1da56bd766e586b9f440ba4115b949f47199aef4b259ef2`. This is an input-record hash, not a pre-label prediction freeze. No candidate artifact, label attack or prediction archive exists at Tier C.

Channel evidence `statsa_data` SHA-256: `29bd835df7bc21f32239de9325955d93194dc99429aa5a96cd07b7c58bdd6e8f`. [Response and acquisition details](evidence/web/statsa_data.json). This hashes the captured sample/file, not an unfetched whole dataset.

**PASS — channel.** Downloaded the public ASCII liquidation time series: **59,645 bytes**, **47 series blocks**, release header **2026 09**, start **2000 01**. These are monthly category-series observations, not individual business liquidation microdata. They support the candidate's declared series/month exceedance grain. [Stats SA ASCII source](https://isibaloweb.statssa.gov.za/data/ETS/Monthly/Liquidations%20and%20InsolvenciesP0043_1/ASCII%20Liquidations.txt).

**PASS — licence for the declared free release.** The source time-series index's copyright notice permits processing/reuse with Stats SA attribution and a statement identifying independent processing, while prohibiting sale without permission. The operator's free release can comply without a permission email. Preserve the **no-sale condition**, attribution and custom terms; do not call this CC BY or relicense the rows. The general copyright web page was not readable, but this source-specific primary notice was. [Official time-series index and terms](https://isibaloweb.statssa.gov.za/docs/Time_series_index.pdf).

**PASS — bounded novelty.** No exact released Stats SA liquidation-exceedance task was found. Nearby macroeconomic forecasting work is not automatically the same target; the inspected April 2026 preprint predicts unemployment, not this task. [Inspected nearby paper](https://www.preprints.org/frontend/manuscript/b08eafbd3adebd0fc9cf386ba872603e/download_pub).

### NOT COVERED

All 47 series values, release-date backtesting, historical revisions, overlap/dependence among category totals, threshold construction or leakage. Commercial redistribution is not cleared; any use requiring permission is outside this build clearance.


# Reproduction and remaining limits

The report's rounded numbers are presentation only. `blind-results.json`, `control-results.json` where completed, `stock-exact-results.json`, `reference-reproduction.json`, `integrity-results.json`, reconstruction logs and destination verification retain machine-readable results. Every A/B item used the same frozen attack hash and a separate frozen prediction hash listed above. Full digest tables deliberately include holdout bytes because the user authorized this audit; none were published externally.

To reproduce frozen attacks with the recorded environment, run `attack.py predict` in a fresh copy of this evidence directory, freeze the resulting archives, and then `attack.py score`. Do not overwrite the signed evidence set. Post-score verification did not add/tune attack rules. Optional supervised controls are separate. The PINS mixed-category failure is retained in `controls.log`; the aborted OCHA rebuild is retained in `extra-verification.log` and its reconstruction log.

The checked package-file manifests also match: IPO **24/24**, PINS **25/25**, UNHCR **24/24** available package files. Nova Scotia has no repository MANIFEST; its five-file checks and destination checks passed. Source reconstruction is strong evidence of consistency with a pinned builder/source, not independent proof of every underlying administrative fact. No claim here establishes that an undiscovered leakage encoding or prior task cannot exist.

**Signed: Codex — independent artifact audit, 1 November 2026, Europe/Paris.**
