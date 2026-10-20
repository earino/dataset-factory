# notes — indonesia-bps-webapi (opened 2026-10-20)

Verdict: REJECT on task grounds. Access is fine; no task can exist from aggregate tables.

## Probes (2026-10-20, anonymous curl)

```
curl https://webapi.bps.go.id/v1/
  -> HTTP 200, 55 bytes: {"title":"API Badan Pusat Statistik","version":"1.0.0"}  (1.29 s)

curl https://webapi.bps.go.id/v1/domain/type/0
curl https://webapi.bps.go.id/v1/domain/type/all/key/xyz
curl https://webapi.bps.go.id/v1/statictable/list/0/100/key/xyz
curl https://webapi.bps.go.id/v1/list-verbs ; /v1/domain ; /v1/press ; /swagger ; /developers/
  -> all HTTP 404 JSON router errors: {"status":"Error","message":"Please re-check your URL Request."}
     (the service is alive; the path contract is documented elsewhere)

curl https://dsp2.bps.go.id/
  -> curl: (6) Could not resolve host: dsp2.bps.go.id  (old DSP catalog host is gone)
```

Documentation located via web search: `webapi.bps.go.id/documentation` — "The BPS API
identifies user with key token. User can get the key token from API-Portal website ...
read about Publication, Press Release, ... static table and dynamic tables." Free
self-registration per BPS's PPID service catalogue (ppid.bps.go.id), which states the
Web API "provide[s] access to aggregate data and other publicly available information".

## Task assessment

The API's own documented surface is: domain lists, subject lists, static/dynamic
statistical tables — aggregate tabular statistics. No event-level or per-entity
outcome data, so no prediction task with a documented label can be built. The key
registration was not pursued because even with a key the content is aggregate.

## Licence

Not pursued past the PPID terms (free service): moot for a source with no task.
