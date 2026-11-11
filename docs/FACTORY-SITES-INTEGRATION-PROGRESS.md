# Sites integration progress

Implementation authorized by Eduardo on 2026-11-11. Scope and completion criteria:
[FACTORY-SITES-INTEGRATION.md](FACTORY-SITES-INTEGRATION.md), S1–S8.

## Current work

- Added `factory/site_modern.py`: the modern manifest/receipt adapter supplies the
  existing renderer record. It reads measured baseline results only from compact
  metadata whose bytes and hashes match the pinned manifest, preserves nested Hub
  paths and actual release asset names, and derives prose from the accepted task.
- Modern pages use the released documentation paths and evaluation scope. No CSS,
  layout or navigation design changed. Real pinned UCMR metadata (43 KiB) is retained
  as the regression fixture; no dataset rows were downloaded.
- The 35 focused site/state/legacy lifecycle tests pass. The previous state-reader
  commit `29ed4f1` passed Linux CI. A full clean macOS run had 16 platform errors
  including Linux-only `os.waitid`; focused state tests passed in that clean clone.
- Added `factory/site_state.py`: a consistent read-only SQLite reader and a compact
  public projection. Missing/corrupt state is unavailable, not an empty factory.
  Candidate data and attempt diagnostics are not serialized into the public view.
- Added receipt identity checks for both anonymous consumers, artifact, version,
  repositories and row counts. These reuse existing evidence; they do not change
  dataset acceptance or candidate state.
- Four focused tests pass for absent/corrupt inputs, private-field exclusion,
  running attempts and mismatched consumer evidence.
- Asked Scout in the main Telegram session to capture fresh compact deployed
  evidence on `scout/sites-integration-inventory`. A preceding `/btw` answer was
  explicitly based on the 10:10 UTC readback and had no tools; it is not a fresh
  deployment observation. Scout remains the sole worker-launching coordinator.

## Next actions

1. Use the fresh deployed records to implement the modern site-model adapter and
   connect modern candidates/releases to the existing dashboard collectors.
2. Adapt schema-aware destination checks and editorial navigation without changing
   frozen modern manifests or tags. Add standing-policy publication and bounded
   site reconciliation to the existing hourly entry point.
3. Verify clean-checkout tests and exact-commit CI, deploy with Scout, backfill,
   inspect live desktop/mobile pages, and observe scheduled recovery/no-op passes.

No site code has been deployed. S1–S8 remain unproven. The existing untracked
`docs/.FACTORY-SITES-INTEGRATION.md.swp` has been left untouched.
