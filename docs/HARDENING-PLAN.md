# Dataset Factory hardening

Started 2026-10-22 with the operator's expanded instruction to collaborate with Scout,
harden the working research system, and deploy verified improvements. Work remains
on branches and PRs; the earlier no-merge instruction remains in force pending an
explicit revision. Published release bytes and the qualification gate are protected.

## Work in progress

1. Canonical release interpretation and fail-closed writers (`refactor/release-schema`).
   Preserve per-config results, baseline provenance, unknowns, publication versus
   verification, and the disposition of withdrawn candidates. Add conformance and
   negative tests without weakening existing tests.
2. Operational correctness: test isolation, safe assembly ownership, consistent health
   states, and evidence-backed transitions. Prioritise actual defects with Scout.
3. Recovery and deployment: review Scout's current runtime handoff, exercise interruptions
   and retries, establish a bounded rollout/rollback, and verify the running revision.

## Coordination

Scout was contacted through the operator's Telegram on 2026-10-22. It confirmed Hermes
v0.22.2, upstream d923a5eb, and `/opt/data/dataset-factory` on main at beab726.
Requested a sanitised handoff PR on `ops/scout-runtime-handoff`: effective configuration,
skills, actual scheduler wrappers, external customisations, operational memory, successful
and interrupted workflows, and recommendations. Asked Scout to keep the live checkout on
main, avoid running workers from a second checkout, and make no operational changes yet.

## Baseline observations

- Python 3.13.1 clean-clone suite: 419 tests, OK, six environment-specific skips.
- Suite mutates Austin DESTINATIONS.json through the website reconciler; restored the
  test-generated change locally. Reproduced independently in a temporary clone.
- Existing dashboard reports unknown CI as failure while overview remains nominal.
- Existing release collector selects maximum per-level AUC and lists a dropped private
  NHS package under published artifacts.
- `assemble-job.py` recursively deletes an existing job directory without an ownership
  marker. The repository explicitly requires ownership-checked deletion.
- The manifest writer writes SHA256SUMS before it has completed validation.
- The NHS package's baseline report names a different artifact from its manifest.
  Historical evidence must remain visible without being represented as a measurement
  of the current artifact. Do not repair this by editing published bytes or inventing scores.

## Resume

Review the working diff, read Scout's Telegram response and fetch its handoff branch.
Finish and test the schema migration, then review the next hardening increment against
the deployed workflow. No workers, external publications, runtime changes, or merges have
been performed by the engineering assistant.
