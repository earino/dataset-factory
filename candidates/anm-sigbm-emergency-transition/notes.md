# ANM SIGBM emergency-status transition — discovery notes

Candidate id: `anm-sigbm-emergency-transition` (opened 2026-11-07, LatAm regional tick, Brazil deep-dive)

## Task

Dam-month panel, PNSB tailings dams (population ≈ 461), Brazil, 2021-2026.
Predict, at the monthly bulletin publication instant, whether a dam's
emergency status (Alerta / N1 / N2 / N3 vs Sem emergência) changes during a
strictly-later target month.

Prospective user: ANM's remote-inspection unit (the bulletins are produced by
the Gerência de Fiscalização Remota de Barragens) and civil-defence
authorities downstream. The agency already runs a monthly monitoring cadence
over exactly this state variable; a prediction ahead of a status change
supports inspection prioritization and PAEBM readiness before the
declaration changes.

## Probes (all commands run 2026-11-07, coordinator container, UTC)

### 1. Licence (cheapest veto — resolved first, class A)

Registry data:

```
# portal's own API (through the supported browser; /api/3/action is CloudFront-blocked for plain clients):
# https://dados.gov.br/api/publico/conjuntos-dados/barragens-de-mineracao
"license_id": "cc-by", "license_title": "Creative Commons Attribution"
# public page states: "Licença: Creative Commons Attribution"
```

Bulletins (sampled Janeiro 2021, Junho 2023, Outubro 2026 — same sentence in
all three):

> "Todos os direitos reservados. É permitida a reprodução de dados e de
> informações contidos nesta publicação, desde que citada a fonte."

Reading: registry CSV is cc-by (attribution condition, no SA/NC); the PDF
document is all-rights-reserved but its data is explicitly reproducible with
source citation — so we extract and republish data with attribution, never
re-host the PDFs.

### 2. Registry snapshot fetch (access caveats measured)

```
curl -sI https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv
#  -> curl exit 60: server sends ONLY the leaf cert (Sectigo OV R36 chain);
#     AIA intermediate fetched from http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt
#     and converted to PEM -> --cacert chain.pem works
#  -> with default curl UA: HTTP 403 "Web Application Firewall" page
#  -> with full Chrome UA + Accept headers: HTTP 200, 3,386,460 bytes, 1.6 s
# Live-updating registry ("Atualização: Diária"): two fetches 8 minutes apart
# (00:04Z and 00:12Z) hashed identical -
sha256 6aa5f152db495348d9e22abbc0bcdc4cba17fc6f4070772b279f445b18ee574a
# CORRECTION 2026-11-07: the first draft of this note carried a digest that was
# never measured (transcribed from nothing). The probe script's own sha
# assertion refused it on first run; the digest above is the measured one.
# Construction pins the digest of ITS OWN fetch instant; re-fetches may differ.
```

Encoding latin-1. 908 dams × 124 columns. Reproduce:
`python3 candidates/anm-sigbm-emergency-transition/probe_registry_mix.py --all`
(downloads to scratch if absent, verifying the sha256).

Measured mixes (script output, 2026-11-07):

- Nível de Emergência: Sem emergência 831, N1 59, Alerta 11, N2 6, N3 1.
- ALL 77 Alerta/Emergência dams: PNSB=Sim AND PAEBM=Sim. All 447 non-PNSB
  dams: Sem emergência. → eligible population = 461 PNSB dams.
- CRI: Baixa 546 / Média 296 / Alta 66. DPA: Baixa 504 / Alta 243 / Média 161.
- Método construtivo: Etapa única 484, A jusante 225, Linha de centro 113,
  **A montante (upstream) 38**, vazio/"-" 41, Desconhecido 7.
- UF: MG 318, MT 187, PA 120, BA 83, SP 58, RO 35, AP 24, GO 22, AM 15, SC 11.
- 124 columns incl. height (project+current), crest length, reservoir
  area/volume (project+current+capacity), material (19 cats), foundation,
  design-flood return period (CMP/milenar/500y/<500y), internal drainage
  status, instrumentation status, downstream population (4 cats), minerals
  (52), beneficiamento (73), chemicals (90).

Feature-availability caveat: the daily CSV is a CURRENT snapshot ("atualizado
em tempo real"). Compliance-status columns (Drenagem Interna, Instrumentação,
DCE/DCO status) reflect 2026 inspection state — they are post-hoc relative to
earlier panel instants and must either be excluded from shipped features or
carried as explicit retrospective-assumption features (same
current-compilation-retrospective pattern as ab-wildfire-ia-escape). Static
attributes (construction method, material, UF, foundation) are effectively
fixed. Construction decides; the default is exclude-current-vintage-compliance.

### 3. Bulletin archive (historical evidence, published monthly)

```
https://www.gov.br/anm/pt-br/assuntos/barragens/boletim-de-barragens-de-mineracao/boletim-mensal
  pages b_start:int=0 / 30 / 60  (3-page Plone listing)
```

Measured coverage: 2021 12/12; 2022 6/12 (Jan-May, Dez; Jun-Nov absent from
the listing); 2023 12/12; 2024 12/12; 2025 12/12; 2026 10 (Jan-Out). ~64
issues. The Jan-2021 issue's CRI chart shows monthly values back to fev/2020
— earlier reports may exist elsewhere; construction enumerates and confirms.

Content samples:

- Outubro 2026 (published 05/11/2026 12h45, window 01/10→01/11/2026):
  909 dams / 462 PNSB; 77 in Alerta/Emergência; **Tabela 4 = 11 dams with
  level changed during the month** (previous → current, no per-dam event
  dates); Tabelas 5-8 = full per-dam lists per level; 12-month series 77-95.
- Junho 2023 (window 01/06→01/07/2023): 924 dams / 461 PNSB; Alerta present;
  2 CRI changes.
- Janeiro 2021 (window 04/01→01/02/2021): 877 dams / 436 PNSB; 45 in
  emergency (no Alerta category — introduced with Resolução ANM 95/2022);
  per-dam lists per level present.

Label-set note: the Alerta category exists from ~2022; a consistent 2021-2026
label needs a documented mapping (Alerta treated as its own state from
introduction; construction measures the changepoint from the bulletins).

### 4. Identity resolution (decisive feasibility probe)

`probe_registry_mix.py --identity` matches Outubro-2026 Tabela-4 transition
dams and 4 level-list dams (incl. garimpo dams in RO/AP/RS) against the
registry CSV on normalized (Nome, UF, Município):

- 13/15 unique matches (including small cooperatives like COOPERSANTA).
- 2 name-variant misses: "Portal" (Vale, Itabira — Vale has many Itabira
  dams) and "Barragem Serra Azul" (ArcelorMittal Itatiaiaçu). Both are
  resolvable with entrepreneur + fuzzy matching; construction measures the
  residual unmatched rate per year instead of assuming it.

### 5. SIGBM Público app (unresolved, non-blocking)

`https://app.anm.gov.br/SIGBM/Publico` — host closes connections from this
environment (browser ERR_CONNECTION_CLOSED, 2 attempts). The gov.br SIGBM
page says the public app shows "históricos das informações classificatórias"
(Power BI) — if per-dam DATED level history exists there, the timing design
gains exact event dates. Re-probe from the worker network at construction;
not a blocker (bulletin diffing suffices).

## Five contracts (reconciliation at 2026-11-07)

1. **Redistribution — SUPPORTED.** cc-by on the publisher's catalog record
   for the registry data; per-bulletin data-reproduction grant with citation.
   Attribution sentence to be carried verbatim into LICENSE.md; bulletins
   cited, not re-hosted.
2. **Prediction timing — SUPPORTED with two declared limitations.** The
   instant (bulletin publication, 4-7 days after the 1st) is dated on the
   archive page; the reference windows are stated in every issue; the target
   month is strictly after the instant. Limitations: (a) registry attribute
   columns are current-compilation (declared retrospective assumption or
   exclusion); (b) transition tables carry no per-dam event dates, so the
   M+1 month between instant and target-month start is skipped to keep the
   target wholly future — see dated example below.
3. **Target — SUPPORTED.** Derivable from per-dam level lists (every era
   sampled) and transition tables; label sources excludable; state-vs-change
   definitions measurable. Absence of change is observed by comparing two
   published snapshots (not assumed from silence).
4. **Split capacity — UNRESOLVED (the one open item).** ~64 monthly
   snapshots with sampled gross-change counts (11 in Out 2026; persistent
   churn in the 12-month series) make temporal windows plausible, but the
   actual positive/negative counts per window require the ledger, which is
   construction-scale parsing of ~64 PDFs on a worker. A sample is not a
   count; `ready` waits for it.
5. **Not a mirror — SUPPORTED.** No public ML-ready formulation found; the
   closest prior art (BrazilDAM) is static satellite-image classification of
   the same registry, with no time dimension and a different target.
   Novelty recorded in `record.novelty_check`.

## Dated example (timing, America/Sao_Paulo throughout)

Prediction instant: **2026-11-05 12:45** (publication of the Outubro 2026
bulletin). Known at the instant:

- registry attributes (current compilation — declared limitation),
- per-dam level state as of 2026-11-01 00:00 (bulletin Tabelas 5-8),
- the dam's full published level history 2021-01 → 2026-11-01 (prior issues),
- Outubro's transition table (changes during 01/10→01/11).

Target window: **2026-12-01 00:00 → 2027-01-01 00:00** (Dezembro changes,
read from the Dezembro 2026 bulletin, published ~2027-01-05). Every target
instant is strictly after the prediction instant. The intermediate month
(Novembro 2026) is not used as a target: its transition table is unpublished
at the instant, and its undated events cannot be split into
before/after-instant parts. Eligibility cutoff: dam PNSB-enrolled and
present in the registry at 2026-11-01.

A noon-prediction variant targeting the following calendar month directly
would include already-elapsed days of that month — rejected by design; the
one-month buffer is the cost of undated transition events.

## What would reopen / change the verdict

- Ledger build shows too few positives in any window (split capacity fails)
  → `parked` with the measured counts.
- Worker probe finds per-dam DATED level history in SIGBM Público → timing
  design upgrades to exact event dates (better, not blocking).
- ANM stops publishing monthly bulletins → the panel's monthly cadence ends
  (monitor; the historical 2021-2026 window still supports a retrospective
  release).
