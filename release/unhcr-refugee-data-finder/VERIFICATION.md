# Verification record

What was actually run, on which bytes, and what that does **not** cover. Every figure
below was read from a recorded artifact (gate report, baseline result, worker log),
not restated from memory.

## Bytes identity

The five shipped files are the worker-built artifact `unhcr-001`, gate-1.5.0 artifact
version
`6fa7becdf32925b74522c81001dcfe802b6a389425fd6deb4af4fc25ba7f1f53`
(sha256 over `public/train.csv`, `public/eval.csv`, `private/holdout.csv`,
`meta.json`, `quality.json`). The packaged tree was rebuilt from the private
staging release parts (tag `job-unhcr-001`) with every part's sha256 verified
on arrival before anything else was done.

## What was run

1. **Construction + qualification + acceptance (worker, 2026-10-27).** Worker job
   `unhcr-001` (server 172873699, cx23, 16.2 s, exit 0): fetched the pinned HDX
   distribution (8,669,567 B, sha256 `d5808616c3d1...`, byte-identical to the
   discovery pin), asserted all four known-event fixtures in-build (SYR->DEU 2015
   label 1, AFG->USA 2022 label 1, AFG->DEU 2022 label 0, UKR->POL below
   eligibility), built the corridor-year extract, then the full sequence
   `construct -> qualify -> --accept` with the gate shipped in
   `code/qualify_dataset.py`: gate 1.5.0 passed 45/45 checks on the **full**
   artifact where the rows are, executed the declared cross-row probe
   (`next_label_year_exposes_outcome`: coverage 2,439/1,265/1,239 rows across
   train/eval/holdout, 0 mismatches), and exact-byte acceptance printed
   `ACCEPTED ... 6fa7becdf32925b7` before any performance figure was computed.
   The construction stage computes no performance metric; the post-acceptance
   reference scores were computed only after acceptance by `code/score.py`
   (byte digest recorded in `MANIFEST.json`).
2. **Runner-contract baseline (worker, 2026-10-27).** Worker job
   `unhcr-baseline-001` (server 172877033, 49.8 s, exit 0, staging release
   425870998) fetched the five accepted files from the private staging release
   (digest-verified on arrival), re-ACCEPTed them through the gate against the
   same collected qualification report (`ACCEPTED: /data/extract matches the
   qualified artifact 6fa7becdf32925b7`), materialized a runner workdir
   (public train+eval only; the holdout was never copied), and ran the
   benchmark's own `train.py` and `validate.sh` **unmodified** - the three
   runner files' sha256 digests bundled into the job equal the digests recorded
   here in `baseline/` (`train.py` `a3c6bcf1...`, `validate.py` `b597e7f8...`,
   `validate.sh` `3f06ca48...`; the job's report records `verbatim: true`).
   Result: `CONTRACT OK`; train.py and validate.py both print
   **Eval AUC 0.5393**; an independent predict_proba recompute agrees
   (0.53935, Brier 0.085099). All references and paired comparisons in
   `RELEASE_NOTES.md` come from this job's `baseline_result.json`, computed on
   the identical 1,887 eval rows. The recomputed reference AUCs match the
   construction-run values to 6 decimal places; the job's 1e-9 agreement flag
   reads false only because the stored references are rounded to 6 dp - the
   agreement is real and is recorded here as measured, not as a pass.
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
- **Point-in-time availability of the HDX resource.** The publisher retains no
  historical vintages, so a reverse-history probe is not performable. The
  evaluation contract declares retrospective research over the pinned current
  snapshot with `access: isolated_rows`; the 232-day publication lag is an
  observed release fact (2026-08-20 refresh carrying complete 2025 data), not a
  guarantee for every row of every year.
- **Headroom over persistence.** The stock baseline trails both persistence
  references (0.5393 vs 0.5742 and 0.5856; paired differences -0.0348
  [-0.1056, +0.0409] and -0.0463 [-0.1103, +0.0144] - inconclusive, observed
  gaps negative). No claim is made that any particular model can or cannot beat
  persistence; the finding recorded is "no demonstrated headroom under this
  protocol with the stock model", and both numbers sit beside each other so
  neither is quoted alone.
- **Provider billing.** Worker reservations are conservative estimates (EUR 0.06
  reserved for each job); actual provider costs are estimates, not read-back
  invoices. Both workers were destroyed and the provider read-back returned 404.

## Where the raw evidence lives

The gate's own qualification report ships with this package as `qualification.json`
(gate 1.5.0, the exact checks and evidence the worker executed over the full
artifact). The factory repository (private during review) preserves the full
candidate record with probes at `candidates/unhcr-refugee-data-finder/`, the
baseline evidence at `candidates/unhcr-refugee-data-finder/baseline/`
(`baseline_result.json`, `container.log`, `references.json`, `summary.json`), and
the worker-written staging manifests for both jobs in
`earino/dataset-factory-staging` (releases `job-unhcr-001` tag `job-unhcr-001`
id 425843785, and `job-unhcr-baseline-001` id 425870998), which is where the
collected gate report, references and baseline logs remain durably downloadable.
