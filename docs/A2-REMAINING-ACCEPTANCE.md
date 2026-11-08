# Remaining published-artifact comparisons

All seventeen remaining A2 source bundles were reassembled offline on 2026-11-07 and matched their previously recorded pins byte-for-byte. They cover ninety configurations; the first eight comparisons are already recorded in `6171970`. This document is preparation, not a claim that these jobs ran.

A4 job `resilience-a4-blocked-004` is closed in `0cca3b2` with recorded provider absence and passing exact-commit CI. All 49 committed compact reports independently match the raw staging manifest. The exact seventeen pins below are now admitted for the remaining comparisons. Scout remains the only launcher. The hold stays true, and each job still passes the live allowance and concurrency checks. No new discovery, construction, package repairs or publication is authorized by these comparisons.

## Fixed order and limits

Use the order below. Each bundle has one fresh attempt, cpx32, four CPUs, 6 GiB container memory, a 120-minute execution limit and 180-minute lifetime. The existing maximum reservation is EUR 0.32 per job (EUR 5.44 for all seventeen), not measured billing or authority to exceed the current monthly allowance. Do not change the EUR 20 allowance or EUR 3 construction reserve.

| Bundle | Job | Configurations | Source SHA-256 | Bytes |
| --- | --- | ---: | --- | ---: |
| `resilience-a2-large-01` | `resilience-a2-large-01-001` | 1 | `597b1ee57c9ea7b81ca1ac576d53ac94a25d1e5d9cbc5e5a08b705b6eff1fcd9` | 266240 |
| `resilience-a2-large-02` | `resilience-a2-large-02-001` | 2 | `aa7959a655ef5bc5e32d5e28560008a7a513dc471b9b8b1d14d62383de204674` | 276480 |
| `resilience-a2-large-03` | `resilience-a2-large-03-001` | 2 | `504f11f652a38b23a3b2ea6264fceb423549c12b9866e311a1ab35efd2323d05` | 276480 |
| `resilience-a2-food-01` | `resilience-a2-food-01-001` | 8 | `45c75778f94e2cda4be1d8d6ac9e086129c55e124d959b4f19a8409428e93322` | 327680 |
| `resilience-a2-food-02` | `resilience-a2-food-02-001` | 8 | `53587e04e7b29404c75a1b020f564c17b3f824aa97ac656432cfd0ee330fbf14` | 327680 |
| `resilience-a2-food-03` | `resilience-a2-food-03-001` | 8 | `dfbcdc049091cd880c7cc6c4fa7b2dd2e8c9129938c2cb201513fdb187f5317a` | 327680 |
| `resilience-a2-food-04` | `resilience-a2-food-04-001` | 8 | `552cfa951a89be4fcb18a841c5e3094c7f2f6d123d50c55a8e31252f1e7a6774` | 327680 |
| `resilience-a2-food-05` | `resilience-a2-food-05-001` | 8 | `93354f6b2571d3d9ff90fe097432e23ba749a88b6f5c3f92e9511b6ea0a9cea2` | 327680 |
| `resilience-a2-msha-01` | `resilience-a2-msha-01-001` | 5 | `4eeeb31afc73fc6242d9ef60cc0e16f9ca5a77cbda0037e36fec33332f5fd7bc` | 307200 |
| `resilience-a2-msha-02` | `resilience-a2-msha-02-001` | 5 | `036a02bda2243fd92e7bc23e00cafee07c654f000c7536d7bf9c0594a28cf0ee` | 307200 |
| `resilience-a2-msha-03` | `resilience-a2-msha-03-001` | 5 | `fb04fc30f3c69ea0da7b0223e4e683112ac2768e1a39f05ab047e584a3a43ca6` | 307200 |
| `resilience-a2-msha-04` | `resilience-a2-msha-04-001` | 5 | `43e0ad1790e7bb528434caed227f0d859bdc5061e0be88841d51aed43badd23b` | 307200 |
| `resilience-a2-msha-05` | `resilience-a2-msha-05-001` | 5 | `31607b9895fc8a6709f08d3bd776cadc53ce3ec90cceb7d473d8f16d7adffe92` | 307200 |
| `resilience-a2-msha-06` | `resilience-a2-msha-06-001` | 5 | `2906b9cff9eea336623bcf67d13220014fbc443abdf7a53a423adbf5ab2d8aeb` | 307200 |
| `resilience-a2-msha-07` | `resilience-a2-msha-07-001` | 5 | `ddcc64ae6c8882e338ba20cf6797e524bf2b4b16f673d21a1d400220f3ac80d4` | 307200 |
| `resilience-a2-msha-08` | `resilience-a2-msha-08-001` | 5 | `8baceb3a64481cd98188820c4fcaa4e2f44d04aebb3be433c0fd501220a1b54a` | 307200 |
| `resilience-a2-msha-09` | `resilience-a2-msha-09-001` | 5 | `a96c9f7c4c15805b6c4daa8d1594d4b43adc49b3e1efc15322eb9451bcfa0d5a` | 307200 |

## One complete worker cycle at a time

For each row, use the existing assembler and worker commands:

```bash
python3 scripts/assemble-job.py BUNDLE
sh scripts/scout-factory worker plan .factory/jobs/JOB/job.json
sh scripts/scout-factory worker launch .factory/jobs/JOB/job.json
```

Before launch, compare the source hash and size to this table and require the live plan to pass. After execution, collect through the existing ledger, locate reports by logical path in the raw upload manifest, and verify every compact JSON report by size and SHA-256. Read the acceptance summary and each per-configuration acceptance/battery/qualification result. Preserve warnings and refusals honestly: successful comparison does not mean an old artifact passes every new gate.

Destroy the owned worker immediately after collection and prove its server and job-owned billable resources are absent. Commit the ledger, bounded reports, receipt, structured event and generated state; read CI for that exact commit. The next row starts only after that complete closeout. Use the existing watcher/reconciler for terminal bookkeeping, not repeated model-driven status sessions.

On infrastructure failure, incomplete comparison, changed input, unexpected exact-recovery failure, insufficient allowance or failed CI, stop the launch sequence and retain the diagnostics. No automatic retries or changed job IDs are authorized by this table. Continue independent code/evidence work while the specific failure is resolved.

## Evidence boundaries

Only workers fetch full dataset rows. PriceCatcher uses its declared bounded public-release fallback with size and digest checks; all other rows use the recorded private-staging fetches. Frozen documentation archives are nonexecuted evidence. Full-row prediction archives stay in worker scratch; compact aggregate results remain in private staging. Collect only bounded reports under 256 KiB each and keep the coordinator report total below 20 MiB.

None of these comparisons rewrites data, manifests, version tags or existing suitability. Their purpose is to measure the exact-recovery false-positive line across all 98 published core configurations. Any disposition of a known defect or lifting of the remediation hold remains a separate operator decision.
