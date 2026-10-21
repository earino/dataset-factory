# chilecompra-tender-outcome — notes

ChileCompra / Mercado Público (Chile). Opened 2026-10-21 in the Latin America discovery tick.
Everything below was measured anonymously from the coordinator (no ticket, no registration).

## Access probes

`python3 probe_desertion.py` (kept in this directory) — 2026-10-21, 214 requests, 2.67 MB, 209 s:

- Monthly licitación totals via `https://api.mercadopublico.cl/APISOCDS/OCDS/listaOCDSAgnoMes/{y}/{m}/1/1`
  (`pagination.total`): 2010-01: 33,366 · 2014-01: 22,218 · 2018-01: 13,049 · 2020-01: 11,661 ·
  2023-01: 11,382 · 2025-01: 7,785. (Earlier quick probes also: 2012-01: 27,701; 2015-01: 20,228;
  2021-01: 7,431; 2026-01: 8,101; 2026-06: 9,302.)
- First 100 processes of closed month 2019-06, award docs fetched: `active` 78 (79.6%),
  `unsuccessful` 17 (17.3%), `cancelled` 3 (3.1%); 2 processes without `urlAward`.
- First 100 processes of 2023-06: `active` 78 (79.6%), `unsuccessful` 14 (14.3%), `cancelled` 2 +
  `cancelled | 15-Revocada` 2 (4.0%), 1 empty status; 2 without `urlAward`.
- Award statusDetails vocabulary observed: `7-Desierta (o art. 3 ó 9 Ley 19.886)`, `8-Adjudicada`,
  `15-Revocada`. The desertion label is directly machine-readable in the OCDS award release.
- Doc sizes: award docs avg 11,418 B (2019-06, n=98) / 8,488 B (2023-06, n=98); tender docs avg
  100,620 B (2019-06, n=5) / 31,987 B (2023-06, n=5). API throughput ~1 req/s ⇒ per-process
  fetching cannot build the historical panel; the monthly bulk zips below are the channel.

## Bulk monthly OCDS zips (construction path)

Found in the datos-abiertos React bundle (`main.b731c6dc.js`, 3.1 MB): the descargas page
documents `https://ocds.blob.core.windows.net/ocds/yyyymm.zip` with "variantes URLs en las que
se modifique la fecha del archivo".

Ranged GET (bytes 0-3, PK magic + Content-Range), 2026-10-21:

- 200901, 200906, 201001, 201406, 201806, 201906, 202006, 202106, 202112, 202202, 202203,
  202204 → real zips. Sizes: 201001: 377,010,777 B; 201406: 948,139,521 B; 201806: 613,891,953 B;
  201906: 1,131,029,693 B.
- 202205, 202206, 202212, 202301, 202306, 202509, 202510 → clean Azure 404 ("The specified blob
  does not exist").

Series = 2009-01 .. 2022-04 (160 months). Panel bytes ESTIMATE ~100-150 GB compressed.

## Provenance streams (per the discovery skill's stream-mix rule)

The OCP registry (data.open-contracting.org/es/publication/144, fetched 2026-10-21) records
that the publisher's bulk downloads carry **only the Licitación stream**; Trato Directo
(`listaOCDSAgnoMesTratoDirecto`) and Convenio Marco (`listaOCDSAgnoMesConvenio`) are separate API
streams. The task is defined on the licitación stream only; streams are not summed. The OCP's own
harvest (Jan 2022–May 2026, all streams) counts 4,920,375 licitaciones / 4,939,558 awards —
cross-check aggregate only. OCP also hosts per-year mirrors (full.jsonl.gz 2,527 MB; 2022: 506 MB;
2023: 620 MB; 2024: 682 MB; 2025: 434 MB; 2026: 186 MB) — not the construction bytes; publisher
bytes preferred.

## Licence channels (posture procedure, all 2026-10-21)

1. OCP registry: "Licencia: Creative Commons CC0 1.0 Universal Dedicación de Dominio Público …
   Puede copiar, modificar, distribuir e interpretar la obra, incluso para propósitos comerciales,
   sin pedir permiso."
2. Publisher's own terms (chilecompra.cl/terminos-y-condiciones/): "La plataforma de Datos
   Abiertos, a disposición del público en general … en formatos que facilitan su análisis,
   monitoreo y fiscalización, así como la reutilización de la información para el desarrollo de
   nuevos informes o aplicaciones." Also confirms the platform publishes in the OCDS standard.
3. Statutory: chilecompra.cl/datos-abiertos/ — the Ley de Compras Públicas amendments effective
   2024-12-12 require "formatos de datos abiertos y reutilizables" for all system information.
4. Channels with NO licence statement (measured): datos-abiertos React bundle (grep for
   licencia/términos/creative commons: no match); OCDS list API metadata (no licence field);
   publisher publication-policy URL recorded by OCP
   (api.mercadopublico.cl/APISOCDS/Utilidades/Politicas/Actualizacion → HTTP 404);
   datos.gob.cl CKAN package_search q=chilecompra → count 0; Política de Gobierno de Datos PDF
   (Res. Exenta 143-B/2024) = internal staff rules only.
5. Field dictionary for the (ticket-gated, unused) v1 API:
   chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf
   — documents tender states "publicada, cerrada, desierta, adjudicada, revocada y suspendida",
   buyer fields, procedure-type codes L1/LE/LP/LQ/LR/E2/CO/B2/H2/I2/LS, currency and payment-term
   code tables.

## Novelty

`check-novelty.py` run 2026-10-21, verdict `differentiated` (in record.json). Prior art compared
explicitly: TenderKG (FR, bidder recommendation), ANAC-Italy tender-variation ML, TED/CAN
void-rate analysis (Springer 2026), MiDES (BR municipal raw tables). None ships a
desertion-prediction task with splits and a scored contract.

## Verdict

GO (ready) 2026-10-21. All four discovery contracts hold with measured evidence: licence
(CC0 registry + publisher reuse terms + statutory mandate), timing (publication instant;
award fields excluded), target (award status unsuccessful/desierta, 14–17% measured base rate),
splits (160 anonymous bulk months; windows proposed in record.json), not a mirror (novelty
check recorded). Next action in record.json names the construction steps.
