# ons-la-claimant-count-direction

Record dated evidence, decisions, and failed approaches here.

## 2026-10-21 discovery session (tick region: United Kingdom) - PARKED on task value

Publisher: Office for National Statistics (GB), probed via its main site and via
nomis (the ONS-hosted labour-market data service).

### Commands and measured results

- `curl https://api.beta.ons.gov.io/` and `/v1/datasets` -> HTTP 000 (TLS
  connection failure) from the coordinator. ons.gov.uk itself is reachable
  (`/api` answers 404 with the normal site shell). Recorded so no future session
  reads "ONS has no API" or "the API is down for everyone".
- `curl https://www.nomisweb.co.uk/api/v01/dataset/def.sdmx.json` -> HTTP 200,
  5,459,028 bytes, 1,617 keyfamilies. The documented `?search=claimant` forms
  all returned a 568-byte `keyfamilies: null` document (4 forms measured) -
  the search endpoint does not match these patterns; grep the full list locally.
- `python3 .factory/nomis_list.py` over the full list -> the current claimant
  dataset is NM_162_1 ("Claimant count by sex and age", annotation "Current
  (being actively updated)"); NM_2_1 and five other claimant datasets are
  annotated "Historical (not actively being updated)".
- Data queries (`NM_162_1.data.csv?...`): the dimension-parameter form returned
  HTTP 200 with 0 bytes for 6 measured combinations (sex/item/measures,
  gender/age/measure with geography=TYPE480 and country codes) - an empty-200
  is a wrong-parameter response, not absence. The minimal form works:
  `?geography=2092957697&date=latest` -> 163,239 bytes; latest month 2026-09
  (published by 2026-10-21, ~3-week lag); `&date=first` -> 1986-01 (489 months).
  UK claimants 2026-09: 1,702,905 (OBS_STATUS A, "Free (free for publication)").
- LA level: `?geography=TYPE480&date=latest` -> 1,936,993 bytes, 4,897 rows
  (all gender/age/measure breakdowns for ~360 local authority districts);
  TYPE464 (small areas) -> 11,311,202 bytes, 25,001 rows. Full LA panel across
  all months is ~40-60 MB - worker-scale.
- Licence: ONS site-wide footer (read 2026-10-21): "All content is available
  under the Open Government Licence v3.0, except where otherwise stated".

### Why parked (the assessment)

Access, licence, cadence and depth all pass: anonymous API, OGL v3, monthly,
current within ~3 weeks, 489 months x ~360 authorities. The blocker is the task
family: ONS publishes aggregate statistics only, so every candidate task is a
direction-forecast over an area's own published history (claimant count, CPI,
HPI, vacancies). That family is already served in ML-ready form by macro
forecasting benchmarks (M4/Monash carry UK monthly economic series with fixed
train/test splits), the differentiation claim is thin, and a
univariate-own-history task measures little about coding agents beyond fitting
a seasonal model. The ONS-held individual-level products (Understanding
Society, Secure Research Service, Census microdata) require registration and
do not permit redistribution - a licence/access veto for an open dataset.

Unpark question recorded in record.json next_action: an open, event/case-grain
ONS release, or an operator request for a macro direction task (in which case
compute base rates and seasonal-naive headroom first).
