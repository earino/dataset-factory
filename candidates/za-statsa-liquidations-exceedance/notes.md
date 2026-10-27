# za-statsa-liquidations-exceedance

Discovered 2026-10-27 (Africa-focus discovery session). Stats SA P0043.1 monthly
liquidations panel via the ISIbalo Data Portal.

## Access and challenge

- `curl -s -m 60 -o P0043_1p.json "https://isibaloweb.statssa.gov.za/data/ETS/Monthly/Liquidations%20and%20InsolvenciesP0043_1/P0043_1p.json"`
  -> HTTP 302 + 122-byte `<TITLE>Loading</TITLE>` page (Imperva JS challenge, `x-cdn: Imperva`).
  Not an absent page: a real browser passes it (verified via the supported browser; full JSON
  body retrieved as page text, 334,470 bytes, 47 series, months MO012000..MO122025).
- `curl ... "https://isibaloweb.statssa.gov.za/data/ETS/Monthly/Liquidations%20and%20InsolvenciesP0043_1/ASCII%20Liquidations.txt"`
  -> plain curl SOMETIMES gets the 302 challenge, sometimes a direct 200 (intermittent; a
  retry with cookie jar + full Chrome UA succeeded: 59,645 bytes HTTP in 1.87 s, content
  identical to the browser copy byte-for-byte, 15,087 numeric lines equal). Browser and
  plain-client retrieval both verified 2026-10-27; the raw ASCII file text is 43,994 chars.
- Per-issue PDFs `https://www.statssa.gov.za/publications/P00431/P00431<Month><Year>.pdf`
  download without the challenge (~470-500 KB). Directory listing is forbidden (403).
- Per-release vintage ZIPs `https://www.statssa.gov.za/timeseriesdata/Ascii/P0043.1%20Liquidations%20(YYYYMM).zip`:
  only the latest issue is kept. Probe of 17 older months (202607, 202604, 202601, 202512,
  202506, 202401, 202306, 202201, 202101, 202006, 201906, 201801, 201701, 201201, 200806,
  200501) -> all 404. 202608 -> 200, 10,551 B, entry `ASCII/ASCII Liquidations.txt`
  'Release: 2026 08', 320 months. Wayback CDX has NO snapshot of the ASCII series file.

## Panel probes (commands in this directory)

- `python3 probe_parse_panel.py` (run in
  /opt/data/cache/scratch/statsa-liq with `ASCII_Liquidations.txt` fetched as above):
  47 blocks, every block exactly 321 values, coverage 2000-01..2026-09, release stamp
  'Release: 2026 09'. Series inventory: LIQ00000 total; companies and close corporations
  x compulsory/voluntary x 9 named SIC industries + unclassified + group totals (40
  industry-level units when unclassified and group totals are excluded by H07 filter, 44
  when the four in-group totals are kept).
- `python3 probe_base_rates.py`: median-exceedance label (target month T = M+2, features
  <= M = T-2, trailing median of T-14..T-2... precisely: months M-11..M): train 2002-2016
  3,910 rows / 1,537 pos (39.3%), eval 2017-2020 992 / 426 (42.9%), holdout 2021-2026
  1,415 / 574 (40.6%). YoY-direction: 41.7% / 47.1% / 43.3%, 39-40 of 40 units with
  positives in every window. Positive months in every year 2001-2026. National total:
  51.6%.
- `python3 probe_revision_check.py`: February 2026 issue (Wayback web.archive.org/web/
  20260402112827, embargoed 25 Mar 2026, 'Preliminary', cover warns 'a revised time
  series is under development') Table 2 totals vs current Release-2026-09 vintage:
  73/74 months differ (2020-2026; only Apr 2020 = 0 unchanged), e.g. Feb 2026 135 -> 223,
  Nov 2023 144 -> 287. September 2023 issue (web.archive.org/web/20260711181608) Table 2
  2017-2019 columns vs current: 36/36 months differ downward (2017 total 1,868 -> 1,454).
  The August 2026 live issue (embargo 30 Sep 2026 14:30, sha256 323fb900...) Table 2
  matches the current vintage on all 80 months (2020-01..2026-08). -> the series was fully
  restated during 2026; PDF releases switched to the restated basis between the Feb 2026
  and Aug 2026 issues.
- `python3 probe_vintage_diff.py ASCII_202608.txt ASCII_Liquidations.txt`: consecutive
  release vintages within the restated basis: 15,040 overlapping values, 19 differ
  (0.13%), all in 2026-03/05/08, magnitudes +1..+7 (late registrations trickling into the
  recent tail).

## Timing observations (as-of evidence)

- Publication instants observed: Feb 2026 issue embargo 25 Mar 2026 14:30; Apr 2026
  published 27 May 2026 (catalogue PDF); Aug 2026 issue 'Embargoed until: 30 September
  2026 14:30' (PDF cover; publication page states 'Publication date & time: 30 September
  2026 @ 14:30'); Sep 2026 issue expected 28 Oct 2026 (stated in Aug issue), PDF still
  404 on 2026-10-27.
- Frame consequence (verified against those dates): the release for reference month M is
  published inside month M+1, so M+1 is partially elapsed at the instant -> target month
  is M+2. Dated example in record.json prediction_time, timezone Africa/Johannesburg.
- Pre-embargo caveat: the Isibalo bulk export already carried month 2026-09 values on
  2026-10-27 (one day before the announced embargo), HTTP Last-Modified 2026-10-16.
  Observation recorded, not treated as a first-availability bound.
- Cross-check vs publisher summary: Aug 2026 issue Table A Jan-Aug 2026 = 1,828 == panel
  sum (159+223+276+233+225+246+239+227). Tertiary blog post 'Economic wrap-up for July
  2026' states H1-2026 = 1,361 while also stating 1,299 voluntary + 132 compulsory
  (=1,431): the blog post is internally inconsistent; release PDF and panel agree.
- Known events verified in-panel: Apr 2020 = 0 (lockdown office closure; unchanged across
  vintages), Nov 2020 = 261 restated (272 old basis; backlog surge), Oct 2024 = 312.

## Licence (class B)

- Stats SA 'Copyright and disclaimer' (https://www.statssa.gov.za/?page_id=425, read
  2026-10-27): 'All Stats SA products are protected by copyright. Users may apply the
  information as they wish, provided that they acknowledge Stats SA as the source of the
  basic data wherever they process, apply, utilise, publish or distribute the data...' -
  redistribution of derived rows permitted with attribution.
- Release/publication notices add a no-sale clause ('neither the basic data nor any
  reprocessed version or application thereof may be sold or offered for sale...'). Our
  releases are free with attribution; conditions carried to LICENSE.md at construction.

## Novelty

- check-novelty.py recorded verdict `no_precedent` (2026-10-27T16:28:18Z, 2 queries,
  3 catalog sources). Nearest prior art is firm-level bankruptcy prediction (different
  population and target); no ML-ready SA aggregate liquidations task found. Web scan for
  HF/Kaggle SA datasets surfaced only National Treasury municipal-finance repackagings
  (electricsheepafrica), i.e. our existing za-municipal domain, not this series.

## Decision

Verdict `ready`. All five contracts evidenced (see record review field). The one design
risk carried to construction is the self-join exposure: a scored row's label operand
(count at its target month T) equals a feature value of the row whose target month is
T+2; construction must enforce the restricted prediction protocol (gate 1.5 probes) so no
solver-visible join couples scored rows.
