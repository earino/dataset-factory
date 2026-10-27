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

## 2026-10-28 session (regional tick: South & South-East Asia): coordinator block persists; worker probe prepared and plan-verified; launch refused by the release-work guard

    curl -m 20 https://data.gov.in     -> HTTP 000, 1.20 s (TCP refusal persists, as on 2026-10-20)
    curl -m 20 https://api.data.gov.in  -> HTTP 000, 1.20 s
    web_extract https://data.gov.in/   -> "An error occurred while processing your request.
        Reference #102.8e620317.1793115086.c3561897 ... errors.edgesuite.net" - an Akamai
        edge answer, i.e. the origin is UP and its edge refuses that particular fetch
        client. Not proof of geo-blocking vs client filtering; a worker curl with a normal
        UA may succeed.

Worker probe prepared this session (the recorded unpark step, exactly):
    candidates/india-datagovin-portal/probe/job.json  (id india-portal-probe-001, cx23,
    hel1, python:3.13-slim, timeout 10 min, lifetime 45 min, reservation EUR 0.04)
    candidates/india-datagovin-portal/probe/run.py   (bounded GETs: www/data.gov.in,
    api.data.gov.in, robots.txt, sitemap.xml, /catalogs, api catalog.json + vantage IP;
    writes /output/probe_report.json)
    sh scripts/scout-factory worker plan candidates/india-datagovin-portal/probe/job.json
    -> plan OK (reservation_eur 0.04, source_sha256 378f75b8..., cloud_calls 0)

    sh scripts/scout-factory worker launch .../probe/job.json
    -> REFUSED: "factory: Release work is pending for unhcr-refugee-data-finder; ship it
       before starting india-portal-probe-001"

The guard (factory/worker.py release_work_pending) blocks every non-release job while any
candidate is status=packaged and not awaiting_operator; unhcr-refugee-data-finder is
packaged and waiting on the factory, not on the operator. Shipping that release is
advancement work and outside this discovery session, so the launch was NOT retried or
bypassed. No worker was created; no spend occurred (plan is offline; cloud_calls 0).

## Next action (unchanged in substance, now one command)

After the pending release ships, run:
    sh scripts/scout-factory worker launch candidates/india-datagovin-portal/probe/job.json
    sh scripts/scout-factory worker status  india-portal-probe-001
    sh scripts/scout-factory worker collect  india-portal-probe-001
    sh scripts/scout-factory worker destroy  india-portal-probe-001
The same probe report also settles the cpcb-aqi-exceedance reopening evidence (reading the
GODL-India licence claim on api.data.gov.in from a reachable network) - see that record.
