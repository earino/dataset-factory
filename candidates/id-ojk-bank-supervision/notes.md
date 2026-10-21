# id-ojk-bank-supervision — probe notes

Discovery session 2026-10-21. Verdict: park (licence + access). All probes from the coordinator:

- https://www.ojk.go.id/ 200, 655,895 B, 17.1 s. SPI page 200, 384,394 B, 9.0-13.9 s.
- SPI page text: 'Terhitung sejak publikasi data periode Juli 2025, penyajian Statistik Perbankan
  Indonesia (SPI) dialihkan sepenuhnya ke Portal Data Sektor Jasa Keuangan Terintegrasi
  ("Portal Data") yang dapat diakses pada tautan https://data.ojk.go.id/SJKPublic'; pre-July-2025
  periods remain downloadable on the old pages (whose monthly archive is JS-loaded - only the
  'Mapping Statistik Perbankan SPI.xlsx' link is present in served HTML; 49 <script> tags).
- https://data.ojk.go.id/SJKPublic 200, 47,249 B, 2.0 s, title 'OJK - Portal Data', custom JS app.
- GET https://data.ojk.go.id/SJKPublic/Dataset/Dataset 200 but HTML shell (37,873 B).
- POST https://data.ojk.go.id/Public/GetIndustriData -> 200 with WAF body 'Request Rejected ... Your
  support ID is: 17926015242475000066' (247 B): scripted data access is walled.
- Terms: https://www.ojk.go.id/id/Pages/syarat-dan-kondisi.aspx 200, 377,070 B; full text has no
  redistribution permission; only rights statement is footer 'Copyright Otoritas Jasa Keuangan
  2024'. /id/term-of-use.aspx 404.
- Site nav confirms a published 'Status Pengawasan Bank' product (Bank Umum / Bank Perekonomian
  Rakyat / Bank Syariah); history/format unmeasured (same walled channel).

Why park, not reject: per-bank monthly panel + published supervisory status is a task family the
bench lacks entirely; both blockers (licence silence, JS/WAF channel) are removable by a
real-browser re-read plus a licence enquiry. No US source substituted for this tick.
