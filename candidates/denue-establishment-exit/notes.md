# denue-establishment-exit — notes

INEGI DENUE (Mexico). Opened 2026-10-21 in the Latin America discovery tick — the candidate
directory existed as an empty, unrecorded stub from a prior session (see STATE.md). All probes
anonymous.

## Access probes

`python3 probe_denue.py` (kept in this directory) — 2026-10-21, 31 requests, 32 s:

- **Current edition bulk** (`https://www.inegi.org.mx/contenidos/masiva/denue/denue_00_{sector}_csv.zip`):
  25/25 sector zips are REAL (PK magic on ranged 0-15 GET; sizes via Content-Range). Measured
  total 571,891,279 B (572 MB) compressed. Per-sector sizes in the probe output (largest
  46111: 59,835,497 B; smallest 55: 58,074 B).
- **This publisher soft-404s**: `zzz_nonexistent.zip` returns HTTP 200 + HTML error page, exactly
  like every historical-edition variant probed. HTTP status is meaningless on inegi.org.mx —
  only the first-bytes zip-magic check distinguishes a real file. (This cost the first probe
  round: an earlier HEAD-based probe wrongly reported "200 OK" for 2015/2019 paths.)
- **Historical editions absent**: patterns `2019/denue_00_23_csv.zip`, `denue_2019_00_23_csv.zip`,
  `2015/denue_00_23_csv.zip`, `denue_05_2024_00_23_csv.zip` → all HTML error pages behind 200.
  The Descarga Masiva app (`/app/descarga/?ti=6`) serves the current edition only; its JSON API
  (POST `/app/api/descarga/descarga/descargamasiva/lista/obtenerlistado`) answers
  "Ocurrio un error" without the SPA's full filter vocabulary (not pursued; direct masiva URLs
  suffice for the current edition).

## What the editions are (documented but not published)

- RNM study catalogue (inegi.org.mx/rnm/index.php/catalog/924, /979, fetched 2026-10-21):
  semiannual editions since 2019 (05/2019 … 05/2024, 11/2024 — ~12 editions), per-edition
  establishment counts (DENUE 05/2024: 5,564,612; 11/2024: 6,058,548), and the key fact an exit
  panel would rest on: "se mantiene la publicación de la clave ID del DENUE para identificar a
  cada establecimiento y, como factor vinculante de los datos entre las diferentes versiones
  publicadas" — the ID is the cross-version linking key.
- The catalogue's own "Descarga masiva" link points at the same current-edition-only app.

## Licence (2026-10-21)

INEGI Términos de Libre Uso (inegi.org.mx/inegi/terminos.html + /contenidos/inegi/doc/terminos_info.pdf):
"Puede hacer y distribuir copias de la información… Puede difundir y publicar la información…
Puede explotar comercialmente la información… Debe otorgar los créditos correspondientes al INEGI
como autor, y cuando técnicamente sea posible, mencionar la fuente… 'Fuente: INEGI, nombre del
producto de donde se extrae la información'". Settled (free use incl. commercial, attribution);
NOT the blocker.

## Why parked

Split capacity is unbuildable: the exit label needs consecutive-edition diffs, and only ONE
edition is downloadable. Measured absence of historical editions (soft-404 pattern above), not
assumed. Secondary (recorded comparison, not the primary reason): the entity-exit family is
already carried by companies-house-company-exit (GB); a second same-family task needs an explicit
operator decision (same reasoning as the air4thai park).

## Verdict

PARK (parked) 2026-10-21. Unpark conditions in record.json: a verifiable archive of ≥4 historical
editions (probe with zip-magic, not status), an institutional mirror with counts verifiable
against the published per-edition totals, or an operator decision + such a source. If reopened:
first probe is a known-event fixture (a large surviving retail chain must survive across
editions) because ID churn reads as exit.
