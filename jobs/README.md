# Job records

The worker CLI stores compact JSON records here before creating any paid server.
Include job/candidate ID, code revision, container identity, provider resource IDs,
creation and expiration times, resource limits, cost reservation, current status,
result/artifact references, and confirmed cleanup time.

Never include credentials, raw data, or unbounded logs. Keep records across agent
sessions and use them when reconciling interrupted work.

Commit and push these records after lifecycle changes. Do not delete old records:
their cost reservations count against the monthly allowance even after cleanup.
Only one coordinator checkout may launch workers with this ledger.
