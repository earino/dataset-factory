# tcu-obra-paralisacao — probe notes

Scheduled discovery tick 2026-10-30, Latin America focus. All observations 2026-10-30 from
the coordinator container, read-only. This lead was PARKED, not dropped; the reasons and the
reopen trigger are in record.json. The recipe for every observation is below so scratch
cleanup does not delete the only copy.

## 1. What the lead is

TCU (Tribunal de Contas da Uniao) maintains the "Painel de Obras Paralisadas"
(https://portal.tcu.gov.br/obras-paralisadas/), consolidating federally funded public works
from five government databases (Caixa/OGU, MEC SIMEC Obras 2.0 + Monitoramento, SETEC/SESu,
Funasa, DNIT, Sismob/MS), created in 2020 after levantamentos ordered by
TC 021.731/2019-5 (Acordao 1.228/2021-TCU-Plenario).

Prospective task: given a work in execution at one published vintage, predict it is recorded
"paralisada" in the next vintage. Genre (infrastructure-delivery stall) is absent from the
factory bench and genuinely useful (governance/budget triage).

## 2. Access probe (decisive, environment-specific)

- Supported browser: `new_tab("https://portal.tcu.gov.br/obras-paralisadas/")` ->
  page title: "Acesso Bloqueado" (security block page; the horse emoji in the title is the
  block page's own). Same for the plain extractor on
  `https://portal.tcu.gov.br/paineis-de-informacoes` (JS/cookie wall, no content rendered).
- This is egress/IP blocking by TCU's WAF, not a dead source: TCU press pages and
  PDFs on the same host appear in search-engine caches; `sites.tcu.gov.br` (different host)
  serves "Lista de Alto Risco" pages readable via search snippets.
- dados.gov.br catalog API `https://dados.gov.br/dados/api/3/action/package_search`
  -> HTTP 401 to unauthenticated plain clients; no catalog entry for a machine-readable
  Painel de Obras distribution found via web search.
- CONSEQUENCE: the panel's data model (per-work fields, dated status, export capability)
  is UNKNOWN from this environment. No data file was downloaded. Access failure is not a
  scientific rejection (skill rule); recorded as blocker (1) of the park decision.

## 3. Structure/split reasoning from publisher communications

TCU press releases and reports (read via search results 2026-10-30; quote-scale numbers):

| vintage | obras mapeadas | paralisadas | share |
|---|---|---|---|
| 2020 | 27,126 | 7,862 | 29% |
| 2023 | 21,007 | 8,603 | 41% |
| Apr 2025 | 22,621 | 11,469 | 50.7% |

Also: 11,944 empreendimentos paralisadas counted over 2022-2024; ~1,200 of 5,505 works
initiated April 2024-April 2025 already stalled (22%); panel news mentions comparison tabs
for 2018 and 2020 bases ("e bem como realizar comparacoes com as bases de dados de trabalhos
anteriores (2018 e 2020)").

Problems this documents:
- Few vintages (2018, 2020, 2022, updates 2023-Apr 2025) -> a vintage-transition label gives
  at most ~4 transition windows; marginal for disjoint train/eval/holdout.
- The mapped base CHANGES COMPOSITION between vintages (27,126 -> 21,007 -> 22,621), so
  cross-vintage work identity is unproven; works leaving the base (concluded? dropped?) are
  a censoring question that must be answered before any label.
- Rescue path, unverified: per-work dated status history inside the panel (e.g. a
  paralizacao date) would allow a single-vintage design; could not be checked from here.

## 4. Prior art (target level)

Web search 2026-10-30 ("prever OR previsao 'obras paralisadas' machine learning ..."):
- UnB master's dissertation (repositorio.unb.br/handle/10482/52676), "Machine Learning na
  Prevencao de Paralisacoes em Obras Publicas: Estudo de Caso em Infraestrutura
  Educacional" (Proinfancia/FNDE school-construction works): CRISP-DM, 205 models, best
  deep-learning model 94.79% accuracy on suspension risk; FNDE program data, no public
  benchmark or splits shipped.
- TCU's own products (painel, Fiscobras, risk-matrix audits) publish status/risk
  communication, not scored prediction tasks.
- No ML-ready public-works stall benchmark with splits located; the prediction TARGET is
  proven in the literature, so any task must state its formulation contribution.

## 5. Licence

NOT READ: portal.tcu.gov.br terms pages are unreachable from this egress (see §2). Recorded
as unread - this is not a class-C closure (no terms page was readable at all) and no
permission is claimed or assumed.

## 6. Park decision and reopen trigger

Parked 2026-10-30 with blockers: access (egress blocked, no machine-readable distribution
located), structure/split (vintage count, unstable base composition, unknown per-work
history), and target-level prior art. REOPEN WHEN a machine-readable distribution is
reachable (official download/API, dados.gov.br entry, Wayback-archived exports, or an
unblocked egress) AND it carries per-work dated status or multiple archived vintages. Then:
read terms and classify licence; verify work identity across vintages; then re-assess. Do
not spend further scheduled ticks before the reopen trigger fires.
