# Verification record

What was actually run, on which bytes, and what that does **not** cover. Every figure
below was read from a recorded artifact (gate report, baseline result, worker log),
not restated from memory.

## Bytes identity

The five shipped files are the worker-built artifact `ec-merger-003`, gate-1.5.0
artifact version
`e5a98dfc9c05d0b087ed2dead21004fbbd972e415d2174469371a908bcaf90ad`
(sha256 over `public/train.csv`, `public/eval.csv`, `private/holdout.csv`,
`meta.json`, `quality.json`). The packaged tree was rebuilt from the private
staging release parts (tag `job-ec-merger-003`) with every part's sha256 verified
on arrival before anything else was done.

## What was run

1. **Construction + qualification + acceptance (worker, 2026-10-27).** Worker job
   `ec-merger-003` (server 172772422, cx23, 40.3 s, exit 0): fetched the
   publisher's daily register snapshot (42,034,960 B, sha256 `420411333e...`,
   last-modified 2026-10-27T01:23:54 GMT), built the extract, then the full
   sequence `construct -> qualify -> --accept` with the gate shipped in
   `code/qualify_dataset.py`: gate 1.5.0 passed 46/46 checks on the **full**
   artifact where the rows are, and exact-byte acceptance printed
   `ACCEPTED: /output/extract matches the qualified artifact e5a98dfc9c05d0b0`
   before any performance figure was computed. The construction stage computes
   no performance metric; the post-acceptance reference scores were computed only
   after acceptance by `code/score.py` (shipped in this release, byte
   digest recorded in `MANIFEST.json`; the paired-bootstrap recipe is
   `code/report.py`, same digest discipline).
2. **Runner-contract baseline (worker, 2026-10-27).** Worker job
   `ec-merger-baseline-001` (server 172773775, 78.5 s, exit 0) fetched the five
   accepted files from the private staging release (digest-verified on arrival),
   re-ACCEPTed them through the gate against the same collected qualification
   report (`ACCEPTED: ... e5a98dfc9c05d0b0`), materialized a runner workdir
   (public train+eval only; the holdout was never copied), and ran the
   benchmark's own `train.py` and `validate.sh` **unmodified** - the three
   runner files' sha256 digests bundled into the job equal the digests recorded
   here in `baseline/` (`train.py` `a3c6bcf1...`, `validate.py` `b597e7f8...`,
   `validate.sh` `3f06ca48...`; the job's report records `verbatim: true`).
   Result: `CONTRACT OK`; train.py and validate.py both print
   **Eval AUC 0.6973**; an independent predict_proba recompute agrees
   (0.69735, Brier 0.025343). All references and paired comparisons in
   `RELEASE_NOTES.md` come from this job's `baseline_result.json`, computed on
   the identical 1,770 eval rows.
3. **Local re-acceptance of the packaged bytes (coordinator, 2026-10-27).** The
   packaged tree re-verified through the same gate's `--accept` against the
   worker's collected qualification report, and `check-package.py` verified
   every document present and every manifest hash matching the bytes on disk.

## What was NOT covered

- **The agent harness loop.** Nothing here runs a coding agent on the task; the
  baseline is the runner contract only. No claim is made about agent performance;
  the benchmark's own score (holdout AUC) is not evaluated in this package.
- **The holdout.** It was never scored, never copied into any workdir, and is
  excluded from every figure above. Its bytes ship verbatim; evaluating it is the
  benchmark's job, once, on a frozen design.
- **Point-in-time availability of the register.** The publisher retains no
  historical vintages (bulk feed since 2025-03-18; older daily objects expire),
  so a reverse-history probe is not performable. The evaluation contract declares
  retrospective research over the pinned current snapshot; the current-vintage
  sector taxonomy is a stated limitation, not a verified as-of property.
  Exception: one fixture (M.4731 GOOGLE/DOUBLECLICK) cross-checks the register's
  sector coding against the OJ prior notice published at notification.
- **Headroom above the sector prior.** The stock baseline trails the required
  comparator (0.6973 vs 0.7679; paired difference -0.0706, 95% CI [-0.1558,
  +0.0168] - inconclusive, observed gap negative). No claim is made that any
  particular model can beat the prior; equally, one weak stock model does not
  establish that none can. Both numbers are recorded beside each other so no
  reader quotes either alone.
- **Provider billing.** Worker reservations are conservative estimates (EUR 0.04
  for ec-merger-003, EUR 0.06 for the baseline job); actual provider costs are
  estimates, not read back invoices.

## Where the raw evidence lives

The gate's own qualification report ships with this package as `qualification.json`
(gate 1.5.0, the exact checks and evidence the worker executed over the full
artifact). The factory repository (private during review) preserves the full
candidate record with probes at `candidates/ec-merger-phase2-opening/`, the
baseline evidence at `candidates/ec-merger-phase2-opening/baseline/`
(`baseline_result.json`, `expected_artifact.json`), and the worker-written
staging manifests for both jobs in `earino/dataset-factory-staging` (releases
`job-ec-merger-003`, `job-ec-merger-baseline-001`), which is where the
collected gate report, references and baseline logs remain durably downloadable.
