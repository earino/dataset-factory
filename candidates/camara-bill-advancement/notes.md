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
own situation vocabulary — the 2026-10-21 line read "idSituacao 251 = became law, 1.5% on the 2005
sample"; CORRECTED 2026-10-23 to situation code 1140, see the construction-probe section below:
the discovery probe mis-indexed column 25), splits (1991–2022 closed-legislature cohorts by
dataApresentacao; API cohort counts measured; right-censoring reframed 2026-10-23), not a
mirror (novelty check recorded). Next action in record.json names the construction steps.

## 2026-10-23 construction-probe tick: the discovery sample's label code was a mis-indexed column; right-censoring reframed; camara-001 launched

Four probe scripts (kept in this directory, each run end-to-end from the coordinator):

- **`probe_censoring.py` (v1) — defective, kept as the diagnosis.** Naive `split("\n")` on ranged
  chunks corrupts rows whose quoted ementa/despacho contains embedded newlines; mid-file fragments
  parsed as full-width rows with empty trailing fields, inflating "empty status" to 77–93%. The
  discovery probe (`probe_samples.py`) has the same line-splitting shape plus a second, worse defect
  (below). v1's numbers are not evidence; recorded so nobody re-runs it as-is.
- **`probe_censoring2.py` — the corrected vocabulary measurement.** Quote-parity-aware record
  trimming; whole-1991 file as ground truth (4,436 rows). Situation codes keyed **by header name**:
  923 `Arquivada` (2,491 rows), **1140 `Transformado em Norma Jurídica` (311 = 7.0%)**, 1230
  `Transformado em nova proposição`, 937 `Vetado totalmente`, and ongoing states 925/907/915/924/
  926/936/1070/1120/1170/1220/1285. **This corrects the discovery record: `probe_samples.py` read
  column 25 positionally as idSituacao, but column 25 is `ultimoStatus_idTipoTramitacao`; "code
  251" never was a situation code.** The same defect produced the "codes 100/319 with empty
  descriptions, 39–40% of rows" note — those were tramitação codes.
- **`probe_empty_status.py` — the empty statuses are real.** 25–53% of rows by year carry an empty
  `ultimoStatus_idSituacao` (whole-1991: 36.6%). For 12 sampled such ids the API v2 returns
  `statusProposicao: null` — genuinely no tramitação on record (many are procedural types RIC/EMP/
  MSC/REQ, some PLs), not a file gap. These are unobserved targets, excluded and counted per
  window in the build.
- **`probe_file_vs_api.py` — the file is current; bills outlive their legislature.** 2019-file
  non-terminal rows match the live API exactly (5/5 sampled) and their `ultimoStatus_dataHora`
  updates run into 2025–2026 (e.g. PL 1/2019 "Aguardando Apreciação pelo Senado Federal",
  2025-08-26). So the recorded "closed-legislature settles the label" assumption is **wrong**:
  Brazilian bills carry across legislatures; the scored population is bills whose status is
  terminal **at the vintage**, with per-window unobserved shares measured and recorded.
- **`probe_file_inventory.py` — the download budget.** 35/35 years 200 OK for both families:
  `proposicoes` 747.4 MB + `proposicoesAutores` 456.0 MB. Autores schema measured: idProposicao,
  tipoAutor, siglaPartidoAutor, siglaUFAutor, ordemAssinatura, proponente.

Label design decided from these measurements (all recorded in record.json before the build ran):
positive = code 1140; terminal negatives = Arquivada* + Vetado totalmente + Retirado + Devolvida
+ Tramitação Finalizada + Enviada ao Arquivo; merged (1230) excluded with its share recorded;
everything else (incl. empty) = unobserved. Sampled cohort positive rates drift 7.0% (1991) →
~2.2% (2005) → ~0.4–0.8% (2019–2022) — a prevalence-drift property to report beside any score.

**Build + smoke.** `source/build.py` (union descending-first-wins, presentation-instant features,
terminal-outcome label, in-build naive references, fixtures: PL 4188/2021 "BR do Mar" must be
positive in the holdout window; portal facet bound 11,640 in situation 1140 across all years/types,
read 2026-10-23). `tests_smoke_build.py` runs the real build over 70 synthetic year files (incl.
multi-line quoted ementas, a true cross-file id collision, an everywhere-undescribed code, and a
proponente-on-higher-ordem author pair) — **SMOKE OK** after it caught three real bugs (the
whole-file header trim, the same in the autores pass, and a wrong row-count metric). The smoke
also produced the corrected expectation for the proponente rule (build prefers `proponente=1`
over lower ordemAssinatura — verified PROPR beats PSDB in the synthetic output).

**camara-001 launched 06:30:58Z** (server 171985941, cx23/hel1, EUR 0.06 reservation, bundle
build.py sha256 e3039dd7241c15ac…). The job downloads the 70 files on the worker, builds the panel,
and runs the qualification gate on the full artifact; collection requires exit 0 + a passing gate
report + `--accept` on the exact bytes before anything is scored (next_action in record.json).

Mirror observation (novelty record, not permission): HF org `belisards` mirrors the raw
proposicoes files 1934–2024 (`ementas_camarabr_1934_2024`) — raw extract, no splits, no scored
contract; the recorded `differentiated` verdict is unchanged.
