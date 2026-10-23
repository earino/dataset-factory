# hk-red-tide-sighting — discovery notes (2026-10-23, East Asia tick)

Verdict: **parked** on the timing contract. Licence, target obtainability and novelty are
settled; the label timestamp is undocumented and the publication lag is unbounded by the
evidence available. Reproduce with `probe_red_tide.py`.

## Lead

Prospective user: AFCD/mariculture operators and marine-park/beach managers deciding whether to
pre-emptively aerate rafts, move stock or issue beach advisories. Prediction: will a red tide
sighting be reported at a monitored fish culture zone / station in the next 7 days after a
weekly publication instant? Outcome: a reported sighting event. Useful prediction enables
precautionary aeration, harvest scheduling and advisory timing rather than after-the-fact
reporting.

New family for the bench: event-grain harmful-algal-bloom *occurrence onset*. The nearest bench
families are environmental threshold exceedance (cpcb-aqi, air4thai, noaa-tide) and event onset
(inpe-foco-municipal-onset), neither of which is an algal-bloom reporting process.

## Licence first

- DATA.GOV.HK Terms and Conditions of Use (`https://data.gov.hk/en/terms-and-conditions`, read
  2026-10-23): "You are allowed to browse, download, distribute, reproduce, hyperlink to, and
  print the Data for both commercial and non-commercial purposes on a free-of-charge basis on
  condition that:- ... you shall also give proper attribution to the Government, the Relevant
  Organisations and ..." → class B (attribution only).
- Package metadata `package_show?id=hk-afcd-afcdlist-red-tide-location`: `license_title=None`,
  `license_id=None`; the dataset page shows no separate licence field. No dataset-specific terms
  were found; the portal terms govern. No operator risk acceptance is being extended.

## Probe commands and results

```bash
# package enumeration (anonymous CKAN API)
curl -s 'https://data.gov.hk/en-data/api/3/action/package_list'
# -> 3,831 package names; keyword scan found no landslip/tree-failure incident dataset and no
#    red-tide package until the name list was scanned (search endpoint returns count 0 for terms
#    that exist, so list scanning was used).

# red tide event list
curl -s 'https://redtide.afcd.gov.hk/data/RTMS_ob_RTLE.csv'   # HTTP 200, 266,991 bytes
python3 candidates/hk-red-tide-sighting/probe_red_tide.py
# live rows 1931 distinct 1757 min 1975-08-06 max 2026-09-08
# years 52 non-zero years 1975-2026: 52
# locations 594
# group mix [('Dinoflagellates', 1324), ('Others', 368), ('Diatom', 239)]
# rows per sighting number [(1, 1615), (2, 111), (3, 30), (4, 1)]
# dissipation lag days: n 1930 min 0 median 3 max 65 negative 0
# split 1975 2010 1108 987 329
# split 2011 2018 488 446 236
# split 2019 2026 335 324 166

# vintages (Wayback CDX; exactly 4 captures total)
curl -s 'http://web.archive.org/cdx/search/cdx?url=redtide.afcd.gov.hk/data/RTMS_ob_RTLE.csv&output=json&fl=timestamp,digest,length&filter=statuscode:200'
# 2018-06-13, 2018-09-08, 2019-11-02, 2025-04-02
python3 candidates/hk-red-tide-sighting/probe_red_tide.py --vintages
# wayback 2019-11-02 rows 1647 min 1975-08-06 max 2019-05-31 (schema: Date, Species Group, Species,
#   Location, Latitude, Longitude, Coordinate System — no sighting number, no dissipation date)
# wayback 2025-04-02 rows 1887 max 2025-03-25
# 2019 rows <=2019-05-31 1647 absent from live 2
# live only 44 vintage only 0 common 1713
# common rows with dissipation changed 2
# new rows since 2025 vintage by year Counter({'2025': 32, '2026': 12})

# feature source (EPD historical marine water quality), 2024 file probed
curl -s 'https://cd.epic.epd.gov.hk/marinepsi/en/marinehistorical/marine-historical-2024-en.csv'
# HTTP 200, 618,074 bytes, 2,923 lines, 28 documented columns (WCZ, station, dates, depth, BOD,
# ammonia, chlorophyll-a, DO, E. coli, nitrate, orthophosphate, pH, salinity, temperature, turbidity...)

# publisher's data dictionary
curl -s 'https://www.afcd.gov.hk/data/Update_of_Red_Tide_Situation.pdf'   # 623,230 bytes
# Field table: "Date | Date." — the label column's meaning is not defined; the dictionary also
# predates the current schema (no Red Tide Sighting No., no Date of Dissipation).

# known-event fixture
# AFCD press release 2022-03-14 (pr2568.html) lists sightings on 2022-03-12/13 at Big Wave Bay,
# Rocky Bay, Middle Bay, South Bay, Repulse Bay, Deep Water Bay, Stanley Main, Chung Hom Kok,
# Tathong Channel to Lei Yue Mun incl. Tung Lung Chau FCZ, Victoria Harbour near Hung Hom,
# Southern waters incl. East Lamma Channel and Sheung Sze Mun.
# CSV rows 2022S0001-2022S0010 match those dates/locations with Noctiluca scintillans.
```

## The blocker (timing)

The label's event time is `Date of Report`, described by the publisher only as "Date." The only
publication-lag evidence is four Wayback captures plus one press release:

- 2022-03-14 release → sightings dated 2022-03-12/13: ~1-2 day lag at that event.
- 2025-04-02 vintage → latest record 2025-03-25: 8 day lag.
- 2019-11-02 vintage → latest record 2019-05-31: 155 day lag.

So the lag ranges from about one day to five months in observed evidence. A weekly instant and a
strictly-future 7-day target window therefore cannot be stated with a supported as-of bound.
Wayback cannot fix this: only 4 captures exist across 2018-2026. Seeding a weekly standing
collector is the only way to build a lag distribution.

## Secondary design issue (censoring)

AFCD documents the sampling design (weekly at 6 core fish culture zones, fortnightly at 5 more
plus 5 offshore stations, quarterly at the remaining 15 FCZs) but publishes no per-day monitoring
log. "No report" therefore conflates absence of a bloom with absence of observation. Restricting
the population to the 6 weekly-sampled core zones is the cheapest honest mitigation, and the
censoring must be stated in the dataset card.

## Regional scan evidence (East Asia tick)

- **Hong Kong**: 3,831 package names scanned. No landslip/tree-failure incident dataset (search
  endpoint returns count 0 for terms present in the list, so names were scanned). `hospital-hadata-ae-waiting-time`
  resolves to a current-snapshot JSON (`aedwtdata2-en.json`, 3,812 bytes, no history field) →
  would need a standing collector. `hk-epd-beachteam-beach-water-quality-grading` is an RSS
  current grade → same family as `ea-bathing-water-classification` (duplicate). Fire classification
  and road-accident files are annual aggregates. Red tide is the one event-grain, long-history,
  non-duplicate family found in Hong Kong.
- **Taiwan**: `data.gov.tw/api/v2/rest/dataset?q=...` returns HTTP 405 Method not allowed for GET
  on several path variants; the portal's bulk/export paths returned 404. Existing Taiwan
  candidates already cover reservoir storage (parked on history) and typhoon day closure
  (investigating, construction next action).
- **Japan (JMA)**: licence is clean (site complies with 公共データ利用規約 第1.0版) and access is
  anonymous, but the JSON status endpoints are current-only. `warning/506.json` (桜島) carries a
  single latest report (`reportDatetime` 2022-07-27, `lastCode` 15); `info/506.json` carries the
  latest 火山の状況に関する解説情報 (reportDatetime 2026-10-23T16:00+09:00, serial 095). The
  PULL-type XML page states the long feed carries "several days" only and blocks IPs above
  10 GB/day; `/data/` is 403. No anonymous historical alert-level archive was located in bounded
  probes, so a volcanic-alert-level transition task would be blocked on history — the same
  structural problem as Taiwan reservoir and HK A&E, not a reason to open a duplicate.
- The prior dropped `jma-typhoon-rapid-intensification` and parked `hk-datagov-portal` /
  `singapore-datagov-catalog` records were read first and not reopened: nothing found here
  addresses their recorded family-duplication blockers.
