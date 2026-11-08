FR (source-000016) build-1 leakage hold (2026-11-08T23:05Z).

OPERATOR FINDING (Codex, reproducible): the hash-verified build-1
builder (90abe8066e34fa305dc1858fee90ec5e16635183343dd81053cb7ca5199c5177)
has a concrete leakage path beyond declarations: agency_state appends
row[TARGET] from all splits once windows mature. A bounded
holdout-only audit (217,991 B, no full dataset download) predicts 128
earlier holdout labels with ZERO mismatches using only later
agency/date/rate differences - after 2021 all pre-holdout windows are
closed, and when one holdout window matures, the rate-change sign
reveals its label. No AUC/benchmark score claimed.

HOLD EXECUTED: scout-factory-tick paused 2026-11-08T23:04:49Z at a
safe boundary. The build-2 declaration-repair worker
(rw-ba904118ba27-build-2) was ALREADY IN FLIGHT and is preserved to
finish and stage its result untouched - but with admissions paused,
no tick will collect it into evaluate/publish. This exact builder must
not publish after a declaration-only repair. Cleanup sweep remains
active; no live model children at pause time; source-17 waits on the
worker slot.

NEXT (operator): the reproducible finding feeds normal automatic
repair - a narrow known-code check plus clearer grouped-rate review
instructions; no manual candidate advance, no new review cascade.
Resume happens on the operator's tested fix; the staged build-2 result
is then collected under the corrected checks.
