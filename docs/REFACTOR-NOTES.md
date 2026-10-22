# Release schema normalisation

`factory/release_schema.py` is the read contract. `load_release()` reads existing bytes; it does
not qualify an artifact or authorise publication. `ReleaseShapeError` identifies the file and
field. Operational loads are strict. Diagnostic dashboard projections retain incomplete draft
facts with explicit errors; those errors are surfaced as alarms. Pure template compatibility
helpers accept decoded manifests through the same normaliser.

## Historical shapes

- Flat splits contain `rows` and sometimes `positives`. NOAA nests splits under `temporal` and
  `station_disjoint`; the typed split retains both config and split name. NOAA records rates,
  not positive counts: unknown counts remain unknown. No rounding/backfill is performed.
- MSHA declares 45 configs under `levels` but one shared split pool. Chicago food also shares a
  pool across 40 configs. Totals count the pool once; Hub loading configs still enumerate targets.
- An empty legacy manifest split map falls back to quality `split_stats`, count-valued quality
  `splits`, summary `splits`, then candidate `construction_output.splits`. Quality path maps are
  layout declarations, never counts. ABS motivated this fallback; its current manifest already
  has counts. A nonempty malformed map fails rather than being hidden by another source.
- Baselines record AUC in top-level, `contract`, `result`, or `artifact` objects, as numeric
  values or strings. Supported aliases are explicit in `AUC_KEYS`; unrelated nested numbers,
  superseded results and references are never selected as current evaluation results. Conflicting
  current aliases fail (rounding tolerance 0.00005).
- Chicago food's `summary.eval_auc_median` is 0.7208, **median of 40 configs**. Its corroborating
  single model is not the suite result. MSHA measured one config, `sec_56_12004` (0.8036); the scope
  says so rather than implying that all 45 were measured.
- NOAA has two evaluation AUCs, temporal 0.8633 and station-disjoint 0.8690. `Baseline.eval_auc`
  is absent for this shape, with both measured values in `per_config`. This deliberately extends
  the brief's scalar sketch: choosing the maximum, mean or median would invent an aggregate.
- NHS is a **private, dropped package**, not a tenth public release. Its 0.5511 result names a
  different accepted artifact. It remains visible as historical, is excluded from current scalar
  metrics, and is not promoted to a current baseline. Published records cannot carry that mismatch.
- Destination entries use `repo` (GitHub/Hub) or `url` (site). Older `publication.site` receipts
  can supply the site entry only if the primary destination map lacks it. Verification status,
  timestamp and URL come from recorded evidence. No site is invented for NHS.
- Artifact identity is the qualification digest, with matching top-level identity required when
  both are present. Multi-config packages already use a labelled composite of the individually
  gated config digests; that identity remains a derived label, never a new gate output.
- Licences pass through unchanged, including `NOASSERTION`, source attribution and scope.
  This layer does not grant rights or replace the existing class C operator-acceptance checks.

Explicit unknown baselines require `baseline: null` and a nonempty `baseline_reason`. All release
projections use `Release.baseline_display`; absent measurements are `not recorded`, or the recorded
reason. A reader accepting historical gate versions does not bypass the current gate's `--accept`.

## Writes and verification

The manifest command validates canonical fields before writing checksums or manifest; each file
is replaced atomically, manifest last. The pair is not a filesystem transaction: an interruption
between replaces leaves a package-check failure, not a silently accepted package. Already public
packages are validated and left byte-identical. Change their editorial material through the
versioned site process, not by regenerating the published manifest.

Destination updates merge evidence and use atomic replacement; malformed existing JSON is refused.
Site reconciliation now writes its destination record at the successful CLI publication boundary,
so fake-client unit tests cannot update a real package's verification timestamp.

The adapter referred to as `factory/site_hf.py` in the brief is actually `scripts/site-hf.py`.
CI discovers the new conformance tests with the normal suite, now explicitly on Python 3.13.
All existing tests and the qualification implementation remain unchanged.
