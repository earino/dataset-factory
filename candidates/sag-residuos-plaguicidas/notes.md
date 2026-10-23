# sag-residuos-plaguicidas — probe notes

Probes run 2026-10-23, read-only, anonymous HTTP + web search.

## 1. What the publisher actually distributes

- SAG "Monitoreo de residuos de plaguicidas" page links annual programme reports as PDFs, e.g.:
  - `https://www.sag.gob.cl/sites/default/files/Resultados%20Programa%20de%20Control%20Residuos%202025%20OK.pdf`
    (2025: 9,390 samples analysed; summary tables by substance group).
  - `...informe_anual_programa_nacional_de_monitoreo_de_residuos_de_plaguicidas_en_vegetales_de_exportacion_ano_2009-2010.pdf`
    (1,639 samples; 10 unauthorized residues = 0.4%; ~99% MRL compliance; exceedance details
    like Durazno/Iprodione 11.19 mg/kg vs LMR 10).
- No CSV/JSON/API distribution of sample-level results was found on the SAG pages.

## 2. National catalog check (datos.gob.cl, CKAN API)

- `package_search?q=residuos%20plaguicidas` → 0 datasets.
- `package_search?q=plaguicidas` → 3 datasets: "Listado de Plaguicidas" (SAG, cc-nc; PDF+CSV —
  the registered-products list, NOT monitoring results) and two regional applicator registries
  (cc-nc). None contain residue-monitoring sample results.

## 3. Licence posture

- No terms/licence statement found on the monitoring page or in the report PDFs.
- SAG's other catalog entries are cc-nc (non-commercial) — evidence of the publisher's general
  posture, not a grant for this data.
- Classification: C (unstated) + PDF-only distribution → closed under the standing policy;
  recorded in record.json rejection_reason with the reopen condition.

## 4. What a reopen would need

Machine-readable sample-level results (commodity, origin, region, date, programme, residues
found, MRL reference, verdict) under an open licence. Multi-year union would be needed: the
measured positive rate is ~0.4–2% at ~1.6k–9.4k samples/year.
