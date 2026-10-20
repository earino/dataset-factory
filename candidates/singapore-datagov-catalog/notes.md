# notes — singapore-datagov-catalog (opened 2026-10-20)

Verdict: PARK (decision point, not a dead source). Access and licence are the best
measured in this region; every event/series-grain task the catalog supports duplicates
a family the bench already carries, or is a mirror.

## Catalog enumeration (2026-10-20, anonymous, no key)

`GET https://api-production.data.gov.sg/v2/public/api/datasets?page=N` — page_limit
and query/search/searchTerms/keywords params are ignored server-side (identical 7,079
bytes for every variant, measured); pagination works via `page` only, fixed 10/page;
meta: totalRowCount 4664, pages 467. Script `.factory/sg_catalog.py` enumerated all
4,664 datasets in 467 requests; id+name extract (621,858 B) at `.factory/sg_catalog.json`
(scratch, not committed; deleted with the probe scripts after this session).

Keyword survey over all 4,664 names: rain 27, weather 33, temperature 22, wind 23,
psi 12, dengue 8, infectious 1, carpark 6, taxi 3, mrt 12, accident 8, complaint 1,
inspection 1, food 18, hawker 5, water 25, flood 2, resale 13, tender 1, crime 1,
fire 4. Most of the catalog is Singapore DOS aggregate tables.

## Row API (documented on each dataset view page; anonymous)

```
curl 'https://data.gov.sg/api/action/datastore_search?resource_id=d_ca168b2cb763640d72c4600a68f9909e&limit=2'
  -> HTTP 200, total=20,070; fields: epi_week, disease, no._of_cases; first record 2012-W01
     ("Weekly Infectious Disease Bulletin Cases"; ~29 diseases x ~690 epi-weeks)

curl 'https://data.gov.sg/api/action/datastore_search?resource_id=d_3b41598f74f1f11fc3430348fea51af5&limit=1'
  -> HTTP 200, total=7,044,646; fields: date, timestamp, update_timestamp, station_id,
     station_name, station_device_id, longitude, latitude, readings
     ("Historical Rainfall across Singapore (2021)"; one year => ~63M rows for 2016-2024)

curl 'https://data.gov.sg/api/3/action/site_status'  -> HTTP 404 {}  (legacy CKAN retired)
```

Dataset view page advertises: `curl --location https://data.gov.sg/api/action/datastore_search?resource_id=<id>`
(one id measured: d_ca168b2cb763640d72c4600a68f9909e).

## Licence

`https://data.gov.sg/open-data-licence` -> HTTP 200 (2026-10-20): datasets may be used
"commercially or non-commercially ("Use")" with a conspicuous attribution notice —
the Singapore Government Open Data Licence. Redistribution is not the blocker.

## Task families found, and why each was not taken forward

- Rainfall / PSI / temperature exceedance from station history — duplicates the
  own-history environmental-exceedance family (cpcb-aqi-exceedance GO,
  noaa-tide-flooding live, air4thai parked with the same duplication note); no
  publisher-defined threshold for daily station rainfall (ours would be arbitrary).
- Weekly Infectious Disease Bulletin exceedance — ~29 disease entities only, threshold
  ours not the publisher's, DrivenData DengAI is the ML-ready precedent for the family.
- HDB resale — Kaggle mirror (rejectable on the standing mirror rule alone).
- Carpark/taxi availability, Dengue Clusters, flood alerts — real-time/snapshot feeds,
  no archive; an archive would still be family (a)'s.
- SLA tender results — duplicates the tender-outcome family already live
  (chilecompra-tender-outcome).

## Unpark

Operator decision naming a family, or a quarterly catalog diff (re-run the
467-request enumeration, compare dataset ids) surfacing a new event-level register.
