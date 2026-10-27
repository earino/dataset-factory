# conagua-dam-drought-onset — discovery notes (2026-10-27)

Latin America discovery tick (regional focus: Mexico). Discovery-only session; no
construction, no worker launched. All probes run on the hosted coordinator unless stated.

## Lead selection

Regional focus Mexico. Shortlist reasoning recorded in STATE.md (this tick): CONAGUA dam
storage chosen because the task shape (dam drought-onset / storage exceedance) was probed
twice before on this bench — `tw-reservoir-drought-storage` (TW, parked: no anonymous
historical bulk source; task "well-posed", licence ODDL clean) and
`za-dws-dam-storage-exceedance` (ZA, parked: publisher unreachable). Both died on ACCESS,
never on the task; neither sourced the shape. ANVISA food-import rejections (BR) was
rejected before probing as the RASFF mirror family (`rasff-notification-risk-decision`
dropped with named prior art; same reasoning as `ar-ecobici-station-demand-exceedance`:
population novelty is not task novelty). DATASUS/SINAN dengue: saturated forecasting
family. Chile MMA air-quality episodes: separate cheap probe this tick, see bottom.

## s1 — Access probe (decisive uncertainty #1: machine-readable history)

Command: `python3 candidates/conagua-dam-drought-onset/probe_access.py`
(plain urllib, no cookie jar):

```
0_Catalogo_de_presas.csv: FAILED HTTPError: HTTP Error 403: Forbidden
presas.csv: FAILED HTTPError: 302 redirect loop
ALRBN.csv: FAILED HTTPError: 302 redirect loop
```

Diagnosed with curl -I: `307` + `set-cookie: visid_incap_...; incap_ses_...` +
`location:` pointing back at the SAME URL, header `x-iinfo:` → Incapsula bot management.
Not a missing dataset and not absent terms. Real-browser navigation to the CSV URL did
not complete either (tab stayed about:blank), so the cookie-jar client was the working
route. TLS chain valid (GlobalSign Atlas R46 DV, `Verify return code: 0 (ok)`).

Working recipe (measured, retained in probe_access.py / probe_sample.py):

```
curl -skL --max-redirs 8 -A "Mozilla/5.0" -c jar -b jar -o out.csv \
     https://sih.conagua.gob.mx/basedatos/Presas/<CLAVE>.csv
```

Result: catalog 25,023 B / 2.48 s; ALRBN.csv 1,233,192 B / 4.92 s, HTTP 200, 1 redirect.
Station list page (`https://sih.conagua.gob.mx/presas.html`) lists 211 CSV links;
catalog has 210 dams (the extra row is a `presas` aggregate that 404s — does not exist).

## s2 — Schema and catalog

Command: `python3 candidates/conagua-dam-drought-onset/probe_schema.py`

Catalog (latin-1): 210 dams, 26 states (Jalisco 25, Michoacán 23, México 14, Durango 13,
Zacatecas 13, Sinaloa 11, Chihuahua 10, Guanajuato 9, ...). Columns: Número, Clave,
Nombre de la presa, Latitud, Longitud, Altitud, Estado, Municipio, cuenca de
disponibilidad, región hidrológica. **No capacity column** → threshold capacity comes from
the weekly-report archive (construction) or the observed-max proxy (discovery).

Station CSV (ALRBN): daily rows 1929-01-01..2026-10-26 (33,881 rows), header
`Estacion,Fecha,Precipitacion(mm),Nivel(m),ObraToma(m3/s),Vertedor(m3/s),Derrame(m3/s),Evaporacion(mm),VolumenAlm(Mm3)`.
VolumenAlm populated: 1990s 50% (1,826/3,652), 2000s+ 100%. Latest row 2026-10-26 on a
2026-10-27 fetch (T = D-1). ALRBN max observed 137.03 Mm3 (1990s), 2000s max 66.76,
2010s min 0.129 (the documented Tijuana near-empty period).

**Parse trap (cost an iteration, caught before any recorded claim):** a fixed-index parse
of `r[8]` produced vmax = 22 Mm3 for El Cuchillo (real ~1,765 observed / 1,123 official) —
because (1) column ORDER VARIES per file (VolumenAlm is index 8 in ALRBN, index 4 in
CCHNL/INFMC/SLSGJ/IALGJ, index 5 in CILAAMSMX/CILAFLCMX) and (2) files contain repeated
header+preamble blocks. Fixed by block-split at `Estacion,` lines + by-name column
mapping (probe_parse2.py). Any construction parser must do the same; the naive parse
silently reads Evaporacion(mm) as storage.

## s3 — Licence (checked before further probing)

Publisher's own per-resource record, national open-data platform, read 2026-10-27:

> https://www.datos.gob.mx/dataset/estaciones_sistema_informacion_hidrologica/resource/35e8d001-6195-45c7-9a1c-58a8594fb3a1
> Información adicional → **Licencia | Creative Commons Attribution 4.0**
> (https://creativecommons.org/licenses/by/4.0/)

Also recorded: the portal's retroactive-update warning on the parent dataset page
("Algunas bases de datos pueden incluir actualizaciones retroactivos por lo que la
información histórica puede cambiar en actualizaciones posteriores") — vintage caveat,
not a licence term. CONAGUA's designation letter under the federal open-data framework
(datos.conagua.gob.mx/docs/DatosAbiertos/Designacion_datosabiertos2020.pdf, DOF Decreto
20-feb-2015) confirms the program but is not itself the licence; the CC BY 4.0 resource
field is. SINA (sinav30.conagua.gob.mx:8080) independently describes the same dam-monitor
series: "el volumen almacenado, actualizado diariamente, de 210 presas del país... pueden
descargarse libremente en formatos CSV...". Class **A**.

## s4 — Multi-dam sample: coverage, events, split capacity

Command: `python3 candidates/conagua-dam-drought-onset/probe_sample.py` (7 named large /
drought-prone dams) then `probe_splits.py` (20 more, one per state where available).
26 dams, 24.8 MB, ~90 s total, all HTTP 200.

Per-dam results (threshold = 25% of per-dam observed max, robust parse):

| dam | state | n days | span | vmax Mm3 | onsets@25% |
| --- | --- | --- | --- | --- | --- |
| CCHNL El Cuchillo | NL | 12,083 | 1993-09→2026-10 | 1,765.7 | 6 |
| CILAAMSMX La Amistad | Coah | 11,187 | 1994→2026-10 | 2,254.2 | 13 |
| CILAFLCMX Falcón | Tamps | 11,138 | 1994→2026-10 | 1,742.5 | 16 |
| IALGJ I. Allende | Gto | 12,331 | 1993→2026-10 | 233.7 | 24 |
| INFMC Infiernillo | Mich | 11,867 | 1994→2026-10 | 10,441.0 | 2 |
| SLSGJ Solís | Gto | 12,351 | 1993→2026-10 | 985.3 | 7 |
| AFIGR | Ags | 10,222 | 1995→2026-10 | 110 | 23 |
| ALMSI | | 12,223 | 1993→2026-10 | 3,233 | 20 |
| ANGCP Angostura | | 12,302 | 1993→2026-10 | 18,870 | 2 |
| ARCSO | | 12,352 | 1993→2026-10 | 1,376 | 28 |
| CBRDR | | 11,601 | 1995→2026-10 | 48 | 6 |
| CDOOX | | 12,348 | 1993→2026-10 | 2,962 | 0 |
| CJNNR | | 7,410 | 2006-07→2026-10 | 2,318 | 0 |
| ELOSL | | 8,833 | 2002-03→2026-10 | 1 | 7 |
| ELZBN | | 11,602 | 1995→2026-10 | 5 | 6 |
| IDFQT | | 11,923 | 1994→2026-10 | 55 | 25 |
| LDACM | | 12,340 | 1993→2026-10 | 43 | 0 |
| LDCVC | | 9,910 | 1995-05→**2026-09-28** | 550 | 46 |
| LLAHD | | 8,789 | 1995-05→2026-10 | 44 | 19 |
| LLNCH | | 12,352 | 1993→2026-10 | 804 | 12 |
| LREZC | | 11,569 | 1995→2026-10 | 128 | 8 |
| MOCMC | Mich | 11,847 | 1994→2026-10 | 253 | 19 |
| NGRAG | Ags | 12,345 | 1993→2026-10 | 21 | 0 |
| PMNMX | Méx | 12,201 | 1993→2026-10 | 8 | 30 |
| PRGHD | | 12,274 | 1993→2026-10 | 54 | 35 |
| PSANL | | 11,913 | 1994→2026-10 | 18 | 3 |

Sample split-window counts (dam-day onsets, 26 dams): **total 357**;
train T≤2010: **202**; eval 2011–2018: **84**; holdout 2019–2026: **71**;
clusters (dam, year): **271**. Both classes present in every window. Additional dams can
only add events (monotone), so the window-emptiness risk measured here cannot be reversed
by the full panel. Full-panel counts remain a worker measurement at construction
(~210 × 0.96 MB ≈ 200 MB; never extrapolated from this sample).

LDCVC shows the per-dam update lag: latest row 2026-09-28 vs 2026-10-26 elsewhere → T must
be measured per dam at fetch.

## s5 — Fixtures and cross-checks

1. **El Cuchillo, 2024-06-09 (critical-low press figure):** Excelsior (June 2024):
   "tan sólo 363 hectómetros cúbicos... 32.3 por ciento de su capacidad".
   Measured SIH: 2024-06-09 → **363.541 Mm3** (363.541/1,123 = 32.4%). Exact
   corroboration of the series against an independently reported CONAGUA figure.
   Neighbours monotone: 06-07 366.148, 06-11 361.586.
2. **2022 Monterrey emergency + 2024 spring low:** CCHNL crossed the proxy threshold
   (441.4 = 25% of observed max 1,765.7) on 2022-08-27 (441.105) and on 2024-03-27;
   press (Zócalo/Posta) documents the 2022 crisis and the post-Tropical-Storm-Alberto
   refill to ~100% in late June 2024 (SIH 06-09 still 363.5, consistent with refill after
   ~June 19-20).
3. **Falcón:** observed minimum 0.8 Mm3 on 1995-05-05; onsets include 2002-12-21.
4. **Publisher's own weekly summary cross-check: INCONCLUSIVE at discovery** — the
   "Periodo del 4 al 11 de Marzo de 2019" PDF text layer is column-scrambled (e.g.
   "ELEVACIÓN 2047.57 msnm" for the Tijuana dam; ALMAC ÚTIL 77.43 vs SIH 14.557 on
   2019-03-04 with visibly wrong adjacent columns). Redo at construction with a proper
   PDF table parse of ftp://ftp.conagua.gob.mx/Gobmx/DisponibilidadenPresas/ — that
   archive also carries official per-dam capacities (CAPACIDAD MUERTA / CAP. UTIL DISEÑO),
   the preferred threshold frame.

**Threshold frame note:** press/CONAGUA percentages use official capacity (El Cuchillo
1,123 Mm3); the observed-max proxy (1,765.7, includes flood surcharge) gives a strictly
higher threshold (441.4 = 39% of official), so proxy-defined events are a subset of
official-frame events at the same 25% level. Capacity therefore holds under both frames.

## s6 — Dated worked example (prediction contract, one timezone: America/Mexico_City)

Dam: CCHNL "Cuchillo Solidaridad, N.L." (Clave CCHNL, Nuevo León).

- Feature event window: SIH daily rows with Fecha in [2021-07-01, T]; all values are
  current-vintage archive rows as they appear in the file fetched at the instant.
- Prediction instant: a fetch of `https://sih.conagua.gob.mx/basedatos/Presas/CCHNL.csv`
  after the weekly update, whose latest row is **T = 2022-06-30** (calendar day,
  America/Mexico_City). Observed rows in the current file: 2022-06-15 = 508.809,
  2022-06-30 = 489.325 Mm3.
- First-available timestamps: no point-in-time snapshots exist; the file as fetched on
  2026-10-27 carries rows through 2026-10-26, i.e. the archive is ~weekly-refreshed with a
  ~1-day data lag (per-dam; LDCVC lagged 29 days). Version = current vintage.
- Eligibility cutoff at T: ≥365 prior VolumenAlm rows (CCHNL has rows since 1993-09) and
  VolumenAlm(T) = 489.325 ≥ 441.4 → eligible.
- Target start/end: 2022-07-01 .. 2022-07-30 (whole days after T). Observed: 07-07
  484.123, 07-15 478.257, 07-31 461.962 — all ≥ 441.4 → **label 0** (the actual crossing
  was 2022-08-27, 58 days after T; a T = 2022-07-30 row has target window 07-31..08-29 and
  label 1 via the 08-27 crossing).
- No part of the target window precedes T; features use only rows ≤ T.

## s7 — Novelty (mechanical search + verdict)

`python3 scripts/check-novelty.py conagua-dam-drought-onset --query ... --verdict
differentiated` — output recorded in record.json (novelty_check). Prior art named:
ResOpsUS/ResOpsUS+CARS (US, raw daily series, reservoir-model parameterisation benchmark,
Zenodo 10.5281/zenodo.15978041), GROWL (global raw water-level/storage series, Sci Data
2026), Türkiye storage-forecasting studies (closed data). No ML-ready public
dam-storage drought-onset prediction task with as-of policy, splits and scored contract
found for any jurisdiction; none for Mexico/CONAGUA.

## s8 — Chile MMA episode declarations (second lead, cheap decisive probe)

Regional coverage probe (Chile). The GEC season label registry ("Registro de episodios
decretados", e.g. Informe GEC 2023: 36 alertas / 18 preemergencias / 2 emergencias,
table of dated decrees) is published **inside annual PDF reports**
(ppda.mma.gob.cl/wp-content/uploads/2024/07/Informe-GEC-2023.pdf and earlier seasons;
source "Reportes diarios SEREMI"). Same PDF-only distribution that dropped
`sag-residuos-plaguicidas` (CL) — and the air-quality family is already declined three
times on this bench for concentration targets (defra-aurn-pm25-exceedance, dropped:
"a genuinely different task formulation" is the reopen condition). SINCA does not expose
a machine-readable historical decree registry (portal checked via search + station data
is separate). Decision: not opened as a candidate record this tick; the label registry
is PDF-only and the bench has no appetite for a fourth air-quality-family instance on
current evidence. Reopen condition: a machine-readable GEC episode registry (API/CSV of
decretos) appearing on sinca.mma.gob.cl or ppda.mma.gob.cl.

## Probe scripts retained

- `probe_access.py` — access + schema first attempt (documents the Incapsula 403/302)
- `probe_schema.py` — catalog + ALRBN decade coverage
- `probe_sample.py` — 7 named dams (fixed-index parse, superseded by probe_parse2.py)
- `probe_parse2.py` — robust block-split/by-name parser + recompute (the correct recipe)
- `probe_fixtures.py` — per-dam onsets + minima dates
- `probe_splits.py` — 20-dam stratified sample + window counts (writes
  /opt/data/cache/scratch/conagua_splits_sample.json)

Raw sample CSVs live in ephemeral scratch (/opt/data/cache/scratch, pruned after 24 h);
summaries + this file are the durable evidence. Re-fetch any dam with the s1 recipe.
