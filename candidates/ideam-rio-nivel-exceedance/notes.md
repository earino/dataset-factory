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
