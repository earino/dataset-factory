# tw-typhoon-day-closure

**Verdict: go, status ready (updated 2026-10-31)** - the modern-era per-county extraction path
was proven by worker job east-asia-measure-002 (census below); everything else was already
measured.

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

## Modern-era label extraction resolved (2026-10-31, session tick East Asia)

Commands: probe_modern_label.py (this dir), /tmp scratch probes replicated in
measure_run.py part B (probe/), worker job east-asia-measure-001/002.

| Probe (all anonymous, DGPA SSL unverified context as recorded 2026-10-22) | Result |
|---|---|
| Daily view `/typh/daily/nds.html` date parameterisation (6 variants incl. ?date=2024-10-03, ?d=1131003, ?ymd=1131003) | NOT parameterisable: byte-identical 13,113 B response for every variant; no form/date controls in HTML. Current-day only. |
| Announcement body text (pid 13128/13129/13130/13097/13095) | No county names in body; statuses live only in the nds.html attachment. Titles carry the effective date: "115年10月24日天然災害停止辦公及上課情形". |
| pid=13130 attachment (2026-10-24 typhoon) | 20,342 B static table, ALL 22 counties: 13 rows "今天已達停止上班及上課標準" (closure reached), 9 rows "今天未達...". |
| pid=13097 attachment (2026-09-02) | **CORRECTION of the 2026-10-22 "shell only" reading**: the attachment DOES carry a status row - "屏東縣|春日鄉士文村:今天停止上班、停止上課。" (township-level closure). The old probe checked only 臺北市/高雄市/照常辦公/停止辦公 phrases; 屏東縣 with 停止上班 phrasing was missed. The "shell" dates were partial-closure days, not missing labels. |
| Old-era attachment (pid=7100, 2011-03-11, descriptive .htm name, Big5) | Parses: 6 county rows (5 county-wide closures + 1 partial). Old records name the Chinese attachment descriptively, not nds.html - extraction must take the first non-English FileConversion link. |
| Archive census (50 list pages) | 500 announcements = 500 DISTINCT effective dates, 2001-2026, every year populated (5-66/yr; 2024: 66, 2025: 65, 2026: 30 through 10-31). One archived record per effective date D (final status). |
| data.gov.tw related datasets of 20457 | 84387 臺中市歷次發布天然災害停止上班上課相關訊息一覽表: machine-readable CSV (西元年,月,日,災害類別,狀況,備註), 80 rows 2018-07-10..2026-06-10, per-day Taichung status incl. district-level closures (newdatacenter.taichung.gov.tw, fetched 2026-10-31, 7,304 B). 161017 桃園市 yearly register exists on opendata.tycg.gov.tw (not fetched). County-portal path works but is per-county; the DGPA archive covers all counties and is the primary label source. |
| DGPA licence (https://www.dgpa.gov.tw/archive?uid=75, 政府網站資料開放宣告, 106.03.28, fetched 2026-10-31) | "行政院人事行政總處全球資訊網上刊載之所有資料與素材...以無償、非專屬，得再授權之方式提供公眾使用，使用者得不限時間及地域，重複、改作、編輯、公開傳輸或為其他方式之利用，開發各種產品或服務...此一授權行為不會嗣後撤回，使用者亦無須取得本機關之書面或其他方式授權；然使用時，應註明出處。" - free, non-exclusive, sublicensable, reuse+derivatives any time/place, irrevocable, attribution required. Class B; covers the closure archive on the DGPA site itself. |

Classifier (measure_run.py part B, validated on 4 fixtures before launch): 13130 -> 13 full + 9 open;
13097 -> 1 partial (屏東縣); 7100 -> 5 full + 1 partial; 7018 (2011-08-28 Nanmadol) -> 2 full + 19 open.

Licence class reclassified 2026-10-31 from the cautious "Class B" reading to **A**:
the directly quoted 政府網站資料開放宣告 is attribution-only (no sharealike, derivatives
explicitly allowed, irrevocable) - the same posture as CC BY, which the triage table
puts in class A. The 2026-10-22 "Class B" line above predates having the quote.

Census result (worker east-asia-measure-002, report probe/measure_report_2026-10-31.json):
500/500 processed, 0 fetch errors; 24 records (all 2013) label-absent (no attachment, no
county rows - verified on pid 7066/7067 by hand); 216/500 records with >=1 county-wide
full-day closure; 1,333 county-day positives; 100 event runs (sizes 19,10,9,5,4,3...);
per-year both classes present 2001-2026 (2020 min: 2 positives; 2024 max: 158).
Pollen part of the same job: see candidates/jp-moe-pollen-exceedance/notes.md.

Follow-up (2026-10-31, worker-watch session): -001 failed at 46 s - python:3.13-slim ships no
xlrd, all 64 .xls pollen files parsed as None and part_a crashed (KeyError 'censored') before
the DGPA census ran; infrastructure failure, recovered in the same tick by -002 (command
prefixed pip install xlrd), the one permitted recovery. All 7 staging assets of releases
429614137/429618656 sha256-verified on the coordinator (.factory/east-asia-measure-*/reports/).
Both workers destroyed; Hetzner read-back: 0 servers, 0 primary IPs. The recorded positives
total was corrected to 1,333 (the tick session had written ~1,395).
