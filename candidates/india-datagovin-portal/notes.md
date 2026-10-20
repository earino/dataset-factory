# notes — india-datagovin-portal (opened 2026-10-20)

Verdict: PARK (infrastructure blocker). The portal is unreachable from the coordinator network.

## Probes (all 2026-10-20, anonymous curl from the coordinator)

```
curl -sS -m 25 -A "<UA>" https://data.gov.in/
  -> curl: (7) Failed to connect to data.gov.in port 443 after 557 ms; HTTP 000, 0 bytes

curl -sS -m 25 -A "<UA>" https://api.data.gov.in/
  -> curl: (7) Failed to connect to api.data.gov.in port 443 after 663 ms; HTTP 000, 0 bytes
```

Corroboration: `candidates/cpcb-aqi-exceedance/record.json` (same day) records
api.data.gov.in resource endpoint `HTTP 000` "from the coordinator on two attempts";
`imd-station-observation-series` records the same class of failure for IMD's portals.
Connection refused within ~0.6 s — not a timeout — so this is a network-path/refusal,
not a slow host.

## Licence

Not read — no page could be fetched. Nothing is claimed about redistribution.

## Unpark question

Can a worker in another network region reach data.gov.in / api.data.gov.in, and does
the reachable catalog contain task families the bench lacks (its best-known family,
station air quality, is already covered by cpcb-aqi-exceedance)?
