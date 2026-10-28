# austender-contract-amendment-occurrence — discovery notes

Opened 2026-10-28 (Oceania regional tick). All probes anonymous HTTPS from the
coordinator. Retained probe scripts (this directory) reproduce every number quoted
in record.json:

- `probe_channels.py` — catalogue metadata, licence terms extraction, weekly export,
  amendments-report window download, OCDS negative finding.
- `probe_fy_panel.py` — FY2017-18 CSV stream measurement (31.0 MB, 73,458 rows).
- `probe_cohort_rate.py` — the decisive 12-month amendment-rate measurement
  (Jul-2017 parent cohort vs Aug-2017..Jul-2018 follow-up).

## Dated example (named timezone)

Source publication timestamps carry no explicit timezone; AusTender is an
Australian Government system and server time is assumed Australia/Sydney
(AEST/AEDT). The assumption is recorded here to be confirmed at construction
(it affects nothing at day granularity, which is what the label window uses).

Feature event window: contract award (up to ~42 days before publication per the
Commonwealth reporting window) and the notice's publication at instant T.
Example CN3439382 (Austrade, "Temporary Personnel: Marketing Advisor"):

- First publication/version: parent Contract Notice published T =
  2017-07-07 15:48:21 Australia/Sydney (Excel serial 42923.658576..., report
  channel, second precision). All shipped features are this row's fields:
  agency, supplier, value, UNSPSC, procurement method, description, dates.
- Eligibility cutoff: Contract Notice Type = Parent, publish date inside the
  split window, value at/above the reporting threshold (all rows are).
- Prediction instant: T = 2017-07-07 15:48:21.
- Target window: (T, T + 365 days] = 2017-07-07 15:48:21 .. 2018-07-07 15:48:21
  Australia/Sydney. No part of the target window precedes the instant.
- Outcome: first amendment notice CN3439382-A1 published 2017-09-06 16:10:18
  (60.9 days after T) -> label TRUE, verified in the cached follow-up file.

Three more verified TRUE fixtures with full datetimes: CN3441078 (2017-07-14
10:16:37 -> -A1 2017-09-01 09:37:22, 48.9 d), CN3444589 (ABS Printing Services,
2017-07-25 11:44:26 -> -A1 2018-02-19 13:50:05, 208.9 d), CN3438465 (2017-07-06
08:58:03 -> -A1 2018-03-27 15:57:59, 264.2 d).

Boundary fixture: CN3350299 (Defence, "Provision of new air combat capability"),
parent published 14/06/2016; amendment CN3350299-A16 published 19/10/2017
(16 months). TRUE at an 18-month horizon, FALSE at 12 months — the window
definition is load-bearing and this row proves it.

## Channel map (measured 2026-10-28)

| Channel | Covers | Amendment events? | Cost |
| --- | --- | --- | --- |
| data.gov.au FY CSVs ("cn-parent-and-amendments") | FY2014-15..2019-20 | yes (Type column, Parent Contract ID, Amendment Date) | 31.0 MB / 4.2 s for FY17-18 |
| /Reports/CnAndAmendmentsDownload (any date window, anonymous GET) | any window incl. 2020-2026 | yes ('-A<n>' CN IDs, own publish date, per-query statistics block) | 0.72 MB / 36-43 s (1 month); 6.4 MB / ~50 s (12 months) |
| /Reports/CnWeeklyExportList (weekly XLSX, 18-month retention) | last ~18 months | yes (Parent CN ID, Amendment Publish Date columns) | 260 KB / week |
| OCDS registry per-year 2007-2026 | parents (compiled) | NO (measured negative: contracts[].amendments empty; amendments overwrite values) | 13.6-98 MB/year |
| AusTender /cn/search + reports | ad-hoc | interactive | search flaky per publisher's own banner |

The OCDS negative matters: it is the easy-looking bulk channel, and it cannot
carry the label. Labels come from notice rows.

## Licence (cheapest veto, checked first)

AusTender Terms of Use clause 5.1: all AusTender materials except Coat of Arms
and ATM material are CC BY 3.0 AU; clause 5.4 confirms only Approaches to Market
are excluded from the grant; clause 6.1 gives the attribution statement.
Contract notices are therefore class A. data.gov.au dataset licence "cc-by"
corroborates. Full quotes in record.json license_evidence.

## What is NOT settled (carried into next_action)

- Per-split-window exact row/positive counts (needs the multi-year harvest; the
  10.96% rate is one measured cohort month, not an era total).
- The 2020-2026 harvest via the report endpoint is slow per request (~40-50 s);
  construction should budget one worker job for it rather than many coordinator
  fetches.
- Publication-timestamp timezone (assumed Australia/Sydney).
- Whether amendment reasons should gate the target (value-change vs extension
  vs cancellation) — reason field is available; decided at construction with
  measured reason mix.
- Same-instant amendments (parent and '-A1' published in the same week, seen in
  the 2026-10-28 weekly file: CN4203477/CN4203477-A2) are excluded by the
  strict-inequality window; count them in-build.
