# inpe-foco-municipal-onset — probe notes

All probes run 2026-10-23 from the coordinator container (4 vCPU). Scripts were kept in
`/opt/data/cache/scratch/inpe_probe*.py` (session scratch; deleted after push). Read-only,
anonymous HTTP.

## 1. Repository and access contract

- Repository listing `https://dataserver-coids.inpe.br/queimadas/queimadas/` → `focos/csv/{anual,mensal,diario,10min}`, `riscofogo_meteorologia/{observado,previsto}`, `focos/documentos/`.
- DNS: `terrabrasilis.dpi.inpe.br` does not resolve from the coordinator resolver
  (`gaierror -3`); resolved via DoH (cloudflare) to 150.163.2.5 and fetched with SNI
  (`server_hostname=terrabrasilis.dpi.inpe.br`), and independently with the supported
  browser — both work. `data.inpe.br` (150.163.218.3) resolves and mirrors the portal.
- Annual reference-satellite inventory `focos/csv/anual/Brasil_sat_ref/`: `focos_br_ref_2003.zip`
  … `focos_br_ref_2025.zip` (23 files, 2.5–11 MB). All-satellite annuals 1998–2025 (2.4–112 MB).

## 2. Full-year counts (downloaded and counted, probe9)

| year | rows | distinct municipios | municipio-days with ≥1 foco |
|---|---|---|---|
| 2019 | 197,632 | 4,417 | 53,369 |
| 2020 | 222,797 | 4,447 | 54,956 |
| 2022 | 200,763 | 4,038 | 49,559 |
| 2024 | 278,299 | 4,502 | 62,450 |

Command shape: fetch `focos_br_ref_{ano}.zip`, unzip member `focos_br_ref_{ano}.csv`,
schema `id_bdq,foco_id,lat,lon,data_pas,pais,estado,municipio,bioma`, group on
`(estado, municipio, data_pas[:10])`.

2024 onset-conditioned (day-of-year 20..360, zero focos in past 14 d, target ≥1 in next 7 d):
1,173,526 pairs, 88,888 positives (7.57%). Raw pairs: 1,535,182 / 244,175 (15.9%).

## 3. Cross-check against the publisher's own summary product

`https://data.inpe.br/queimadas/portal/csv/download/historico-mensal/estados/mato_grosso.csv`
(reference-satellite monthly totals). My MT-2024 counts from `focos_br_ref_2024.zip`:
Jan 847, Feb 863, Mar 1624, Apr 797, May 1996, Jun 2671, Jul 2472, Aug 14617, Sep 19964,
Oct 3814, Nov 435, Dec 451 (total 50,551) — identical to the CSV row `2024`.

## 4. Schema of the monthly all-satellite files (probe6, partial 25 MB of 202406)

`id, lat, lon, data_hora_gmt, satelite, municipio, estado, pais, municipio_id, estado_id, pais_id,
numero_dias_sem_chuva, precipitacao, risco_fogo, bioma, frp`. Satellite mix (partial):
GOES-16 38,953; NOAA-20 36,133; NOAA-21 34,924; NPP-375 19,837; NPP-375D 10,310; AQUA_M-T 5,720;
TERRA_M-T 2,669; METOP-B 2,270; METOP-C 2,069; TERRA_M-M 2,191; AQUA_M-M 699; MSG-03 754.
All-satellite counts are constellation-size-dependent → target defined on the reference series.

## 5. Publication timing (lastmod evidence, probes 7/9)

- `focos/csv/diario/Brasil/focos_diario_br_20261021.csv` lastmod `2026-10-22 09:05`;
  the 20261022 file was already written during 2026-10-22 (20:06, 3.6 MB), the 20261023 file
  existed at 143 bytes on 2026-10-22 21:06. Portal: updates every 10 minutes; day-D file complete
  by 09:05 on D+1.
- Risk grids `INPE_FireRiskModel_2.2_FireRisk_20260104.nc` lastmod `2026-01-05 03:32` →
  observed risk for day D published early on D+1; `previsto/` holds D+1..D+3 forecasts.
- Observed risk NetCDF archive on the dataserver starts 2026-01-01 (285 files through
  2026-10-21) — not a feature for historical windows; a live-period baseline comparison only.
- Estatísticas page: current-month values partial "até ontem" (through yesterday).

## 6. Licence instruments read

- Portal footer: "2025 • Dados Abertos para Uso Público • Programa Queimadas do INPE".
- FAQ Q3: data free of cost for any user. Q18: transfer to any GIS/use free. Q36: citation format.
- `data.inpe.br/geonetwork` record (potential structured licence): HTTP 502 on all attempts.
- Governance PDF `Curadoria-Governanca-Dados-FocosFogoAtivo.pdf` (fetched, 22 pp): internal
  INPE document boilerplate ("não podendo ser reproduzido... sem prévia autorização") — about
  the *document*, not the data; not treated as a data-terms instrument either way.

## 7. Extraction cost

4 ref years = 35,536,896 B / 16.9 s wall on the coordinator. All 23 ref years ≈ 150 MB
(sum of measured per-file sizes) — minutes on the worker.

## 8. Negative/absent findings (probed, not assumed)

- No structured licence field readable (geonetwork 502) — recorded as unread channel.
- No historical file vintages: files regenerated 2025-09-08 (2003–2017) and 2025-06-06 (2024);
  no Wayback-style vintage archive found on the dataserver.
- No ML-ready Brazilian fire benchmark artifact found in catalogue/literature search — see
  `novelty_check` in record.json (closest artifacts named there).
