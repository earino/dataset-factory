# ar-ecobici-station-demand-exceedance — probe notes

Probes run 2026-10-23, read-only, anonymous HTTP (scripts in session scratch
disc-latam-20261023/probe4..20.py, deleted after push). Opened as the Argentina
coverage lead (Argentina had zero candidates) and closed at the novelty gate.

## 1. Licence (class A — not the blocker)

- CKAN package_show id=bicicletas-publicas (data.buenosaires.gob.ar): license_id
  `CC-BY-2.5-AR`. Dataset page shows "Licencia CC-BY-2.5-AR". Attribution-only.
- Third-party audit (1001smartcities.org, 2026-07-26): all 451 BA datasets carry
  CC BY variants; the city's own publication guide claims CC BY 4.0 always applies —
  a version contradiction, not an openness question.

## 2. Access and inventory (measured, HEAD requests 2026-10-23)

- Trips = one file per year 2010-2026 at
  cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/bicicletas-publicas/
  (2010-2013 CSV, 2014-2026 ZIP). All 17 years HTTP 200 with Content-Length; sizes
  0.68 MB (2010) .. 398 MB (2019), ~1.75 GB total. Full table in record.json sources.
- Publication cadence evidence from CDN Last-Modified: the current-year file updates
  in-year (2026 file: 2026-10-07; portal metadata_modified 2026-10-08) and year-Y
  files stop after year end (2023 -> 2024-01-03; 2024 -> 2025-03-01; 2025 -> 2026-01-14).
  2010/2013/2020 stamps read 2023-03-06/07 — a CDN migration stamp, not a content date.

## 3. Bounded sample (2015)

- Downloaded recorridos-realizados-2015.zip: 8.8 MB in 30.8 s (0.3 MB/s), single member
  116,754,579 B uncompressed; parsed 503,252 trips, 15 documented columns (periodo,
  genero_usuario, fecha_origen_recorrido, id/nombre/long/lat/domicilio estacion origen,
  duracion_recorrido, fecha_destino_recorrido, id/nombre/long/lat/domicilio estacion
  destino). Station-day aggregation directly constructible.
- The 2026 partial-year sample (143 MB) download was started and killed: the novelty
  gate had already closed the task, so no recent-era station-day counts were measured.
  Recorded as not-measured.

## 4. Novelty search (the decisive gate — see novelty_check in record.json)

- Task family (bike-share demand prediction) is saturated and exists ML-ready for
  other cities: UCI Bike Sharing hourly, Seoul Bike Sharing Demand, Kaggle Bike
  Sharing Demand (2015); active literature across NYC/Beijing/Shenzhen/Seoul.
- Ecobici-specific: UTDT thesis predicting Ecobici demand 2018-2020 (econometric +
  panel models + rebalancing optimisation); UBA datamining course project benchmarking
  xgboost on Ecobici 2016-2017 with weather, explicitly comparing to the Kaggle
  competition (RMSLE 0.90-0.93); a TFI predicting 2016 hourly demand with weather;
  a UTDT thesis on Ecobici user churn; and a third-party Kaggle mirror of the 2025
  trips ("3.15M+ trips", usability 10/10, EDA notebook, "great for ML projects").
- What would have been ours (splits, gating, frozen-threshold binary exceedance) is
  packaging on a saturated task. Verdict: mirror → dropped. check-novelty.py recorded
  verdict=mirror (2026-10-23).

## 5. What is NOT claimed

No split counts, no base rates, no station-day panel, no model results: nothing was
constructed. The licence and access evidence is recorded so a reopen does not
re-verify it.
