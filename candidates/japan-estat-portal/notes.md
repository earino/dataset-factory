# japan-estat-portal

East Asia tick 2026-10-28. e-Stat is named in the tick brief; assessed and
dropped at triage before any expensive probing.

## Commands and results

- `GET https://www.e-stat.go.jp/api/api-info/api-guide` -> HTTP 200.
  Text captured: "API機能をご利用いただくには、政府統計の総合窓口(e-Stat)の
  ユーザ登録が必要ですので、最初に登録を行ってください" (API use requires
  e-Stat user registration first).
- `GET https://www.e-stat.go.jp/api/terms-of-use` -> HTTP 200.
  第2条（利用登録）1: "本機能は、利用登録をした利用者のみ利用することが
  できます" (only registered users may use the API). 第3条（アプリケーションID）:
  the Application ID is issued after registration.
- Wrong guesses recorded, not absent terms: `/terms` and
  `/help/main/help-riyou` -> HTTP 404.

## Decision

Dropped, two independent grounds:

1. Task level. e-Stat is by construction the aggregate statistical tables
   portal (政府統計の総合窓口). Its task shapes (monthly/annual panel
   exceedance) are covered bench families with live members:
   za-statsa-liquidations-exceedance (ready, ZA), who-flunet-activity-exceedance
   (published, CH), abs-visitor-arrivals-direction (published, AU). A second
   member of a covered family is an operator decision (air4thai,
   chilecompra precedents), not a discovery probe.
2. Access. The documented API is behind a free personal registration
   (quoted above), the same shape as the parked kr-kosis-kma-access record;
   the anonymous path is web-UI scraping, which the pipeline does not take.

No event-grain register was found on the portal; survey microdata is a
separate application process outside the portal.

## Reopen

Only if the operator (a) names a Japan monthly/annual panel family member
and provisions an e-Stat registration per the KOSIS precedent, or (b) e-Stat
publishes an event-grain register with an anonymous documented API.
