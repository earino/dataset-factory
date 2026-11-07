# Publication invariants and rule reconciliation

The operator selected the stricter rule on 2026-11-07: demonstrated label-blind
exact recovery is an unconditional new-release block. Scope, disclosure, row
isolation and purported waiver fields cannot clear it. The current factory
implementation goal authorises code shipping and private acceptance work; it does
not approve a dataset flip. Frozen published data, manifests and tags stay intact.

## Code boundary verified

The review correctly identified a gap. `factory.suitability.validate` checked
schema/evidence and refused demonstrated recovery for unrestricted batch access,
but allowed `retain_restricted` with `isolated_rows`. The current CPCB review is
an actual example. A coherent review is not the same as permission to publish.

`publication_check` now separately checks the current review's dataset, tag and
artifact version, requires its evidence, and refuses recovery, rebuild or retirement
decisions for new publication. Missing, stale, malformed, oversized or symlinked
reviews refuse. Package checks, manifest generation, GitHub publication preparation
and Hub package generation call it. Manifest generation checks before its first
write; the Hub check runs before writing its outgoing package.

The ordinary suitability command still validates truthful historical/blocked
records without pretending they are publishable. Use
`python3 scripts/check-suitability.py --publication <dataset>` for strict admission.
Exact frozen-manifest diagnostics can report historical recovery as a warning so
current editorial corrections remain possible; the strict command has no such
exception. A supplied `published: true`, waiver or unrelated frozen package cannot
borrow that exception. This does not discover every possible new recovery identity;
the battery and independent audit remain separate layers.

The current publication scripts do not themselves implement a visibility flip:
GitHub execution explicitly refuses its unimplemented upload path, and the Hub
tool creates only private repositories. Manual provider commands therefore remain
outside these code boundaries. Digest-bound approval records and a supported flip
path are a separate implementation item; no claim is made that this PR enforces
approvals for arbitrary shell/API calls.

## Descriptor hash gap reproduced

At review base `3866a8c0ae943ce6f658002c2a29c45c7446ed25`, the package checker
hashed `package_files` but only compared asset/checksum metadata for files absent
from that inventory. A synthetic regression changed `meta.json` and `quality.json`
while their old asset/files/SHA256SUMS records agreed and omitted each descriptor
from `package_files`. The historical checker returned no errors in both cases;
the R3 asset verifier refused both actual-byte mismatches, including external mode.

The compact reproduction receipt is
`audits/resilience/2026-11-07-publication-invariants.json`; the maintained regression
is in `tests/test_asset_integrity.py`. This establishes the code defect class, not
the exact October 28 EC-merger filesystem state. R3 already closed the gap; this
item adds the explicit descriptor regression rather than a second hash system.

## Contradictions resolved from existing instructions

| Wording found | Resolution and authority |
| --- | --- |
| OPERATIONS granted publication without a per-release yes while excluding private-to-public changes | The supplied AGENTS instructions and current release boundary require operator approval of the specific flip. The guide now states that once, followed by completion of the approved plan and anonymous verification. No historical approval is inferred. |
| Release skill allowed unreadable source terms after risk acceptance, while AGENTS and R4 require refusal | Current packaging refuses unreadable/conflicting evidence. Historical risk acceptances remain records, not publisher grants or new-package admission. Discovery and release wording now agree. |
| Candidate licence declarations were described as the generator's source after R4 introduced captured-source receipts | The declaration remains research history; new generated terms bind captured source text and the standing contribution policy. |
| An early budget section called wall-clock limits advisory and treated fresh lock age as ownership | Existing wrapper code enforces per-run time/turn limits and owns an OS mutex. Documentation now reflects that implementation. No budget, cadence or runtime setting changed. |

The old wording remains in Git history. No substantive rule was silently removed,
and no new operator approval or publication permission was manufactured. Website
publication continues to require its operator-reviewed plan as well as public,
verified data destinations.

## Inventory and remaining obligations

`docs/NORMATIVE-RULE-INVENTORY.md` preserves every matching normative source block
from AGENTS, OPERATIONS and the three versioned skills. Its reviewed map names
checks and tests for mechanically covered rules; broader statements remain
prose-only with partial coverage noted where identified. `--check` prevents the
inventory from silently drifting after a source edit.

Source truth, novelty, compatibility of upstream terms, causal prediction timing,
honest measurements, full consumer reproduction and avoidance of arbitrary manual
API bypasses are not proved by prose linting. The autonomous adversarial stage and
digest-bound operator approvals remain required work. The active remediation hold
continues until the specified real-artifact acceptance and operator decision.
