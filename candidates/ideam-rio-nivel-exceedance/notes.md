# ideam-rio-nivel-exceedance — probe notes

Probes run 2026-10-23, read-only, anonymous HTTP (scripts in session scratch, deleted after push).

## 1. Socrata metadata and counts

- `https://www.datos.gov.co/api/views/vfth-yucv.json` → name "Nivel Máximo del Rio",
  licenseId `CC_40_BY_SA`, attribution IDEAM. Columns: codigoestacion, codigosensor,
  fechaobservacion, valorobservado, nombreestacion, departamento, municipio, zonahidrografica,
  latitud, longitud, descripcionsensor, unidadmedida.
- SoQL `SELECT count(*)` → 14,672,316 rows.
- SoQL `SELECT MIN(fechaobservacion), MAX(fechaobservacion)` → 2001-01-01T07:17 .. 2026-10-21T23:59.
- SoQL distinct codigoestacion → 345 stations.
- Rows by year: 2001: 2,612; 2005: 64,454; 2009: 844,095; 2015: 773,649; 2019: 1,547,326;
  2022: 446,478; 2023: 344,500; 2024: 618,874; 2025: 1,219,800; 2026 (partial): 991,988.
- Sample rows: hourly "Nivel Maximo" in metres, e.g. station 0029037701 COMPUERTAS GUAJIRO -
  C DEL DIQUE (Bolívar), 2018-02-14T00:26, 3.39 mt.
- First SoQL attempt used a wrong field name (`fecha_observation`) and returned HTTP 400;
  re-read the metadata for the correct `fechaobservacion` before recording the span — the
  negative was a query-typo artifact, not missing data.

## 2. Threshold hunt (unresolved — the blocking fact)

- Station catalog `cqmv-a99d` columns: Codigo, Nombre, Categoria, Estado, Departamento,
  Municipio, Ubicación, Altitud, Fecha_instalacion, Fecha_suspension, Corriente — no
  alert/danger threshold column.
- Catalog v1 search (`q=alerta nivel rio`) returned no machine-readable result.
- IDEAM's open-data page lists the full hydrometric family (hourly/monthly/annual levels and
  flows) but no threshold table in the bounded pass.
- Next probe must target SAIC/IDEAM flood-warning pages and any 'niveles de alerta' publication.

## 3. Licence and data-quality clauses

- Socrata licenseId `CC_40_BY_SA` on both datasets read.
- Dataset description: raw unvalidated instantaneous sensor data, freely consumable, published
  under Ley 1712 de 2014. Validated series ('Niveles Horarios', ig79-2jr9) document a
  preliminary → en revisión → definitivo lifecycle — the as-of/vintage question is unresolved.

## 4. What is NOT claimed

No base rate, no positive count, no split claim: none of these are measurable before a
threshold exists. Volume (26 years, 345 stations, 14.7M rows) is the only measured capacity
fact so far.

## 5. Threshold hunt pass 2 (2026-10-23, this session) - BLOCKER RESOLVED: official cotas exist, extractable from IHD archives

Channels probed (commands: plain HTTP GETs, scripts in session scratch disc-latam-20261023/probe2..19.py):

- **Current products do NOT carry per-station cotas.** Fetched the 10 most recent BAH files
  (290..295_bah_octubre_16..22_2026_*.pdf, 11-19 MB each, via www.ideam.gov.co/file-download/download/public/{id},
  ids listed on the BAH page), one ITD (295_itd_octubre_22_2026.pdf, 90 pp) and one BCH
  (885_bch_octubre_22_2026_1800.pdf, 85 pp): zone/municipality-level alert tables only; the only "Cota"
  in extracted text is the municipality of Cota (Cundinamarca). No per-station threshold values.
- **Historical IHD (Informe Hidrológico) DOES.** Wayback copy of
  10_IHD_Octubre_01_Dia.pdf (IHD dated 01 Oct 2016 per its first page; Wayback capture 20240805031921, 11 pp, 700,710 B, sha256 307c83c9…; pypdf extract_text) yields 16
  per-station "COTA CRITICA x.xx m" chart annotations, e.g. PUERTO SALGAR (Rio Magdalena) 6.20;
  EL BANCO (Magdalena) 8.30; LA VICTORIA (Cauca) 8.74; QUIBDO (Atrato) 6.50; CABUYARO (Meta) 7.36;
  PUENTE YOPAL (Cravo Sur) 3.48; CRAVO NORTE (Casanare) 8.68; SAN JOSE (Guaviare) 8.70;
  MAPIRIPAN (Guaviare) 11.39; PINALITO (Guejar) 5.47; PUERTO ANGOSTURAS (Ariari) 6.20;
  LA MACARENA (Guayabero) 8.79; PUERTO CARRENO (Orinoco) 14.27; PUERTO INIRIDA (Inirida) 11.14;
  MITU (Vaupes) 10.20; PUENTE TEXAS (Putumayo) 6.55. (Full json kept in session scratch; recipe =
  regex 'COTA CR[IÍ]TICA ([0-9]+[.,][0-9]+) M' over pypdf page text, station name from the 300 chars before.)
- **Two-sample match, not decade stability:** Puerto Salgar 6.20 and El Banco 8.30 are identical in the November-2014
  IHD (pronosticosyalertas.gov.co, web-search snippet) and the IHD dated 01 Oct 2016 extracted here (the
  2024-08-05 date is a Wayback capture, not publication; the document says it may be corrected) - cotas are
  stable gauge reference levels, so an archive-harvested threshold table stays valid.
- **Wayback CDX evidence of harvestability:** IHD PDFs archived on pronosticosyalertas.gov.co and
  ideam.gov.co /documents/78690/* paths, captures spanning 2017-2025 (40 per CDX query page, more behind
  pagination; collapse=urlkey). Live Liferay fetch of the Oct-2024 IHD timed out from this host
  (the archived copy works). Older IHD naming: NN_IHD_<MES>_<DD>_<Dia|Noche>.pdf.
- **No machine-readable threshold dataset exists on datos.gov.co** ('cota critica estacion' -> 0 results;
  'nivel de evacuacion' -> 0; 'cotas de inundacion' -> only a ronda/foreshore dataset). The Socrata
  "Alertas Hidrologicas" (h4gs-wsmg) is a NON-TABULAR view: /resource/h4gs-wsmg.json returns 403
  "no row or column access to non-tabular tables"; its own description presents the data only via the
  interactive daily report and warns the latest day's availability "no siempre estara disponible en un
  horario fijo" (a cadence caveat to quote if that dataset is ever used).

## 6. Join and base-rate evidence (2026-10-23)

- Telemetry panel: 345 distinct codigoestacion (SoQL count DISTINCT). Name field has 2-3 spelling variants
  per code (e.g. 0044017110 = "ANDAQUI", "ANDAQUI - AUT", "ANDAQUÍ - AUT [44017110]") - group by code, never
  by name. Catalog (cqmv-a99d) nombre embeds bracket codes; its 10-char codigo matches telemetry codigoestacion.
- **Name-collision trap measured:** IHD "PUERTO ANGOSTURAS - RIO ARIARI" (cota 6.20) matches telemetry
  0021137050 "ANGOSTURA" by name - but that station is Angostura del Magdalena (Natagaima). The join MUST
  use river/municipality + code, not name alone; the 11.96% rate measured for 0021137050 against 6.20 is a
  FALSE PAIR and is excluded from any claim.
- **Measured exceedances (SoQL, hourly maxima >= cota, 2015-01-01..2026-10-21):**
  - EL BANCO 0025027020, cota 8.30: 105,354 obs, 5,937 over (5.64% of hours). Distinct days over cota by
    window: train 2015-2019 = 137/1,777 days-with-data (7.7%); eval 2020-2023 = 137/828 (16.6%);
    holdout 2024-2026 = 111/957 (11.6%). Both classes in every window on this station; positives cluster
    into flood episodes (137 positive days over 5 years is NOT 137 independent events - clustered count
    at panel scale is construction's to measure). Telemetry gaps visible: eval window has data on only
    828 of ~1,461 days - continuity/gap rates must be measured per station before split windows are fixed.
  - CABUYARO 0035107030, cota 7.36: telemetry only from 2026-03-28 (4,886 obs, 135 over, 2.8%) - recent
    stations constrain which stations can carry historical windows.
  - MITU 0042077020, cota 10.20: 29,688 obs 2016-11-28..2026-10-21, ZERO >= cota - a frame/station
    anomaly (wrong station pairing, datum, or sensor range). Every joined station needs this zero/always-
    positive sanity check before entering the panel; unexplained-anomaly stations are excluded, not fixed.
- Access channels: current bulletins at www.ideam.gov.co/file-download/download/public/{id} (ids enumerated
  from the boletin pages); historical IHDs via web.archive.org CDX (url pattern recorded above).

What is NOT yet claimed: panel-scale station count with valid thresholds (IHD harvest pending), clustered
positive counts, per-station continuity tables, raw-vs-validated as-of comparison, novelty check.
