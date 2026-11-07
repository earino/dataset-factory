# Read-only blocked-package acceptance

`resilience-a4-blocked` runs the current gates on the four original November 7
blocked packages. It does not rebuild or correct them. The declaration is under
`candidates/cpcb-aqi-exceedance/resilience-a4/`; the candidate name anchors the
existing job system and does not limit the four-case scope.

Each case contains every original manifest-listed code/document file, the original
manifest and all five assets. The independent audit's manifest identity is pinned;
all compact document bytes match that manifest. `prepare-blocked-audit.py` creates
deterministic, exclusively created archives without reading CSVs. Those archives
are in private draft staging release 437803069. Dataset rows transfer only from
their already-staged, size-and-digest-pinned assets to the worker.

`audit-blocked-package.py` never executes the historical builder, loader or runner.
It verifies the exact inventory before and after inspection. Each case uses a fresh
process and worker scratch. Eight stages independently record their outcomes:
qualification/battery, answer scrub, full-row claims, asset/loader integrity,
qualification admission, claims admission, source-licence admission and the complete
package checker. New reports remain outside the original artifact. Missing current
evidence is a refusal; a checker exception is incomplete inspection. Later stages
still run after a refusal so the operator receives the full defect inventory.

An experiment exit of zero means the observations completed. It never means the
package passed or may publish. `acceptance.json` records each stage's `completed`
and `ok` separately, immutable input hashes, implementation hashes, elapsed time
and peak memory. Compact reports are below 256 KiB each; diagnostic shards have an
8 MiB per-case ceiling. Full prediction vectors remain private worker scratch.
These are current-gate findings, not independent source reconstruction or a new
paired-interval measurement without the original row-aligned score evidence.

The R5 model audit is explicitly not run by this experiment. Original packages
missing licence captures fail admission; that refusal does not resolve their
source terms. The preserved Alberta and SINASC captures in the R4 evidence remain
separate real-source refusal checks. No disposition is chosen for the operator.

The declared job is one cpx32 attempt under the existing EUR 0.08/hour policy,
120-minute execution / 180-minute lifetime, at most EUR 0.32 reservation including
cleanup grace. It needs a reviewed exact source pin, current complete worker ledger,
passing CI, budget admission and zero active workers before Scout alone launches.
The admission hold, spending limits, frozen artifacts and public destinations stay
unchanged. Collect and reconcile cleanup before any next worker.
