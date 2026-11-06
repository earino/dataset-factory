#!/usr/bin/env python3
"""Prepend the 2026-11-07 session entry to STATE.md (close-out step)."""
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
STATE = ROOT / "STATE.md"

ENTRY = """## 2026-11-07 (00:0XZ) - scheduled advancement: ab-wildfire-ia-escape PACKAGED and the GitHub private-staging destination COMPLETED AND VERIFIED (runner-contract baseline abwildfire-baseline-002: eval AUC 0.9554 beats every pre-registered triad member -> HEADROOM DEMONSTRATED, construction-time logistic-vs-persistence INCONCLUSIVE kept beside it); release/ assembled, MANIFEST + check-package + suitability + suite green; repo earino/ab-wildfire-ia-escape private with release v2026.11 (437179999), 5/5 assets digest-equal; consumer job + Hub + packaged remain; nothing public, holdout sealed

Release work only (brief priority; the packaged cpcb-aqi-exceedance track still
awaits the operator's flip - a human wait, untouched). Two worker jobs, both
destroyed with provider 404 read-back (0 servers, 0 primary IPs); EUR 0.08
reserved total.

- RUNNER-CONTRACT BASELINE (the recorded evidence-order step the construction
  session had left to packaging; abwildfire-baseline-002, cx23 hel1, server
  174894664, 264.6 s, exit 0): re-accept of the five fetched assets against
  the gate's own collected report BEFORE any score; workdir materialized from
  the PUBLIC splits only (holdout fetched for --accept over the full artifact,
  never copied into a workdir); the benchmark's own train.py + validate.sh
  unmodified (bundled sha256 == runner_files.json); [validate] CONTRACT OK;
  both implementations print eval AUC 0.9554. The PRE-REGISTERED deciding
  check (baseline/report.py, day-cluster paired bootstrap, cluster =
  assessment_date, fixed-seed LCG): model 0.9554 beats persistence
  (assessment_hectares) 0.9096 by +0.0459 CI [+0.0154, +0.0871], the
  calendar/identity prior 0.7130 by +0.2428 CI [+0.1911, +0.2998], and the
  degenerate majority constant (model day-cluster AUC CI [0.9382, 0.9686]
  entirely above 0.5) -> HEADROOM DEMONSTRATED under the pre-registered rule,
  eval 2016-2020 only, holdout sealed. Supplementary: model sits +0.0348 above
  the construction-time logistic reference (0.9206) - both models, not a
  deciding member. The construction-time finding stays beside every number:
  the simple logistic's edge over persistence is INCONCLUSIVE (+0.0111,
  CI [-0.0292, +0.0514], interval contains zero) - a simple linear reference
  does not demonstrably beat the one-feature persistence rule; the stock runner
  does. score.py's triad re-ran byte-identically except the report-path field
  (deterministic bootstrap confirmed across independent executions). Reports
  fetched digest-verified to .factory/abwildfire-baseline-002/output/ and
  committed in candidates/ab-wildfire-ia-escape/baseline/.
- PACKAGING (dataset-release skill; commit 07521ee, CI green run 42312693644
  + one run pending at last check): release/ab-wildfire-ia-escape/ assembled
  by candidates/ab-wildfire-ia-escape/package/build_release_2026_11_07.py
  from digest-verified recorded bytes only (construction code equal to the
  abwildfire-build-001 bundle digests; byte-pinned meta.json/quality.json
  fetched digest-verified from staging 437132110; qualification.json = the gate
  report itself, 16697cd8; the canonical gate 1.5.0 4fab8a34; runner files
  verbatim; the publisher's data-dictionary transcript shipped). Documents
  GENERATED from the gate report, references report, build summary,
  baseline_result.json and license.json - the comparison ladder leads every
  document; one defect caught and fixed in-session: the check count was
  hardcoded 41 in the draft template and the gate report has 45 - now derived
  (@@NCHECKS@@). OGL-Alberta v2.2 attribution sentence carried verbatim;
  derived-not-official labelling throughout. license.json (class A) +
  release.json + baseline/expected_artifact.json written;
  record.construction_output.splits written from the gate's split_counts
  cross-checked against meta.json and baseline_result.json.
  release-manifest.py wrote MANIFEST + SHA256SUMS (5 files, 4.1 MB, baseline
  present, licenses generated from license.json); check-package rc=0 first
  pass; publish-dataset dry-run rc=0; get_dataset.py compiles; sh -n OK;
  no unreplaced token. suitability/ab-wildfire-ia-escape.json written in the
  same change (retain_restricted, cross_row_audit bounded_no_recovery with
  the measured probe coverage 1017/6/8795, 437/14/2791, 553/10/2620) -
  check-suitability 22 OK; check-candidate --all rc=0 (133); suite 723 OK.
- GITHUB PRIVATE STAGING (this session, after the packaging commit): private
  repo earino/ab-wildfire-ia-escape created (id 1448854079); 26 package files
  pushed as the initial commit d610ffe2; release v2026.11 (437179999) created
  non-draft at main; abwildfire-publish-001 (release-flagged transfer job,
  server 174897047, 10.1 s, EUR 0.04) copied the five accepted c2c8ceb5
  assets from staging 437132110 into 437179999 under flat names - 5/5
  transferred, failures [], every sha256 verified on arrival and server-side.
  Live authenticated read-back 23:38:39Z: repo private:true, tag v2026.11,
  exactly the five assets, every GitHub-reported digest equal to MANIFEST.json
  (meta aeb2ef92, train 575649d5, eval d099e4cb, holdout 53583f4d, quality
  331a4ceb); anonymous API read-back correctly 404s. DESTINATIONS.json github
  block written (files_verified as the logical path list, top-level
  artifact_version c2c8ceb5...); the consumer check is NOT in it yet because
  the consumer job has not run - it is appended when it does, never invented.
  Worker destroyed 23:38:14Z; provider read-back: server 174897047 -> 404,
  0 servers, 0 primary IPs.
- Hygiene: no release byte of any PUBLISHED package, no tag move, no
  destination visibility change; the holdout stays sealed; nothing public.
  candidates/fenz-incident-data/ left untracked for its owner.

Next action (a fresh session can carry it out; also in record.next_action):
finish private staging - (1) the fresh-consumer worker job on the released
bytes of 437179999 (cqc/cpcb consumer pattern): gate 1.5.0 re-run, exact-byte
--accept c2c8ceb5, get_dataset.py + sha256sum -c, baseline reproduce (both AUC
prints 0.9554, CONTRACT OK), references recomputed equal to measurements.json
(fixed-seed CIs reproduce exactly), then APPEND the consumer check to the
DESTINATIONS github block (merge, never replace); (2) hf-publish.py --plan,
--create --upload-small, the hf_publish worker job, --verify, --tag LAST, then
the DESTINATIONS huggingface block; (3) record -> packaged with packaged_at +
awaiting_operator TRUE only after the pre-flip adversarial audit prompt is
generated from the frozen manifest; then all checks + suite + CI for the
exact commit. The flip is the operator's single approval and waits for the
independent auditor's verdict unless waived; the cpcb flip also remains the
operator's.


"""

text = STATE.read_text()
STATE.write_text(ENTRY.replace("2026-11-07 (00:0XZ)", "2026-11-06 (23:40Z)") + text)
print("STATE.md entry prepended")
