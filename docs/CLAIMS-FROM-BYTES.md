# Package claims from bytes

New packages need `CLAIMS.json`, a worker-produced `claims-facts.json`, and exact
generated claim blocks in their documents. The verifier runs automatically in
`check-package.py` and before `release-manifest.py` writes either manifest or
checksums. A declaration without a matching computed receipt is a refusal.
Published packages keep their frozen bytes and receive exact-file historical
warnings; a published flag alone is not an exemption.

The worker measures every shipped row after exact-artifact qualification. Automatic
checks cannot be disabled by the declaration: row/positive counts, positive rates,
declared identifier uniqueness or explicitly declared repeated entity identifiers,
numeric ranges, bounded observed domains, year values and named min/max invariants.
Metadata population claims are compared with those measurements. Literal Python
prose is inspected without executing package code, including stale scorer notes.
Dictionary bin and prevalence patterns, reversed edge-over intervals and unsupported
scoring guarantees are checked independently of the registered claims.

## Construction and packaging

Keep count-only `summary.json` inside the artifact before qualification if packaging
will quote it. Its digest must appear in the qualification inventory. Neither a
summary nor a source definition is a substitute for source reconstruction.

Declare each quantitative statement under a stable ID. Supported kinds are
`population`, `domain`, `years`, `grain`, `summary_value`, `source_definition` and
`paired_interval`. For example:

```json
{
  "version": 1,
  "claims": [
    {"id": "eval-population", "kind": "population", "split": "eval"},
    {"id": "eval-years", "kind": "years", "split": "eval", "column": "date", "expected": [2024]},
    {"id": "eval-grain", "kind": "grain", "split": "eval", "columns": ["station", "date"], "unique": true},
    {"id": "excluded", "kind": "summary_value", "pointer": "/excluded/burn_in", "expected": 1230}
  ]
}
```

Those example values illustrate the schema; they are not measurements from a
dataset. Domain claims may declare an `expected` string list and year claims an
`expected` integer list. Grain claims assert `unique: true` or `false`; both are
checked. Summary assertions name an exact JSON pointer and expected scalar.
Source definitions address only timing, target/task or external-threshold fields
in `quality.json`, are labelled as construction declarations, and cannot carry
population-result prose. Their source semantics still require independent audit.

On the worker, after the full gate and acceptance:

```sh
python3 scripts/check-claims.py /output/package --measure \
  --qualification /output/package/qualification.json \
  --evidence-dir /data/scorer-evidence --output /output/claims-facts.json
```

Copy that compact report into the proposed package as `claims-facts.json`. Render
each claim using `factory.claim_contract.render(claim, facts)` and insert its exact
output between these markers in at least one release document:

```text
<!-- FACTORY-CLAIM eval-population -->
<exact renderer output>
<!-- /FACTORY-CLAIM -->
```

The checker compares every block exactly. Numeric prose and uniqueness assertions
outside these blocks refuse new packaging. URLs, fenced command/example blocks,
inline code identifiers, numbered-list markers, card frontmatter and release tags
are syntax exclusions, not quantitative evidence. The answer-artifact scrubber
still inspects those files, and the independent auditor must check that exemptions
are not used to hide factual claims. Unknown semantic assertions are not mechanically
proved by passing the pattern checks.

`check-claims.py <package>` verifies the receipt, exact qualification binding, all
measurement inputs, implementation hashes, declaration, generated blocks and
automatic checks. `--external-assets` checks missing CSV digests against the manifest
without claiming to have read them; every present file must still hash correctly.
The package verifier additionally checks complete asset/checksum/loader agreement.

## Paired intervals

A `paired_interval` claim supplies an `evidence` object with `file`, `sha256`,
`split`, `left`, `right`, `cluster_columns`, optional `resamples` (default 1000,
range 100–5000) and integer `seed` (default zero). The evidence CSV contains the
accepted ID columns and target plus the two score columns. It must cover every
accepted split row exactly once, with identical labels. Cluster fields come from
the accepted artifact, never from scorer-supplied identifiers. Full evidence stays
on the worker/private audit staging; only the bounded interval receipt is packaged.

The verifier recomputes tie-aware AUC and paired cluster bootstrap percentiles.
All rendered comparisons explicitly name **left minus right**. Reversing the
comparison reverses the point estimate and interval endpoints. An interval
containing zero is inconclusive; it is not evidence of equivalence. Degenerate
inputs or excessive single-class resamples refuse the claim.

## Historical acceptance and limits

Use `--measure --historical --qualification <current-gate-report> --output <outside-path>`
for read-only inspection of original audited bytes. The report is explicitly
historical-only and cannot clear a new release. Never insert a new receipt, edit a
blocked package or rebuild data in this mode. Static diagnostics are not full-row
acceptance: A3/A4 still need the pinned worker artifacts and recorded outcomes.

The implementation uses the standard library. Domain inventories stop at 128
distinct values; a complete-domain assertion beyond that bound refuses, while
numeric summaries still cover all rows. Reports over 256 KiB refuse collection
rather than silently dropping evidence. There is no general proof of arbitrary
code semantics, licensing, causal availability or all possible natural-language
claims. Those remain explicit responsibilities of the independent auditor.
