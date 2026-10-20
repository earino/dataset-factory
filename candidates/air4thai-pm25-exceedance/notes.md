# air4thai-pm25-exceedance - probe evidence (2026-10-20)

## Access probes (measured from the coordinator)
    curl -L "https://envilink.go.th/dataset/air-quality-pm2point5"
       -> HTTP 403, Cloudflare challenge page (5,485 bytes, challenges.cloudflare.com in body)
    curl "https://air4thai.pcd.go.th/webV3/api/airquality?limit=5"  -> HTTP 000 (TLS failure)
    curl "http://air4thai.pcd.go.th/webV3/api/airquality?limit=5"  -> HTTP 301 (to https, which then fails)
    curl "https://air4thai.com/webV3/api/airquality?limit=5"       -> HTTP 000
    curl "https://api.data.gov.my/airquality"                      -> HTTP 404 (no such mirror)

## Catalog metadata (read via search snippet of the Envilink entry, 2026-10-20)
    - dataset: hourly average PM2.5 from Air4Thai automatic stations (AQM Thai database)
    - update frequency: hourly (1 h); access condition: Download
    - resources: JSON nationwide (65 downloads), XML nationwide (19), JSON Bangkok metro...
    - publisher's own history page: http://air4thai.pcd.go.th/webV3/#/History

## PCD service terms (read via search of a pcd.go.th PDF, 2026-04)
    Bulk air-quality data ("การให้บริการข้อมูล") is described as a per-case service:
    "จัดทาชุดข้อมูลตามที่ผู้รับบริการร้องขอ เป็นรายกรณี" (datasets prepared per requester,
    case by case), historically delivered on physical media after payment - i.e. the public
    web/app display is free, the bulk series is by request. No open licence statement found
    on anything fetchable; a third-party site's "reproduced with attribution" is not a
    publisher licence.

## Task-shape note
    This duplicates cpcb-aqi-exceedance (opened the same session) at one-country remove:
    station-level next-day PM2.5 exceedance. The bench does not need two same-shape
    air-quality tasks; reopening requires an explicit operator decision plus the access
    and licence blockers above resolved.
