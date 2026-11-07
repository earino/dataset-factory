# jp-meti-recall-expansion — discovery notes (East Asia tick, 2026-11-07)

Verdict: **investigating** — opened this tick. Licence triaged first (METI channel class B,
NITE channel class D, CAA channel volume-rejected); event grain and a later-resolving
target structure measured on one register page; split capacity and the update-lag
distribution are the named unmeasured facts. No construction; the record is buffer-only
while the operator's 2026-11-07 factory-repair directive stands.

## The lead

Prospective user: METI/CAA product-safety officers and the recalling business's quality
team, at the moment a consumer-product recall is first published. Decision: how much
follow-up scrutiny this recall gets (re-inspection of scope, repeat consumer notices,
press handling). Prediction: will this recall's register row later record a substantive
lifecycle update — 対象追加 (scope addition), 型番追加, 品番追加・対象期間拡大, or 対策内容更新
— i.e. did the initial recall under-scope the hazard? An under-scoped recall leaves
hazardous units in consumers' homes and forces repeat notices; predicting expansion risk
at publication is an operational triage question, not a curiosity.

New family for the bench: consumer-product-safety **recall lifecycle** (per-recall
post-publication update prediction). The nearest published artefacts are US
hazard-classification datasets (RECALL-MM on US CPSC recalls; SemEval-2025 Task 9 food
hazard detection from announcement titles) — neither predicts a within-register
lifecycle update, and neither is Japanese data. Formal check-novelty.py runs at
ready-review.

## Licence first (cheapest veto applied)

- NITE channel (リコール情報/SAFE-Lite, the searchable pre-2007+ channel): NITE homepage
  terms (`https://www.nite.go.jp/homepage/policy.html`, read 2026-11-07) state all content
  is NITE's or the original rights-holder's work, reproduction/public transmission outside
  private use/quotation is infringement, and "使用する場合は、機構の使用許諾が必要となります"
  (use requires NITE's permission). No dataset-level but-clause found for SAFE-Lite data.
  **Class D — channel rejected**; also its list pages stopped updating 2025-04-01
  (publisher notice read 2026-11-07).
- CAA リコール情報サイト 重要なお知らせ一覧 (`recall.caa.go.jp/result/index.php?screenkbn=02`,
  measured 2026-11-07): 265 records over ~18 years, ~15/year, event-clustered, includes
  回収命令 entries. **Rejected on volume** (cannot fill three disjoint windows); kept as
  a cross-check product only. Licence not assessed (veto came first).
- METI 製品安全ガイド リコール情報: METI 利用規約 (`https://www.meti.go.jp/main/rules.html`,
  fetched 2026-11-07, 16,703 bytes): "特記されていない限り経済産業省に帰属し、権利表記の記載が
  ない限り「公共データ利用規約（第1.0版）」（PDL1.0）に準拠した利用条件の下で、利用することが
  できます。" **Class B**: PDL 1.0 requires 出典記載 attribution, disclosed
  editing/processing, and no presenting modified data as government-made; third-party
  rights (product photographs, business-written hazard text) must not be shipped — the
  task ships extracted structured facts only. Register pages carry no additional
  dataset-level notice, so the site default governs.

## Probe evidence (2026-11-07; commands reproducible)

```bash
# register index (categories + sub-pages; server-rendered list; capture kept in cache)
curl -s -m 30 -A "Mozilla/5.0 ..." "https://www.meti.go.jp/product_safety/recall/index.html"
# -> 9-10 category hubs; ~20 sub-pages (baby_1-3, daidokoro_1, denki_1-7, hoken_1-3,
#    kagu_1, nenshou_1-3, norimono_1-2); coverage since 平成19年5月14日 (2007-05-14).

# hub pages 403 to plain clients; sub-pages serve 200
curl -s -o /dev/null -w "%{http_code} %{size_download}" "https://www.meti.go.jp/product_safety/recall/denki.html"
# -> 403 5045      (hub)
curl -s -o /dev/null -w "%{http_code} %{size_download}" "https://www.meti.go.jp/product_safety/recall/denki_5.html"
# -> 200 63763    (sub-page; twice, 3 s apart)

# after a ~10-request plain-client burst: empty 200s / HTTP 202 WAF interstitial (2,483 bytes)
# urllib-style clients got empty 200s even for pages curl served normally (host fingerprint
# behaviour, not a missing page). Enumeration must be polite-paced (>=3 s) or browser-driven.

# sample-page structure (this is the full evidence for grain + target structure today):
python3 probe/probe_meti_recall_counts_2026_11_07.py     # counts reproduced in the record
# denki_5.html (リチウム電池使用製品): 225 dated tokens 2007-2026, ~210 recall rows,
# schema: リコール日 | リコール製品名 | リコール実施事業者名 (+ red-text 重大製品事故契機リコール
# marker; 海外事業者 marker on overseas businesses; two-date update entries).
# markers: 対象追加 4, 対策内容(等)更新 2, 型番追加 1, 品番追加・対象期間拡大 1 (label classes;
# ~3-4% sample base rate), cosmetic 問い合わせ先等 4 / 電話番号 1 / 受付時間等 4 / URL 1 / 回収開始 1.
```

Cross-category confirmation from the publisher's rendered pages (2026-11-07 search
fetches): kagu 2025-01-24 折りたたみ椅子 (良品計画) -> 2025-02-19 （対象追加）; kagu
2023-01-12 鏡 (イケア・ジャパン) -> 2023-09-13 （対象追加）; norimono 2022-06-20 自転車（子供用）
-> 2022-08-01 （対象追加）; rejya/norimono 2019-08-28 ゴムボート -> 2019-11-08 (対象追加).

## One dated example (Asia/Tokyo throughout)

- Feature event window: the recalled product's 販売期間 (sales period, published on the
  detail page at publication, e.g. "1997年3月～2001年3月" style) and the hazard/market
  facts as published — all strictly before publication. (Per-field verification on the
  detail pages is next_action step 1; the 販売期間 above is the documented field name on
  this register's detail pages, unverified for every row.)
- First publication (prediction instant): リコール日 2014-05-28 for the denki_5 row
  "リチウム電池内蔵充電器" (row measured on the fetched page). The register index states
  publication happens as a rule on METI's web pages and is announced on X at posting
  (current behaviour).
- Eligibility cutoff: every recall row published on the register on/before the instant;
  never outcome-conditioned.
- Target start/end: strictly after the instant — the observed update for this row was
  品番追加・対象期間拡大 recorded 2014-11-13 (167 days later). Under the 365-day primary
  window the target interval is (2014-05-28, 2015-05-28]; no part of the target window
  precedes the instant. The window is DRAFT: measured lags span 42 days to ~4.9 years
  (2019-07-05 -> 2024-04-12 対象追加), so the full-register lag distribution must fix it.

## As-of caveat (recorded, unresolved)

The register revises entries in place — the two-date markers prove in-place revision of
both scope and cosmetic fields. A shipped row's feature values as of ITS publication day
are therefore not guaranteed by the current compilation; the task is a
current-compilation retrospective (explicit evaluation_contract assumptions, ab-wildfire
precedent) unless the Wayback CDX probe (next_action step 3) bounds historical vintages
for the intended period. Historical operational availability is NOT claimed.

## Decision, uncertainty, next action

- Decision: open as **investigating** (buffer-only; no construction under the operator's
  2026-11-07 directive).
- Decisive uncertainty: full-register outcome-update counts per year (split capacity) and
  the update-lag distribution; then detail-page feature availability; then vintage
  evidence; then the formal novelty verdict.
- Next action: the six ordered steps in record.next_action (detail-page schema probe ->
  full-register enumeration -> Wayback vintages -> CAA cross-check -> check-novelty.py ->
  five-contract reconciliation / ready review).

## Detail-page schema probe (2026-11-07, one spaced fetch - next_action step 1 partially done)

Single spaced fetch of one modern detail page (register row 2025-08-25, 自転車用ライト,
ダイアテック株式会社): `https://www.meti.go.jp/product_safety/recall/file/250825-1.html`
-> HTTP 200, 15,314 bytes, utf-8 (old pages are shift_jis-like; pin the decoder per era).

Verified fields on the detail page: リコール実施日 | 製品名 | リコール事業者名 + 法人番号
(structured corporate number, joinable) | リコール実施の理由 (reason text) | リコール対策内容
(remedy: 回収・交換) | リコール製品の概要 table: 商品名, EANコード, バッチコード, 販売期間
(sales period 2023年5月〜2025年8月), 対象台数 (1,350台 / 700台 per product line) | 対象製品の
外観・確認方法 | 事業者問い合わせ先 | 事業者リコール情報URL | 最終更新日 2025-08-26 (one
day after publication - the detail page carries its own revision date).

AS-OF FINDING (measured): the updated row 2014-05-28 -> 品番追加・対象期間拡大 2014-11-13
links to file/141113-1.html, i.e. TODAY's row link points at the CURRENT detail-page
revision, not the original. Per-row feature values as of each row's publication day
therefore require Wayback vintages (or restriction to register-row stable fields); the
最終更新日 detects revision but does not reconstruct original values. The as-of caveat
above stands, now with direct evidence.
