# gba-hospital-quality-breach - discovery notes

Tick: 2026-10-24, regional focus Europe - EU/EEA (German national
sector-regulator publisher). Closed at licence/access triage; no order form
submitted, no XML downloaded.

## The would-be task

For a German hospital site (Standort) with a published Structured Quality
Report (Strukturierter Qualitaetsbericht, statutory under SGB V §136b) for
reporting year N-1: will any of its external quality-assurance indicator
values breach the reference range (unterschritten/ueberschritten) in
reporting year N? Features would be the site's published indicator history,
procedure volumes and structure data; the label is a published, thresholded
result. Population ~1,500-2,000 sites; reports annual since 2005; a
regulator-driven clean timing contract (reports publish each spring for the
prior year).

## Evidence trail (2026-10-24)

1. IQTIG (iqtig.org/veroeffentlichungen/strukturierterqualitaetsbericht):
   recommends per year which indicator/Kennzahl values are published
   standortbezogen (Berichtsjahr 2025: 177 Qualitaetsindikatoren + 83
   Kennzahlen = 260 results; BJ 2024: 185 + 81 = 266). Downloads measured:
   Indikatoren- und Kennzahlenuebersicht CSV 402 KB / XLSX 50 KB - these
   are indicator DEFINITIONS, not per-hospital values.
2. G-BA fachnews (2026-03-18): Berichtsjahr 2024 reports online in the
   Referenzdatenbank as PDFs; "maschinenlesbare Version" feeds commercial
   clinic search engines via the Qb-Datenportal XML channel.
3. Qb-Datenportal (qb-datenportal.g-ba.de/): "Die maschinenverwertbaren
   Daten der Qualitaetsberichte liegen ... (XML) vor... Sie werden auf der
   Grundlage der Allgemeinen Nutzungsbedingungen zum Download zur
   Verfuegung gestellt. Hierzu ist eine Bestellung ueber das
   Auftragsformular erforderlich. Nach erfolgreicher Verifizierung der
   Auftragsdaten erhalten Sie individuelle Zugangsdaten fuer den Download
   der gewuenschten Qualitaetsberichtsdaten."
4. ANB (qb-datenportal.g-ba.de/anb), read in full: §3 free of charge;
   §2 contract per order form; §7 provision after registration + order;
   §4(2) redistribution only if declared on the order form with recipient,
   platform, purpose, scope; §4(3) unprocessed redistribution requires the
   G-BA's PRIOR WRITTEN CONSENT; §4(5)-(7) attribution-style display duties;
   §5(2) duty to notify G-BA of future publications making statements about
   specific hospitals; §6 user data stored to check ANB compliance per case;
   §9 contractual penalty and exclusion up to four years.
5. No alternative anonymous bulk channel found: per-hospital PDFs only
   (one per site per year), IQTIG aggregates only. No govdata.de or
   data.europa.eu distribution of per-hospital values was found in this
   tick's searches.

## Decision

The machine-readable panel exists in exactly the needed shape, but it sits
behind a gated, conditional instrument (ANB) and no anonymous bulk channel
exists. Standing policy: build only on clean sources; no order form was
submitted. Class C (conditional application-based instrument). DROPPED.

Reopen conditions (record.json rejection_reason): an anonymous
machine-readable distribution of per-hospital values under an open licence
(govdata/data.europa, dl-de or CC BY), or an operator-recorded decision to
apply under the ANB.
