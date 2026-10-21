# camara-bill-advancement — notes

Câmara dos Deputados (Brazil) Dados Abertos. Opened 2026-10-21 in the Latin America discovery
tick. All probes anonymous from the coordinator.

## Access probes

`python3 probe_samples.py` (kept in this directory) — 2026-10-21, 15 requests, ~4 MB ranged
samples, 31 s:

- Bulk file family: `https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-{ano}.csv`
  (semicolon CSV, byte-range supported). Measured sizes: 1991: 4,451,452 B · 1995: 4,914,946 B ·
  2000: 6,846,297 B · 2005: 22,247,788 B · 2010: 15,888,349 B · 2015: 34,171,659 B ·
  2019: 33,295,980 B (last-modified 2026-10-21 → live) · 2023: 52,259,953 B · 2024: 53,088,881 B ·
  2025: 90,204,760 B. Companion families on the same pattern: `proposicoesAutores`,
  `proposicoesTemas`, `votacoesProposicoes` (documented on dadosabertos.camara.leg.br/swagger/api.html).
- CSV columns (30, from the header row): id, uri, siglaTipo, numero, ano, codTipo, descricaoTipo,
  ementa, ementaDetalhada, keywords, dataApresentacao, uriOrgaoNumerador, uriPropAnterior,
  uriPropPrincipal, uriPropPosterior, urlInteiroTeor, urnFinal, ultimoStatus_dataHora, …,
  ultimoStatus_regime, ultimoStatus_descricaoTramitacao, ultimoStatus_idTipoTramitacao,
  ultimoStatus_descricaoSituacao, ultimoStatus_idSituacao, ultimoStatus_despacho,
  ultimoStatus_apreciacao, ultimoStatus_url.

## Sample findings (4 × 1 MB ranged chunks per file)

- **File semantics**: 2005 file → 100% of 4,852 sampled rows have dataApresentacao in 2005;
  2019 file → 98% in 2019. The ~2% remainder are older bills re-numbered to the current `ano`
  when un-archived at a legislature boundary (2019-file rows with dataApresentacao 2000-11-10 /
  2001-05-23 observed directly). Cohorts must be defined by dataApresentacao over the union of
  files, not by file year.
- **2005 cohort sample (n=4,852)**: ultimoStatus descriptions: `Arquivada` ~62% across codes
  (1005, 502, 241, 100, 1001, 180…); `Transformado em nova proposição` ~3.5% (469, 604);
  **`Transformado em Norma Jurídica` (idSituacao 251): 72 = 1.5%** — the became-law signal.
  `urnFinal` non-empty: 0/4,852 (do not use as label).
- **2019 cohort sample (n=4,909)**: statuses still mixed (Arquivada 14.8%, ongoing tramitação
  states) — recent cohorts are right-censored; the task scores only closed-legislature cohorts.
- **Code-table quality**: many rows carry idSituacao with empty descricaoSituacao (codes 100 and
  319 most frequent, 39–40% of rows with empty descriptions) while the same codes appear with
  descriptions elsewhere — the label must be frozen on the publisher's situation CODE table
  (Referências), descriptions as cross-check.

## Cohort counts via API (Link rel="last" page count × 100)

`GET /api/v2/proposicoes?dataApresentacaoInicio=…&dataApresentacaoFim=…&itens=100` — the date-range
parameter pair is correct but limited to ≤ 3 months per request (measured HTTP 400: "A diferença
entre as datas não pode ser maior que 3 meses"). Quarterly last-pages:

- 2005: 41+92+61+69 pages → ~26,300 propositions presented.
- 2019: 68+105+107+135 pages → ~41,400 propositions presented.

The `referencias` situation-code endpoint exists but both GET and POST answer 405 (method not
supported) — the code table must be resolved from the publisher's Referências documentation at
construction.

## Licence (2026-10-21)

- Portal terms (www2.camara.leg.br/termo-de-uso-e-politica-de-privacidade): "Todas as informações
  publicadas no Portal da Câmara são de domínio público, gratuitas e podem ser reproduzidas desde
  que citada a fonte 'Câmara dos Deputados' e a autoria da informação, quando houver."
- Portaria nº 226 de 23/12/2025 (open-data policy): dados abertos = "disponibilizados ao público
  para livre utilização, consumo ou cruzamento", disclosure under arts. 29–37 da Lei 14.129/2021.

## Timing exclusions (documented reasoning)

Features at presentation only: siglaTipo/codTipo, ementa text, dataApresentacao + calendar,
authors (proposicoesAutores), ano/numero. EXCLUDED as post-hoc: `keywords` and the
`proposicoesTemas` family (assigned by the Chamber's indexação service after presentation),
all `ultimoStatus_*` fields (label source), `ultimoStatus_regime` (current, mutable),
uriPropAnterior/Principal/Posterior (later links), urnFinal. The publisher's own file
documentation places keywords/temas beside "informações sobre a tramitação mais recente",
i.e. not guaranteed at presentation.

## Novelty

`check-novelty.py` run 2026-10-21, verdict `differentiated` (in record.json). Prior art compared
explicitly: LegisPL-BR (GitHub, PL 2022–2024 raw extract, no splits/scored contract, current
legislature only → labels right-censored, cannot carry the task); ZFM 2011–2018 logistic-regression
paper; SBSI 5085 approval-prediction paper; LLM constitutionality study (194-bill curated sample).

## Verdict

GO (ready) 2026-10-21. Contracts: licence (free reproduction with attribution, quoted), timing
(presentation instant; indexação fields excluded with documented reasoning), target (publisher's
own situation vocabulary, idSituacao 251 = became law, 1.5% measured on the 2005 sample),
splits (1991–2022 closed-legislature cohorts by dataApresentacao; API cohort counts measured),
not a mirror (novelty check recorded). Next action in record.json names the construction steps.
