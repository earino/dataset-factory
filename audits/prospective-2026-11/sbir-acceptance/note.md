# SBIR acceptance evidence (source-000072 / sbir-phase1-to-phase2-conversion)

Read-only export for Eduardo's paper analysis. No judgment was rerun, no consumer result was used,
and no production state, evaluated release, candidate, attempt or acceptance rule was changed.

## Contents

- `evaluate-1/` — the saved acceptance evidence for `rw-9f58fbd0fa13-evaluate-1`:
  `prompt.txt` (exact input bytes), `response.json` / `response.txt` (exact saved response),
  `usage.json` (recorded route and token counts), `attempt.json` (invocation metadata and the
  session snapshot list), `transcript.json` (derived from state.db: 4 messages including the single
  `web_extract` tool call, its 11,406-char result and the final response).
- `candidate-descriptors.json` — task/source description histories, construction notes and access
  recipe, publication record and saved review, extracted from `candidates.data`.
- `build-3/` — exact `response.json` (build_py + quality), exact `usage.json` and `attempt.json`,
  plus `quality.json`, a compact extract of the check reports (measurements, splits, timing,
  feature evidence, evaluation contract).
- `deployed-code.json` — code commit live during the attempt (`202b83b`) with the deployment basis.
- `maintenance-inventory.json` — bounded inventory of maintenance/configuration changes since
  `2026-11-12T21:27:59.319944Z`, split into service administration and manual dataset/source/
  label/acceptance changes (the latter: none).
- `manifest.json` — sha256 source/copy hashes, byte counts, derivation notes and credential scan.

## Integrity

Original files are byte-identical copies (sha256 verified before/after). No credential-shaped
strings were found; redactions: none. Bulk artifacts (public evidence manifest, release assets)
are not duplicated here.
