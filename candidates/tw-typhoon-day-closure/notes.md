# tw-typhoon-day-closure

**Verdict: go (2026-10-22), status investigating** - the one unproven step is the
modern-era per-county extraction path; everything else is measured.

## The task

Predict, at the statutory announcement instant (19:00-22:00 TPE on D-1, quoted from the
DGPA's own operating-rule text), whether a Taiwan county fully stops work and school on D.
Label = the government's own published decision; features = only what was published before
the instant (CWA typhoon warning bulletins, prior closure status, county identity).

## Probe evidence (2026-10-22, all anonymous; commands in probe_dgpa_archive.py)

| Probe | Result |
|---|---|
| DGPA 歷次 list page 1 (`/informationlist?uid=374&pgnum=50&page=1`) | 500 records, 50 pages; newest 115.09.03 (2026-09-02) |
| Same, page 50 | oldest record 民國90.07.30 (2001-07-30) -> 25 typhoon seasons |
| Detail page `/information?uid=374&pid=13097` | 34,360 bytes; 2 FileConversion attachments (nds.html + ndsE.html) |
| 2002 attachment (Big5) | static per-county table: 區域/縣市名稱/是否停止辦公上課情形, e.g. 基隆巿 今天照常辦公、照常上課 |
| 2024-10-04 attachment (pid=12145, typhoon Krathon day) | static UTF-8 county table, 21,661 bytes |
| 2023-06-01, 2025-09-30, 2026-09-02 attachments | shell only (statutory disclaimer block, no county rows) - modern-era extraction step unproven |
| Daily current-day view `/typh/daily/nds.html` (browser) | server-rendered per-county statuses for today (縣市名稱/是否停止上班上課情形), NO XHR - data is in the HTML |
| Timing rule (on the daily view and in attachments) | 全日或上午半日停止上班及上課: 前一日晚間7時至10時前發布; same-day reinforced closures 04:30前發布/05:00前播報 |
| data.gov.tw dataset 20457 | DGPA CAP feed, Open Government Data License 1.0, free, RSS+KMZ (current only) |
| data.taipei 臺北市歷次 CSV | 9.49 KB, 民國年/月/日/災害名稱/停止上班上課情形, yearly updates - per-county fallback template |
| CWA TDB (rdc28.cwa.gov.tw) | warning-typhoon list 1958-2026; per-typhoon pages carry issuance/release timestamps and bulletin counts |

## Access notes for construction

- DGPA HTTPS fails strict SSL validation (chain missing Subject Key Identifier); the probe uses an
  unverified context. The browser accepts the chain as-is. Record this in the build script.
- Older attachments are Big5; 2024+ are UTF-8. Detect per file.
- data.taipei is IPv6-only from this host; fetch it on a worker or via a browser.

## Licence

ODDL 1.0 (data.gov.tw mirror of the DGPA data) + CWA/DGPA government-website open
declarations: free use, redistribution and derivatives, attribution required. Class B.
