# Verification

What was verified, on what, and by which command. Nothing here is asserted from memory: each line
names the evidence.

| what | how | result |
| --- | --- | --- |
| Artifact qualified | `python3 code/qualify_dataset.py ./task/temporal` and `.../station_disjoint`, on the worker (job `noaa-003`) | **PASSED - 32 checks per level, 0 failed** |
| Panel completeness | `code/build.py` coverage gate, recorded in `output/build_summary.json` | **122/122 stations, 2,440/2,440 station-years, 0 errors** |
| Report describes the uploaded bytes | gate report digests vs the staging release manifest, all ten files | **10/10 match** |
| Baseline | `sh baseline/reproduce_baseline.sh ./task both`, runner files copied verbatim | temporal **0.8638**, station_disjoint **0.8688**, `CONTRACT OK` both |
| Persistence floor | `code/persistence_baseline.py --fetch` | **0.8265** and **0.8454**, no training |
| Package consistency | `python3 scripts/check-package.py release/noaa-tide-flooding` | see `MANIFEST.json`; run as part of this release |
| CI for the construction commit | GitHub Actions run for the pushed SHA | recorded in `STATE.md` |

## What this verification does **not** cover

- **Consumer verification is pending.** A clean-room check - download from the destination with no
  access to the building repository, verify `SHA256SUMS`, re-run the gate, reproduce the baseline -
  is part of this release and had not been run when this document was written. It must pass before
  the package is reported ready for review, and the result belongs here.
- **The holdout was never scored.** No model selection, threshold choice or tuning used it. It ships
  labelled, as a reported result, not as a hidden test set.
- **No agent or harness comparison.** The baseline is one pass through the training and validation
  contract; nothing about coding-agent performance is measured or implied.
- **Dependency versions of the baseline run are missing.** That job's report recorded the runner's
  output but not the installed package versions; the generator has since been corrected for future
  runs. The runner's own printed output is the recorded evidence.
- **The 6-minute raw series was not re-derived.** The build uses NOAA's verified daily maxima and
  their own daily flood flags. Re-deriving the panel from raw observations is possible but is not
  part of this verification, and the label route was separately checked against NOAA's own counts
  (`code/label_route_check.py`).
- **The datum trap was measured, not assumed.** Comparing MLLW-referenced heights to `nos_minor`
  silently yields zero positives; `code/datum_check.py` records the regression that shows it, which
  is why `datum=STND` is a requirement rather than a note.
