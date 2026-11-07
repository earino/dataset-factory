# Deterministic recovery battery and gate 1.6

The rule selected by the operator is unconditional: a feature-only algebraic or
shipped-fixture reconstruction with at least one eval/holdout prediction and zero
errors blocks new qualification. Retrospective scope, disclosure and restricted
runner access do not waive a demonstrated exact recovery. Statistical predictions
are not identities merely because a small subset happens to be correct.

## Construction and read-only audit

On the worker, after construction and before scoring or staging:

```sh
python3 /workspace/qualify_dataset.py /output/extract --record-battery \
  --battery-output /output/audit-vectors --report /output/qualification.json --json
python3 /workspace/qualify_dataset.py --accept /output/qualification.json /output/extract
```

`--record-battery` explicitly adds the computed aggregate receipt to `quality.json`.
Never use it on frozen published or historical audit inputs. A read-only run omits
that option and records the new findings externally; an old artifact lacking the
new receipt is not a newly qualified release. Historical comparison reports must
distinguish new-rule failures from their warning-only disposition for frozen releases.

The report and audit-vector directory must be outside the artifact. The vector
directory must be new. It contains feature-only predictions and full diagnostics
for worker-side audit; **never package or publish those vectors**. Collect only the
compact qualification/battery receipts. Preserve diagnostic hashes and worker
provenance. An incomplete run is a failed gate, not a negative leakage finding.

`assemble-job.py` automatically copies the canonical battery, recipe and scrubber
modules beside the gate. It refuses obsolete source scaffolds before provisioning.
Legacy job entrypoints must explicitly record the receipt before acceptance; merely
copying a newer gate does not manufacture the required construction evidence.

## Two phases and byte binding

The first phase reads all feature rows while excluding the target column from its
panel. It freezes blind vectors before reading even training labels. A second
archive holds train-only single/pair lookup controls and unanimous-donor predictions.
Eval and holdout labels are first accessed after both archives and every input file
are hashed. Scoring verifies them again, including individual vector hashes.

`quality.json`'s generated aggregate receipt is omitted only from the battery's own
input fingerprint, avoiding a circular hash. Qualification subsequently hashes the
complete descriptor, including that receipt, and every other generated file.
`--accept` rechecks the full file inventory, required gate results, code identities,
receipt equality and artifact hashes. Adding an answer file after qualification is
therefore a refusal even when all CSV hashes remain unchanged.

## Fixed audited identities

Recipes are activated by target/column contracts independently of builder-declared
probes. They use same-split and all-shipped-feature donor scopes separately.

| Family | Feature-only construction | Audit provenance |
| --- | --- | --- |
| NZ-EA | Same-island D+7 `last_day_mean`, compared with the audited NZD 100 threshold | `candidates/nz-ea-wholesale-price-exceedance/audits/2026-10-24-independent-codex-audit.md` |
| UNHCR | Corridor successor flag; next-year count or two-years-later lagged count versus twice current count | `audits/2026-10-28-unhcr-pre-flip-audit.md`, `audits/2026-11-01-queue-audit-codex.md` |
| NS-BWA | One added advisory and one resolution, no earlier active advisory; unique integer cumulative positives recovered from count × rounded rate, then subtracted | `audits/2026-11-01-queue-audit-codex.md` |
| OCHA | Country cumulative count/rate differences, isolated or homogeneous outcome groups, and the last-prior reverse link | `audits/2026-11-01-queue-audit-codex.md` |
| CPCB | Successor mean and lags, zero/last-exceed recency, rolling-count changes, count × rolling-mean differences with outgoing observation | `audits/2026-11-07-queue-audit-codex.md` |
| Wildfire/CQC | Literal shipped fixture tuples, or salt + fixture table; dated boundary comment where explicitly printed | `audits/2026-11-07-queue-audit-codex.md` |

These are finite, audited semantic contracts, not universal inference of a column's
meaning. New targets/units/rounding conventions need reviewed recipe extensions.
Duplicate or missing donor identities abstain. Cumulative-rate reconstruction
requires a unique integer inside the rounding interval. Rolling means abstain when
the rounding interval straddles the threshold. Conflicting rules abstain in the
union rather than letting iteration order decide an answer. All individual rules
remain reported. Builder-declared probes add coverage; they cannot disable the
automatic recipes or waive their findings.

## Exploratory controls and limits

Every column receives numeric, absolute, lexical, length and missingness probes.
The 80 most frequent feature-only words/bigrams per eligible text column are probed;
frequency ties are lexical and require ten appearances. Rank AUC above 0.95 in
either orientation is a warning. Train-donor single/pair rate tables and two-or-more
unanimous-donor coverage are recorded separately as supervised controls.

Schema-independent joins explore eight repeated identifier-like columns and their
pairs, eight history-like operands, and fixed 1/2/7/30/365/366-day offsets. The known
CQC five-field quasi-identifier combination is included. Missing-successor and
quasi-identifier survival probes are heuristics, not algebraic recovery proofs.
The audit records these finite bounds. More than 128 columns refuses inspection;
it does not silently truncate the input schema. Constant/uncovered vector counts
are retained, all evaluated results stay on the worker, and the compact receipt
retains all exact-rule results plus the top 40 warning flags and total flag count.

These checks do not prove absence of arbitrary encodings, semantic errors or unseen
attack families. The independent model audit remains required. Algorithm unit tests
and synthetic gate rehearsals are not A1/A2/A4 historical-artifact acceptance.

## Unit evidence without answer scaffolds

For an external threshold, `unit_validation` records positive `checks`, zero
`mismatches`, the source and `evidence_sha256` for the underlying validation evidence.
It is a counts-only construction receipt. Do not put scored identifiers, fixture
answers or salts in that receipt or in shipped code. The receipt is a declaration
whose source/measurement provenance remains auditable; the gate does not claim that
an arbitrary supplied hash independently proves the source semantics.

## Historical acceptance operation

`resilience-a1-small` is a four-case read-only worker bundle declared under
`candidates/nz-ea-wholesale-price-exceedance/resilience-a1/`. The candidate field
only anchors the existing job system; its cases cover NZ-EA, UNHCR, original
NS-BWA and original OCHA artifacts. Core hashes reconstruct each audited artifact
version. Original code is fetched from already-staged source archives and copied
only by explicitly named member and digest. It is never executed. Missing bytes,
changed hashes, reduced expected coverage or any error in the expected exact
recovery fails acceptance. No old package is repaired or requalified by this run.

The first assembled ID `resilience-a1-small-001` was superseded locally before
launch after a path-containment unit test exposed macOS `/tmp` ancestry handling.
It has no admission pin. The reviewed attempt is `resilience-a1-small-002`, pinned
in `config/admission.json`. The job uses one cx23, 3 GiB container memory, 90-minute
timeout, 120-minute lifetime and 20 MiB output cap. Scout must confirm the live
worker plan and allowance before launch; no allowance or policy limit is raised.

Scout is the sole launcher. Fetch the reviewed PR commit into the existing checkout
only with a clean working tree, assemble `resilience-a1-small`, verify the generated
source-bundle hash equals the policy pin, and use the existing worker plan/launch,
collect and destroy operations. This is acceptance of a draft gate under the hold,
not a claim that the gate is ready for ordinary construction. Return to the main
branch after the experiment, preserving the ledger and collected reports. Do not
launch a second attempt without a recorded diagnosis and separately reviewed pin.

Collect `acceptance-summary.json`, each case's `acceptance.json`, `qualification.json`,
`battery.json` and bounded `results-*.jsonl`. Their hashes bind all original inputs
and the new gate code. Full prediction vectors remain worker scratch and are
discarded at cleanup; they never become dataset release assets. A job success means
the specified historical defects were reproduced and refused, not that those old
artifacts passed qualification. A1's remaining cases and all A2/A4 work are separate.
