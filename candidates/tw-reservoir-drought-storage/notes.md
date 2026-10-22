# tw-reservoir-drought-storage

**Verdict: park (2026-10-22) - no anonymous historical series; current-day snapshots only.**

## The task (well-posed, blocked on data history)

Predict drought-onset: storage ratio of a major reservoir (石門/曾文/德基/南化/烏山頭...)
crosses below 20-30% within 30 days, from snapshots up to the 07:00 observation instant.
Persistence cannot win the onset formulation by construction. Positives cluster in drought
years (2021 桃園-新竹, 2024南部), so clustered counts must be reported by drought episode.

## Probe evidence (2026-10-22; commands in probe_fhy_reservoir.py)

| Probe | Result |
|---|---|
| data.gov.tw 45501 page (browser) | ODDL 1.0, free; fields documented; 更新頻率 每1時; note: history -> fhyv2 viewer |
| fhyv2 SPA resource capture | API family /Api/v2/* + /disaster/Reservoir/Comparison |
| GET /Api/v2/Event/Year/2025, /Api/v2/Event/Active (plain client) | HTTP 401 |
| GET /disaster/Reservoir/Comparison (plain client) | AngularJS HTML shell (4,252 B), not JSON |
| opendata.wra.gov.tw swagger | unreachable: strict-SSL failure + intermittent DNS |
| WraBigData/WraApi legacy endpoints | 404/503 |

## Licence

ODDL 1.0 on the datasets (class B, attribution). Not the blocker.
