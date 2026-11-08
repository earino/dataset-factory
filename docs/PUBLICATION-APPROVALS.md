# Digest-bound publication approvals

A passing internal audit makes a candidate ready for independent review. It does not
make a repository public. Publication needs the operator-relayed independent verdict
and the operator's explicit approval of a concrete plan for both destinations.

The supported visibility path is shared by these commands:

```bash
python3 scripts/publish-dataset.py DATASET --flip-plan
python3 scripts/hf-publish.py --candidate DATASET --flip-plan
python3 scripts/check-approvals.py --candidate DATASET
python3 scripts/publish-dataset.py DATASET --flip
# Equivalent entry point, not a second destination-specific action:
python3 scripts/hf-publish.py --candidate DATASET --flip
```

Planning performs current local checks and prints `plan` plus `plan_sha256`. It
requires the R5 autonomous receipt and the independent review described below. It
changes nothing. The flip uses the shared factory GitHub and Hugging Face write
credential mechanisms; no inference credential is read or changed. It creates no
repository, moves no bulk data and changes no tag, manifest or artifact file.
Legacy `publish-dataset.py --execute` still cannot transfer data from this host.

## Independent review record

Save the operator-relayed independent report and the relay evidence as bounded local
text files. Record `candidates/DATASET/independent-audit.json` with exactly:

- `schema_version: 1`, `dataset`, `artifact_version`, `manifest_sha256`, and
  `binding_digest` from the current autonomous audit binding;
- `verdict: "pass"`, `unresolved_findings: []`, and `conditions: []`;
- `auditor` and timezone-aware `reviewed_at`;
- `report` and `operator_relay`, each `{ "path": ..., "sha256": ..., "quote": ... }`.
  Paths are repository-relative, hashes identify the actual text files, and quotes
  must appear verbatim in those files.

Unresolved conditions require corrections and a current review of the corrected
bytes. Merely relaying a conditional verdict cannot approve an unreviewed change.
The independent auditor is separate from the build/staging/internal-audit sessions.
A recorded pass is an evidence claim, not a cryptographic proof of independence.

## Approval record

Present the complete plan and its hash to the operator. Preserve the response with
that presented hash in a repository evidence file. Drafts may leave unknown values
null and use `decision: "draft"`; drafts deliberately fail the validator. Only after
an actual approval, record `candidates/DATASET/approval.json` with exactly:

- `schema_version: 1`, `kind: "publication_approval"`;
- `dataset`, `release_tag`, `artifact_version`, `manifest_sha256`, `plan_sha256`,
  and `independent_review_sha256` from the reviewed plan;
- `decision: "approve_both_public"`, `waived_rules: []`;
- `operator`, timezone-aware `approved_at`, and the verbatim `operator_words`;
- `source: { "path": ..., "sha256": ..., "quote": ... }`, where `quote` is exactly
  `operator_words`, and the source also contains the presented plan hash.

The timestamp must follow the independent review. There is no waiver route for a
known recovery, unreadable licence, failed mechanical gate or unresolved finding.
A plan, an agent's statement that approval exists, a Git author, a broad standing
instruction, and the instruction to repair the factory are not dataset approval.
The files cannot authenticate who spoke; recording actual operator words and their
provenance remains the recorder's responsibility. Do not invent or paraphrase them.

## Execution and interrupted publication

The command checks current package gates, the autonomous receipt, independent review,
operator evidence, destination identities and implementation hashes before mutation.
Both remote tags and default branches must still name the reviewed commits. GitHub
asset sizes/digests and manifest/package documents are rechecked; Hub assets use LFS
SHA-256 or the existing pinned worker receipt, with only bounded metadata downloads.
Missing bulk digest evidence refuses instead of downloading a dataset locally.

`publication-attempt.json` is durable intent written before the first visibility call.
A per-dataset lock prevents two flip commands racing, without blocking worker cleanup.
If one provider fails, the command preserves the intent and leaves the local
`DESTINATIONS.json` unchanged. Correct the provider issue and rerun the same command;
it verifies the same approval and current bytes and only flips a still-private target.
Changed approval, code, data or review evidence requires reconciliation, not a retry
with a silently different plan. There is no automatic retry loop or rollback to private.

Success requires new anonymous clients, both public repositories, unchanged tag/main
commits, all asset digests, and one-byte ranged access to every asset at the version
tag. Tokens, cookies and cached Hub credentials are excluded from anonymous reads.
Only then does `DESTINATIONS.json` record public visibility and anonymous proof.
The attempt receipt also supports recovery from a crash between that local write and
the final completed marker. No data bytes or frozen manifests change.

The result is verified data visibility, not the entire editorial/site release. Refresh
current card, LOADING, README and release notes separately, keep the frozen tag intact,
and prepare the website plan for operator review using the existing website procedure.
After editorial changes advance a branch, use ordinary release verification rather
than replaying the original flip plan.

## Historical approvals

`candidates/*/approval-history/*.json` indexes all fourteen already-public frozen
identities. `audits/resilience/2026-11-07-approval-history/source-records.json` preserves
compact excerpts of the original publication fields; archive citations preserve exact
recorded words where found. These records do not authenticate the historical narrative.

Five entries preserve recorded quotes, including MSHA's later reported ratification.
Six have reported authorization or an operator-relayed audit without verbatim approval;
three explicitly retain gaps. No contemporaneous digest-bound approval is fabricated.
The MSHA entry distinguishes the 2026-10-19 publication from the narrative's interpretation
of the 2026-10-20 “Fine” as ratification. Historical interpretations of waivers grant no
current permission. Every historical entry has `authorizes_new_publication: false`.

```bash
python3 scripts/check-approvals.py --history
```

CI checks the complete historical registry, immutable source hashes and exact quotations.
Tests cover missing/stale approvals, unconditional recovery refusal, both command entry
points, anonymous read bounds, remote drift and interrupted two-platform publication.
They use fake providers; no real visibility change is part of factory remediation.

Provider interfaces: [GitHub repository update](https://docs.github.com/en/rest/repos/repos#update-a-repository)
and [Hub visibility](https://huggingface.co/docs/huggingface_hub/guides/repository#change-repository-settings).
